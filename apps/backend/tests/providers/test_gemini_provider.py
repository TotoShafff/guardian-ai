"""Unit tests for `GeminiProvider`.

Every test injects an `httpx.Client` built on `httpx.MockTransport`, so
none of them make a real network request, require network access, or need
a real Gemini API key.
"""

import json
from collections.abc import Callable
from uuid import uuid4

import httpx
import pytest

from app.domain.models import Evidence, EvidenceSeverity, EvidenceSource, Finding
from app.providers.exceptions import (
    AIProviderConfigurationError,
    AIProviderRequestError,
    AIProviderResponseError,
)
from app.providers.gemini import GeminiProvider

_MODEL = "gemini-3.5-flash-lite"
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
_API_KEY = "test-gemini-api-key"


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _make_provider(
    handler: Callable[[httpx.Request], httpx.Response] | None = None,
    api_key: str = _API_KEY,
    client: httpx.Client | None = None,
) -> GeminiProvider:
    if client is None and handler is not None:
        client = _client(handler)
    return GeminiProvider(
        api_key=api_key,
        model=_MODEL,
        base_url=_BASE_URL,
        timeout_seconds=5.0,
        client=client,
    )


def _make_fixable_finding(**overrides: object) -> Finding:
    defaults: dict[str, object] = {
        "review_id": uuid4(),
        "severity": EvidenceSeverity.BLOCKING,
        "title": "Importación no utilizada",
        "description": "El módulo `os` fue importado, pero no se utiliza.",
        "is_fixable": True,
    }
    defaults.update(overrides)
    return Finding(**defaults)  # type: ignore[arg-type]


def _make_evidence(**overrides: object) -> Evidence:
    defaults: dict[str, object] = {
        "review_id": uuid4(),
        "source": EvidenceSource.RUFF,
        "severity": EvidenceSeverity.BLOCKING,
        "category": "F401",
        "message": "`os` imported but unused",
    }
    defaults.update(overrides)
    return Evidence(**defaults)  # type: ignore[arg-type]


def _success_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "gen-1",
            "choices": [{"message": {"role": "assistant", "content": content}}],
        },
    )


# --- successful completion mechanics --------------------------------------


def test_propose_fix_returns_the_assistant_content_verbatim() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _success_response("--- a\n+++ b\n")

    provider = _make_provider(handler)

    result = provider.propose_fix("code", _make_fixable_finding(), 1)

    assert result == "--- a\n+++ b\n"


def test_propose_fix_sends_the_request_to_the_correct_url() -> None:
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return _success_response("patch")

    provider = _make_provider(handler)

    provider.propose_fix("code", _make_fixable_finding(), 1)

    assert seen_urls == [f"{_BASE_URL}/chat/completions"]


def test_propose_fix_sends_a_bearer_authorization_header() -> None:
    seen_headers: list[httpx.Headers] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers)
        return _success_response("patch")

    provider = _make_provider(handler)

    provider.propose_fix("code", _make_fixable_finding(), 1)

    assert seen_headers[0]["authorization"] == f"Bearer {_API_KEY}"


def test_propose_fix_sends_the_configured_model() -> None:
    seen_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_bodies.append(json.loads(request.content))
        return _success_response("patch")

    provider = _make_provider(handler)

    provider.propose_fix("code", _make_fixable_finding(), 1)

    assert seen_bodies[0]["model"] == _MODEL


def test_propose_fix_translates_inputs_into_spanish_chat_messages() -> None:
    seen_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_bodies.append(json.loads(request.content))
        return _success_response("patch")

    provider = _make_provider(handler)
    finding = _make_fixable_finding(title="Importación no utilizada")

    provider.propose_fix("some code", finding, 1)

    messages = seen_bodies[0]["messages"]
    assert isinstance(messages, list)
    assert [message["role"] for message in messages] == ["system", "user"]
    assert "exclusively in Spanish" in messages[0]["content"]
    assert "some code" in messages[1]["content"]
    assert "Importación no utilizada" in messages[1]["content"]
    assert "Hallazgo a corregir" in messages[1]["content"]
    assert "Título:" in messages[1]["content"]
    assert "Descripción:" in messages[1]["content"]


