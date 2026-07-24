"""FastAPI dependency providers for the Guardian AI backend.

This module is the only place allowed to construct concrete infrastructure
objects for a request — a database session, `RuffTool`, `PytestTool`,
`MockProvider`, `MockFixValidator`, `ReviewWorkflowNodes`, the compiled
review graph, and `ReviewService` — and the only place that reads
`Settings`/`get_settings()` for this API layer (see `.cursor/rules/
backend.mdc`: "prefer explicit dependencies over global state"). Routers
and `ReviewService` only ever receive these as parameters/constructor
arguments; they never build or look them up themselves.
"""

from collections.abc import Generator

from fastapi import Depends
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.orm import Session

from app.config import get_settings
from app.orchestrator.graph import build_review_graph
from app.orchestrator.nodes import ReviewWorkflowNodes
from app.orchestrator.validation import FixValidator, MockFixValidator
from app.persistence.database import SessionLocal
from app.persistence.repositories import ReviewRepository
from app.providers.base import AIProvider
from app.providers.mock import MockProvider
from app.services.review_service import ReviewService
from app.tools.pytest_tool import PytestTool
from app.tools.ruff_tool import RuffTool


def get_db_session() -> Generator[Session, None, None]:
    """Yield a request-scoped session that commits on success, rolls back on error.

    This session's transaction is owned by the API request it serves — see
    `ReviewRepository`'s docstring ("transaction ownership belongs to
    whoever owns the session"). This is distinct from the lower-level
    `app.persistence.database.get_db()`, which only opens and closes a
    session and leaves commit/rollback to its caller; his dependency uses the shared SessionLocal factory while adding
    request-level commit and rollback behavior.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_review_repository(
    session: Session = Depends(get_db_session),
) -> ReviewRepository:
    """Construct a `ReviewRepository` bound to this request's session."""
    return ReviewRepository(session)


def get_ai_provider() -> AIProvider:
    """Construct the configured `AIProvider`.

    Only `MockProvider` is wired up so far; selecting a real provider via
    configuration is a later stage (see `docs/ROADMAP.md` Phase 3).
    """
    return MockProvider()


def get_fix_validator() -> FixValidator:
    """Construct the configured `FixValidator`.

    Only `MockFixValidator` is wired up so far; a validator that actually
    applies patches and re-runs deterministic tools is a later stage.
    """
    return MockFixValidator()


def get_ruff_tool() -> RuffTool:
    """Construct a `RuffTool` using the configured tool timeout."""
    settings = get_settings()
    return RuffTool(timeout_seconds=settings.tool_timeout_seconds)


def get_pytest_tool() -> PytestTool:
    """Construct a `PytestTool` using the configured tool timeout."""
    settings = get_settings()
    return PytestTool(timeout_seconds=settings.tool_timeout_seconds)


def get_review_workflow_nodes(
    ruff_tool: RuffTool = Depends(get_ruff_tool),
    pytest_tool: PytestTool = Depends(get_pytest_tool),
    ai_provider: AIProvider = Depends(get_ai_provider),
    fix_validator: FixValidator = Depends(get_fix_validator),
) -> ReviewWorkflowNodes:
    """Construct `ReviewWorkflowNodes`, reading `max_fix_attempts` from settings.

    `max_fix_attempts` is read from `Settings` only here — `nodes.py` and
    `graph.py` always receive it explicitly, never reading settings
    themselves (see `docs/DECISIONS.md` ADR-014).
    """
    settings = get_settings()
    return ReviewWorkflowNodes(
        ruff_tool=ruff_tool,
        pytest_tool=pytest_tool,
        ai_provider=ai_provider,
        fix_validator=fix_validator,
        max_fix_attempts=settings.max_fix_attempts,
    )


def get_review_graph(
    nodes: ReviewWorkflowNodes = Depends(get_review_workflow_nodes),
) -> CompiledStateGraph:
    """Build and compile the review workflow graph for this request."""
    return build_review_graph(nodes)


def get_review_service(
    review_repository: ReviewRepository = Depends(get_review_repository),
    review_graph: CompiledStateGraph = Depends(get_review_graph),
) -> ReviewService:
    """Construct a `ReviewService` wired with this request's dependencies."""
    return ReviewService(
        review_repository=review_repository,
        review_graph=review_graph,
    )
