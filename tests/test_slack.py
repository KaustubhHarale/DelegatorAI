import asyncio
import hashlib
import hmac
import json
import sqlite3
import time
from datetime import date

import httpx
import pytest

from config import SlackSettings
from database import (
    add_participant,
    add_task,
    connect,
    init_db,
    save_outbound_slack_message,
)
from main import app
from models import InterpretationKind, Participant, Task, TaskStatus
from slack_bot import (
    SlackApiError,
    SlackClient,
    SlackMessageReceipt,
    SlackRateLimitError,
    process_slack_event,
    send_slack_reply,
    verify_slack_signature,
)


class FakeSlackSender:
    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []

    def post_message(
        self,
        *,
        channel_id: str,
        text: str,
        thread_ts: str | None = None,
        client_msg_id: str | None = None,
    ) -> SlackMessageReceipt:
        self.sent.append(
            {
                "channel_id": channel_id,
                "text": text,
                "thread_ts": thread_ts,
                "client_msg_id": client_msg_id,
            }
        )
        return SlackMessageReceipt(channel_id, f"170000000{len(self.sent)}.000001", thread_ts)


class FakeProvider:
    def __init__(self, interpretation: dict[str, object] | None = None) -> None:
        self.interpretation = interpretation or {
            "interpretation": InterpretationKind.PROGRESS.value,
            "progress_summary": "The implementation is underway.",
            "proposed_status": TaskStatus.IN_PROGRESS.value,
            "blocker": None,
            "completion_confirmed": False,
            "needs_clarification": False,
            "clarification_question": None,
            "next_action": "Continue implementation.",
        }

    def complete(self, _system_prompt: str, _user_prompt: str) -> str:
        return json.dumps(self.interpretation)

    def respond(self, _messages: list[dict[str, str]]) -> str:
        return "The project has one pending task."


@pytest.fixture
def slack_setup(tmp_path):
    database_path = tmp_path / "slack.db"
    init_db(database_path)
    add_participant(
        Participant(
            id="kabir",
            name="Kabir Mehta",
            email="kabir@example.edu",
            slack_user_id="U12345",
        ),
        database_path,
    )
    add_participant(
        Participant(id="riya", name="Riya Sharma", slack_user_id="U22222"),
        database_path,
    )
    add_task(
        Task(
            id="payment",
            project_id="college-app",
            title="Connect the payment API",
            owner_id="kabir",
            deadline=date(2026, 11, 1),
            completion_criteria="API connected and payment flow tested",
        ),
        database_path,
    )
    settings = SlackSettings(
        bot_token="xoxb-test-token",
        signing_secret="test-signing-secret",
        bot_user_id="UBOT",
        project_channels={"C123ABC": "college-app"},
        admin_user_ids=frozenset({"UADMIN"}),
    )
    return database_path, settings


def sign_body(body: bytes, secret: str, timestamp: str | None = None) -> dict[str, str]:
    request_timestamp = timestamp or str(int(time.time()))
    base = f"v0:{request_timestamp}:".encode() + body
    signature = "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return {
        "X-Slack-Request-Timestamp": request_timestamp,
        "X-Slack-Signature": signature,
    }


def request(method: str, path: str, **kwargs):
    async def send_request():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                return await client.request(method, path, **kwargs)

    return asyncio.run(send_request())


def test_slack_signature_verification_and_replay_protection(slack_setup):
    _, settings = slack_setup
    body = b'{"type":"event_callback"}'
    valid = sign_body(body, settings.signing_secret, "1700000000")

    assert verify_slack_signature(
        signing_secret=settings.signing_secret,
        timestamp=valid["X-Slack-Request-Timestamp"],
        signature=valid["X-Slack-Signature"],
        raw_body=body,
        now=1700000000,
    )
    assert not verify_slack_signature(
        signing_secret=settings.signing_secret,
        timestamp=valid["X-Slack-Request-Timestamp"],
        signature=valid["X-Slack-Signature"],
        raw_body=body + b" ",
        now=1700000000,
    )
    assert not verify_slack_signature(
        signing_secret=settings.signing_secret,
        timestamp="1699999000",
        signature=valid["X-Slack-Signature"],
        raw_body=body,
        now=1700000000,
    )


