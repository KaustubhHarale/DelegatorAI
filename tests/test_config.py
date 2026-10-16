import pytest

from config import get_llm_settings


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
