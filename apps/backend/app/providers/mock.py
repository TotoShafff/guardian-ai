"""Deterministic mock `AIProvider` implementation.

`MockProvider` requires no network access, no API key, and no vendor SDK. It
exists so the orchestrator, the Decision Agent, and tests can exercise the
full agent workflow without a real LLM (see `docs/ARCHITECTURE.md` Section 9
and `docs/DECISIONS.md` ADR-010). Both methods are pure functions of their
inputs: the same call always produces the same semantically equivalent
output, which is what makes this provider suitable for tests and for local
runs without a configured provider.

Human-facing titles and descriptions are produced in Spanish; diagnostic
codes, paths, and patch content keep their original technical form.
"""

from app.domain.models import Evidence, Finding
from app.providers.base import AIProvider

#: Maximum length of the message portion embedded in a Finding's title,
#: to keep titles skimmable; the full message is always kept in the description.
_TITLE_MESSAGE_MAX_LENGTH = 100

#: Known English evidence messages → Spanish human-readable equivalents.
_KNOWN_MESSAGE_TRANSLATIONS: dict[str, str] = {
    "`os` imported but unused": (
        "El módulo `os` fue importado, pero no se utiliza."
    ),
    "Failed: DID NOT RAISE ValueError": (
        "La prueba esperaba que se lanzara ValueError, "
        "pero la excepción no ocurrió."
    ),
    "The file is executable but no shebang is present": (
        "El archivo figura como ejecutable, pero no contiene una línea shebang."
    ),
}


class MockProvider(AIProvider):
    """Deterministic `AIProvider` that turns `Evidence` into `Finding`s 1:1."""

    def analyze_code(
        self,
        code: str,
        evidence: tuple[Evidence, ...],
    ) -> tuple[Finding, ...]:
        """Convert each `Evidence` item into exactly one `Finding`, in order.

        `code` is accepted for interface compatibility but is not inspected:
        this mock never performs real semantic analysis, it only relabels
        the deterministic evidence it is given.
        """
        return tuple(self._to_finding(item) for item in evidence)

    def propose_fix(
        self,
        code: str,
        finding: Finding,
        attempt_number: int,
    ) -> str:
        """Return a deterministic, diff-like placeholder correction.

        Returns an empty string when `finding.is_fixable` is False. `code`
        is accepted for interface compatibility but is not inspected or
        modified: this mock never touches files, executes tools, or calls
        an external service. Patch text stays as code/diff content.
        """
        if attempt_number < 1:
            raise ValueError("attempt_number must be at least 1")
        if not finding.is_fixable:
            return ""

        return (
            "--- a/finding\n"
            "+++ b/finding\n"
            f"@@ MockProvider fix attempt {attempt_number} for: {finding.title} @@\n"
            "- # TODO: original code related to this finding\n"
            f"+ # TODO: placeholder correction (attempt {attempt_number}) "
            f"for: {finding.title}\n"
        )

    @staticmethod
    def _human_message(message: str) -> str:
        """Return a Spanish message for known English tool output, else original."""
        return _KNOWN_MESSAGE_TRANSLATIONS.get(message, message)

    @staticmethod
    def _to_finding(evidence: Evidence) -> Finding:
        """Build a `Finding` for one `Evidence` item, preserving its identity/severity."""
        return Finding(
            review_id=evidence.review_id,
            evidence_ids=(evidence.id,),
            severity=evidence.severity,
            title=MockProvider._build_title(evidence),
            description=MockProvider._build_description(evidence),
            is_fixable=evidence.suggested_fix is not None,
        )

    @staticmethod
    def _build_title(evidence: Evidence) -> str:
        """Build a concise Spanish title from the evidence's category and message."""
        message = MockProvider._human_message(evidence.message.strip())
        if len(message) > _TITLE_MESSAGE_MAX_LENGTH:
            message = message[: _TITLE_MESSAGE_MAX_LENGTH - 1].rstrip() + "…"
        return f"{evidence.category}: {message}"

    @staticmethod
    def _build_description(evidence: Evidence) -> str:
        """Build a fuller Spanish description including source, category, and location."""
        location = ""
        if evidence.file_path is not None:
            location = f" en {evidence.file_path}"
            if evidence.line_start is not None:
                location += f":{evidence.line_start}"

        message = MockProvider._human_message(evidence.message)
        return (
            f"{evidence.source.value} reportó '{evidence.category}'{location}: "
            f"{message}"
        )
