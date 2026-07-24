"""Unit tests for the application settings module."""

from collections.abc import Iterator

import pytest
from pydantic import ValidationError

from app.config.settings import Settings, get_settings

_VALID_DATABASE_URL = "postgresql://user:pass@localhost:5432/guardian"


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    """Ensure each test observes a fresh `Settings` build, not a cached one."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_defaults_match_documented_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _VALID_DATABASE_URL)

    settings = get_settings()

    assert settings.app_name == "Guardian AI API"
    assert settings.app_version == "0.1.0"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.ai_provider == "mock"
    assert settings.ai_model is None
    assert settings.ai_api_key is None
    assert settings.tool_timeout_seconds == 30
    assert settings.provider_timeout_seconds == 60
    assert settings.max_fix_attempts == 1


def test_environment_variables_override_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", _VALID_DATABASE_URL)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("AI_MODEL", "gpt-test")
    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setenv("TOOL_TIMEOUT_SECONDS", "15")
    monkeypatch.setenv("PROVIDER_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("MAX_FIX_ATTEMPTS", "2")

    settings = get_settings()

    assert settings.database_url == _VALID_DATABASE_URL
    assert settings.environment == "production"
    assert settings.log_level == "DEBUG"
    assert settings.ai_provider == "openai"
    assert settings.ai_model == "gpt-test"
    assert settings.ai_api_key == "test-key"
    assert settings.tool_timeout_seconds == 15
    assert settings.provider_timeout_seconds == 45
    assert settings.max_fix_attempts == 2


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _VALID_DATABASE_URL)

    first = get_settings()
    second = get_settings()

    assert first is second


def test_unknown_environment_variables_are_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", _VALID_DATABASE_URL)
    monkeypatch.setenv("SOME_UNRELATED_VARIABLE", "unexpected-value")

    settings = get_settings()

    assert settings.database_url == _VALID_DATABASE_URL


def test_missing_database_url_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "timeout_field", ["TOOL_TIMEOUT_SECONDS", "PROVIDER_TIMEOUT_SECONDS"]
)
def test_non_positive_timeout_is_rejected(
    monkeypatch: pytest.MonkeyPatch, timeout_field: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", _VALID_DATABASE_URL)
    monkeypatch.setenv(timeout_field, "0")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_max_fix_attempts_below_one_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", _VALID_DATABASE_URL)
    monkeypatch.setenv("MAX_FIX_ATTEMPTS", "0")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
