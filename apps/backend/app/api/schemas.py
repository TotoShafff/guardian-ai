"""Pydantic API schemas for the reviews endpoints.

These are dedicated request/response models for the HTTP boundary — they
never expose the domain dataclasses (`app.domain.models`) directly as
FastAPI schemas, per `docs/ARCHITECTURE.md` Section 10 and
`.cursor/rules/backend.mdc` ("Keep HTTP concerns ... inside the API layer
only"). Each response schema has a `from_domain`/`from_review`/
`from_run_result` constructor performing the one-way domain -> schema
translation; nothing here is ever converted back into a domain object.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain.models import (
    Decision,
    Evidence,
    EvidenceSeverity,
    EvidenceSource,
    Finding,
    FixAttempt,
    Review,
    ReviewStatus,
    ValidationResult,
    ValidationStatus,
)
from app.services.review_service import ReviewRunResult


class ReviewCreateRequest(BaseModel):
    """Request body for `POST /api/reviews`.

    Only the three inputs needed to start a review are accepted; the
    client can never supply an id, status, timestamps, findings, fix
    attempts, or a decision — those are always computed server-side.
    """

    target_reference: str = Field(min_length=1)
    target_path: str = Field(min_length=1)
    code: str = Field(min_length=1)

    @field_validator("target_reference", "target_path", "code")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        """Reject a value that is empty or contains only whitespace."""
        if value.strip() == "":
            raise ValueError("must not be blank")
        return value


class ValidationResultResponse(BaseModel):
    """API representation of a `ValidationResult`."""

    status: ValidationStatus
    tool: str
    message: str

    @classmethod
    def from_domain(
        cls, validation_result: ValidationResult
    ) -> "ValidationResultResponse":
        return cls(
            status=validation_result.status,
            tool=validation_result.tool,
            message=validation_result.message,
        )


class EvidenceResponse(BaseModel):
    """API representation of an `Evidence` item."""

    id: UUID
    review_id: UUID
    source: EvidenceSource
    severity: EvidenceSeverity
    category: str
    message: str
    file_path: str | None
    line_start: int | None
    line_end: int | None
    suggested_fix: str | None
    confidence: float | None
    created_at: datetime

    @classmethod
    def from_domain(cls, evidence: Evidence) -> "EvidenceResponse":
        return cls(
            id=evidence.id,
            review_id=evidence.review_id,
            source=evidence.source,
            severity=evidence.severity,
            category=evidence.category,
            message=evidence.message,
            file_path=evidence.file_path,
            line_start=evidence.line_start,
            line_end=evidence.line_end,
            suggested_fix=evidence.suggested_fix,
            confidence=evidence.confidence,
            created_at=evidence.created_at,
        )


class FindingResponse(BaseModel):
    """API representation of a `Finding`."""

    id: UUID
    review_id: UUID
    evidence_ids: list[UUID]
    severity: EvidenceSeverity
    title: str
    description: str
    is_fixable: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, finding: Finding) -> "FindingResponse":
        return cls(
            id=finding.id,
            review_id=finding.review_id,
            evidence_ids=list(finding.evidence_ids),
            severity=finding.severity,
            title=finding.title,
            description=finding.description,
            is_fixable=finding.is_fixable,
            created_at=finding.created_at,
        )


class FixAttemptResponse(BaseModel):
    """API representation of a `FixAttempt`."""

    id: UUID
    finding_id: UUID
    patch: str
    attempt_number: int
    validation_results: list[ValidationResultResponse]
    created_at: datetime

    @classmethod
    def from_domain(cls, fix_attempt: FixAttempt) -> "FixAttemptResponse":
        return cls(
            id=fix_attempt.id,
            finding_id=fix_attempt.finding_id,
            patch=fix_attempt.patch,
            attempt_number=fix_attempt.attempt_number,
            validation_results=[
                ValidationResultResponse.from_domain(result)
                for result in fix_attempt.validation_results
            ],
            created_at=fix_attempt.created_at,
        )


class DecisionResponse(BaseModel):
    """API representation of a `Decision`."""

    status: ReviewStatus
    rationale: str
    blocking_findings: list[FindingResponse]
    non_blocking_findings: list[FindingResponse]
    fix_attempts: list[FixAttemptResponse]

    @classmethod
    def from_domain(cls, decision: Decision) -> "DecisionResponse":
        return cls(
            status=decision.status,
            rationale=decision.rationale,
            blocking_findings=[
                FindingResponse.from_domain(finding)
                for finding in decision.blocking_findings
            ],
            non_blocking_findings=[
                FindingResponse.from_domain(finding)
                for finding in decision.non_blocking_findings
            ],
            fix_attempts=[
                FixAttemptResponse.from_domain(attempt)
                for attempt in decision.fix_attempts
            ],
        )


class ReviewResponse(BaseModel):
    """API representation of a `Review`, its workflow outputs, and its `Decision`.

    `evidence`, `findings`, and `fix_attempts` are populated directly from
    the final LangGraph workflow state right after `POST /api/reviews` runs
    it (see `from_run_result`); none of that is persisted yet (only
    `Review` itself is — see `docs/ARCHITECTURE.md` Section 12), so
    `GET /api/reviews/{id}` (see `from_review`) always returns them empty.
    """

    id: UUID
    target_reference: str
    status: ReviewStatus
    created_at: datetime
    updated_at: datetime | None
    evidence: list[EvidenceResponse] = Field(default_factory=list)
    findings: list[FindingResponse] = Field(default_factory=list)
    fix_attempts: list[FixAttemptResponse] = Field(default_factory=list)
    decision: DecisionResponse | None = None
    error: str | None = None

    @classmethod
    def from_review(cls, review: Review) -> "ReviewResponse":
        """Build a response from a persisted `Review` alone (used by `GET`)."""
        return cls(
            id=review.id,
            target_reference=review.target_reference,
            status=review.status,
            created_at=review.created_at,
            updated_at=review.completed_at,
        )

    @classmethod
    def from_run_result(cls, result: ReviewRunResult) -> "ReviewResponse":
        """Build a response from a freshly completed run (used by `POST`)."""
        review = result.review
        state = result.workflow_state
        decision = state["decision"]
        return cls(
            id=review.id,
            target_reference=review.target_reference,
            status=review.status,
            created_at=review.created_at,
            updated_at=review.completed_at,
            evidence=[EvidenceResponse.from_domain(item) for item in state["evidence"]],
            findings=[FindingResponse.from_domain(item) for item in state["findings"]],
            fix_attempts=[
                FixAttemptResponse.from_domain(item) for item in state["fix_attempts"]
            ],
            decision=DecisionResponse.from_domain(decision) if decision else None,
            error=state["error"],
        )
