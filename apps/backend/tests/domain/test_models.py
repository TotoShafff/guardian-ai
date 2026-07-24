"""Unit tests for framework-independent domain models."""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

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


def test_evidence_can_be_constructed_with_valid_values() -> None:
    review_id = uuid4()

    evidence = Evidence(
        review_id=review_id,
        source=EvidenceSource.RUFF,
        severity=EvidenceSeverity.BLOCKING,
        category="style",
        message="Unused import",
        file_path="app/domain/models.py",
        line_start=1,
        line_end=1,
        confidence=0.9,
    )

    assert isinstance(evidence.id, UUID)
    assert evidence.review_id == review_id
    assert evidence.source is EvidenceSource.RUFF
    assert evidence.confidence == 0.9


def test_evidence_rejects_confidence_out_of_range() -> None:
    with pytest.raises(ValueError, match="confidence"):
        Evidence(
            review_id=uuid4(),
            source=EvidenceSource.LLM,
            severity=EvidenceSeverity.INFO,
            category="design",
            message="Suspicious logic",
            confidence=1.5,
        )


def test_evidence_rejects_non_positive_line_start() -> None:
    with pytest.raises(ValueError, match="line_start"):
        Evidence(
            review_id=uuid4(),
            source=EvidenceSource.MYPY,
            severity=EvidenceSeverity.BLOCKING,
            category="type_error",
            message="Incompatible type",
            line_start=0,
        )


def test_evidence_rejects_line_end_before_line_start() -> None:
    with pytest.raises(ValueError, match="line_end"):
        Evidence(
            review_id=uuid4(),
            source=EvidenceSource.MYPY,
            severity=EvidenceSeverity.BLOCKING,
            category="type_error",
            message="Incompatible type",
            line_start=10,
            line_end=5,
        )


def test_evidence_default_created_at_is_timezone_aware_utc() -> None:
    evidence = Evidence(
        review_id=uuid4(),
        source=EvidenceSource.ESLINT,
        severity=EvidenceSeverity.NON_BLOCKING,
        category="style",
        message="Missing semicolon",
    )

    assert evidence.created_at.tzinfo is not None
    assert evidence.created_at.utcoffset() == timedelta(0)


def test_evidence_rejects_naive_created_at() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Evidence(
            review_id=uuid4(),
            source=EvidenceSource.PYTEST,
            severity=EvidenceSeverity.BLOCKING,
            category="test_failure",
            message="Test failed",
            created_at=datetime(2026, 1, 1),  # noqa: DTZ001
        )


def test_finding_can_be_constructed_with_valid_values() -> None:
    review_id = uuid4()
    evidence_id = uuid4()

    finding = Finding(
        review_id=review_id,
        evidence_ids=(evidence_id,),
        severity=EvidenceSeverity.BLOCKING,
        title="Negative discount total",
        description="Discount calculation allows a negative total.",
        is_fixable=True,
    )

    assert finding.evidence_ids == (evidence_id,)
    assert finding.created_at.utcoffset() == timedelta(0)


def test_validation_result_can_be_constructed() -> None:
    result = ValidationResult(
        status=ValidationStatus.PASSED, tool="pytest", message="ok"
    )

    assert result.status is ValidationStatus.PASSED
    assert result.tool == "pytest"


def test_fix_attempt_can_be_constructed_with_valid_attempt_number() -> None:
    attempt = FixAttempt(
        finding_id=uuid4(),
        patch="--- a/file.py\n+++ b/file.py\n",
        attempt_number=1,
        validation_results=(
            ValidationResult(
                status=ValidationStatus.PASSED, tool="pytest", message="ok"
            ),
        ),
    )

    assert attempt.attempt_number == 1
    assert len(attempt.validation_results) == 1


def test_fix_attempt_rejects_attempt_number_below_one() -> None:
    with pytest.raises(ValueError, match="attempt_number"):
        FixAttempt(
            finding_id=uuid4(),
            patch="--- a/file.py\n+++ b/file.py\n",
            attempt_number=0,
        )


def test_decision_can_be_constructed_with_findings_and_fix_attempts() -> None:
    finding = Finding(
        review_id=uuid4(),
        severity=EvidenceSeverity.BLOCKING,
        title="Failing test",
        description="A unit test fails.",
        is_fixable=True,
    )

    decision = Decision(
        status=ReviewStatus.BLOCKED,
        rationale="One blocking finding was not resolved.",
        blocking_findings=(finding,),
    )

    assert decision.blocking_findings == (finding,)
    assert decision.non_blocking_findings == ()
    assert decision.fix_attempts == ()


def test_review_can_be_constructed_and_defaults_are_safe() -> None:
    review = Review(target_reference="demo-diff-001", status=ReviewStatus.PENDING)

    assert review.target_reference == "demo-diff-001"
    assert review.completed_at is None
    assert isinstance(review.id, UUID)
    assert review.created_at.utcoffset() == timedelta(0)


def test_review_rejects_naive_completed_at() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Review(
            target_reference="demo-diff-001",
            status=ReviewStatus.APPROVED,
            completed_at=datetime(2026, 1, 1),  # noqa: DTZ001
        )


def test_domain_models_are_immutable() -> None:
    review = Review(target_reference="demo-diff-001", status=ReviewStatus.PENDING)

    with pytest.raises(AttributeError):
        review.status = ReviewStatus.APPROVED  # type: ignore[misc]
