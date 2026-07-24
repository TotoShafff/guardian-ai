"""Application service coordinating a review request end to end.

`ReviewService` is the single place that sequences persisting a `Review`
and running it through the compiled LangGraph review workflow (see
`app.orchestrator.graph.build_review_graph`). It contains no HTTP concerns
(those belong to `app.api`, per `.cursor/rules/backend.mdc`) and no
LangGraph node/graph-wiring logic (that belongs to `app.orchestrator`) —
only the request-level sequencing described in `docs/ARCHITECTURE.md`
Section 10 and ADR-013 (synchronous review processing).

This module does not instantiate a database session, `RuffTool`,
`PytestTool`, an `AIProvider`, a `FixValidator`, or read global settings —
all of that is supplied by the caller (see `app/api/dependencies.py`)
through the `ReviewRepository` and compiled graph passed into the
constructor.
"""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple, cast
from uuid import UUID

from langgraph.graph.state import CompiledStateGraph

from app.domain.models import Review, ReviewStatus
from app.orchestrator.state import ReviewWorkflowState
from app.persistence.repositories import ReviewRepository


def _utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


class ReviewRunResult(NamedTuple):
    """The outcome of `ReviewService.run_review()`."""

    #: The persisted `Review`, with its final status and completion time.
    review: Review
    #: The final LangGraph state, carrying evidence/findings/fix_attempts/decision.
    workflow_state: ReviewWorkflowState


class ReviewService:
    """Coordinates persisting a `Review` and running it through the review graph."""

    def __init__(
        self,
        review_repository: ReviewRepository,
        review_graph: CompiledStateGraph,
    ) -> None:
        self._review_repository = review_repository
        self._review_graph = review_graph

    def run_review(
        self,
        target_reference: str,
        target_path: Path,
        code: str,
    ) -> ReviewRunResult:
        """Persist a new `RUNNING` review, run it through the graph, and persist the outcome.

        The review is saved with status `RUNNING` *before* the graph is
        invoked, so a persisted record exists even if the graph later
        raises. The compiled graph then runs synchronously (per ADR-013,
        no background job queue); its final `Decision` determines the
        persisted review's final `status` and `completed_at`. Graph
        exceptions are not caught here — they propagate to the caller, and
        in that case transaction handling is delegated to the caller. Neither the
        initial nor the final `Review` is mutated in place; updates go
        through `dataclasses.replace()`.
        """
        review = Review(target_reference=target_reference, status=ReviewStatus.RUNNING)
        saved_review = self._review_repository.add(review)

        initial_state: ReviewWorkflowState = {
            "review": saved_review,
            "target_path": target_path,
            "code": code,
            "evidence": (),
            "findings": (),
            "fix_attempts": (),
            "decision": None,
            "error": None,
        }

        # `CompiledStateGraph.invoke()` is typed generically as `dict[str, Any]`;
        # it is built from `StateGraph(ReviewWorkflowState)` (see
        # `app.orchestrator.graph.build_review_graph`), so its result always has
        # the `ReviewWorkflowState` shape.
        final_state = cast(
            ReviewWorkflowState, self._review_graph.invoke(initial_state)
        )

        decision = final_state["decision"]
        assert decision is not None, "the review graph must always produce a decision"
        updated_review = replace(
            saved_review, status=decision.status, completed_at=_utc_now()
        )
        persisted_review = self._review_repository.update(updated_review)

        return ReviewRunResult(review=persisted_review, workflow_state=final_state)

    def get_review(self, review_id: UUID) -> Review | None:
        """Return the review with `review_id`, or None if it does not exist."""
        return self._review_repository.get_by_id(review_id)
