"""Framework-independent domain models for Guardian AI.

These types describe evidence, findings, fix attempts, and the final review
decision as understood by the domain, independent of FastAPI, SQLAlchemy,
Pydantic, LangGraph, or any AI provider SDK. See `docs/ARCHITECTURE.md`
Section 8 for the conceptual evidence model these types implement.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4


class EvidenceSource(StrEnum):
    """Where a piece of evidence came from."""

    LLM = "llm"
    RUFF = "ruff"
    MYPY = "mypy"
    PYTEST = "pytest"
    ESLINT = "eslint"
    TSC = "tsc"
    VITEST = "vitest"


class EvidenceSeverity(StrEnum):
    """How significant a piece of evidence or a finding is."""

    BLOCKING = "blocking"
    NON_BLOCKING = "non_blocking"
    INFO = "info"


class ReviewStatus(StrEnum):
    """Lifecycle/outcome status shared by `Review` and `Decision`."""

    PENDING = "pending"
    RUNNING = "running"
    APPROVED = "approved"
    BLOCKED = "blocked"
    FAILED = "failed"


class ValidationStatus(StrEnum):
    """Outcome of re-running one deterministic check against a proposed fix."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


def _utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


def _require_utc(value: datetime, field_name: str) -> None:
    """Raise if `value` is not a timezone-aware UTC datetime."""
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be timezone-aware UTC")


@dataclass(frozen=True, kw_only=True)
class Evidence:
    """A single, normalized piece of evidence about a code change."""

    id: UUID = field(default_factory=uuid4)
    review_id: UUID
    source: EvidenceSource
    severity: EvidenceSeverity
    category: str
    message: str
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    suggested_fix: str | None = None
    confidence: float | None = None
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        _require_utc(self.created_at, "created_at")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.line_start is not None and self.line_start <= 0:
            raise ValueError("line_start must be positive")
        if self.line_end is not None and self.line_end <= 0:
            raise ValueError("line_end must be positive")
        if (
            self.line_start is not None
            and self.line_end is not None
            and self.line_end < self.line_start
        ):
            raise ValueError("line_end cannot be before line_start")


@dataclass(frozen=True, kw_only=True)
class Finding:
    """A classified, human-facing finding derived from one or more evidence items."""

    id: UUID = field(default_factory=uuid4)
    review_id: UUID
    evidence_ids: tuple[UUID, ...] = field(default_factory=tuple)
    severity: EvidenceSeverity
    title: str
    description: str
    is_fixable: bool
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        _require_utc(self.created_at, "created_at")


@dataclass(frozen=True, kw_only=True)
class ValidationResult:
    """Outcome of re-running one deterministic tool against a proposed fix."""

    status: ValidationStatus
    tool: str
    message: str


@dataclass(frozen=True, kw_only=True)
class FixAttempt:
    """One bounded attempt to propose and validate a correction for a finding."""

    id: UUID = field(default_factory=uuid4)
    finding_id: UUID
    patch: str
    attempt_number: int
    validation_results: tuple[ValidationResult, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        _require_utc(self.created_at, "created_at")
        if self.attempt_number < 1:
            raise ValueError("attempt_number must be at least 1")


@dataclass(frozen=True, kw_only=True)
class Decision:
    """The Decision Agent's consolidated output for a review."""

    status: ReviewStatus
    rationale: str
    blocking_findings: tuple[Finding, ...] = field(default_factory=tuple)
    non_blocking_findings: tuple[Finding, ...] = field(default_factory=tuple)
    fix_attempts: tuple[FixAttempt, ...] = field(default_factory=tuple)


@dataclass(frozen=True, kw_only=True)
class Review:
    """A single review request and its current lifecycle/outcome status."""

    id: UUID = field(default_factory=uuid4)
    target_reference: str
    target_path: str = ""
    status: ReviewStatus
    created_at: datetime = field(default_factory=_utc_now)
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_utc(self.created_at, "created_at")
        if self.completed_at is not None:
            _require_utc(self.completed_at, "completed_at")


@dataclass(frozen=True, kw_only=True)
class ReviewSummary:
    """Lightweight listing row for a persisted review (history views)."""

    id: UUID
    target_reference: str
    target_path: str
    status: ReviewStatus
    created_at: datetime
    completed_at: datetime | None
    blocking_findings_count: int
    non_blocking_findings_count: int
