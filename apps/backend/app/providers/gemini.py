"""Real `AIProvider` adapter backed by Gemini's OpenAI-compatible API.

`GeminiProvider` calls Google's Generative Language OpenAI-compatible
`/chat/completions` endpoint and translates the response into the domain
objects expected by the workflow. Auth, request shaping, and error
translation stay isolated here; callers depend only on `AIProvider`.
"""

import json
from uuid import UUID

import httpx

from app.domain.models import Evidence, EvidenceSeverity, Finding
from app.providers.base import AIProvider
from app.providers.exceptions import (
    AIProviderConfigurationError,
    AIProviderRequestError,
    AIProviderResponseError,
)

_CHAT_COMPLETIONS_PATH = "/chat/completions"

_LANGUAGE_RULES = (
    "Respond exclusively in Spanish for all human-readable text "
    "(titles, descriptions, explanations, and any rationale).\n"
    "Do not translate code identifiers, function names, variables, file "
    "names, paths, diagnostic codes (e.g. F401), or exception names "
    "(e.g. ValueError).\n"
    "Patches and code blocks must remain valid code and must not be "
    "translated.\n"
)

_AUTO_FIX_CRITERIA = (
    "CRITERIO DE AUTO-CORRECCIÓN\n\n"
    "Marcá un hallazgo como auto-corregible (`is_fixable: true`) cuando "
    "pueda resolverse con un cambio local, pequeño y seguro en el código "
    "mostrado, sin requerir rediseñar el sistema ni conocer archivos "
    "externos no provistos.\n\n"
    "Ejemplos que normalmente deben considerarse auto-corregibles:\n"
    "- imports sin usar;\n"
    "- validaciones de rango;\n"
    "- guard clauses;\n"
    "- validaciones faltantes cubiertas por tests existentes;\n"
    "- errores simples detectados por Ruff;\n"
    "- condiciones faltantes;\n"
    "- excepciones esperadas por tests;\n"
    "- cambios pequeños en una única función.\n\n"
    "Ejemplos que normalmente NO deben considerarse auto-corregibles:\n"
    "- rediseños amplios;\n"
    "- cambios de arquitectura;\n"
    "- modificaciones que afecten contratos externos;\n"
    "- problemas que requieran conocer varios archivos no provistos;\n"
    "- cambios con efectos secundarios inciertos;\n"
    "- problemas donde no exista suficiente contexto para producir un "
    "patch seguro.\n\n"
    "Para este escenario concreto, una validación faltante de "
    "discount_percent cubierta por tests existentes debe considerarse "
    "auto-corregible.\n\n"
    "No fuerces todos los hallazgos a ser corregibles. Solo los que "
    "cumplan el criterio anterior."
)

_ANALYZE_SYSTEM_PROMPT = (
    "You are a meticulous code-review assistant for Guardian AI. Given a "
    "code snippet and a numbered list of deterministic evidence items "
    "already collected about it, identify additional semantic findings a "
    "linter or test runner would miss (e.g. logic errors, security issues, "
    "unclear naming, missing validation).\n\n"
    f"{_LANGUAGE_RULES}\n"
    f"{_AUTO_FIX_CRITERIA}\n\n"
    "Respond with ONLY a JSON array (no prose, no markdown code fences). "
    "Each element must be an object with exactly these fields:\n"
    '  "severity": one of "blocking", "non_blocking", "info" '
    "(keep these exact English enum values)\n"
    '  "title": a short human-readable title in Spanish\n'
    '  "description": a fuller explanation in Spanish\n'
    '  "is_fixable": true or false\n'
    '  "evidence_indices": a possibly empty array of the 0-based indices '
    "from the numbered evidence list that this finding relates to\n\n"
    "If there are no additional findings, respond with exactly: []"
)

_PROPOSE_FIX_SYSTEM_PROMPT = (
    "You are a precise code-fixing assistant for Guardian AI. Given a code "
    "snippet and one specific finding about it, propose a single corrected "
    "version of the relevant code as a unified diff/patch.\n\n"
    f"{_LANGUAGE_RULES}\n"
    "Respond with ONLY the patch text (no prose, no markdown code fences). "
    "The patch itself must remain valid code and must not be translated."
)


