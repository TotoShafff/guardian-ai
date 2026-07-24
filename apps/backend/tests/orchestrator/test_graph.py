"""Unit tests for `build_review_graph`.

These tests focus on graph construction and execution order, not on
retesting each node's business logic (already covered by
`tests/orchestrator/test_nodes.py`). `RuffTool`, `PytestTool`, and
`AIProvider` are always mocked: no test here invokes a real Ruff/Pytest
process, requires PostgreSQL/SQLite/Docker/network access, or touches the
persistence layer.
"""

from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

from langgraph.graph.state import CompiledStateGraph

from app.domain.models import (
    Decision,
    Evidence,
    EvidenceSeverity,
    EvidenceSource,
    Finding,
    FixAttempt,
    Review,
    ReviewStatus,
)
from app.orchestrator.graph import (
    COLLECT_EVIDENCE,
    MAKE_DECISION,
    PROPOSE_FIXES,
    SEMANTIC_ANALYSIS,
    build_review_graph,
)
from app.orchestrator.nodes import ReviewWorkflowNodes
from app.orchestrator.state import ReviewWorkflowState
from app.providers.base import AIProvider
from app.tools.pytest_tool import PytestTool
from app.tools.ruff_tool import RuffTool

EXPECTED_NODE_NAMES = {
    COLLECT_EVIDENCE,
    SEMANTIC_ANALYSIS,
    PROPOSE_FIXES,
    MAKE_DECISION,
}


def _make_state(**overrides: object) -> ReviewWorkflowState:
    review = Review(
        target_reference="feature/checkout-fix", status=ReviewStatus.RUNNING
    )
    state: ReviewWorkflowState = {
        "review": review,
        "target_path": Path("/example/target"),
        "code": "def add(a, b):\n    return a + b\n",
        "evidence": (),
        "findings": (),
        "fix_attempts": (),
        "decision": None,
        "error": None,
    }
    state.update(overrides)  # type: ignore[typeddict-item]
    return state


def _make_nodes(
    ruff_tool: RuffTool | None = None,
    pytest_tool: PytestTool | None = None,
    ai_provider: AIProvider | None = None,
) -> ReviewWorkflowNodes:
    return ReviewWorkflowNodes(
        ruff_tool=ruff_tool if ruff_tool is not None else MagicMock(spec=RuffTool),
        pytest_tool=pytest_tool
        if pytest_tool is not None
        else MagicMock(spec=PytestTool),
        ai_provider=ai_provider
        if ai_provider is not None
        else MagicMock(spec=AIProvider),
    )


def test_build_review_graph_returns_a_compiled_runnable_graph() -> None:
    nodes = _make_nodes()

    compiled = build_review_graph(nodes)

    assert isinstance(compiled, CompiledStateGraph)
    assert hasattr(compiled, "invoke")


def test_build_review_graph_registers_exactly_the_four_expected_nodes() -> None:
    nodes = _make_nodes()

    compiled = build_review_graph(nodes)

    assert set(compiled.get_graph().nodes.keys()) - {"__start__", "__end__"} == (
        EXPECTED_NODE_NAMES
    )


def test_build_review_graph_executes_nodes_in_the_required_order() -> None:
    call_order: list[str] = []

    ruff_tool = MagicMock(spec=RuffTool)
    pytest_tool = MagicMock(spec=PytestTool)
    ai_provider = MagicMock(spec=AIProvider)

    nodes = ReviewWorkflowNodes(
        ruff_tool=ruff_tool,
        pytest_tool=pytest_tool,
        ai_provider=ai_provider,
    )

    nodes.collect_deterministic_evidence = MagicMock(
        side_effect=lambda state: (
            call_order.append(COLLECT_EVIDENCE) or {"evidence": ()}
        )
    )
    nodes.analyze_semantically = MagicMock(
        side_effect=lambda state: (
            call_order.append(SEMANTIC_ANALYSIS) or {"findings": ()}
        )
    )
    nodes.propose_fixes = MagicMock(
        side_effect=lambda state: (
            call_order.append(PROPOSE_FIXES) or {"fix_attempts": ()}
        )
    )

    decision = Decision(
        status=ReviewStatus.APPROVED,
        rationale="Review approved: no blocking findings.",
    )
    nodes.make_decision = MagicMock(
        side_effect=lambda state: (
            call_order.append(MAKE_DECISION) or {"decision": decision}
        )
    )

    compiled = build_review_graph(nodes)

    compiled.invoke(_make_state())

    assert call_order == [
        COLLECT_EVIDENCE,
        SEMANTIC_ANALYSIS,
        PROPOSE_FIXES,
        MAKE_DECISION,
    ]

