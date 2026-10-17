import json
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from config import get_database_path
from models import Participant, Task, TaskPriority, TaskStatus


SCHEMA = """
CREATE TABLE IF NOT EXISTS participants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    google_user_id TEXT UNIQUE,
    email TEXT UNIQUE,
    telegram_user_id TEXT,
    slack_user_id TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    owner_id TEXT NOT NULL REFERENCES participants(id),
    deadline TEXT NOT NULL,
    completion_criteria TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending'
        CHECK (status IN ('Pending', 'In Progress', 'Blocked', 'Complete')),
    priority TEXT NOT NULL DEFAULT 'Medium'
        CHECK (priority IN ('Low', 'Medium', 'High')),
    blocker TEXT,
    progress INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    last_follow_up_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    participant_id TEXT NOT NULL REFERENCES participants(id),
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    chat_space_id TEXT,
    chat_message_name TEXT,
    chat_thread_name TEXT,
    telegram_chat_id TEXT,
    telegram_message_id TEXT,
    telegram_thread_id TEXT,
    slack_channel_id TEXT,
    slack_message_ts TEXT,
    slack_thread_ts TEXT
);

CREATE TABLE IF NOT EXISTS status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    old_status TEXT NOT NULL
        CHECK (old_status IN ('Pending', 'In Progress', 'Blocked', 'Complete')),
    new_status TEXT NOT NULL
        CHECK (new_status IN ('Pending', 'In Progress', 'Blocked', 'Complete')),
    reason TEXT NOT NULL,
    source_message_id INTEGER REFERENCES messages(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS telegram_updates (
    update_id INTEGER PRIMARY KEY,
    payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'processed', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    claimed_at TEXT,
    next_attempt_at TEXT,
    processed_at TEXT
);

CREATE TABLE IF NOT EXISTS slack_events (
    event_id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'processed', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    claimed_at TEXT,
    next_attempt_at TEXT,
    processed_at TEXT,
    response_text TEXT,
    response_channel_id TEXT,
    response_thread_ts TEXT,
    response_task_id TEXT,
    response_participant_id TEXT
);

CREATE TABLE IF NOT EXISTS slack_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE,
    project_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    slack_user_id TEXT,
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    text TEXT NOT NULL,
    message_ts TEXT,
    thread_ts TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_owner_id ON tasks(owner_id);
CREATE INDEX IF NOT EXISTS idx_messages_task_id ON messages(task_id);
CREATE INDEX IF NOT EXISTS idx_status_history_task_id
    ON status_history(task_id, created_at);
"""


@contextmanager
def connect(
    database_path: Path | str | None = None,
) -> Generator[sqlite3.Connection, None, None]:
    path = Path(database_path) if database_path is not None else get_database_path()
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(database_path: Path | str | None = None) -> None:
    with connect(database_path) as connection:
        connection.executescript(SCHEMA)
        participant_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(participants)")
        }
        if "telegram_user_id" not in participant_columns:
            connection.execute(
                "ALTER TABLE participants ADD COLUMN telegram_user_id TEXT"
            )
        if "slack_user_id" not in participant_columns:
            connection.execute(
                "ALTER TABLE participants ADD COLUMN slack_user_id TEXT"
            )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_participants_telegram_user_id
            ON participants(telegram_user_id)
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_participants_slack_user_id
            ON participants(slack_user_id)
            """
        )
        task_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(tasks)")
        }
        if "priority" not in task_columns:
            connection.execute(
                """
                ALTER TABLE tasks
                ADD COLUMN priority TEXT NOT NULL DEFAULT 'Medium'
                CHECK (priority IN ('Low', 'Medium', 'High'))
                """
            )
        if "progress" not in task_columns:
            connection.execute(
                "ALTER TABLE tasks ADD COLUMN progress INTEGER NOT NULL DEFAULT 0"
            )
            connection.execute(
                """
                UPDATE tasks
                SET progress = CASE status
                    WHEN 'Complete' THEN 100
                    WHEN 'In Progress' THEN 50
                    WHEN 'Blocked' THEN 25
                    ELSE 0
                END
                """
            )
        message_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(messages)")
        }
        for column in (
            "chat_space_id",
            "chat_message_name",
            "chat_thread_name",
            "telegram_chat_id",
            "telegram_message_id",
            "telegram_thread_id",
            "slack_channel_id",
            "slack_message_ts",
            "slack_thread_ts",
        ):
            if column not in message_columns:
                connection.execute(f"ALTER TABLE messages ADD COLUMN {column} TEXT")
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_chat_thread
            ON messages(chat_space_id, chat_thread_name)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_slack_thread
            ON messages(slack_channel_id, slack_thread_ts, slack_message_ts)
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_slack_receipt
            ON messages(slack_channel_id, slack_message_ts)
            WHERE slack_message_ts IS NOT NULL
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_slack_messages_receipt
            ON slack_messages(channel_id, message_ts)
            WHERE message_ts IS NOT NULL
            """
        )