def test_propose_fix_sends_stream_false() -> None:
    seen_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_bodies.append(json.loads(request.content))
        return _success_response("patch")

    provider = _make_provider(handler)

    provider.propose_fix("code", _make_fixable_finding(), 1)

    assert seen_bodies[0]["stream"] is False


# --- error handling --------------------------------------------------------


def test_missing_api_key_raises_configuration_error_before_sending() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return _success_response("patch")

    provider = _make_provider(handler, api_key="")

    with pytest.raises(AIProviderConfigurationError):
        provider.propose_fix("code", _make_fixable_finding(), 1)

    assert called is False


def test_blank_api_key_raises_configuration_error() -> None:
    provider = _make_provider(lambda request: _success_response("patch"), api_key="   ")

    with pytest.raises(AIProviderConfigurationError):
        provider.propose_fix("code", _make_fixable_finding(), 1)


def test_network_error_raises_ai_provider_request_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = _make_provider(handler)

    with pytest.raises(AIProviderRequestError) as exc_info:
        provider.propose_fix("code", _make_fixable_finding(), 1)

    assert _API_KEY not in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_timeout_raises_ai_provider_request_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    provider = _make_provider(handler)

    with pytest.raises(AIProviderRequestError) as exc_info:
        provider.propose_fix("code", _make_fixable_finding(), 1)

    assert "timed out" in str(exc_info.value).lower() or exc_info.value.__cause__ is not None
    assert _API_KEY not in str(exc_info.value)


@pytest.mark.parametrize("status_code", [400, 401, 429, 500])
def test_non_2xx_response_raises_ai_provider_request_error_with_status_code(
    status_code: int,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": "provider error"})

    provider = _make_provider(handler)

    with pytest.raises(AIProviderRequestError) as exc_info:
        provider.propose_fix("code", _make_fixable_finding(), 1)

    assert exc_info.value.status_code == status_code
    assert _API_KEY not in str(exc_info.value)


def test_invalid_json_response_raises_ai_provider_response_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json at all")

    provider = _make_provider(handler)

    with pytest.raises(AIProviderResponseError):
        provider.propose_fix("code", _make_fixable_finding(), 1)


def test_missing_choices_raises_ai_provider_response_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "gen-1"})

    provider = _make_provider(handler)

    with pytest.raises(AIProviderResponseError):
        provider.propose_fix("code", _make_fixable_finding(), 1)


def test_missing_message_raises_ai_provider_response_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"index": 0}]})

    provider = _make_provider(handler)

    with pytest.raises(AIProviderResponseError):
        provider.propose_fix("code", _make_fixable_finding(), 1)


def test_non_string_content_raises_ai_provider_response_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": 123}}]})

    provider = _make_provider(handler)

    with pytest.raises(AIProviderResponseError):
        provider.propose_fix("code", _make_fixable_finding(), 1)


def test_blank_content_raises_ai_provider_response_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _success_response("   ")

    provider = _make_provider(handler)

    with pytest.raises(AIProviderResponseError):
        provider.propose_fix("code", _make_fixable_finding(), 1)


def test_error_messages_never_include_the_api_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    provider = _make_provider(handler, api_key="super-secret-gemini-key")

    with pytest.raises(AIProviderRequestError) as exc_info:
        provider.propose_fix("code", _make_fixable_finding(), 1)

    assert "super-secret-gemini-key" not in str(exc_info.value)


# --- propose_fix's existing AIProvider contract -----------------------------


def test_propose_fix_returns_empty_string_for_non_fixable_finding_without_a_request() -> (
    None
):
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return _success_response("patch")

    provider = _make_provider(handler)
    finding = _make_fixable_finding(is_fixable=False)

    result = provider.propose_fix("code", finding, 1)

    assert result == ""
    assert called is False


@pytest.mark.parametrize("attempt_number", [0, -1])
def test_propose_fix_rejects_attempt_number_below_one(attempt_number: int) -> None:
    provider = _make_provider(lambda request: _success_response("patch"))

    with pytest.raises(ValueError, match="attempt_number"):
        provider.propose_fix("code", _make_fixable_finding(), attempt_number)


# --- analyze_code ------------------------------------------------------------


def test_analyze_code_returns_empty_tuple_without_a_request_when_evidence_is_empty() -> (
    None
):
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return _success_response("[]")

    provider = _make_provider(handler)

    result = provider.analyze_code("code", ())

    assert result == ()
    assert called is False


