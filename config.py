import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def get_database_path() -> Path:
    return Path(os.environ.get("DATABASE_PATH", "delegatorai.db"))


@dataclass(frozen=True)
class LLMSettings:
    api_key: str
    base_url: str
    model: str


def get_llm_settings() -> LLMSettings:
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "LLM_API_KEY is not configured. Set it to your NVIDIA API key "
            "in the environment or .env file."
        )
    return LLMSettings(
        api_key=api_key,
        base_url=os.environ.get(
            "LLM_BASE_URL", "https://integrate.api.nvidia.com/v1"
        ),
        model=os.environ.get("LLM_MODEL", "openai/gpt-oss-20b"),
    )


@dataclass(frozen=True)
class SlackSettings:
    bot_token: str
    signing_secret: str
    bot_user_id: str | None
    project_channels: dict[str, str]
    admin_user_ids: frozenset[str]


def get_slack_settings() -> SlackSettings:
    bot_token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "").strip()
    if not bot_token.startswith("xoxb-"):
        raise RuntimeError("SLACK_BOT_TOKEN must be a Slack bot token beginning with xoxb-.")
    if not signing_secret:
        raise RuntimeError("SLACK_SIGNING_SECRET is not configured.")

    project_channels_setting = os.environ.get("SLACK_PROJECT_CHANNELS", "{}")
    try:
        project_channels = json.loads(project_channels_setting)
    except json.JSONDecodeError as exc:
        raise RuntimeError("SLACK_PROJECT_CHANNELS must be valid JSON.") from exc
    if not isinstance(project_channels, dict) or not all(
        isinstance(project_id, str)
        and project_id
        and isinstance(channel_id, str)
        and re.fullmatch(r"[CG][A-Z0-9]+", channel_id) is not None
        for channel_id, project_id in project_channels.items()
    ):
        raise RuntimeError(
            "SLACK_PROJECT_CHANNELS must map Slack channel IDs to project IDs."
        )
    admin_user_ids = _parse_slack_user_ids("SLACK_ADMIN_USER_IDS")
    bot_user_id = os.environ.get("SLACK_BOT_USER_ID", "").strip() or None
    if bot_user_id is not None and re.fullmatch(r"[UW][A-Z0-9]+", bot_user_id) is None:
        raise RuntimeError("SLACK_BOT_USER_ID must be a Slack user ID.")
    return SlackSettings(
        bot_token=bot_token,
        signing_secret=signing_secret,
        bot_user_id=bot_user_id,
        project_channels=project_channels,
        admin_user_ids=admin_user_ids,
    )


def _parse_slack_user_ids(name: str) -> frozenset[str]:
    raw_value = os.environ.get(name, "").strip()
    if not raw_value:
        return frozenset()
    values = {value.strip() for value in raw_value.split(",") if value.strip()}
    if not all(re.fullmatch(r"[UW][A-Z0-9]+", value) for value in values):
        raise RuntimeError(f"{name} must contain comma-separated Slack user IDs.")
    return frozenset(values)