def add_participant(
    participant: Participant, database_path: Path | str | None = None
) -> None:
    with connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO participants (
                id, name, google_user_id, email, telegram_user_id, slack_user_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                participant.id,
                participant.name,
                participant.google_user_id,
                participant.email,
                participant.telegram_user_id,
                participant.slack_user_id,
            ),
        )


def add_task(task: Task, database_path: Path | str | None = None) -> None:
    with connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO tasks (
                id, project_id, title, owner_id, deadline,
                completion_criteria, status, priority, blocker, progress,
                last_follow_up_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.id,
                task.project_id,
                task.title,
                task.owner_id,
                task.deadline.isoformat(),
                task.completion_criteria,
                task.status.value,
                task.priority.value,
                task.blocker,
                task.progress,
                task.last_follow_up_at.isoformat()
                if task.last_follow_up_at is not None
                else None,
            ),
        )


def list_participants(database_path: Path | str | None = None) -> list[Participant]:
    with connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, name, google_user_id, email, telegram_user_id, slack_user_id
            FROM participants ORDER BY id
            """
        ).fetchall()
    return [Participant.model_validate(dict(row)) for row in rows]


def get_participant_by_slack_id(
    slack_user_id: str, database_path: Path | str | None = None
) -> Participant | None:
    with connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT id, name, google_user_id, email, telegram_user_id, slack_user_id
            FROM participants WHERE slack_user_id = ?
            """,
            (slack_user_id,),
        ).fetchone()
    return Participant.model_validate(dict(row)) if row is not None else None


def link_slack_user(
    participant_id: str,
    slack_user_id: str,
    database_path: Path | str | None = None,
) -> bool:
    with connect(database_path) as connection:
        cursor = connection.execute(
            "UPDATE participants SET slack_user_id = ? WHERE id = ?",
            (slack_user_id, participant_id),
        )
    return cursor.rowcount == 1


def list_tasks(database_path: Path | str | None = None) -> list[Task]:
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM tasks ORDER BY deadline, id"
        ).fetchall()
    return [_task_from_row(row) for row in rows]


def get_task(task_id: str, database_path: Path | str | None = None) -> Task | None:
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    return _task_from_row(row) if row is not None else None


def list_project_tasks(
    project_id: str, database_path: Path | str | None = None
) -> list[Task]:
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM tasks WHERE project_id = ? ORDER BY deadline, id",
            (project_id,),
        ).fetchall()
    return [_task_from_row(row) for row in rows]


