from typing import NamedTuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.models import (
    Decision,
    Evidence,
    Finding,
    FixAttempt,
    Review,
    ValidationResult,
)
from app.persistence.models import (
    DecisionFindingModel,
    DecisionFixAttemptModel,
    DecisionModel,
    EvidenceModel,
    FindingEvidenceModel,
    FindingModel,
    FixAttemptModel,
    ReviewModel,
    ValidationResultModel,
)


class ReviewNotFoundError(Exception):
    """Raised when a `Review` cannot be found by its id."""

    def __init__(self, review_id: UUID) -> None:
        super().__init__(f"Review not found: {review_id}")
        self.review_id = review_id


class ReviewResult(NamedTuple):
   
    review: Review
    evidence: tuple[Evidence, ...]
    findings: tuple[Finding, ...]
    fix_attempts: tuple[FixAttempt, ...]
    decision: Decision | None


def _to_model(review: Review) -> ReviewModel:
    """Convert a domain `Review` into a new, unattached `ReviewModel`."""
    return ReviewModel(
        id=review.id,
        target_reference=review.target_reference,
        status=review.status,
        created_at=review.created_at,
        completed_at=review.completed_at,
    )


def _to_domain(model: ReviewModel) -> Review:
    """Convert a persisted `ReviewModel` into a domain `Review`."""
    return Review(
        id=model.id,
        target_reference=model.target_reference,
        status=model.status,
        created_at=model.created_at,
        completed_at=model.completed_at,
    )


def _evidence_to_model(evidence: Evidence, order_index: int) -> EvidenceModel:
    """Convert a domain `Evidence` into a new, unattached `EvidenceModel`."""
    return EvidenceModel(
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
        order_index=order_index,
    )


def _evidence_to_domain(model: EvidenceModel) -> Evidence:
    """Convert a persisted `EvidenceModel` into a domain `Evidence`."""
    return Evidence(
        id=model.id,
        review_id=model.review_id,
        source=model.source,
        severity=model.severity,
        category=model.category,
        message=model.message,
        file_path=model.file_path,
        line_start=model.line_start,
        line_end=model.line_end,
        suggested_fix=model.suggested_fix,
        confidence=model.confidence,
        created_at=model.created_at,
    )


def _finding_to_model(finding: Finding, order_index: int) -> FindingModel:
    return FindingModel(
        id=finding.id,
        review_id=finding.review_id,
        severity=finding.severity,
        title=finding.title,
        description=finding.description,
        is_fixable=finding.is_fixable,
        created_at=finding.created_at,
        order_index=order_index,
    )


def _finding_to_domain(model: FindingModel) -> Finding:
    return Finding(
        id=model.id,
        review_id=model.review_id,
        evidence_ids=tuple(evidence.id for evidence in model.evidence),
        severity=model.severity,
        title=model.title,
        description=model.description,
        is_fixable=model.is_fixable,
        created_at=model.created_at,
    )


def _fix_attempt_to_model(fix_attempt: FixAttempt, order_index: int) -> FixAttemptModel:
    return FixAttemptModel(
        id=fix_attempt.id,
        finding_id=fix_attempt.finding_id,
        patch=fix_attempt.patch,
        attempt_number=fix_attempt.attempt_number,
        created_at=fix_attempt.created_at,
        order_index=order_index,
    )


def _fix_attempt_to_domain(model: FixAttemptModel) -> FixAttempt:
    return FixAttempt(
        id=model.id,
        finding_id=model.finding_id,
        patch=model.patch,
        attempt_number=model.attempt_number,
        validation_results=tuple(
            _validation_result_to_domain(result) for result in model.validation_results
        ),
        created_at=model.created_at,
    )


def _validation_result_to_domain(model: ValidationResultModel) -> ValidationResult:
    """Convert a persisted `ValidationResultModel` into a domain `ValidationResult`."""
    return ValidationResult(status=model.status, tool=model.tool, message=model.message)


