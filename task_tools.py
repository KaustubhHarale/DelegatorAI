import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from database import connect, get_task as load_task, list_project_tasks as load_project_tasks
from models import Task, TaskInterpretation, TaskPriority, TaskStatus


ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {
        TaskStatus.PENDING,
        TaskStatus.IN_PROGRESS,
        TaskStatus.BLOCKED,
        TaskStatus.COMPLETE,
    },
    TaskStatus.IN_PROGRESS: {
        TaskStatus.IN_PROGRESS,
        TaskStatus.BLOCKED,
        TaskStatus.COMPLETE,
    },
    TaskStatus.BLOCKED: {
        TaskStatus.BLOCKED,
        TaskStatus.IN_PROGRESS,
        TaskStatus.COMPLETE,
    },
    TaskStatus.COMPLETE: {TaskStatus.COMPLETE},
}


class TaskNotFoundError(ValueError):
    pass


class TaskOwnershipError(ValueError):
    pass


class InvalidStatusTransitionError(ValueError):
    pass


class DuplicateEventError(ValueError):
    pass


def get_task(
    task_id: str, database_path: Path | str | None = None
) -> Task:
    task = load_task(task_id, database_path)
    if task is None:
        raise TaskNotFoundError(f"Task {task_id!r} does not exist.")
    return task


def list_project_tasks(
    project_id: str, database_path: Path | str | None = None
) -> list[Task]:
    return load_project_tasks(project_id, database_path)


def find_tasks_needing_follow_up(
    *,
    inactive_for: timedelta = timedelta(days=3),
    now: datetime | None = None,
    database_path: Path | str | None = None,
) -> list[Task]:
    current_time = now or datetime.now(timezone.utc)
    cutoff = (current_time - inactive_for).isoformat()
    with connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM tasks
            WHERE status != ?
              AND (
                    last_follow_up_at IS NULL
                    OR datetime(last_follow_up_at) <= datetime(?)
              )
            ORDER BY deadline, id
            """,
            (TaskStatus.COMPLETE.value, cutoff),
        ).fetchall()
    return [Task.model_validate(_task_row_dict(row)) for row in rows]


def validate_interpretation(
    task: Task, interpretation: TaskInterpretation
) -> None:
    if interpretation.proposed_status not in ALLOWED_TRANSITIONS[task.status]:
        raise InvalidStatusTransitionError(
            f"Cannot change status from {task.status.value} "
            f"to {interpretation.proposed_status.value}."
        )
    if interpretation.needs_clarification:
        if interpretation.proposed_status != task.status:
            raise ValueError(
                "A reply needing clarification cannot change task status."
            )
        if interpretation.completion_confirmed:
            raise ValueError(
                "A reply needing clarification cannot confirm completion."
            )
        if interpretation.blocker is not None:
            raise ValueError(
                "A reply needing clarification cannot change the task blocker."
            )
    if interpretation.proposed_status == TaskStatus.COMPLETE:
        if (
            not interpretation.completion_confirmed
            or interpretation.needs_clarification
            or interpretation.blocker
        ):
            raise ValueError(
                "Complete status requires clear confirmation and no blocker."
            )
    if interpretation.completion_confirmed and (
        interpretation.proposed_status != TaskStatus.COMPLETE
        or interpretation.interpretation.value != "completion"
    ):
        raise ValueError("Only a completion interpretation can confirm completion.")
    if interpretation.proposed_status == TaskStatus.BLOCKED and not (
        interpretation.blocker or task.blocker
    ):
        raise ValueError("Blocked status requires a specific blocker.")
    if interpretation.interpretation.value == "ambiguous":
        if not interpretation.needs_clarification:
            raise ValueError("Ambiguous replies must request clarification.")


def record_progress(
    *,
    task_id: str,
    participant_id: str,
    reply: str,
    interpretation: TaskInterpretation,
    event_id: str | None = None,
    slack_channel_id: str | None = None,
    slack_message_ts: str | None = None,
    slack_thread_ts: str | None = None,
    database_path: Path | str | None = None,
) -> Task:
    if not reply.strip():
        raise ValueError("Reply text cannot be empty.")

    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise TaskNotFoundError(f"Task {task_id!r} does not exist.")
        task = Task.model_validate(_task_row_dict(row))
        if participant_id != task.owner_id:
            raise TaskOwnershipError("Only the task owner may update this task.")

        validate_interpretation(task, interpretation)
        message_event_id = event_id or f"local-{uuid4()}"
        duplicate = connection.execute(
            "SELECT 1 FROM messages WHERE event_id = ?", (message_event_id,)
        ).fetchone()
        if duplicate is not None:
            raise DuplicateEventError(f"Event {message_event_id!r} was processed.")

        created_at = datetime.now(timezone.utc).isoformat()
        cursor = connection.execute(
            """
            INSERT INTO messages (
                event_id, task_id, participant_id, direction, text, created_at,
                slack_channel_id, slack_message_ts, slack_thread_ts
            ) VALUES (?, ?, ?, 'inbound', ?, ?, ?, ?, ?)
            """,
            (
                message_event_id,
                task_id,
                participant_id,
                reply,
                created_at,
                slack_channel_id,
                slack_message_ts,
                slack_thread_ts,
            ),
        )
        new_blocker = (
            interpretation.blocker or task.blocker
            if interpretation.proposed_status == TaskStatus.BLOCKED
            else None
        )
        connection.execute(
            "UPDATE tasks SET status = ?, blocker = ?, progress = ? WHERE id = ?",
            (
                interpretation.proposed_status.value,
                new_blocker,
                _progress_for_status(
                    interpretation.proposed_status, task.progress
                ),
                task_id,
            ),
        )
        if task.status != interpretation.proposed_status:
            connection.execute(
                """
                INSERT INTO status_history (
                    task_id, old_status, new_status, reason,
                    source_message_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    task.status.value,
                    interpretation.proposed_status.value,
                    interpretation.progress_summary,
                    cursor.lastrowid,
                    created_at,
                ),
            )

    return get_task(task_id, database_path)


