import pytest

from apps.frontend.config import (
    DEFAULT_API_BASE_URL,
    DEFAULT_TIMEOUT_SECONDS,
    get_frontend_config,
)


def test_get_frontend_config_uses_defaults_when_env_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PITAGORAS_FRONTEND_API_BASE_URL", raising=False)
    monkeypatch.delenv("PITAGORAS_FRONTEND_API_TIMEOUT_SECONDS", raising=False)

    config = get_frontend_config()

    assert config.base_url == DEFAULT_API_BASE_URL
    assert config.timeout_seconds == DEFAULT_TIMEOUT_SECONDS


def test_get_frontend_config_reads_values_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PITAGORAS_FRONTEND_API_BASE_URL", "http://backend.internal:9000")
    monkeypatch.setenv("PITAGORAS_FRONTEND_API_TIMEOUT_SECONDS", "4.5")

    config = get_frontend_config()

    assert config.base_url == "http://backend.internal:9000"
    assert config.timeout_seconds == 4.5