def list_task_history(
    task_id: str, database_path: Path | str | None = None
) -> list[sqlite3.Row]:
    with connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT record_type, id, created_at, old_status, new_status,
                   reason, direction, text, chat_message_name, chat_thread_name,
                   slack_channel_id, slack_message_ts, slack_thread_ts,
                   telegram_chat_id, chat_space_id
            FROM (
                SELECT
                    'status' AS record_type, id, created_at, old_status,
                    new_status, reason, NULL AS direction, NULL AS text,
                    NULL AS chat_message_name, NULL AS chat_thread_name,
                    NULL AS slack_channel_id, NULL AS slack_message_ts,
                    NULL AS slack_thread_ts, NULL AS telegram_chat_id,
                    NULL AS chat_space_id
                FROM status_history
                WHERE task_id = ?
                UNION ALL
                SELECT
                    'message' AS record_type, id, created_at, NULL AS old_status,
                    NULL AS new_status, NULL AS reason, direction, text,
                    chat_message_name, chat_thread_name, slack_channel_id,
                    slack_message_ts, slack_thread_ts, telegram_chat_id,
                    chat_space_id
                FROM messages
                WHERE task_id = ?
            )
            ORDER BY created_at DESC, id DESC
            """,
            (task_id, task_id),
        ).fetchall()
    return rows


def save_outbound_chat_message(
    *,
    task_id: str,
    participant_id: str,
    space_id: str,
    text: str,
    message_name: str | None,
    thread_name: str | None,
    database_path: Path | str | None = None,
) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    with connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO messages (
                task_id, participant_id, direction, text, created_at,
                chat_space_id, chat_message_name, chat_thread_name
            ) VALUES (?, ?, 'outbound', ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                participant_id,
                text,
                created_at,
                space_id,
                message_name,
                thread_name,
            ),
        )
        connection.execute(
            "UPDATE tasks SET last_follow_up_at = ? WHERE id = ?",
            (created_at, task_id),
        )


def save_outbound_slack_message(
    *,
    task_id: str,
    participant_id: str,
    channel_id: str,
    text: str,
    message_ts: str,
    thread_ts: str | None,
    project_id: str,
    database_path: Path | str | None = None,
) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    with connect(database_path) as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO messages (
                task_id, participant_id, direction, text, created_at,
                slack_channel_id, slack_message_ts, slack_thread_ts
            ) VALUES (?, ?, 'outbound', ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                participant_id,
                text,
                created_at,
                channel_id,
                message_ts,
                thread_ts,
            ),
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO slack_messages (
                project_id, channel_id, slack_user_id, direction, text,
                message_ts, thread_ts, created_at
            ) VALUES (?, ?, NULL, 'outbound', ?, ?, ?, ?)
            """,
            (project_id, channel_id, text, message_ts, thread_ts, created_at),
        )
        connection.execute(
            "UPDATE tasks SET last_follow_up_at = ? WHERE id = ?",
            (created_at, task_id),
        )


