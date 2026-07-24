"""Unit tests for `ReviewRepository`.

All tests use a mocked SQLAlchemy `Session` (via `unittest.mock`), so none of
them require PostgreSQL, SQLite, Docker, or network access. The goal is to
verify the repository's *contract* with the session (what it calls, and
when) and its domain <-> ORM conversion, not real SQL execution.

For `get_review_result()`, the mocked session's `execute()` chain returns a
hand-built (transient, never session-attached) ORM object graph rather than
a real query result, so the eager-loaded relationship reconstruction logic
is exercised without needing a real database.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

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
from app.persistence.repositories import (
    ReviewNotFoundError,
    ReviewRepository,
    ReviewResult,
)


def _make_review(**overrides: object) -> Review:
    defaults: dict[str, object] = {
        "target_reference": "feature/checkout-fix",
        "status": ReviewStatus.PENDING,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return Review(**defaults)  # type: ignore[arg-type]


def _make_model(**overrides: object) -> ReviewModel:
    defaults: dict[str, object] = {
        "id": uuid4(),
        "target_reference": "feature/checkout-fix",
        "status": ReviewStatus.PENDING,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "completed_at": None,
    }
    defaults.update(overrides)
    return ReviewModel(**defaults)  # type: ignore[arg-type]


def test_add_calls_session_add_and_flush_and_returns_a_domain_review() -> None:
    session = MagicMock(spec=Session)
    repository = ReviewRepository(session)
    review = _make_review()

    result = repository.add(review)

    session.add.assert_called_once()
    added_model = session.add.call_args[0][0]
    assert isinstance(added_model, ReviewModel)
    assert added_model.id == review.id
    session.flush.assert_called_once()
    session.commit.assert_not_called()

    assert isinstance(result, Review)
    assert result.id == review.id
    assert result.target_reference == review.target_reference
    assert result.status == review.status


def test_get_by_id_returns_none_when_missing() -> None:
    session = MagicMock(spec=Session)
    session.get.return_value = None
    repository = ReviewRepository(session)

    result = repository.get_by_id(uuid4())

    assert result is None
    session.commit.assert_not_called()


def test_get_by_id_converts_an_orm_model_to_a_domain_review() -> None:
    model = _make_model()
    session = MagicMock(spec=Session)
    session.get.return_value = model
    repository = ReviewRepository(session)

    result = repository.get_by_id(model.id)

    session.get.assert_called_once_with(ReviewModel, model.id)
    assert isinstance(result, Review)
    assert result.id == model.id
    assert result.target_reference == model.target_reference
    assert result.status == model.status
    assert result.created_at == model.created_at
    assert result.completed_at == model.completed_at
    session.commit.assert_not_called()


def test_list_recent_orders_by_created_at_descending_with_limit_and_offset() -> None:
    session = MagicMock(spec=Session)
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    session.execute.return_value = execute_result
    repository = ReviewRepository(session)

    repository.list_recent(limit=5, offset=10)

    session.execute.assert_called_once()
    statement = session.execute.call_args[0][0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "ORDER BY reviews.created_at DESC" in compiled
    assert "LIMIT 5" in compiled
    assert "OFFSET 10" in compiled
    session.commit.assert_not_called()


def test_list_recent_converts_all_returned_models_to_domain_reviews() -> None:
    models = [_make_model(), _make_model()]
    session = MagicMock(spec=Session)
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = models
    session.execute.return_value = execute_result
    repository = ReviewRepository(session)

    result = repository.list_recent()

    assert len(result) == 2
    assert all(isinstance(item, Review) for item in result)
    assert {item.id for item in result} == {model.id for model in models}


@pytest.mark.parametrize("limit", [0, -1])
def test_list_recent_rejects_limit_values_below_one(limit: int) -> None:
    session = MagicMock(spec=Session)
    repository = ReviewRepository(session)

    with pytest.raises(ValueError, match="limit"):
        repository.list_recent(limit=limit)

    session.execute.assert_not_called()


def test_list_recent_rejects_negative_offset() -> None:
    session = MagicMock(spec=Session)
    repository = ReviewRepository(session)

    with pytest.raises(ValueError, match="offset"):
        repository.list_recent(offset=-1)

    session.execute.assert_not_called()


def test_update_raises_review_not_found_error_when_missing() -> None:
    session = MagicMock(spec=Session)
    session.get.return_value = None
    repository = ReviewRepository(session)
    review = _make_review()

    with pytest.raises(ReviewNotFoundError) as exc_info:
        repository.update(review)

    assert exc_info.value.review_id == review.id
    session.flush.assert_not_called()
    session.commit.assert_not_called()


def test_update_modifies_the_orm_object_and_flushes_without_committing() -> None:
    model = _make_model(status=ReviewStatus.PENDING, completed_at=None)
    session = MagicMock(spec=Session)
    session.get.return_value = model
    repository = ReviewRepository(session)

    updated_review = _make_review(
        id=model.id,
        target_reference=model.target_reference,
        status=ReviewStatus.APPROVED,
        created_at=model.created_at,
        completed_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    # `update()` looks up the existing row by the review's own id.
    object.__setattr__(updated_review, "id", model.id)

    result = repository.update(updated_review)

    assert model.status == ReviewStatus.APPROVED
    assert model.completed_at == updated_review.completed_at
    session.flush.assert_called_once()
    session.commit.assert_not_called()
    assert isinstance(result, Review)
    assert result.status == ReviewStatus.APPROVED
    assert result.completed_at == updated_review.completed_at


def test_repository_methods_never_call_commit() -> None:
    session = MagicMock(spec=Session)
    session.get.return_value = _make_model()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    session.execute.return_value = execute_result
    repository = ReviewRepository(session)

    repository.add(_make_review())
    repository.get_by_id(uuid4())
    repository.list_recent()
    repository.update(_make_review(status=ReviewStatus.APPROVED))

    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_get_review_result_preserves_review_wide_fix_attempt_order() -> None:
    review_model = _make_model(status=ReviewStatus.BLOCKED)
    review_id = review_model.id
    review_model.evidence = []

    first_finding = _fake_finding_model(
        review_id=review_id,
        order_index=0,
        severity=EvidenceSeverity.BLOCKING,
        evidence=[],
        fix_attempts=[],
    )
    second_finding = _fake_finding_model(
        review_id=review_id,
        order_index=1,
        severity=EvidenceSeverity.BLOCKING,
        evidence=[],
        fix_attempts=[],
    )

    globally_second = _fake_fix_attempt_model(
        finding_id=first_finding.id,
        order_index=1,
        validation_results=[],
    )
    globally_first = _fake_fix_attempt_model(
        finding_id=second_finding.id,
        order_index=0,
        validation_results=[],
    )

    first_finding.fix_attempts = [globally_second]
    second_finding.fix_attempts = [globally_first]

    review_model.findings = [first_finding, second_finding]
    review_model.decision = None

    session = MagicMock(spec=Session)
    session.execute.return_value = _mock_execute_result(review_model)
    repository = ReviewRepository(session)

    result = repository.get_review_result(review_id)

    assert result is not None
    assert [attempt.id for attempt in result.fix_attempts] == [
        globally_first.id,
        globally_second.id,
    ]


# --- save_workflow_output() / get_review_result() -----------------------


def _make_evidence(**overrides: object) -> Evidence:
    defaults: dict[str, object] = {
        "review_id": uuid4(),
        "source": EvidenceSource.RUFF,
        "severity": EvidenceSeverity.NON_BLOCKING,
        "category": "F401",
        "message": "unused import",
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return Evidence(**defaults)  # type: ignore[arg-type]


def _make_finding(**overrides: object) -> Finding:
    defaults: dict[str, object] = {
        "review_id": uuid4(),
        "evidence_ids": (),
        "severity": EvidenceSeverity.BLOCKING,
        "title": "Unused import",
        "description": "`os` is imported but never used",
        "is_fixable": True,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return Finding(**defaults)  # type: ignore[arg-type]


def _make_fix_attempt(**overrides: object) -> FixAttempt:
    defaults: dict[str, object] = {
        "finding_id": uuid4(),
        "patch": "--- a\n+++ b\n",
        "attempt_number": 1,
        "validation_results": (),
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return FixAttempt(**defaults)  # type: ignore[arg-type]


def _added_models(session: MagicMock, model_type: type) -> list[object]:
    """Return every object of `model_type` passed to `session.add()`, in order."""
    return [
        call.args[0]
        for call in session.add.call_args_list
        if isinstance(call.args[0], model_type)
    ]


def test_save_workflow_output_persists_evidence_in_order() -> None:
    session = MagicMock(spec=Session)
    repository = ReviewRepository(session)
    review_id = uuid4()
    evidence = (
        _make_evidence(review_id=review_id, category="F401"),
        _make_evidence(review_id=review_id, category="E501"),
    )

    repository.save_workflow_output(
        review_id=review_id,
        evidence=evidence,
        findings=(),
        fix_attempts=(),
        decision=None,
    )

    added = _added_models(session, EvidenceModel)
    assert [model.id for model in added] == [item.id for item in evidence]
    assert [model.order_index for model in added] == [0, 1]
    session.flush.assert_called_once()


def test_save_workflow_output_persists_findings_and_evidence_associations() -> None:
    session = MagicMock(spec=Session)
    repository = ReviewRepository(session)
    review_id = uuid4()
    evidence = _make_evidence(review_id=review_id)
    other_evidence = _make_evidence(review_id=review_id)
    finding = _make_finding(
        review_id=review_id, evidence_ids=(evidence.id, other_evidence.id)
    )

    repository.save_workflow_output(
        review_id=review_id,
        evidence=(evidence, other_evidence),
        findings=(finding,),
        fix_attempts=(),
        decision=None,
    )

    finding_models = _added_models(session, FindingModel)
    assert len(finding_models) == 1
    assert finding_models[0].id == finding.id
    assert finding_models[0].order_index == 0

    associations = _added_models(session, FindingEvidenceModel)
    assert [(a.finding_id, a.evidence_id, a.order_index) for a in associations] == [
        (finding.id, evidence.id, 0),
        (finding.id, other_evidence.id, 1),
    ]


def test_save_workflow_output_persists_fix_attempts_and_ordered_validation_results() -> (
    None
):
    session = MagicMock(spec=Session)
    repository = ReviewRepository(session)
    review_id = uuid4()
    finding = _make_finding(review_id=review_id)
    attempt = _make_fix_attempt(
        finding_id=finding.id,
        attempt_number=1,
        validation_results=(
            ValidationResult(status=ValidationStatus.FAILED, tool="ruff", message="x"),
            ValidationResult(
                status=ValidationStatus.PASSED, tool="pytest", message="ok"
            ),
        ),
    )

    repository.save_workflow_output(
        review_id=review_id,
        evidence=(),
        findings=(finding,),
        fix_attempts=(attempt,),
        decision=None,
    )

    attempt_models = _added_models(session, FixAttemptModel)
    assert len(attempt_models) == 1
    assert attempt_models[0].id == attempt.id
    assert attempt_models[0].order_index == 0

    result_models = _added_models(session, ValidationResultModel)
    assert [(r.tool, r.status, r.order_index) for r in result_models] == [
        ("ruff", ValidationStatus.FAILED, 0),
        ("pytest", ValidationStatus.PASSED, 1),
    ]
    assert all(r.fix_attempt_id == attempt.id for r in result_models)


def test_save_workflow_output_persists_decision_groups_and_order() -> None:
    session = MagicMock(spec=Session)
    repository = ReviewRepository(session)
    review_id = uuid4()
    blocking_a = _make_finding(review_id=review_id, severity=EvidenceSeverity.BLOCKING)
    blocking_b = _make_finding(review_id=review_id, severity=EvidenceSeverity.BLOCKING)
    non_blocking = _make_finding(
        review_id=review_id, severity=EvidenceSeverity.NON_BLOCKING
    )
    attempt = _make_fix_attempt(finding_id=blocking_a.id)
    decision = Decision(
        status=ReviewStatus.BLOCKED,
        rationale="2 blocking findings.",
        blocking_findings=(blocking_a, blocking_b),
        non_blocking_findings=(non_blocking,),
        fix_attempts=(attempt,),
    )

    repository.save_workflow_output(
        review_id=review_id,
        evidence=(),
        findings=(blocking_a, blocking_b, non_blocking),
        fix_attempts=(attempt,),
        decision=decision,
    )

    decision_models = _added_models(session, DecisionModel)
    assert len(decision_models) == 1
    assert decision_models[0].review_id == review_id
    assert decision_models[0].status == ReviewStatus.BLOCKED

    finding_links = _added_models(session, DecisionFindingModel)
    assert [
        (link.finding_id, link.is_blocking, link.order_index) for link in finding_links
    ] == [
        (blocking_a.id, True, 0),
        (blocking_b.id, True, 1),
        (non_blocking.id, False, 0),
    ]

    fix_attempt_links = _added_models(session, DecisionFixAttemptModel)
    assert [(link.fix_attempt_id, link.order_index) for link in fix_attempt_links] == [
        (attempt.id, 0)
    ]


def test_save_workflow_output_does_not_persist_a_decision_when_none() -> None:
    session = MagicMock(spec=Session)
    repository = ReviewRepository(session)
    review_id = uuid4()

    repository.save_workflow_output(
        review_id=review_id,
        evidence=(),
        findings=(),
        fix_attempts=(),
        decision=None,
    )

    assert _added_models(session, DecisionModel) == []
    assert _added_models(session, DecisionFindingModel) == []
    assert _added_models(session, DecisionFixAttemptModel) == []


def test_save_workflow_output_flushes_without_committing_or_rolling_back() -> None:
    session = MagicMock(spec=Session)
    repository = ReviewRepository(session)
    review_id = uuid4()
    finding = _make_finding(review_id=review_id)
    attempt = _make_fix_attempt(finding_id=finding.id)
    decision = Decision(
        status=ReviewStatus.APPROVED, rationale="ok", non_blocking_findings=(finding,)
    )

    repository.save_workflow_output(
        review_id=review_id,
        evidence=(_make_evidence(review_id=review_id),),
        findings=(finding,),
        fix_attempts=(attempt,),
        decision=decision,
    )

    session.flush.assert_called_once()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def _fake_validation_result_model(
    status: ValidationStatus, order_index: int
) -> ValidationResultModel:
    return ValidationResultModel(
        id=uuid4(),
        fix_attempt_id=uuid4(),
        status=status,
        tool="mock_validator",
        message="message",
        order_index=order_index,
    )


def _fake_fix_attempt_model(
    finding_id: UUID, order_index: int, validation_results: list[ValidationResultModel]
) -> FixAttemptModel:
    model = FixAttemptModel(
        id=uuid4(),
        finding_id=finding_id,
        patch="--- a\n+++ b\n",
        attempt_number=1,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        order_index=order_index,
    )
    model.validation_results = validation_results
    return model


def _fake_finding_model(
    review_id: UUID,
    order_index: int,
    severity: EvidenceSeverity,
    evidence: list[EvidenceModel],
    fix_attempts: list[FixAttemptModel],
) -> FindingModel:
    model = FindingModel(
        id=uuid4(),
        review_id=review_id,
        severity=severity,
        title="Unused import",
        description="`os` is imported but never used",
        is_fixable=True,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        order_index=order_index,
    )
    model.evidence = evidence
    model.fix_attempts = fix_attempts
    return model


def _fake_evidence_model(review_id: UUID, order_index: int) -> EvidenceModel:
    return EvidenceModel(
        id=uuid4(),
        review_id=review_id,
        source=EvidenceSource.RUFF,
        severity=EvidenceSeverity.NON_BLOCKING,
        category="F401",
        message="unused import",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        order_index=order_index,
    )


def _mock_execute_result(model: ReviewModel | None) -> MagicMock:
    execute_result = MagicMock()
    execute_result.unique.return_value.scalar_one_or_none.return_value = model
    return execute_result


def test_get_review_result_returns_none_when_review_is_missing() -> None:
    session = MagicMock(spec=Session)
    session.execute.return_value = _mock_execute_result(None)
    repository = ReviewRepository(session)

    result = repository.get_review_result(uuid4())

    assert result is None


def test_get_review_result_reconstructs_the_complete_review_result_in_order() -> None:
    review_model = _make_model(status=ReviewStatus.BLOCKED)
    review_id = review_model.id

    evidence_a = _fake_evidence_model(review_id, order_index=0)
    evidence_b = _fake_evidence_model(review_id, order_index=1)
    review_model.evidence = [evidence_a, evidence_b]

    passed_result = _fake_validation_result_model(ValidationStatus.PASSED, 0)
    attempt = _fake_fix_attempt_model(
        finding_id=uuid4(), order_index=0, validation_results=[passed_result]
    )
    blocking_finding = _fake_finding_model(
        review_id,
        order_index=0,
        severity=EvidenceSeverity.BLOCKING,
        evidence=[evidence_a],
        fix_attempts=[attempt],
    )
    attempt.finding_id = blocking_finding.id
    non_blocking_finding = _fake_finding_model(
        review_id,
        order_index=1,
        severity=EvidenceSeverity.NON_BLOCKING,
        evidence=[evidence_b],
        fix_attempts=[],
    )
    review_model.findings = [blocking_finding, non_blocking_finding]

    decision_model = DecisionModel(
        review_id=review_id,
        status=ReviewStatus.BLOCKED,
        rationale="1 blocking finding.",
    )
    decision_model.finding_links = [
        DecisionFindingModel(
            decision_review_id=review_id,
            finding_id=blocking_finding.id,
            is_blocking=True,
            order_index=0,
        ),
        DecisionFindingModel(
            decision_review_id=review_id,
            finding_id=non_blocking_finding.id,
            is_blocking=False,
            order_index=0,
        ),
    ]
    decision_model.fix_attempt_links = [
        DecisionFixAttemptModel(
            decision_review_id=review_id,
            fix_attempt_id=attempt.id,
            order_index=0,
        )
    ]
    review_model.decision = decision_model

    session = MagicMock(spec=Session)
    session.execute.return_value = _mock_execute_result(review_model)
    repository = ReviewRepository(session)

    result = repository.get_review_result(review_id)

    assert isinstance(result, ReviewResult)
    assert result.review.id == review_id
    assert [item.id for item in result.evidence] == [evidence_a.id, evidence_b.id]

    assert [f.id for f in result.findings] == [
        blocking_finding.id,
        non_blocking_finding.id,
    ]
    assert result.findings[0].evidence_ids == (evidence_a.id,)
    assert result.findings[1].evidence_ids == (evidence_b.id,)

    assert [a.id for a in result.fix_attempts] == [attempt.id]
    assert result.fix_attempts[0].validation_results == (
        ValidationResult(
            status=ValidationStatus.PASSED, tool="mock_validator", message="message"
        ),
    )

    assert result.decision is not None
    assert result.decision.status == ReviewStatus.BLOCKED
    assert [f.id for f in result.decision.blocking_findings] == [blocking_finding.id]
    assert [f.id for f in result.decision.non_blocking_findings] == [
        non_blocking_finding.id
    ]
    assert [a.id for a in result.decision.fix_attempts] == [attempt.id]


def test_get_review_result_returns_none_decision_when_no_decision_persisted() -> None:
    review_model = _make_model()
    review_model.evidence = []
    review_model.findings = []
    review_model.decision = None
    session = MagicMock(spec=Session)
    session.execute.return_value = _mock_execute_result(review_model)
    repository = ReviewRepository(session)

    result = repository.get_review_result(review_model.id)

    assert result is not None
    assert result.decision is None
    assert result.evidence == ()
    assert result.findings == ()
    assert result.fix_attempts == ()


def test_get_review_result_never_commits_or_rolls_back() -> None:
    review_model = _make_model()
    review_model.evidence = []
    review_model.findings = []
    review_model.decision = None
    session = MagicMock(spec=Session)
    session.execute.return_value = _mock_execute_result(review_model)
    repository = ReviewRepository(session)

    repository.get_review_result(review_model.id)

    session.commit.assert_not_called()
    session.rollback.assert_not_called()
