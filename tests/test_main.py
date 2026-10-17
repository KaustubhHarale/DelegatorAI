import asyncio
from datetime import date

import httpx
import pytest
import httplib2
from googleapiclient.errors import HttpError

import google_chat
from config import GoogleChatSettings
from database import add_participant, add_task, connect, init_db
from google_chat import ChatMessageReceipt
from main import app
from models import Participant, Task, TaskStatus


class FakeChatClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.sent: list[dict[str, object]] = []
        self.fail = fail

    def send_message(
        self,
        *,
        space_id: str,
        text: str,
        thread_name: str | None,
        thread_key: str | None,
    ) -> ChatMessageReceipt:
        self.sent.append(
            {
                "space_id": space_id,
                "text": text,
                "thread_name": thread_name,
                "thread_key": thread_key,
            }
        )
        if self.fail:
            raise RuntimeError("Chat API is unavailable.")
        return ChatMessageReceipt(
            message_name=f"{space_id}/messages/{len(self.sent)}",
            thread_name=thread_name or f"{space_id}/threads/task-thread",
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
            google_user_id="users/12345",
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
    settings = GoogleChatSettings(
        audience="https://example.test/google-chat/events",
        service_account_file=None,
        project_spaces={"college-app": "spaces/payment-team"},
        expected_service_account_email=None,
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
    assert history[0]["detail"] == "Started implementation."
    assert history[0]["kind"] == "update"
    assert history[1]["title"] == "Google Chat reply received"
    assert history[1]["detail"] == "The API is connected."
    assert all({"id", "kind", "title", "detail", "time"} <= entry.keys() for entry in history)


def test_task_history_returns_404_for_unknown_task(api_setup):
    response = request("GET", "/tasks/missing/history")

    assert response.status_code == 404


def test_follow_up_sends_and_persists_chat_message(api_setup, monkeypatch):
    database_path, settings = api_setup
    client = FakeChatClient()
    monkeypatch.setattr("main.get_google_chat_settings", lambda: settings)
    monkeypatch.setattr(
        google_chat.GoogleChatClient,
        "from_settings",
        classmethod(lambda _cls, _settings: client),
    )

    response = request("POST", "/tasks/payment/follow-up")

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "sent"
    assert result["task_id"] == "payment"
    assert result["thread_name"] == "spaces/payment-team/threads/task-thread"
    assert client.sent == [
        {
            "space_id": "spaces/payment-team",
            "text": (
                "<users/12345> Hi Kabir Mehta, quick check-in on "
                "“Connect the payment API” (currently Pending). How is it "
                "progressing? Please share an update and let us know if you’re blocked."
            ),
            "thread_name": None,
            "thread_key": "delegatorai-payment",
        }
    ]
    with connect(database_path) as connection:
        message = connection.execute(
            "SELECT direction, text, chat_space_id, chat_thread_name "
            "FROM messages WHERE task_id = 'payment'"
        ).fetchone()
        task = connection.execute(
            "SELECT last_follow_up_at FROM tasks WHERE id = 'payment'"
        ).fetchone()
    assert message["direction"] == "outbound"
    assert message["chat_space_id"] == "spaces/payment-team"
    assert message["chat_thread_name"] == result["thread_name"]
    assert "Connect the payment API" in message["text"]
    assert task["last_follow_up_at"] is not None


def test_follow_up_returns_404_for_unknown_task(api_setup, monkeypatch):
    _, settings = api_setup
    monkeypatch.setattr("main.get_google_chat_settings", lambda: settings)

    response = request("POST", "/tasks/missing/follow-up")

    assert response.status_code == 404


def test_follow_up_reports_missing_configuration_without_sending(api_setup, monkeypatch):
    _, settings = api_setup
    settings_without_space = GoogleChatSettings(
        audience=settings.audience,
        service_account_file=None,
        project_spaces={},
        expected_service_account_email=None,
    )
    monkeypatch.setattr(
        "main.get_google_chat_settings", lambda: settings_without_space
    )
    client = FakeChatClient()
    monkeypatch.setattr(
        google_chat.GoogleChatClient,
        "from_settings",
        classmethod(lambda _cls, _settings: client),
    )

    response = request("POST", "/tasks/payment/follow-up")

    assert response.status_code == 503
    assert "No Google Chat space" in response.json()["detail"]
    assert client.sent == []


def test_follow_up_reports_missing_google_chat_configuration(api_setup, monkeypatch):
    def missing_settings():
        raise RuntimeError("CHAT_AUDIENCE is not configured.")

    monkeypatch.setattr("main.get_google_chat_settings", missing_settings)

    response = request("POST", "/tasks/payment/follow-up")

    assert response.status_code == 503
    assert response.json()["detail"] == "CHAT_AUDIENCE is not configured."


def test_follow_up_reports_unavailable_credentials(api_setup, monkeypatch, tmp_path):
    _, settings = api_setup
    settings_without_credentials = GoogleChatSettings(
        audience=settings.audience,
        service_account_file=tmp_path / "missing-service-account.json",
        project_spaces=settings.project_spaces,
        expected_service_account_email=None,
    )
    monkeypatch.setattr(
        "main.get_google_chat_settings", lambda: settings_without_credentials
    )

    response = request("POST", "/tasks/payment/follow-up")

    assert response.status_code == 503
    assert "credentials are invalid" in response.json()["detail"]


def test_follow_up_reports_chat_failure_without_success_response(api_setup, monkeypatch):
    _, settings = api_setup
    client = FakeChatClient(fail=True)
    monkeypatch.setattr("main.get_google_chat_settings", lambda: settings)
    monkeypatch.setattr(
        google_chat.GoogleChatClient,
        "from_settings",
        classmethod(lambda _cls, _settings: client),
    )

    response = request("POST", "/tasks/payment/follow-up")

    assert response.status_code == 503
    assert response.json()["detail"] == "Chat API is unavailable."


def test_follow_up_reports_google_chat_api_failure(api_setup, monkeypatch):
    _, settings = api_setup

    class FailedChatClient(FakeChatClient):
        def send_message(self, **kwargs):
            raise HttpError(
                httplib2.Response({"status": "500", "reason": "Server Error"}),
                b"Chat API failure",
            )

    monkeypatch.setattr("main.get_google_chat_settings", lambda: settings)
    monkeypatch.setattr(
        google_chat.GoogleChatClient,
        "from_settings",
        classmethod(lambda _cls, _settings: FailedChatClient()),
    )

    response = request("POST", "/tasks/payment/follow-up")

    assert response.status_code == 502
    assert "could not deliver" in response.json()["detail"]


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
