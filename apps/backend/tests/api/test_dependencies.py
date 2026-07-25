"""Unit tests for AI provider selection in `app.api.dependencies`.

These exercise `build_ai_provider()` directly, as a plain function of
`Settings`, without going through FastAPI's dependency injection
machinery, a database, or any network access.
"""

import pytest

from app.api.dependencies import build_ai_provider
from app.config.settings import Settings
from app.providers.exceptions import AIProviderConfigurationError
from app.providers.gemini import GeminiProvider
from app.providers.mock import MockProvider
from app.providers.openrouter import OpenRouterProvider

_DATABASE_URL = "postgresql://user:pass@localhost:5432/guardian"


def _make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {"database_url": _DATABASE_URL}
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)  # type: ignore[arg-type]


def test_default_settings_select_mock_provider() -> None:
    settings = _make_settings()

    provider = build_ai_provider(settings)

    assert isinstance(provider, MockProvider)


def test_ai_provider_mock_selects_mock_provider() -> None:
    settings = _make_settings(ai_provider="mock")

    provider = build_ai_provider(settings)

    assert isinstance(provider, MockProvider)


def test_ai_provider_openrouter_selects_openrouter_provider() -> None:
    settings = _make_settings(
        ai_provider="openrouter",
        openrouter_api_key="test-key",
        openrouter_model="cvidia/nemotron-3-ultra:free",
    )

    provider = build_ai_provider(settings)

    assert isinstance(provider, OpenRouterProvider)


def test_ai_provider_openrouter_is_case_insensitive() -> None:
    settings = _make_settings(ai_provider="OpenRouter")

    provider = build_ai_provider(settings)

    assert isinstance(provider, OpenRouterProvider)


def test_openrouter_provider_is_built_from_settings() -> None:
    settings = _make_settings(
        ai_provider="openrouter",
        openrouter_api_key="test-key",
        openrouter_model="some/model",
        openrouter_base_url="https://example.com/api/v1",
        openrouter_timeout_seconds=12.5,
        openrouter_app_name="Custom App",
        openrouter_app_url="https://custom.example.com",
    )

    provider = build_ai_provider(settings)

    assert isinstance(provider, OpenRouterProvider)


def test_ai_provider_gemini_selects_gemini_provider() -> None:
    settings = _make_settings(
        ai_provider="gemini",
        gemini_api_key="gemini-test-key",
        gemini_model="gemini-3.5-flash-lite",
    )

    provider = build_ai_provider(settings)

    assert isinstance(provider, GeminiProvider)


def test_ai_provider_gemini_is_case_insensitive() -> None:
    settings = _make_settings(ai_provider="Gemini")

    provider = build_ai_provider(settings)

    assert isinstance(provider, GeminiProvider)


def test_gemini_provider_is_built_from_settings() -> None:
    settings = _make_settings(
        ai_provider="gemini",
        gemini_api_key="gemini-test-key",
        gemini_model="gemini-custom-model",
        gemini_base_url="https://example.com/gemini/openai",
        gemini_timeout_seconds=12.5,
    )

    provider = build_ai_provider(settings)

    assert isinstance(provider, GeminiProvider)
    assert provider._api_key == "gemini-test-key"
    assert provider._model == "gemini-custom-model"
    assert provider._base_url == "https://example.com/gemini/openai"
    assert provider._timeout_seconds == 12.5


def test_unsupported_ai_provider_raises_a_clear_configuration_error() -> None:
    settings = _make_settings(ai_provider="anthropic")

    with pytest.raises(AIProviderConfigurationError, match="anthropic"):
        build_ai_provider(settings)


def test_ai_provider_selection_ignores_surrounding_whitespace() -> None:
    settings = _make_settings(ai_provider="  OpenRouter  ")

    provider = build_ai_provider(settings)

    assert isinstance(provider, OpenRouterProvider)