def test_build_review_graph_merges_partial_state_updates_into_final_state() -> None:
    evidence_item = Evidence(
        review_id=uuid4(),
        source=EvidenceSource.RUFF,
        severity=EvidenceSeverity.NON_BLOCKING,
        category="F401",
        message="unused import",
    )
    finding = Finding(
        review_id=uuid4(),
        severity=EvidenceSeverity.NON_BLOCKING,
        title="Unused import",
        description="`os` is imported but never used",
        is_fixable=False,
    )
    ruff_tool = MagicMock(spec=RuffTool)
    ruff_tool.analyze.return_value = [evidence_item]
    pytest_tool = MagicMock(spec=PytestTool)
    pytest_tool.analyze.return_value = []
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.analyze_code.return_value = (finding,)
    nodes = _make_nodes(
        ruff_tool=ruff_tool, pytest_tool=pytest_tool, ai_provider=ai_provider
    )
    compiled = build_review_graph(nodes)

    result = compiled.invoke(_make_state())

    assert result["evidence"] == (evidence_item,)
    assert result["findings"] == (finding,)


def test_build_review_graph_final_state_contains_all_workflow_outputs() -> None:
    finding = Finding(
        review_id=uuid4(),
        severity=EvidenceSeverity.BLOCKING,
        title="Failing test",
        description="`test_checkout` fails",
        is_fixable=True,
    )
    ruff_tool = MagicMock(spec=RuffTool)
    ruff_tool.analyze.return_value = []
    pytest_tool = MagicMock(spec=PytestTool)
    pytest_tool.analyze.return_value = []
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.analyze_code.return_value = (finding,)
    ai_provider.propose_fix.return_value = "--- a\n+++ b\n"
    nodes = _make_nodes(
        ruff_tool=ruff_tool, pytest_tool=pytest_tool, ai_provider=ai_provider
    )
    compiled = build_review_graph(nodes)

    result = compiled.invoke(_make_state())

    assert isinstance(result["evidence"], tuple)
    assert result["findings"] == (finding,)
    assert len(result["fix_attempts"]) == 1
    assert isinstance(result["fix_attempts"][0], FixAttempt)
    assert isinstance(result["decision"], Decision)
    assert result["decision"].status == ReviewStatus.BLOCKED


def test_build_review_graph_does_not_mutate_the_original_input_state() -> None:
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.analyze_code.return_value = ()
    ai_provider.propose_fix.return_value = ""
    nodes = _make_nodes(ai_provider=ai_provider)
    compiled = build_review_graph(nodes)
    state = _make_state()
    snapshot = dict(state)

    compiled.invoke(state)

    assert state == snapshot


def test_build_review_graph_uses_dependencies_from_the_supplied_nodes_instance() -> (
    None
):
    ruff_tool = MagicMock(spec=RuffTool)
    ruff_tool.analyze.return_value = []
    pytest_tool = MagicMock(spec=PytestTool)
    pytest_tool.analyze.return_value = []
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.analyze_code.return_value = ()
    nodes = _make_nodes(
        ruff_tool=ruff_tool, pytest_tool=pytest_tool, ai_provider=ai_provider
    )
    compiled = build_review_graph(nodes)

    compiled.invoke(_make_state())

    ruff_tool.analyze.assert_called_once()
    pytest_tool.analyze.assert_called_once()
    ai_provider.analyze_code.assert_called_once()


def test_build_review_graph_never_touches_persistence_or_web_frameworks() -> None:
    import ast

    import app.orchestrator.graph as graph_module

    forbidden_root_modules = {
        "sqlalchemy",
        "fastapi",
        "requests",
        "httpx",
        "socket",
        "app.persistence",
    }

    source = Path(graph_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)

    for forbidden in forbidden_root_modules:
        assert forbidden not in imported_modules, (
            f"graph module unexpectedly imports '{forbidden}'"
        )


def test_build_review_graph_does_not_instantiate_concrete_tools_or_providers() -> None:
    import inspect

    import app.orchestrator.graph as graph_module

    source = inspect.getsource(graph_module.build_review_graph)

    assert "RuffTool(" not in source
    assert "PytestTool(" not in source
    assert "MockProvider(" not in source
