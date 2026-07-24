"""Unit tests for `ReviewRepository`.

All tests use a mocked SQLAlchemy `Session` (via `unittest.mock`), so none of
them require PostgreSQL, SQLite, Docker, or network access. The goal is to
verify the repository's *contract* with the session (what it calls, and
when) and its domain <-> ORM conversion, not real SQL execution.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.domain.models import Review, ReviewStatus
from app.persistence.models import ReviewModel
from app.persistence.repositories import ReviewNotFoundError, ReviewRepository


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
