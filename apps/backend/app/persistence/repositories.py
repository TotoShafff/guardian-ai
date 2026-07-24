"""SQLAlchemy repository for the `Review` aggregate root.

Translates between the framework-independent `Review` domain model
(`app.domain.models.Review`) and its ORM counterpart (`ReviewModel`), so
callers (API handlers, orchestrator nodes, tests) work only with the domain
model at the public boundary and never see SQLAlchemy types. Conversion
between `Review` and `ReviewModel` is an implementation detail kept private
to this module.

`ReviewRepository` receives its `Session` from the caller (see `get_db()` in
`app.persistence.database`) and never creates, commits, or rolls back a
transaction itself — transaction ownership belongs to whoever owns the
session (e.g. a FastAPI request handler or a test). Nested evidence,
findings, decisions, and fix attempts are out of scope for this repository.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Review
from app.persistence.models import ReviewModel


class ReviewNotFoundError(Exception):
    """Raised when a `Review` cannot be found by its id."""

    def __init__(self, review_id: UUID) -> None:
        super().__init__(f"Review not found: {review_id}")
        self.review_id = review_id


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


class ReviewRepository:
    """Persistence gateway for the `Review` aggregate root.

    Contains no business rules — only translation between the domain `Review`
    model and the `reviews` table via a caller-provided `Session`.
    """

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
        """Update the mutable fields of an existing review and flush the session.

        Raises `ReviewNotFoundError` when no review with `review.id` exists.
        Does not commit; the caller owns the transaction.
        """
        model = self._session.get(ReviewModel, review.id)
        if model is None:
            raise ReviewNotFoundError(review.id)

        model.target_reference = review.target_reference
        model.status = review.status
        model.created_at = review.created_at
        model.completed_at = review.completed_at

        self._session.flush()
        return _to_domain(model)
