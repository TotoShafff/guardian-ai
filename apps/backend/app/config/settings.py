"""Application configuration for the Guardian AI backend.

Defines the typed `Settings` model (via pydantic-settings) and a cached
`get_settings()` accessor. Values are read from environment variables and,
when present, from a `.env` file at the repository root. `Settings` is not
instantiated at import time, so importing this module has no side effects
and tests/tooling can freely control the environment before the first call
to `get_settings()`.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/backend/app/config/settings.py -> repository root is four levels up.
_REPO_ROOT_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


class Settings(BaseSettings):
    """Typed application settings, loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Guardian AI API"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str

    ai_provider: str = "mock"
    ai_model: str | None = None
    ai_api_key: str | None = None

    tool_timeout_seconds: int = 30
    provider_timeout_seconds: int = 60
    max_fix_attempts: int = 1

    @field_validator("tool_timeout_seconds", "provider_timeout_seconds")
    @classmethod
    def _validate_positive_timeout(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be greater than zero")
        return value

    @field_validator("max_fix_attempts")
    @classmethod
    def _validate_max_fix_attempts(cls, value: int) -> int:
        if value < 1:
            raise ValueError("must be at least one")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached `Settings` instance built from the current environment."""
    return Settings()
