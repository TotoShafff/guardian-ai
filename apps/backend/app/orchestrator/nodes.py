"""Initial nodes of the Guardian AI review LangGraph workflow.

`ReviewWorkflowNodes` groups the workflow's node methods behind explicit,
constructor-injected dependencies (a `RuffTool`, a `PytestTool`, and an
`AIProvider`), so the graph wiring (added in a later stage, per
`docs/ROADMAP.md`) can compose them without any node reaching into global
state, a database session, or a concrete tool/provider implementation.

Only the two nodes needed to start collecting evidence are implemented
here: `collect_deterministic_evidence` (Ruff + Pytest) and
`analyze_semantically` (the AI provider). Neither node mutates the `state`
it receives — each returns only the partial state update it is responsible
for, matching the convention LangGraph uses to merge node outputs into the
graph's state.
"""

from app.orchestrator.state import ReviewWorkflowState
from app.providers.base import AIProvider
from app.tools.pytest_tool import PytestTool
from app.tools.ruff_tool import RuffTool


class ReviewWorkflowNodes:
    """Constructor-injected collection of the review workflow's node methods."""

    def __init__(
        self,
        ruff_tool: RuffTool,
        pytest_tool: PytestTool,
        ai_provider: AIProvider,
    ) -> None:
        self._ruff_tool = ruff_tool
        self._pytest_tool = pytest_tool
        self._ai_provider = ai_provider

    def collect_deterministic_evidence(
        self,
        state: ReviewWorkflowState,
    ) -> dict[str, object]:
        """Run Ruff and Pytest against `state["target_path"]` and merge their evidence.

        Evidence is combined in a fixed order (Ruff first, then Pytest) so
        downstream nodes see a stable, reproducible ordering. Tool
        exceptions are not caught here — they propagate to the caller, which
        decides how a failed evidence-collection step affects the review
        (see `docs/ARCHITECTURE.md` Section 10 on degrading rather than
        crashing; that handling is added in a later stage). This method does
        not access the database and does not mutate `state`.
        """
        target_path = state["target_path"]
        review_id = state["review"].id

        ruff_evidence = self._ruff_tool.analyze(target_path, review_id)
        pytest_evidence = self._pytest_tool.analyze(target_path, review_id)

        return {"evidence": tuple(ruff_evidence) + tuple(pytest_evidence)}

    def analyze_semantically(
        self,
        state: ReviewWorkflowState,
    ) -> dict[str, object]:
        """Ask the AI provider for semantic findings given the code and evidence so far.

        This node only gathers findings from `AIProvider.analyze_code()`; it
        does not propose fixes — that is a later step in the workflow (see
        `docs/ROADMAP.md` Stage 6). This method does not access the database
        and does not mutate `state`.
        """
        code = state["code"]
        evidence = state["evidence"]

        findings = self._ai_provider.analyze_code(code, evidence)

        return {"findings": findings}
