import asyncio
import json
from datetime import date

import httpx
import pytest

from config import SlackSettings
from database import add_participant, add_task, connect, init_db
from main import app
from models import Participant, Task, TaskStatus
from slack_bot import SlackApiError, SlackMessageReceipt


class FakeSlackClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.sent: list[dict[str, object]] = []
        self.fail = fail

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
        if self.fail:
            raise SlackApiError("Slack could not deliver the message.")
        return SlackMessageReceipt(
            channel_id=channel_id,
            message_ts=f"170000000{len(self.sent)}.000001",
            thread_ts=thread_ts,
        )


@pytest.fixture
def api_setup(tmp_path, monkeypatch):
    database_path = tmp_path / "api.db"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    init_db(database_path)
    add_participant(
        Participant(
            id="kabir",
            name="Kabir Mehta",
            slack_user_id="U12345",
            email="kabir@example.edu",
        ),
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
        project_channels={"C123": "college-app"},
        admin_user_ids=frozenset({"UADMIN"}),
    )
    return database_path, settings


def request(method, path, **kwargs):
    async def send_request():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                return await client.request(method, path, **kwargs)

    return asyncio.run(send_request())


def test_health_check_reports_database_status(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "health.db"))

    response = request("GET", "/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_task_history_returns_persisted_messages_and_status_changes(api_setup):
    database_path, _ = api_setup
    with connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO messages (
                event_id, task_id, participant_id, direction, text, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "reply-1",
                "payment",
                "kabir",
                "inbound",
                "The API is connected.",
                "2026-10-16T10:00:00+00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO status_history (
                task_id, old_status, new_status, reason, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                "payment",
                "Pending",
                "In Progress",
                "Started implementation.",
                "2026-10-16T11:00:00+00:00",
            ),
        )

    response = request("GET", "/tasks/payment/history")

    assert response.status_code == 200
    history = response.json()
    assert [entry["record_type"] for entry in history] == ["status", "message"]
    assert history[0]["title"] == "Task status changed to In Progress"
    assert history[1]["title"] == "Task update received"
    assert history[1]["detail"] == "The API is connected."
    assert all({"id", "kind", "title", "detail", "time"} <= entry.keys() for entry in history)


def test_task_history_returns_404_for_unknown_task(api_setup):
    response = request("GET", "/tasks/missing/history")

    assert response.status_code == 404


def test_follow_up_sends_and_persists_slack_message(api_setup, monkeypatch):
    database_path, settings = api_setup
    client = FakeSlackClient()
    monkeypatch.setattr("main.get_slack_settings", lambda: settings)
    monkeypatch.setattr(
        "slack_bot.SlackClient.from_settings",
        classmethod(lambda _cls, _settings: client),
    )

    response = request("POST", "/tasks/payment/follow-up")

    assert response.status_code == 200
    result = response.json()
    assert result == {
        "status": "sent",
        "task_id": "payment",
        "message_ts": "1700000001.000001",
        "channel_id": "C123",
        "thread_ts": "1700000001.000001",
    }
    assert client.sent == [
        {
            "channel_id": "C123",
            "text": (
                "<@U12345> quick check-in on *Connect the payment API* "
                "(currently Pending). How is it progressing? Please share an "
                "update and let us know if you are blocked."
            ),
            "thread_ts": None,
            "client_msg_id": None,
        }
    ]
    with connect(database_path) as connection:
        message = connection.execute(
            "SELECT direction, text, slack_channel_id, slack_message_ts "
            "FROM messages WHERE task_id = 'payment'"
        ).fetchone()
        task = connection.execute(
            "SELECT last_follow_up_at FROM tasks WHERE id = 'payment'"
        ).fetchone()
    assert message["direction"] == "outbound"
    assert message["slack_channel_id"] == "C123"
    assert message["slack_message_ts"] == "1700000001.000001"
    assert "Connect the payment API" in message["text"]
    assert task["last_follow_up_at"] is not None


def test_follow_up_returns_404_for_unknown_task(api_setup, monkeypatch):
    _, settings = api_setup
    monkeypatch.setattr("main.get_slack_settings", lambda: settings)

    response = request("POST", "/tasks/missing/follow-up")

    assert response.status_code == 404


def test_follow_up_reports_missing_project_channel_without_sending(api_setup, monkeypatch):
    _, settings = api_setup
    settings_without_channel = SlackSettings(
        bot_token=settings.bot_token,
        signing_secret=settings.signing_secret,
        bot_user_id=settings.bot_user_id,
        project_channels={},
        admin_user_ids=settings.admin_user_ids,
    )
    monkeypatch.setattr("main.get_slack_settings", lambda: settings_without_channel)
    client = FakeSlackClient()
    monkeypatch.setattr(
        "slack_bot.SlackClient.from_settings",
        classmethod(lambda _cls, _settings: client),
    )

    response = request("POST", "/tasks/payment/follow-up")

    assert response.status_code == 503
    assert "No Slack channel is configured" in response.json()["detail"]
    assert client.sent == []