class GeminiProvider(AIProvider):
    """`AIProvider` adapter calling Gemini's OpenAI-compatible chat endpoint."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client

    def analyze_code(
        self,
        code: str,
        evidence: tuple[Evidence, ...],
    ) -> tuple[Finding, ...]:
        """Ask the model for semantic findings related to deterministic evidence."""
        if not evidence:
            return ()

        review_id = evidence[0].review_id
        user_prompt = self._build_analysis_prompt(code, evidence)
        content = self._complete(_ANALYZE_SYSTEM_PROMPT, user_prompt)

        return self._parse_findings(content, review_id, evidence)

    def propose_fix(
        self,
        code: str,
        finding: Finding,
        attempt_number: int,
    ) -> str:
        """Ask the model for a unified diff addressing one finding."""
        if attempt_number < 1:
            raise ValueError("attempt_number must be at least 1")

        if not finding.is_fixable:
            return ""

        user_prompt = self._build_fix_prompt(code, finding, attempt_number)
        return self._complete(_PROPOSE_FIX_SYSTEM_PROMPT, user_prompt)

    def _send_request(
        self,
        *,
        headers: dict[str, str],
        body: dict[str, object],
    ) -> httpx.Response:
        """Send one request using an injected client or a short-lived client."""
        url = f"{self._base_url}{_CHAT_COMPLETIONS_PATH}"

        if self._client is not None:
            return self._client.post(
                url,
                headers=headers,
                json=body,
                timeout=self._timeout_seconds,
            )

        with httpx.Client(timeout=self._timeout_seconds) as client:
            return client.post(
                url,
                headers=headers,
                json=body,
            )

    def _complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send one chat completion request and return assistant text."""
        if not self._api_key or not self._api_key.strip():
            raise AIProviderConfigurationError("Gemini API key is not configured")

        api_key = self._api_key.strip()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        body: dict[str, object] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }

        try:
            response = self._send_request(headers=headers, body=body)
        except httpx.TimeoutException as exc:
            raise AIProviderRequestError("Gemini request timed out") from exc
        except httpx.HTTPError as exc:
            raise AIProviderRequestError(
                f"Gemini request failed: {exc.__class__.__name__}"
            ) from exc

        if not 200 <= response.status_code < 300:
            raise AIProviderRequestError(
                f"Gemini returned HTTP {response.status_code}",
                status_code=response.status_code,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise AIProviderResponseError(
                "Gemini response was not valid JSON"
            ) from exc

        return self._extract_content(payload)

    @staticmethod
    def _extract_content(payload: object) -> str:
        """Extract and validate assistant content from a Gemini response."""
        if not isinstance(payload, dict):
            raise AIProviderResponseError("Gemini response was not a JSON object")

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise AIProviderResponseError("Gemini response has no choices")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise AIProviderResponseError("Gemini response choice was malformed")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise AIProviderResponseError("Gemini response has no message")

        content = message.get("content")
        if not isinstance(content, str) or content.strip() == "":
            raise AIProviderResponseError(
                "Gemini response message has no textual content"
            )

        return content

    @staticmethod
    def _build_analysis_prompt(
        code: str,
        evidence: tuple[Evidence, ...],
    ) -> str:
        """Build the semantic-analysis user prompt."""
        evidence_lines = "\n".join(
            f"{index}. [{item.source.value}/{item.severity.value}] "
            f"{item.category}: {item.message}"
            for index, item in enumerate(evidence)
        )

        return (
            "Código bajo revisión:\n"
            f"```\n{code}\n```\n\n"
            "Evidencia determinística ya recopilada:\n"
            f"{evidence_lines}"
        )

    @staticmethod
    def _build_fix_prompt(
        code: str,
        finding: Finding,
        attempt_number: int,
    ) -> str:
        """Build the fix-proposal user prompt."""
        return (
            "Código bajo revisión:\n"
            f"```\n{code}\n```\n\n"
            f"Hallazgo a corregir (intento {attempt_number}):\n"
            f"- Título: {finding.title}\n"
            f"- Descripción: {finding.description}\n"
        )

    def _parse_findings(
        self,
        content: str,
        review_id: UUID,
        evidence: tuple[Evidence, ...],
    ) -> tuple[Finding, ...]:
        """Parse the model JSON response into domain `Finding` objects."""
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AIProviderResponseError(
                "Gemini analysis response was not valid JSON"
            ) from exc

        if not isinstance(parsed, list):
            raise AIProviderResponseError(
                "Gemini analysis response was not a JSON array"
            )

        findings = [
            finding
            for entry in parsed
            if (
                finding := self._finding_from_entry(
                    entry,
                    review_id,
                    evidence,
                )
            )
            is not None
        ]

        return tuple(findings)

    @staticmethod
    def _finding_from_entry(
        entry: object,
        review_id: UUID,
        evidence: tuple[Evidence, ...],
    ) -> Finding | None:
        """Build one `Finding` from a JSON entry, or return `None` if invalid."""
        if not isinstance(entry, dict):
            return None

        title = entry.get("title")
        description = entry.get("description")
        is_fixable = entry.get("is_fixable")
        severity_value = entry.get("severity")
        indices = entry.get("evidence_indices", [])

        if not isinstance(title, str) or title.strip() == "":
            return None

        if not isinstance(description, str):
            return None

        if not isinstance(is_fixable, bool):
            return None

        if not isinstance(severity_value, str):
            return None

        try:
            severity = EvidenceSeverity(severity_value)
        except ValueError:
            return None

        if not isinstance(indices, list):
            indices = []

        evidence_ids = tuple(
            evidence[index].id
            for index in indices
            if isinstance(index, int) and 0 <= index < len(evidence)
        )

        return Finding(
            review_id=review_id,
            evidence_ids=evidence_ids,
            severity=severity,
            title=title,
            description=description,
            is_fixable=is_fixable,
        )