def test_slack_url_verification_returns_challenge(slack_setup, monkeypatch):
    _, settings = slack_setup
    monkeypatch.setattr("main.get_slack_settings", lambda: settings)
    body = json.dumps({"type": "url_verification", "challenge": "challenge-token"}).encode()

    response = request(
        "POST",
        "/slack/events",
        content=body,
        headers=sign_body(body, settings.signing_secret),
    )

    assert response.status_code == 200
    assert response.json() == {"challenge": "challenge-token"}


def test_slack_webhook_rejects_invalid_signature(slack_setup, monkeypatch):
    _, settings = slack_setup
    monkeypatch.setattr("main.get_slack_settings", lambda: settings)

    response = request(
        "POST",
        "/slack/events",
        content=b'{"type":"event_callback","event_id":"Ev1"}',
        headers={
            "X-Slack-Request-Timestamp": str(int(time.time())),
            "X-Slack-Signature": "v0=invalid",
        },
    )

    assert response.status_code == 401


def test_slack_webhook_durably_deduplicates_events(slack_setup, monkeypatch):
    database_path, settings = slack_setup
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    monkeypatch.setattr("main.get_slack_settings", lambda: settings)
    body = json.dumps(
        {
            "type": "event_callback",
            "event_id": "Ev123",
            "event": {"type": "unknown"},
        }
    ).encode()
    headers = sign_body(body, settings.signing_secret)

    first = request("POST", "/slack/events", content=body, headers=headers)
    retry = request("POST", "/slack/events", content=body, headers=headers)

    assert first.status_code == retry.status_code == 200
    assert first.json() == {"ok": True, "queued": True}
    assert retry.json() == {"ok": True, "queued": False}
    with connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM slack_events WHERE event_id='Ev123'"
        ).fetchone()[0] == 1


def test_worker_posts_help_reply_once_and_persists_conversation(slack_setup, monkeypatch):
    database_path, settings = slack_setup
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    monkeypatch.setattr("main.get_slack_settings", lambda: settings)
    sender = FakeSlackSender()
    monkeypatch.setattr(
        "main.SlackClient.from_settings",
        classmethod(lambda _cls, _settings: sender),
    )
    body = json.dumps(
        {
            "type": "event_callback",
            "event_id": "EvStart",
            "event": {
                "type": "app_mention",
                "channel": "C123ABC",
                "user": "U12345",
                "text": "<@UBOT> /start",
                "ts": "1700000000.000001",
            },
        }
    ).encode()
    headers = sign_body(body, settings.signing_secret)

    async def send_and_wait():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.post("/slack/events", content=body, headers=headers)
                for _ in range(200):
                    with connect(database_path) as connection:
                        row = connection.execute(
                            "SELECT status FROM slack_events WHERE event_id='EvStart'"
                        ).fetchone()
                    if row is not None and row["status"] == "processed":
                        break
                    await asyncio.sleep(0.01)
                return response, row

    response, row = asyncio.run(send_and_wait())

    assert response.status_code == 200
    assert row["status"] == "processed"
    assert len(sender.sent) == 1
    assert sender.sent[0]["channel_id"] == "C123ABC"
    assert sender.sent[0]["thread_ts"] == "1700000000.000001"
    assert sender.sent[0]["text"].startswith("Hi! I'm DelegatorAI")
    assert sender.sent[0]["client_msg_id"]
    with connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM slack_messages"
        ).fetchone()[0] == 2


