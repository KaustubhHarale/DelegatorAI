import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date
import os
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import APIError
from pydantic import BaseModel, ConfigDict, Field

from agent import COORDINATOR_SYSTEM_PROMPT, OpenAICompatibleProvider
from config import get_slack_settings
from database import (
    add_task,
    claim_slack_event,
    complete_slack_event,
    connect,
    enqueue_slack_event,
    fail_slack_event,
    get_task,
    init_db,
    list_participants,
    list_task_history,
    list_tasks,
    store_slack_event_response,
)
from models import Participant, Task, TaskPriority, TaskStatus
from task_tools import (
    InvalidStatusTransitionError,
    TaskNotFoundError,
    update_task_from_dashboard,
)
from slack_bot import (
    SlackApiError,
    SlackClient,
    SlackRateLimitError,
    SlackReply,
    process_slack_event,
    send_slack_follow_up,
    send_slack_reply,
)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    worker = asyncio.create_task(_slack_event_worker())
    try:
        yield
    finally:
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass


app = FastAPI(title="DelegatorAI", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.environ.get(
            "FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ],
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class DashboardTaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    project_id: str = Field(default="college-app", min_length=1, max_length=200)
    owner_id: str = Field(min_length=1, max_length=200)
    deadline: date
    description: str = Field(default="", max_length=2000)
    priority: Literal["Low", "Medium", "High"] = "Medium"


class DashboardTaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=300)
    deadline: date | None = None
    description: str | None = Field(default=None, max_length=2000)
    priority: Literal["Low", "Medium", "High"] | None = None
    status: str | None = None
    blocker: str | None = Field(default=None, max_length=1000)
    progress: int | None = Field(default=None, ge=0, le=100)


class CoordinatorChatTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class CoordinatorChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=2000)
    history: list[CoordinatorChatTurn] = Field(default_factory=list, max_length=12)


@app.get("/participants")
def dashboard_participants() -> list[Participant]:
    return list_participants()


@app.get("/tasks")
def dashboard_tasks() -> list[dict[str, object]]:
    participants = {person.id: person for person in list_participants()}
    return [
        _dashboard_task(task, participants[task.owner_id])
        for task in list_tasks()
    ]


@app.post("/tasks", status_code=201)
def dashboard_create_task(request: DashboardTaskCreate) -> dict[str, object]:
    participants = {person.id: person for person in list_participants()}
    owner = participants.get(request.owner_id)
    if owner is None:
        raise HTTPException(status_code=422, detail="owner_id is not a known participant.")
    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Task title cannot be blank.")
    task = Task(
        id=str(uuid4()),
        project_id=request.project_id,
        title=title,
        owner_id=owner.id,
        deadline=request.deadline,
        completion_criteria=request.description.strip() or title,
        priority=TaskPriority(request.priority),
    )
    add_task(task)
    return _dashboard_task(task, owner)


@app.patch("/tasks/{task_id}")
def dashboard_update_task(
    task_id: str, request: DashboardTaskUpdate
) -> dict[str, object]:
    fields = request.model_fields_set
    if not fields:
        raise HTTPException(status_code=422, detail="Provide at least one task field to update.")
    status = _parse_dashboard_status(request.status) if "status" in fields else None
    title = request.title.strip() if request.title is not None else None
    if title == "":
        raise HTTPException(status_code=422, detail="Task title cannot be blank.")
    description = (
        request.description.strip() if request.description is not None else None
    )
    blocker = (
        request.blocker.strip() or None
        if request.blocker
        else None
    ) if "blocker" in fields else None
    try:
        task = update_task_from_dashboard(
            task_id=task_id,
            title=title,
            deadline=request.deadline if "deadline" in fields else None,
            completion_criteria=description,
            priority=TaskPriority(request.priority)
            if request.priority is not None
            else None,
            new_status=status,
            blocker=blocker,
            progress=request.progress if "progress" in fields else None,
            completion_confirmed=status == TaskStatus.COMPLETE,
        )
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    owner = next(
        participant
        for participant in list_participants()
        if participant.id == task.owner_id
    )
    return _dashboard_task(task, owner)