class ReviewRepository:

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, review: Review) -> Review:
        """Add `review` to the session, flush it, and return the persisted value.

        Does not commit; the caller owns the transaction.
        """
        model = _to_model(review)
        self._session.add(model)
        self._session.flush()
        return _to_domain(model)

    def get_by_id(self, review_id: UUID) -> Review | None:
        """Return the review with `review_id`, or None if it does not exist."""
        model = self._session.get(ReviewModel, review_id)
        if model is None:
            return None
        return _to_domain(model)

    def list_recent(self, limit: int = 20, offset: int = 0) -> list[Review]:
        """Return up to `limit` reviews, most recently created first.

        Raises `ValueError` for `limit < 1` or `offset < 0`.
        """
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if offset < 0:
            raise ValueError("offset must be zero or positive")

        statement = (
            select(ReviewModel)
            .order_by(ReviewModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        models = self._session.execute(statement).scalars().all()
        return [_to_domain(model) for model in models]

    def update(self, review: Review) -> Review:
        model = self._session.get(ReviewModel, review.id)
        if model is None:
            raise ReviewNotFoundError(review.id)

        model.target_reference = review.target_reference
        model.status = review.status
        model.created_at = review.created_at
        model.completed_at = review.completed_at

        self._session.flush()
        return _to_domain(model)

    def save_workflow_output(
        self,
        review_id: UUID,
        evidence: tuple[Evidence, ...],
        findings: tuple[Finding, ...],
        fix_attempts: tuple[FixAttempt, ...],
        decision: Decision | None,
    ) -> None:
        """Persist the complete final workflow output for one review.

        Persists evidence, findings, their associations, fix attempts,
        validation results, and the final decision while preserving order.

        Flushes are intentionally staged so every parent row exists before
        inserting association or child rows that reference it.

        Does not commit or roll back; the caller owns the transaction.
        """
        for evidence_index, item in enumerate(evidence):
            self._session.add(_evidence_to_model(item, evidence_index))

        # Evidence rows must exist before finding_evidence associations.
        self._session.flush()

        for finding_index, finding in enumerate(findings):
            self._session.add(_finding_to_model(finding, finding_index))

        # Finding rows must exist before associations and fix attempts.
        self._session.flush()

        for finding in findings:
            for association_index, evidence_id in enumerate(finding.evidence_ids):
                self._session.add(
                    FindingEvidenceModel(
                        finding_id=finding.id,
                        evidence_id=evidence_id,
                        order_index=association_index,
                    )
                )

        for attempt_index, attempt in enumerate(fix_attempts):
            self._session.add(_fix_attempt_to_model(attempt, attempt_index))

        # Fix-attempt rows must exist before validation results and decision links.
        self._session.flush()

        for attempt in fix_attempts:
            for result_index, result in enumerate(attempt.validation_results):
                self._session.add(
                    ValidationResultModel(
                        fix_attempt_id=attempt.id,
                        status=result.status,
                        tool=result.tool,
                        message=result.message,
                        order_index=result_index,
                    )
                )

        if decision is not None:
            self._session.add(
                DecisionModel(
                    review_id=review_id,
                    status=decision.status,
                    rationale=decision.rationale,
                )
            )

            # The decision row must exist before its association rows.
            self._session.flush()

            for order_index, finding in enumerate(decision.blocking_findings):
                self._session.add(
                    DecisionFindingModel(
                        decision_review_id=review_id,
                        finding_id=finding.id,
                        is_blocking=True,
                        order_index=order_index,
                    )
                )

            for order_index, finding in enumerate(decision.non_blocking_findings):
                self._session.add(
                    DecisionFindingModel(
                        decision_review_id=review_id,
                        finding_id=finding.id,
                        is_blocking=False,
                        order_index=order_index,
                    )
                )

            for order_index, attempt in enumerate(decision.fix_attempts):
                self._session.add(
                    DecisionFixAttemptModel(
                        decision_review_id=review_id,
                        fix_attempt_id=attempt.id,
                        order_index=order_index,
                    )
                )

        self._session.flush()

    def get_review_result(self, review_id: UUID) -> ReviewResult | None:
        statement = (
            select(ReviewModel)
            .where(ReviewModel.id == review_id)
            .options(
                selectinload(ReviewModel.evidence),
                selectinload(ReviewModel.findings).selectinload(FindingModel.evidence),
                selectinload(ReviewModel.findings)
                .selectinload(FindingModel.fix_attempts)
                .selectinload(FixAttemptModel.validation_results),
                selectinload(ReviewModel.decision).selectinload(
                    DecisionModel.finding_links
                ),
                selectinload(ReviewModel.decision).selectinload(
                    DecisionModel.fix_attempt_links
                ),
            )
        )
        model = self._session.execute(statement).unique().scalar_one_or_none()
        if model is None:
            return None

        findings_by_id: dict[UUID, Finding] = {}
        fix_attempts_by_id: dict[UUID, FixAttempt] = {}
        fix_attempt_order: dict[UUID, int] = {}
        findings: list[Finding] = []

        for finding_model in model.findings:
            finding = _finding_to_domain(finding_model)
            findings.append(finding)
            findings_by_id[finding.id] = finding

            for fix_attempt_model in finding_model.fix_attempts:
                fix_attempt = _fix_attempt_to_domain(fix_attempt_model)
                fix_attempts_by_id[fix_attempt.id] = fix_attempt
                fix_attempt_order[fix_attempt.id] = fix_attempt_model.order_index

        # `fix_attempts` must preserve the review-wide order (across all
        # findings), not the per-finding traversal order above.
        fix_attempts = tuple(
            fix_attempts_by_id[attempt_id]
            for attempt_id in sorted(
                fix_attempts_by_id, key=lambda attempt_id: fix_attempt_order[attempt_id]
            )
        )

        decision = None
        if model.decision is not None:
            decision = self._decision_to_domain(
                model.decision, findings_by_id, fix_attempts_by_id
            )

        return ReviewResult(
            review=_to_domain(model),
            evidence=tuple(_evidence_to_domain(item) for item in model.evidence),
            findings=tuple(findings),
            fix_attempts=fix_attempts,
            decision=decision,
        )

    @staticmethod
    def _decision_to_domain(
        model: DecisionModel,
        findings_by_id: dict[UUID, Finding],
        fix_attempts_by_id: dict[UUID, FixAttempt],
    ) -> Decision:
        blocking_findings = tuple(
            findings_by_id[link.finding_id]
            for link in model.finding_links
            if link.is_blocking
        )
        non_blocking_findings = tuple(
            findings_by_id[link.finding_id]
            for link in model.finding_links
            if not link.is_blocking
        )
        fix_attempts = tuple(
            fix_attempts_by_id[link.fix_attempt_id] for link in model.fix_attempt_links
        )
        return Decision(
            status=model.status,
            rationale=model.rationale,
            blocking_findings=blocking_findings,
            non_blocking_findings=non_blocking_findings,
            fix_attempts=fix_attempts,
        )