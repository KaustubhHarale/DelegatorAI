from contextlib import asynccontextmanager
from datetime import date
import os
from typing import AsyncIterator, Literal
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.auth.exceptions import GoogleAuthError
from googleapiclient.errors import Error as GoogleApiError
from httplib2 import HttpLib2Error
from pydantic import BaseModel, ConfigDict, Field

from config import get_google_chat_settings
from database import (
    add_task,
    connect,
    get_task,
    init_db,
    list_participants,
    list_task_history,
    list_tasks,
)
from google_chat import (
    process_google_chat_event,
    send_chat_message,
    verify_google_chat_token,
)
from models import GoogleChatEvent, Participant, Task, TaskPriority, TaskStatus
from task_tools import (
    InvalidStatusTransitionError,
    TaskNotFoundError,
    update_task_from_dashboard,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


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
            title = (
                "Google Chat follow-up sent"
                if direction == "outbound"
                else "Google Chat reply received"
            )
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
        settings = get_google_chat_settings()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    text = (
        f"Hi {owner.name}, quick check-in on “{task.title}” "
        f"(currently {task.status.value}). How is it progressing? "
        "Please share an update and let us know if you’re blocked."
    )
    try:
        receipt = send_chat_message(
            task_id=task_id,
            text=text,
            settings=settings,
        )
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GoogleAuthError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Google Chat credentials are unavailable: {exc}",
        ) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Google Chat configuration or credentials are invalid: {exc}",
        ) from exc
    except (GoogleApiError, HttpLib2Error) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Google Chat could not deliver the follow-up: {exc}",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "status": "sent",
        "task_id": task_id,
        "message_name": receipt.message_name,
        "thread_name": receipt.thread_name,
    }


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


@app.post("/google-chat/events")
def google_chat_events(
    event: GoogleChatEvent,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="A Google Chat bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=401,
            detail="A Google Chat bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        settings = get_google_chat_settings()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        verify_google_chat_token(
            token.strip(),
            settings=settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid Google Chat token.") from exc

    if event.type == "APP_HOME":
        return {
            "action": {
                "navigations": [
                    {
                        "pushCard": {
                            "header": {"title": "DelegatorAI"},
                            "sections": [
                                {
                                    "widgets": [
                                        {
                                            "textParagraph": {
                                                "text": (
                                                    "Task coordination happens in "
                                                    "your project space. Reply in a "
                                                    "task follow-up thread to share "
                                                    "progress or report a blocker."
                                                )
                                            }
                                        }
                                    ]
                                }
                            ],
                        }
                    }
                ]
            }
        }

    process_google_chat_event(event, settings=settings)
    return {}
