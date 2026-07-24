"""Provider-agnostic AI interface for the Guardian AI backend.

Defines the `AIProvider` abstraction used by the Semantic Analysis Agent and
the fix-proposal flow (see `docs/ARCHITECTURE.md` Section 9). Concrete
adapters — a real LLM vendor adapter, or `MockProvider` for tests/local
runs — live under `app/providers/` and are the only place provider-specific
logic may appear; callers depend only on this interface.

This module has no framework or infrastructure imports: no FastAPI,
SQLAlchemy, LangGraph, repositories, tools, or vendor SDKs.
"""

from abc import ABC, abstractmethod

from app.domain.models import Evidence, Finding


class AIProvider(ABC):
    """Common interface every AI provider adapter must implement."""

    @abstractmethod
    def analyze_code(
        self,
        code: str,
        evidence: tuple[Evidence, ...],
    ) -> tuple[Finding, ...]:
        """Produce semantic findings for `code`, informed by deterministic `evidence`."""
        raise NotImplementedError

    @abstractmethod
    def propose_fix(
        self,
        code: str,
        finding: Finding,
        attempt_number: int,
    ) -> str:
        """Propose a correction for `finding` in `code`, for the given attempt number.

        Implementations should return an empty string when `finding` is not
        fixable, and otherwise a patch/diff-like text describing the
        proposed correction.
        """
        raise NotImplementedError