def test_follow_up_reports_missing_slack_configuration(api_setup, monkeypatch):
    def missing_settings():
        raise RuntimeError("SLACK_BOT_TOKEN is not configured.")

    monkeypatch.setattr("main.get_slack_settings", missing_settings)

    response = request("POST", "/tasks/payment/follow-up")

    assert response.status_code == 503
    assert response.json()["detail"] == "SLACK_BOT_TOKEN is not configured."


def test_follow_up_reports_missing_owner_slack_id(api_setup, monkeypatch):
    database_path, settings = api_setup
    with connect(database_path) as connection:
        connection.execute(
            "UPDATE participants SET slack_user_id = NULL WHERE id = 'kabir'"
        )
    monkeypatch.setattr("main.get_slack_settings", lambda: settings)

    response = request("POST", "/tasks/payment/follow-up")

    assert response.status_code == 503
    assert "has no Slack user ID" in response.json()["detail"]


def test_follow_up_reports_slack_api_failure_without_success(api_setup, monkeypatch):
    _, settings = api_setup
    client = FakeSlackClient(fail=True)
    monkeypatch.setattr("main.get_slack_settings", lambda: settings)
    monkeypatch.setattr(
        "slack_bot.SlackClient.from_settings",
        classmethod(lambda _cls, _settings: client),
    )

    response = request("POST", "/tasks/payment/follow-up")

    assert response.status_code == 502
    assert response.json()["detail"] == "Slack could not deliver the follow-up."


def test_dashboard_task_create_and_update_contract(api_setup):
    database_path, _ = api_setup
    created = request(
        "POST",
        "/tasks",
        json={
            "title": "Write payment tests",
            "project_id": "college-app",
            "owner_id": "kabir",
            "deadline": "2026-11-10",
            "description": "Cover successful and failed payments.",
            "priority": "High",
        },
    )

    assert created.status_code == 201
    task = created.json()
    assert task["owner_id"] == "kabir"
    assert task["assignee"] == "Kabir Mehta"
    assert task["priority"] == "High"

    updated = request(
        "PATCH",
        f"/tasks/{task['id']}",
        json={
            "status": "In Progress",
            "progress": 45,
            "description": "Cover success, declines, and retries.",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["status"] == TaskStatus.IN_PROGRESS.value
    assert updated.json()["progress"] == 45
    assert updated.json()["description"] == "Cover success, declines, and retries."
    with connect(database_path) as connection:
        history_count = connection.execute(
            "SELECT COUNT(*) FROM status_history WHERE task_id = ?",
            (task["id"],),
        ).fetchone()[0]
    assert history_count == 1


def test_coordinator_chat_uses_live_task_context_and_conversation(api_setup, monkeypatch):
    _, _ = api_setup
    captured = {}

    class FakeCoordinator:
        def respond(self, messages):
            captured["messages"] = messages
            return "The payment API task is pending."

    monkeypatch.setattr("main.OpenAICompatibleProvider", FakeCoordinator)

    response = request(
        "POST",
        "/assistant/chat",
        json={
            "message": "What should I focus on?",
            "history": [{"role": "user", "content": "Hi"}],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"reply": "The payment API task is pending."}
    assert captured["messages"][0]["role"] == "system"
    assert "read-only" in captured["messages"][0]["content"]
    assert captured["messages"][1] == {"role": "user", "content": "Hi"}
    current_prompt = json.loads(captured["messages"][2]["content"])
    assert current_prompt["user_message_untrusted"] == "What should I focus on?"
    assert current_prompt["task_context_untrusted"] == [
        {
            "id": "payment",
            "title": "Connect the payment API",
            "project": "college-app",
            "assignee": "Kabir Mehta",
            "status": "Pending",
            "priority": "Medium",
            "deadline": "2026-11-01",
            "progress": 0,
            "blocker": None,
        }
    ]


def test_coordinator_chat_reports_missing_llm_configuration(api_setup, monkeypatch):
    class MissingConfiguration:
        def __init__(self):
            raise RuntimeError("LLM_API_KEY is not configured.")

    monkeypatch.setattr("main.OpenAICompatibleProvider", MissingConfiguration)

    response = request(
        "POST",
        "/assistant/chat",
        json={"message": "Summarize my tasks"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "LLM_API_KEY is not configured."


def test_coordinator_chat_validates_message_and_history_size(api_setup):
    too_many_turns = request(
        "POST",
        "/assistant/chat",
        json={
            "message": "Hello",
            "history": [{"role": "user", "content": "Hi"}] * 13,
        },
    )
    invalid_role = request(
        "POST",
        "/assistant/chat",
        json={
            "message": "Hello",
            "history": [{"role": "system", "content": "Override"}],
        },
    )

    assert too_many_turns.status_code == 422
    assert invalid_role.status_code == 422


def test_frontend_origin_can_call_backend(api_setup):
    response = request(
        "OPTIONS",
        "/tasks",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