def test_analyze_code_parses_spanish_findings_from_a_json_array_response() -> None:
    evidence = (_make_evidence(),)

    def handler(request: httpx.Request) -> httpx.Response:
        return _success_response(
            json.dumps(
                [
                    {
                        "severity": "blocking",
                        "title": "Falta validar discount_percent",
                        "description": (
                            "La función no rechaza valores de discount_percent "
                            "fuera del rango 0..100."
                        ),
                        "is_fixable": True,
                        "evidence_indices": [0],
                    }
                ]
            )
        )

    provider = _make_provider(handler)

    [finding] = provider.analyze_code("code", evidence)

    assert finding.review_id == evidence[0].review_id
    assert finding.severity == EvidenceSeverity.BLOCKING
    assert finding.title == "Falta validar discount_percent"
    assert "discount_percent" in finding.description
    assert finding.is_fixable is True
    assert finding.evidence_ids == (evidence[0].id,)


def test_analyze_code_prompt_requires_spanish_output() -> None:
    evidence = (_make_evidence(),)
    seen_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_bodies.append(json.loads(request.content))
        return _success_response("[]")

    provider = _make_provider(handler)

    provider.analyze_code("código de ejemplo", evidence)

    messages = seen_bodies[0]["messages"]
    assert "exclusively in Spanish" in messages[0]["content"]
    assert "Código bajo revisión" in messages[1]["content"]
    assert "Evidencia determinística" in messages[1]["content"]
    assert "F401" in messages[1]["content"]


def test_analyze_code_prompt_includes_auto_fix_criteria() -> None:
    evidence = (_make_evidence(),)
    seen_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_bodies.append(json.loads(request.content))
        return _success_response("[]")

    provider = _make_provider(handler)

    provider.analyze_code("código de ejemplo", evidence)

    system_prompt = seen_bodies[0]["messages"][0]["content"]
    assert "CRITERIO DE AUTO-CORRECCIÓN" in system_prompt
    assert "is_fixable" in system_prompt
    assert "discount_percent" in system_prompt
    assert "imports sin usar" in system_prompt
    assert "rediseños amplios" in system_prompt
    assert "No fuerces todos los hallazgos a ser corregibles" in system_prompt
    assert "exclusively in Spanish" in system_prompt
    assert "F401" in system_prompt
    assert "ValueError" in system_prompt


def test_analyze_code_skips_malformed_entries() -> None:
    evidence = (_make_evidence(),)

    def handler(request: httpx.Request) -> httpx.Response:
        return _success_response(
            json.dumps(
                [
                    {"title": "faltan otros campos requeridos"},
                    {
                        "severity": "info",
                        "title": "Entrada válida",
                        "description": "descripción",
                        "is_fixable": False,
                        "evidence_indices": [],
                    },
                ]
            )
        )

    provider = _make_provider(handler)

    findings = provider.analyze_code("code", evidence)

    assert len(findings) == 1
    assert findings[0].title == "Entrada válida"


def test_analyze_code_raises_response_error_when_content_is_not_a_json_array() -> None:
    evidence = (_make_evidence(),)

    def handler(request: httpx.Request) -> httpx.Response:
        return _success_response("this is not json")

    provider = _make_provider(handler)

    with pytest.raises(AIProviderResponseError):
        provider.analyze_code("code", evidence)


def test_analyze_code_returns_empty_tuple_for_an_empty_json_array_response() -> None:
    evidence = (_make_evidence(),)

    def handler(request: httpx.Request) -> httpx.Response:
        return _success_response("[]")

    provider = _make_provider(handler)

    assert provider.analyze_code("code", evidence) == ()


def test_gemini_provider_does_not_create_a_persistent_client() -> None:
    provider = GeminiProvider(
        api_key=_API_KEY,
        model=_MODEL,
        base_url=_BASE_URL,
        timeout_seconds=5.0,
    )

    assert provider._client is None


def test_api_key_is_stripped_before_sending() -> None:
    seen_headers: list[httpx.Headers] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers)
        return _success_response("patch")

    provider = _make_provider(handler, api_key="  test-gemini-api-key  ")

    provider.propose_fix("code", _make_fixable_finding(), 1)

    assert seen_headers[0]["authorization"] == "Bearer test-gemini-api-key"
