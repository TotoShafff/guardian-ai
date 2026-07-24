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
from app.config.settings import Settings
from app.orchestrator.graph import build_review_graph
from app.orchestrator.nodes import ReviewWorkflowNodes
from app.orchestrator.validation import FixValidator, MockFixValidator
from app.persistence.database import SessionLocal
from app.persistence.repositories import ReviewRepository
from app.providers.base import AIProvider
from app.providers.exceptions import AIProviderConfigurationError
from app.providers.mock import MockProvider
from app.providers.openrouter import OpenRouterProvider
from app.services.review_service import ReviewService
from app.tools.pytest_tool import PytestTool
from app.tools.ruff_tool import RuffTool

#: Supported `Settings.ai_provider` values and the constructors they select.
_MOCK_PROVIDER_NAME = "mock"
_OPENROUTER_PROVIDER_NAME = "openrouter"


def get_db_session() -> Generator[Session, None, None]:
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


def build_ai_provider(settings: Settings) -> AIProvider:
    """Construct the `AIProvider` selected by `settings.ai_provider`.

    `"mock"` (the default) selects `MockProvider`, requiring no API key or
    network access. `"openrouter"` selects `OpenRouterProvider`, calling
    OpenRouter's `/chat/completions` API using the `openrouter_*` settings
    (see `docs/DECISIONS.md` ADR-010). Any other value raises
    `AIProviderConfigurationError` immediately, rather than silently
    falling back to a provider the operator did not ask for. Exposed as a
    plain function of `Settings` (not just inlined in `get_ai_provider()`)
    so provider selection can be unit tested without FastAPI's dependency
    injection machinery.
    """
    provider_name = settings.ai_provider.strip().lower()

    if provider_name == _MOCK_PROVIDER_NAME:
        return MockProvider()

    if provider_name == _OPENROUTER_PROVIDER_NAME:
        return OpenRouterProvider(
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            base_url=settings.openrouter_base_url,
            timeout_seconds=settings.openrouter_timeout_seconds,
            app_name=settings.openrouter_app_name,
            app_url=settings.openrouter_app_url,
        )

    raise AIProviderConfigurationError(
        f"Unsupported AI_PROVIDER: {settings.ai_provider!r}"
    )


def get_ai_provider() -> AIProvider:
    """Construct the configured `AIProvider` for this request (see `build_ai_provider`)."""
    return build_ai_provider(get_settings())


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
