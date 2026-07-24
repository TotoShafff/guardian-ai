"""Unit tests for `ReviewService`.

`ReviewRepository` and the compiled review graph are always mocked, so
none of these tests require PostgreSQL, SQLite, Docker, network access, a
real LangGraph invocation, a Ruff/Pytest subprocess, or an AI provider API
key.
"""

from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.domain.models import Decision, Review, ReviewStatus
from app.orchestrator.state import ReviewWorkflowState
from app.persistence.repositories import ReviewRepository
from app.services.review_service import ReviewRunResult, ReviewService

_TARGET_REFERENCE = "feature/checkout-fix"
_TARGET_PATH = Path("./sample_project")
_CODE = "def add(a, b):\n    return a + b\n"


def _make_review(**overrides: object) -> Review:
    defaults: dict[str, object] = {
        "target_reference": _TARGET_REFERENCE,
        "status": ReviewStatus.RUNNING,
    }
    defaults.update(overrides)
    return Review(**defaults)  # type: ignore[arg-type]


def _make_final_state(review: Review, decision: Decision) -> ReviewWorkflowState:
    state: ReviewWorkflowState = {
        "review": review,
        "target_path": _TARGET_PATH,
        "code": _CODE,
        "evidence": (),
        "findings": (),
        "fix_attempts": (),
        "decision": decision,
        "error": None,
    }
    return state


def _make_service(
    repository: ReviewRepository | None = None,
    graph: MagicMock | None = None,
) -> tuple[ReviewService, ReviewRepository, MagicMock]:
    repository = (
        repository if repository is not None else MagicMock(spec=ReviewRepository)
    )
    graph = graph if graph is not None else MagicMock()
    return (
        ReviewService(review_repository=repository, review_graph=graph),
        repository,
        graph,
    )


def test_run_review_persists_a_running_review_before_invoking_the_graph() -> None:
    saved_review = _make_review()
    decision = Decision(status=ReviewStatus.APPROVED, rationale="ok")
    graph = MagicMock()
    graph.invoke.return_value = _make_final_state(saved_review, decision)

    repository = MagicMock(spec=ReviewRepository)

    def _add_side_effect(review: Review) -> Review:
        assert graph.invoke.call_count == 0, "graph invoked before review was saved"
        return saved_review

    repository.add.side_effect = _add_side_effect
    repository.update.return_value = saved_review
    service, _, _ = _make_service(repository=repository, graph=graph)

    service.run_review(
        target_reference=_TARGET_REFERENCE, target_path=_TARGET_PATH, code=_CODE
    )

    repository.add.assert_called_once()
    added_review = repository.add.call_args[0][0]
    assert isinstance(added_review, Review)
    assert added_review.status == ReviewStatus.RUNNING


def test_run_review_invokes_the_graph_with_the_correct_initial_state() -> None:
    saved_review = _make_review()
    decision = Decision(status=ReviewStatus.APPROVED, rationale="ok")
    repository = MagicMock(spec=ReviewRepository)
    repository.add.return_value = saved_review
    repository.update.return_value = saved_review
    graph = MagicMock()
    graph.invoke.return_value = _make_final_state(saved_review, decision)
    service, _, _ = _make_service(repository=repository, graph=graph)

    service.run_review(
        target_reference=_TARGET_REFERENCE, target_path=_TARGET_PATH, code=_CODE
    )

    graph.invoke.assert_called_once_with(
        {
            "review": saved_review,
            "target_path": _TARGET_PATH,
            "code": _CODE,
            "evidence": (),
            "findings": (),
            "fix_attempts": (),
            "decision": None,
            "error": None,
        }
    )


def test_run_review_updates_review_status_from_the_final_decision() -> None:
    saved_review = _make_review(status=ReviewStatus.RUNNING)
    repository = MagicMock(spec=ReviewRepository)
    repository.add.return_value = saved_review
    repository.update.side_effect = lambda review: review
    decision = Decision(status=ReviewStatus.BLOCKED, rationale="1 blocking finding.")
    graph = MagicMock()
    graph.invoke.return_value = _make_final_state(saved_review, decision)
    service, _, _ = _make_service(repository=repository, graph=graph)

    result = service.run_review(
        target_reference=_TARGET_REFERENCE, target_path=_TARGET_PATH, code=_CODE
    )

    updated_review = repository.update.call_args[0][0]
    assert updated_review.status == ReviewStatus.BLOCKED
    assert result.review.status == ReviewStatus.BLOCKED


def test_run_review_saves_the_updated_review_via_the_repository() -> None:
    saved_review = _make_review(status=ReviewStatus.RUNNING)
    repository = MagicMock(spec=ReviewRepository)
    repository.add.return_value = saved_review
    repository.update.side_effect = lambda review: review
    decision = Decision(status=ReviewStatus.APPROVED, rationale="ok")
    graph = MagicMock()
    graph.invoke.return_value = _make_final_state(saved_review, decision)
    service, _, _ = _make_service(repository=repository, graph=graph)

    service.run_review(
        target_reference=_TARGET_REFERENCE, target_path=_TARGET_PATH, code=_CODE
    )

    repository.update.assert_called_once()
    updated_review = repository.update.call_args[0][0]
    assert updated_review.id == saved_review.id
    # `saved_review` itself is a frozen dataclass and must not have been mutated.
    assert saved_review.status == ReviewStatus.RUNNING
    assert saved_review.completed_at is None
    assert updated_review.completed_at is not None
    assert updated_review.completed_at.tzinfo is not None


def test_run_review_returns_the_persisted_review_and_final_workflow_state() -> None:
    saved_review = _make_review()
    updated_review = _make_review(id=saved_review.id, status=ReviewStatus.APPROVED)
    repository = MagicMock(spec=ReviewRepository)
    repository.add.return_value = saved_review
    repository.update.return_value = updated_review
    decision = Decision(status=ReviewStatus.APPROVED, rationale="ok")
    final_state = _make_final_state(saved_review, decision)
    graph = MagicMock()
    graph.invoke.return_value = final_state
    service, _, _ = _make_service(repository=repository, graph=graph)

    result = service.run_review(
        target_reference=_TARGET_REFERENCE, target_path=_TARGET_PATH, code=_CODE
    )

    assert isinstance(result, ReviewRunResult)
    assert result.review is updated_review
    assert result.workflow_state is final_state


def test_get_review_delegates_to_the_repository() -> None:
    review = _make_review()
    repository = MagicMock(spec=ReviewRepository)
    repository.get_by_id.return_value = review
    service, _, _ = _make_service(repository=repository)

    result = service.get_review(review.id)

    repository.get_by_id.assert_called_once_with(review.id)
    assert result is review


def test_get_review_returns_none_when_the_repository_finds_nothing() -> None:
    repository = MagicMock(spec=ReviewRepository)
    repository.get_by_id.return_value = None
    service, _, _ = _make_service(repository=repository)

    result = service.get_review(uuid4())

    assert result is None


def test_run_review_propagates_graph_exceptions_without_updating_the_review() -> None:
    class _FakeGraphError(Exception):
        pass

    saved_review = _make_review()
    repository = MagicMock(spec=ReviewRepository)
    repository.add.return_value = saved_review
    graph = MagicMock()
    graph.invoke.side_effect = _FakeGraphError("graph blew up")
    service, _, _ = _make_service(repository=repository, graph=graph)

    with pytest.raises(_FakeGraphError, match="graph blew up"):
        service.run_review(
            target_reference=_TARGET_REFERENCE, target_path=_TARGET_PATH, code=_CODE
        )

    repository.update.assert_not_called()