def set_task_status(
    *,
    task_id: str,
    new_status: TaskStatus,
    reason: str,
    completion_confirmed: bool = False,
    blocker: str | None = None,
    database_path: Path | str | None = None,
) -> Task:
    if not reason.strip():
        raise ValueError("A reason is required for a task status update.")
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise TaskNotFoundError(f"Task {task_id!r} does not exist.")
        task = Task.model_validate(_task_row_dict(row))
        if new_status not in ALLOWED_TRANSITIONS[task.status]:
            raise InvalidStatusTransitionError(
                f"Cannot change status from {task.status.value} to {new_status.value}."
            )
        if new_status == TaskStatus.COMPLETE and not completion_confirmed:
            raise ValueError("Complete status requires explicit completion confirmation.")
        if new_status == TaskStatus.BLOCKED and not (blocker or task.blocker):
            raise ValueError("Blocked status requires a specific blocker.")
        updated_blocker = blocker if blocker is not None else task.blocker
        if new_status != task.status and new_status != TaskStatus.BLOCKED:
            updated_blocker = None
        connection.execute(
            "UPDATE tasks SET status = ?, blocker = ?, progress = ? WHERE id = ?",
            (
                new_status.value,
                updated_blocker,
                _progress_for_status(new_status, task.progress),
                task_id,
            ),
        )
        if task.status != new_status:
            connection.execute(
                """
                INSERT INTO status_history (
                    task_id, old_status, new_status, reason, source_message_id,
                    created_at
                ) VALUES (?, ?, ?, ?, NULL, ?)
                """,
                (
                    task_id,
                    task.status.value,
                    new_status.value,
                    reason,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
    return get_task(task_id, database_path)


def update_task_from_dashboard(
    *,
    task_id: str,
    title: str | None = None,
    deadline: date | None = None,
    completion_criteria: str | None = None,
    priority: TaskPriority | None = None,
    new_status: TaskStatus | None = None,
    blocker: str | None = None,
    progress: int | None = None,
    completion_confirmed: bool = False,
    database_path: Path | str | None = None,
) -> Task:
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise TaskNotFoundError(f"Task {task_id!r} does not exist.")
        task = Task.model_validate(_task_row_dict(row))
        status = new_status or task.status
        if status not in ALLOWED_TRANSITIONS[task.status]:
            raise InvalidStatusTransitionError(
                f"Cannot change status from {task.status.value} to {status.value}."
            )
        if (
            status == TaskStatus.COMPLETE
            and task.status != TaskStatus.COMPLETE
            and not completion_confirmed
        ):
            raise ValueError("Complete status requires explicit completion confirmation.")

        updated_blocker = blocker if blocker is not None else task.blocker
        if status == TaskStatus.BLOCKED and not (
            updated_blocker and updated_blocker.strip()
        ):
            raise ValueError("Blocked status requires a specific blocker.")
        if status != task.status and status != TaskStatus.BLOCKED:
            updated_blocker = None

        updated_progress = (
            progress if progress is not None else _progress_for_status(status, task.progress)
        )
        if status == TaskStatus.COMPLETE:
            updated_progress = 100
        elif status == TaskStatus.PENDING:
            updated_progress = 0

        connection.execute(
            """
            UPDATE tasks
            SET title = ?, deadline = ?, completion_criteria = ?,
                priority = ?, status = ?, blocker = ?, progress = ?
            WHERE id = ?
            """,
            (
                title if title is not None else task.title,
                deadline.isoformat() if deadline is not None else task.deadline.isoformat(),
                completion_criteria
                if completion_criteria is not None
                else task.completion_criteria,
                (priority or task.priority).value,
                status.value,
                updated_blocker,
                updated_progress,
                task_id,
            ),
        )
        if task.status != status:
            connection.execute(
                """
                INSERT INTO status_history (
                    task_id, old_status, new_status, reason,
                    source_message_id, created_at
                ) VALUES (?, ?, ?, ?, NULL, ?)
                """,
                (
                    task_id,
                    task.status.value,
                    status.value,
                    "Updated from the DelegatorAI dashboard.",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
    return get_task(task_id, database_path)


def record_blocker(
    *, task_id: str, blocker: str, reason: str, database_path: Path | str | None = None
) -> Task:
    if not blocker.strip():
        raise ValueError("Blocker text cannot be empty.")
    return set_task_status(
        task_id=task_id,
        new_status=TaskStatus.BLOCKED,
        reason=reason,
        blocker=blocker,
        database_path=database_path,
    )


def ask_clarification(interpretation: TaskInterpretation) -> str:
    if not interpretation.needs_clarification:
        raise ValueError("This interpretation does not need clarification.")
    if not interpretation.clarification_question:
        raise ValueError("No clarification question was provided.")
    return interpretation.clarification_question


def _task_row_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "title": row["title"],
        "owner_id": row["owner_id"],
        "deadline": row["deadline"],
        "completion_criteria": row["completion_criteria"],
        "status": row["status"],
        "priority": row["priority"],
        "blocker": row["blocker"],
        "progress": row["progress"],
        "last_follow_up_at": row["last_follow_up_at"],
    }


def _progress_for_status(status: TaskStatus, current_progress: int) -> int:
    if status == TaskStatus.COMPLETE:
        return 100
    if status == TaskStatus.PENDING:
        return 0
    if current_progress == 0 and status == TaskStatus.IN_PROGRESS:
        return 50
    return current_progress
