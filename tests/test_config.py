import pytest

from config import get_llm_settings, get_slack_settings


def test_nvidia_llm_defaults(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-nvidia-key")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    settings = get_llm_settings()

    assert settings.api_key == "test-nvidia-key"
    assert settings.base_url == "https://integrate.api.nvidia.com/v1"
    assert settings.model == "openai/gpt-oss-20b"


def test_llm_settings_require_nvidia_api_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="LLM_API_KEY.*NVIDIA API key"):
        get_llm_settings()


def test_slack_settings_parse_channel_mapping(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "signing-secret")
    monkeypatch.setenv("SLACK_PROJECT_CHANNELS", '{"C123ABC":"college-app"}')
    monkeypatch.setenv("SLACK_ADMIN_USER_IDS", "UADMIN")
    monkeypatch.setenv("SLACK_BOT_USER_ID", "UBOT")

    settings = get_slack_settings()

    assert settings.project_channels == {"C123ABC": "college-app"}
    assert settings.admin_user_ids == frozenset({"UADMIN"})
    assert settings.bot_user_id == "UBOT"


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("SLACK_BOT_TOKEN", "bad-token", "beginning with xoxb"),
        ("SLACK_SIGNING_SECRET", "", "not configured"),
        ("SLACK_PROJECT_CHANNELS", "not-json", "valid JSON"),
        ("SLACK_PROJECT_CHANNELS", '{"not-a-channel":"project"}', "channel IDs"),
        ("SLACK_ADMIN_USER_IDS", "1234", "Slack user IDs"),
    ],
)
def test_slack_settings_reject_invalid_configuration(monkeypatch, name, value, message):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "signing-secret")
    monkeypatch.setenv("SLACK_PROJECT_CHANNELS", "{}")
    monkeypatch.setenv("SLACK_ADMIN_USER_IDS", "")
    monkeypatch.delenv("SLACK_BOT_USER_ID", raising=False)
    monkeypatch.setenv(name, value)

    with pytest.raises(RuntimeError, match=message):
        get_slack_settings()