def test_slack_message_client_sends_thread_and_idempotency_key():
    captured = {}

    def mock_request(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "ok": True,
                "channel": "C123ABC",
                "ts": "1700000001.000001",
                "message": {"thread_ts": "1700000000.000001"},
            },
        )

    client = SlackClient("xoxb-test", httpx.MockTransport(mock_request))
    receipt = client.post_message(
        channel_id="C123ABC",
        text="Progress?",
        thread_ts="1700000000.000001",
        client_msg_id="request-id",
    )

    assert captured["url"] == "https://slack.com/api/chat.postMessage"
    assert captured["auth"] == "Bearer xoxb-test"
    assert captured["payload"] == {
        "channel": "C123ABC",
        "text": "Progress?",
        "thread_ts": "1700000000.000001",
        "client_msg_id": "request-id",
    }
    assert receipt == SlackMessageReceipt(
        "C123ABC", "1700000001.000001", "1700000000.000001"
    )


def test_slack_client_handles_rate_limit_and_api_failures():
    limited = SlackClient(
        "xoxb-test",
        httpx.MockTransport(
            lambda _request: httpx.Response(
                429, headers={"Retry-After": "7"}, json={"ok": False}
            )
        ),
    )
    rejected = SlackClient(
        "xoxb-test",
        httpx.MockTransport(
            lambda _request: httpx.Response(200, json={"ok": False, "error": "not_in_channel"})
        ),
    )

    with pytest.raises(SlackRateLimitError) as rate_limit:
        limited.post_message(channel_id="C123ABC", text="Hi")
    with pytest.raises(SlackApiError):
        rejected.post_message(channel_id="C123ABC", text="Hi")
    assert rate_limit.value.retry_after == 7


def test_unmapped_and_bot_messages_are_ignored(slack_setup):
    database_path, settings = slack_setup
    event = {
        "type": "message",
        "channel": "C999",
        "user": "U12345",
        "text": "hello",
        "ts": "1.1",
    }

    assert process_slack_event(
        event, event_id="Ev1", settings=settings, database_path=database_path
    ) is None
    event["channel"] = "C123ABC"
    event["bot_id"] = "B123"
    assert process_slack_event(
        event, event_id="Ev2", settings=settings, database_path=database_path
    ) is None
    with connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM slack_messages").fetchone()[0] == 0


def test_thread_reply_updates_assigned_task_and_keeps_thread(slack_setup):
    database_path, settings = slack_setup
    save_outbound_slack_message(
        task_id="payment",
        participant_id="kabir",
        channel_id="C123ABC",
        text="Please share your progress.",
        message_ts="1700000000.000001",
        thread_ts="1700000000.000001",
        project_id="college-app",
        database_path=database_path,
    )
    result = process_slack_event(
        {
            "type": "message",
            "channel": "C123ABC",
            "user": "U12345",
            "text": "I started connecting the API.",
            "ts": "1700000001.000001",
            "thread_ts": "1700000000.000001",
        },
        event_id="EvProgress",
        settings=settings,
        provider=FakeProvider(),
        database_path=database_path,
    )

    assert result is not None
    assert result.thread_ts == "1700000000.000001"
    assert result.task_id == "payment"
    assert "In Progress" in result.text
    with connect(database_path) as connection:
        task = connection.execute(
            "SELECT status FROM tasks WHERE id='payment'"
        ).fetchone()
        message = connection.execute(
            "SELECT slack_channel_id, slack_thread_ts FROM messages "
            "WHERE event_id='EvProgress'"
        ).fetchone()
    assert task["status"] == TaskStatus.IN_PROGRESS.value
    assert message["slack_channel_id"] == "C123ABC"
    assert message["slack_thread_ts"] == "1700000000.000001"