@app.get("/tasks/{task_id}/history")
def dashboard_task_history(task_id: str) -> list[dict[str, object]]:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} does not exist.")
    history = []
    for row in list_task_history(task_id):
        if row["record_type"] == "status":
            status = row["new_status"]
            kind = "success" if status == TaskStatus.COMPLETE.value else (
                "warning" if status == TaskStatus.BLOCKED.value else "update"
            )
            title = f"Task status changed to {status}"
            detail = row["reason"]
        else:
            direction = row["direction"]
            kind = "bot" if direction == "outbound" else "update"
            provider = (
                "Slack"
                if row["slack_channel_id"]
                else "Telegram"
                if row["telegram_chat_id"]
                else "Google Chat"
                if row["chat_space_id"]
                else "Task"
            )
            action = "follow-up sent" if direction == "outbound" else "update received"
            title = f"{provider} {action}"
            detail = row["text"]
        history.append(
            {
                "id": f"{row['record_type']}-{row['id']}",
                "kind": kind,
                "title": title,
                "detail": detail,
                "time": row["created_at"],
                "record_type": row["record_type"],
                "direction": row["direction"],
                "old_status": row["old_status"],
                "new_status": row["new_status"],
                "message_name": row["chat_message_name"],
                "thread_name": row["chat_thread_name"],
                "channel_id": row["slack_channel_id"],
                "message_ts": row["slack_message_ts"],
                "thread_ts": row["slack_thread_ts"],
            }
        )
    return history


@app.post("/tasks/{task_id}/follow-up")
def dashboard_task_follow_up(task_id: str) -> dict[str, str | None]:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} does not exist.")
    owner = next(
        (participant for participant in list_participants() if participant.id == task.owner_id),
        None,
    )
    if owner is None:
        raise HTTPException(
            status_code=503, detail=f"Owner {task.owner_id!r} is not configured."
        )
    try:
        settings = get_slack_settings()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        receipt = send_slack_follow_up(
            task_id=task_id,
            settings=settings,
        )
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SlackRateLimitError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Slack rate limited the request; retry after {exc.retry_after} seconds.",
        ) from exc
    except SlackApiError as exc:
        raise HTTPException(
            status_code=502,
            detail="Slack could not deliver the follow-up.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "status": "sent",
        "task_id": task_id,
        "message_ts": receipt.message_ts,
        "channel_id": receipt.channel_id,
        "thread_ts": receipt.thread_ts,
    }


@app.post("/assistant/chat")
def coordinator_chat(request: CoordinatorChatRequest) -> dict[str, str]:
    participants = {person.id: person.name for person in list_participants()}
    context = [
        {
            "id": task.id,
            "title": task.title,
            "project": task.project_id,
            "assignee": participants.get(task.owner_id, task.owner_id),
            "status": task.status.value,
            "priority": task.priority.value,
            "deadline": task.deadline.isoformat(),
            "progress": task.progress,
            "blocker": task.blocker,
        }
        for task in list_tasks()
    ]
    messages = [
        {"role": "system", "content": COORDINATOR_SYSTEM_PROMPT},
        *[
            {"role": turn.role, "content": turn.content}
            for turn in request.history
        ],
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task_context_untrusted": context,
                    "user_message_untrusted": request.message,
                },
                ensure_ascii=False,
            ),
        },
    ]
    try:
        reply = OpenAICompatibleProvider().respond(messages)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (APIError, ValueError) as exc:
        logger.error(
            "Coordinator chat request failed (%s).", type(exc).__name__
        )
        raise HTTPException(
            status_code=502, detail="The AI coordinator could not respond."
        ) from exc
    return {"reply": reply}


@app.get("/health")
def health() -> dict[str, str]:
    with connect() as connection:
        connection.execute("SELECT 1").fetchone()
    return {"status": "ok", "database": "ok"}


def _dashboard_task(task: Task, owner: Participant) -> dict[str, object]:
    return {
        "id": task.id,
        "project_id": task.project_id,
        "title": task.title,
        "description": task.completion_criteria,
        "owner_id": task.owner_id,
        "assignee": owner.name,
        "email": owner.email,
        "deadline": task.deadline.isoformat(),
        "due_date": task.deadline.isoformat(),
        "dueDate": f"{task.deadline.strftime('%b')} {task.deadline.day}",
        "status": task.status.value,
        "blocker": task.blocker or "",
        "progress": task.progress,
        "priority": task.priority.value,
        "project": task.project_id,
        "initials": "".join(part[0] for part in owner.name.split())[:2].upper(),
    }


def _parse_dashboard_status(status: str | None) -> TaskStatus | None:
    if status is None:
        return None
    if status == "Completed":
        return TaskStatus.COMPLETE
    aliases = {
        "Pending": TaskStatus.PENDING,
        "In Progress": TaskStatus.IN_PROGRESS,
        "Blocked": TaskStatus.BLOCKED,
        "Complete": TaskStatus.COMPLETE,
    }
    try:
        return aliases[status]
    except KeyError as exc:
        raise HTTPException(
            status_code=422, detail=f"Unsupported task status: {status!r}."
        ) from exc


