"""Typed state for the Guardian AI review LangGraph workflow.

`ReviewWorkflowState` is the single data structure threaded through every
node of the review workflow (see `docs/ARCHITECTURE.md` Section 7). It only
ever holds domain types (`app.domain.models`) plus plain `Path`/`str`
values — no SQLAlchemy models, sessions, repositories, FastAPI request
objects, or provider SDK objects belong here. Persistence and HTTP
translation happen outside the graph, in `persistence/` and `api/`
respectively.
"""

from pathlib import Path
from typing import TypedDict

from app.domain.models import Decision, Evidence, Finding, FixAttempt, Review


class ReviewWorkflowState(TypedDict):
    """Data threaded through every node of the review LangGraph workflow."""

    #: The review request this workflow run is processing.
    review: Review
    #: Filesystem path (file or directory) the deterministic tools analyze.
    target_path: Path
    #: The code under review, as sent to the AI provider for semantic analysis.
    code: str
    #: Normalized evidence collected so far, from deterministic tools and/or the LLM.
    evidence: tuple[Evidence, ...]
    #: Findings derived from evidence so far (classification happens in a later node).
    findings: tuple[Finding, ...]
    #: Bounded fix-and-validate attempts made so far.
    fix_attempts: tuple[FixAttempt, ...]
    #: The Decision Agent's final consolidated output, once produced.
    decision: Decision | None
    #: A human-readable error message if the workflow could not complete, else None.
    error: str | None