def test_ambiguous_reply_requests_clarification_without_completing(slack_setup):
    database_path, settings = slack_setup
    save_outbound_slack_message(
        task_id="payment",
        participant_id="kabir",
        channel_id="C123ABC",
        text="Please share progress.",
        message_ts="1700000000.000001",
        thread_ts="1700000000.000001",
        project_id="college-app",
        database_path=database_path,
    )
    ambiguous = FakeProvider(
        {
            "interpretation": InterpretationKind.AMBIGUOUS.value,
            "progress_summary": "The task status is unclear.",
            "proposed_status": TaskStatus.PENDING.value,
            "blocker": None,
            "completion_confirmed": False,
            "needs_clarification": True,
            "clarification_question": "Is the payment flow tested too?",
            "next_action": "Wait for clarification.",
        }
    )

    result = process_slack_event(
        {
            "type": "message",
            "channel": "C123ABC",
            "user": "U12345",
            "text": "Almost done.",
            "ts": "1700000001.000001",
            "thread_ts": "1700000000.000001",
        },
        event_id="EvAmbiguous",
        settings=settings,
        provider=ambiguous,
        database_path=database_path,
    )

    assert result is not None
    assert result.text == "Is the payment flow tested too?"
    with connect(database_path) as connection:
        status = connection.execute(
            "SELECT status FROM tasks WHERE id='payment'"
        ).fetchone()["status"]
    assert status == TaskStatus.PENDING.value


def test_admin_can_create_and_assign_a_task_idempotently(slack_setup):
    database_path, settings = slack_setup
    event = {
        "type": "app_mention",
        "channel": "C123ABC",
        "user": "UADMIN",
        "text": "<@UBOT> create Design checkout | kabir | 2026-11-15 | Checkout works on mobile",
        "ts": "1700000002.000001",
    }

    first = process_slack_event(
        event, event_id="EvCreate", settings=settings, database_path=database_path
    )
    second = process_slack_event(
        event, event_id="EvCreate", settings=settings, database_path=database_path
    )

    assert first is not None and second is not None
    assert first.task_id == second.task_id
    with connect(database_path) as connection:
        created = connection.execute(
            "SELECT title, owner_id, project_id FROM tasks WHERE id=?",
            (first.task_id,),
        ).fetchone()
    assert dict(created) == {
        "title": "Design checkout",
        "owner_id": "kabir",
        "project_id": "college-app",
    }


def test_ai_delegate_selects_linked_member_and_persists_task(slack_setup):
    database_path, settings = slack_setup

    class DelegationProvider(FakeProvider):
        def complete(self, _system_prompt: str, user_prompt: str) -> str:
            context = json.loads(user_prompt)
            assert context["project_id"] == "college-app"
            assert {item["participant_id"] for item in context["candidate_members"]} == {
                "kabir",
                "riya",
            }
            return json.dumps(
                {
                    "title": "Review checkout accessibility",
                    "completion_criteria": "Keyboard and screen reader checks pass",
                    "owner_id": "riya",
                    "deadline": (date.today()).isoformat(),
                }
            )

    result = process_slack_event(
        {
            "type": "app_mention",
            "channel": "C123ABC",
            "user": "UADMIN",
            "text": "<@UBOT> delegate review checkout accessibility",
            "ts": "1700000003.000001",
        },
        event_id="EvDelegate",
        settings=settings,
        provider=DelegationProvider(),
        database_path=database_path,
    )

    assert result is not None
    assert result.task_id
    assert "<@U22222>" in result.text
    with connect(database_path) as connection:
        task = connection.execute(
            "SELECT title, owner_id, completion_criteria FROM tasks WHERE id=?",
            (result.task_id,),
        ).fetchone()
    assert dict(task) == {
        "title": "Review checkout accessibility",
        "owner_id": "riya",
        "completion_criteria": "Keyboard and screen reader checks pass",
    }


def test_bot_mention_uses_nvidia_coordinator_context_without_mutation(slack_setup):
    database_path, settings = slack_setup
    result = process_slack_event(
        {
            "type": "app_mention",
            "channel": "C123ABC",
            "user": "U12345",
            "text": "<@UBOT> what is blocked?",
            "ts": "1700000004.000001",
        },
        event_id="EvMention",
        settings=settings,
        provider=FakeProvider(),
        database_path=database_path,
    )

    assert result is not None
    assert result.text == "The project has one pending task."
    with connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM tasks"
        ).fetchone()[0] == 1