def find_task_for_slack_reply(
    *,
    channel_id: str,
    thread_ts: str,
    database_path: Path | str | None = None,
) -> tuple[Task, Participant] | None:
    with connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT t.*, p.id AS participant_id, p.name AS participant_name,
                   p.google_user_id, p.email, p.telegram_user_id, p.slack_user_id
            FROM messages AS m
            JOIN tasks AS t ON t.id = m.task_id
            JOIN participants AS p ON p.id = t.owner_id
            WHERE m.direction = 'outbound'
              AND m.slack_channel_id = ?
              AND (m.slack_message_ts = ? OR m.slack_thread_ts = ?)
            ORDER BY m.id DESC
            LIMIT 1
            """,
            (channel_id, thread_ts, thread_ts),
        ).fetchone()
    if row is None:
        return None
    return _task_from_row(row), Participant(
        id=row["participant_id"],
        name=row["participant_name"],
        google_user_id=row["google_user_id"],
        email=row["email"],
        telegram_user_id=row["telegram_user_id"],
        slack_user_id=row["slack_user_id"],
    )


def find_slack_thread_for_task(
    task_id: str,
    channel_id: str,
    database_path: Path | str | None = None,
) -> str | None:
    with connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT slack_thread_ts, slack_message_ts FROM messages
            WHERE task_id = ? AND direction = 'outbound'
              AND slack_channel_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (task_id, channel_id),
        ).fetchone()
    return (row["slack_thread_ts"] or row["slack_message_ts"]) if row else None


def enqueue_slack_event(
    event_id: str,
    payload: dict[str, object],
    database_path: Path | str | None = None,
) -> bool:
    with connect(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO slack_events (event_id, payload, created_at)
            VALUES (?, ?, ?)
            """,
            (
                event_id,
                json.dumps(payload, separators=(",", ":")),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    return cursor.rowcount == 1


def claim_slack_event(
    database_path: Path | str | None = None,
) -> sqlite3.Row | None:
    now = datetime.now(timezone.utc)
    stale_before = (now - timedelta(minutes=5)).isoformat()
    with connect(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT event_id, payload, attempts, response_text,
                   response_channel_id, response_thread_ts, response_task_id,
                   response_participant_id
            FROM slack_events
            WHERE (
                status = 'pending'
                AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
            ) OR (
                status = 'processing' AND claimed_at <= ?
            )
            ORDER BY created_at, event_id
            LIMIT 1
            """,
            (now.isoformat(), stale_before),
        ).fetchone()
        if row is None:
            return None
        connection.execute(
            """
            UPDATE slack_events
            SET status = 'processing', attempts = attempts + 1,
                claimed_at = ?, next_attempt_at = NULL
            WHERE event_id = ?
            """,
            (now.isoformat(), row["event_id"]),
        )
        return row


def complete_slack_event(
    event_id: str, database_path: Path | str | None = None
) -> None:
    with connect(database_path) as connection:
        connection.execute(
            """
            UPDATE slack_events SET status = 'processed', processed_at = ?
            WHERE event_id = ?
            """,
            (datetime.now(timezone.utc).isoformat(), event_id),
        )


def fail_slack_event(
    event_id: str,
    attempts: int,
    retry_after: int | None = None,
    database_path: Path | str | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    status = "failed" if attempts >= 8 else "pending"
    delay = min(
        max(30 * 2 ** max(attempts - 1, 0), retry_after or 0),
        3600,
    )
    retry_at = now + timedelta(seconds=delay)
    with connect(database_path) as connection:
        connection.execute(
            """
            UPDATE slack_events
            SET status = ?, next_attempt_at = ?, claimed_at = NULL
            WHERE event_id = ?
            """,
            (
                status,
                retry_at.isoformat() if status == "pending" else None,
                event_id,
            ),
        )


def store_slack_event_response(
    *,
    event_id: str,
    text: str,
    channel_id: str,
    thread_ts: str | None,
    task_id: str | None = None,
    participant_id: str | None = None,
    database_path: Path | str | None = None,
) -> None:
    with connect(database_path) as connection:
        connection.execute(
            """
            UPDATE slack_events SET response_text = ?, response_channel_id = ?,
                response_thread_ts = ?, response_task_id = ?,
                response_participant_id = ?
            WHERE event_id = ? AND response_text IS NULL
            """,
            (text, channel_id, thread_ts, task_id, participant_id, event_id),
        )


def save_slack_conversation_message(
    *,
    event_id: str,
    project_id: str,
    channel_id: str,
    slack_user_id: str | None,
    direction: str,
    text: str,
    message_ts: str | None,
    thread_ts: str | None,
    database_path: Path | str | None = None,
) -> bool:
    with connect(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO slack_messages (
                event_id, project_id, channel_id, slack_user_id, direction,
                text, message_ts, thread_ts, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                project_id,
                channel_id,
                slack_user_id,
                direction,
                text,
                message_ts,
                thread_ts,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    return cursor.rowcount == 1


def find_task_for_chat_thread(
    *,
    space_id: str,
    thread_name: str,
    database_path: Path | str | None = None,
) -> tuple[Task, Participant] | None:
    with connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT t.*, p.id AS participant_id, p.name AS participant_name,
                   p.google_user_id, p.email, p.telegram_user_id, p.slack_user_id
            FROM messages AS m
            JOIN tasks AS t ON t.id = m.task_id
            JOIN participants AS p ON p.id = t.owner_id
            WHERE m.direction = 'outbound'
              AND m.chat_space_id = ?
              AND m.chat_thread_name = ?
            ORDER BY m.id DESC
            LIMIT 1
            """,
            (space_id, thread_name),
        ).fetchone()
    if row is None:
        return None
    task = _task_from_row(row)
    participant = Participant(
        id=row["participant_id"],
        name=row["participant_name"],
        google_user_id=row["google_user_id"],
        email=row["email"],
        telegram_user_id=row["telegram_user_id"],
        slack_user_id=row["slack_user_id"],
    )
    return task, participant


def _task_from_row(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"],
        project_id=row["project_id"],
        title=row["title"],
        owner_id=row["owner_id"],
        deadline=date.fromisoformat(row["deadline"]),
        completion_criteria=row["completion_criteria"],
        status=TaskStatus(row["status"]),
        priority=TaskPriority(row["priority"]),
        blocker=row["blocker"],
        progress=row["progress"],
        last_follow_up_at=datetime.fromisoformat(row["last_follow_up_at"])
        if row["last_follow_up_at"] is not None
        else None,
    )