@app.post("/slack/events")
async def slack_events(
    request: Request,
    timestamp: str | None = Header(default=None, alias="X-Slack-Request-Timestamp"),
    signature: str | None = Header(default=None, alias="X-Slack-Signature"),
) -> dict[str, str | bool]:
    try:
        settings = get_slack_settings()
    except RuntimeError as exc:
        logger.error("Slack integration configuration is invalid (%s).", type(exc).__name__)
        raise HTTPException(
            status_code=503, detail="Slack integration is not configured."
        ) from exc

    raw_body = await request.body()
    from slack_bot import verify_slack_signature

    if not verify_slack_signature(
        signing_secret=settings.signing_secret,
        timestamp=timestamp,
        signature=signature,
        raw_body=raw_body,
    ):
        raise HTTPException(status_code=401, detail="Invalid Slack request signature.")
    try:
        payload = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=400, detail="Slack request body must be JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400, detail="Slack request body must be a JSON object."
        )
    if payload.get("type") == "url_verification":
        challenge = payload.get("challenge")
        if not isinstance(challenge, str) or not challenge:
            raise HTTPException(status_code=400, detail="Slack challenge is missing.")
        return {"challenge": challenge}
    if payload.get("type") != "event_callback":
        return {"ok": True}
    event_id = payload.get("event_id")
    if (
        not isinstance(event_id, str)
        or not event_id
        or not isinstance(payload.get("event"), dict)
    ):
        raise HTTPException(
            status_code=422,
            detail="A valid Slack event_id and event object are required.",
        )
    inserted = await asyncio.to_thread(enqueue_slack_event, event_id, payload)
    logger.info(
        "Accepted Slack event (event_id=%s, duplicate=%s).",
        event_id,
        not inserted,
    )
    return {"ok": True, "queued": inserted}


async def _slack_event_worker() -> None:
    while True:
        try:
            event_row = await asyncio.to_thread(claim_slack_event)
            if event_row is None:
                await asyncio.sleep(1)
                continue
            event_id = event_row["event_id"]
            try:
                settings = get_slack_settings()
                payload = json.loads(event_row["payload"])
                if not isinstance(payload, dict) or not isinstance(payload.get("event"), dict):
                    raise ValueError("Queued Slack event is malformed.")
                if event_row["response_text"] is None:
                    reply = await asyncio.to_thread(
                        lambda: process_slack_event(
                            payload["event"],
                            event_id=event_id,
                            settings=settings,
                        )
                    )
                    if reply is not None:
                        await asyncio.to_thread(
                            store_slack_event_response,
                            event_id=event_id,
                            text=reply.text,
                            channel_id=reply.channel_id,
                            thread_ts=reply.thread_ts,
                            task_id=reply.task_id,
                            participant_id=reply.participant_id,
                        )
                else:
                    project_id = settings.project_channels.get(
                        str(payload.get("event", {}).get("channel", ""))
                    )
                    if project_id is None:
                        raise ValueError("Queued Slack event channel is not mapped.")
                    reply = SlackReply(
                        text=event_row["response_text"],
                        channel_id=event_row["response_channel_id"],
                        thread_ts=event_row["response_thread_ts"],
                        project_id=project_id,
                        task_id=event_row["response_task_id"],
                        participant_id=event_row["response_participant_id"],
                    )
                if reply is not None:
                    await asyncio.to_thread(
                        send_slack_reply,
                        event_id=event_id,
                        reply=reply,
                        client=SlackClient.from_settings(settings),
                    )
                await asyncio.to_thread(complete_slack_event, event_id)
            except SlackRateLimitError as exc:
                logger.warning(
                    "Slack rate limit while processing event (event_id=%s, retry_after=%s).",
                    event_id,
                    exc.retry_after,
                )
                await asyncio.to_thread(
                    fail_slack_event,
                    event_id,
                    event_row["attempts"] + 1,
                    exc.retry_after,
                )
            except Exception as exc:
                logger.error(
                    "Slack event processing failed (event_id=%s, error=%s).",
                    event_id,
                    type(exc).__name__,
                )
                await asyncio.to_thread(
                    fail_slack_event,
                    event_id,
                    event_row["attempts"] + 1,
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Slack event queue worker failed (%s).", type(exc).__name__)
            await asyncio.sleep(1)