def test_send_slack_reply_uses_stable_client_message_id(slack_setup):
    database_path, _ = slack_setup
    sender = FakeSlackSender()
    from slack_bot import SlackReply

    reply = SlackReply(
        text="The task is on track.",
        channel_id="C123ABC",
        thread_ts="1700000000.000001",
        project_id="college-app",
    )
    first = send_slack_reply(
        event_id="EvIdempotent",
        reply=reply,
        client=sender,
        database_path=database_path,
    )
    second = send_slack_reply(
        event_id="EvIdempotent",
        reply=reply,
        client=sender,
        database_path=database_path,
    )

    assert first.thread_ts == second.thread_ts
    assert sender.sent[0]["client_msg_id"] == sender.sent[1]["client_msg_id"]
    with connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM slack_messages WHERE direction='outbound'"
        ).fetchone()[0] == 1


def test_database_migration_preserves_telegram_records(tmp_path):
    database_path = tmp_path / "legacy.db"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE participants (
                id TEXT PRIMARY KEY, name TEXT NOT NULL,
                google_user_id TEXT UNIQUE, email TEXT UNIQUE,
                telegram_user_id TEXT
            );
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL, title TEXT NOT NULL,
                owner_id TEXT NOT NULL REFERENCES participants(id),
                deadline TEXT NOT NULL, completion_criteria TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending', blocker TEXT,
                last_follow_up_at TEXT
            );
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE,
                task_id TEXT NOT NULL REFERENCES tasks(id),
                participant_id TEXT NOT NULL REFERENCES participants(id),
                direction TEXT NOT NULL, text TEXT NOT NULL, created_at TEXT NOT NULL,
                chat_space_id TEXT, chat_message_name TEXT, chat_thread_name TEXT,
                telegram_chat_id TEXT, telegram_message_id TEXT,
                telegram_thread_id TEXT
            );
            CREATE TABLE status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL REFERENCES tasks(id),
                old_status TEXT NOT NULL, new_status TEXT NOT NULL,
                reason TEXT NOT NULL, source_message_id INTEGER,
                created_at TEXT NOT NULL
            );
            CREATE TABLE telegram_updates (
                update_id INTEGER PRIMARY KEY, payload TEXT NOT NULL,
                status TEXT NOT NULL, attempts INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            INSERT INTO participants VALUES ('p1', 'Member', NULL, NULL, '1001');
            INSERT INTO tasks (
                id, project_id, title, owner_id, deadline, completion_criteria
            ) VALUES ('t1', 'college-app', 'Legacy task', 'p1', '2026-11-01', 'Finish it');
            INSERT INTO messages (
                event_id, task_id, participant_id, direction, text, created_at,
                telegram_chat_id, telegram_message_id
            ) VALUES ('old-event', 't1', 'p1', 'inbound', 'Old update',
                      '2026-10-20T10:00:00+00:00', '-1001', '501');
            INSERT INTO telegram_updates VALUES (
                501, '{"update_id":501}', 'processed', 1,
                '2026-10-20T10:00:00+00:00'
            );
            """
        )

    init_db(database_path)

    with connect(database_path) as connection:
        participant = connection.execute(
            "SELECT telegram_user_id, slack_user_id FROM participants WHERE id='p1'"
        ).fetchone()
        message = connection.execute(
            "SELECT text, telegram_chat_id, slack_channel_id FROM messages WHERE event_id='old-event'"
        ).fetchone()
        queued = connection.execute(
            "SELECT status FROM telegram_updates WHERE update_id=501"
        ).fetchone()
        slack_queue_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='slack_events'"
        ).fetchone()

    assert participant["telegram_user_id"] == "1001"
    assert participant["slack_user_id"] is None
    assert message["text"] == "Old update"
    assert message["telegram_chat_id"] == "-1001"
    assert message["slack_channel_id"] is None
    assert queued["status"] == "processed"
    assert slack_queue_exists is not None
