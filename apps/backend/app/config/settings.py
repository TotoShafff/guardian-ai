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

# Prefer the repository-root `.env` (four levels up from this file in a
# normal checkout: app/config -> app -> backend -> apps -> repo root).
# In the Docker image the package lives at `/app/app/config/...`, which is
# shallower than four parents, so fall back to a non-existent path and rely
# on real environment variables supplied by Compose.
_SETTINGS_PATH = Path(__file__).resolve()
_REPO_ROOT_ENV_FILE = (
    _SETTINGS_PATH.parents[4] / ".env"
    if len(_SETTINGS_PATH.parents) > 4
    else Path("/nonexistent/.env")
)


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

    #: OpenRouter-specific settings, used only when `ai_provider == "openrouter"`
    #: (see `app.providers.openrouter.OpenRouterProvider`). Never read directly
    #: by the provider from the environment — only via this `Settings` object,
    #: constructed in `app/api/dependencies.py`.
    openrouter_api_key: str | None = None
    openrouter_model: str = "deepseek/deepseek-v4-flash:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_seconds: float = 60.0
    openrouter_app_url: str | None = None
    openrouter_app_name: str = "Guardian AI"

    tool_timeout_seconds: int = 30
    max_fix_attempts: int = 1

    @field_validator("tool_timeout_seconds")
    @classmethod
    def _validate_positive_timeout(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be greater than zero")
        return value

    @field_validator("openrouter_timeout_seconds")
    @classmethod
    def _validate_positive_openrouter_timeout(cls, value: float) -> float:
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
