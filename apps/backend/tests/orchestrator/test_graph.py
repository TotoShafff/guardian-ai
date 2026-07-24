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

import pytest
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
    ValidationResult,
    ValidationStatus,
)
from app.orchestrator.graph import (
    COLLECT_EVIDENCE,
    MAKE_DECISION,
    PROPOSE_FIXES,
    ROUTE_DECISION,
    ROUTE_RETRY,
    SEMANTIC_ANALYSIS,
    VALIDATE_FIXES,
    build_review_graph,
    route_after_validation,
)
from app.orchestrator.nodes import ReviewWorkflowNodes
from app.orchestrator.state import ReviewWorkflowState
from app.orchestrator.validation import FixValidator, MockFixValidator
from app.providers.base import AIProvider
from app.tools.pytest_tool import PytestTool
from app.tools.ruff_tool import RuffTool

EXPECTED_NODE_NAMES = {
    COLLECT_EVIDENCE,
    SEMANTIC_ANALYSIS,
    PROPOSE_FIXES,
    VALIDATE_FIXES,
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
    fix_validator: FixValidator | None = None,
    max_fix_attempts: int = 3,
) -> ReviewWorkflowNodes:
    return ReviewWorkflowNodes(
        ruff_tool=ruff_tool if ruff_tool is not None else MagicMock(spec=RuffTool),
        pytest_tool=pytest_tool
        if pytest_tool is not None
        else MagicMock(spec=PytestTool),
        ai_provider=ai_provider
        if ai_provider is not None
        else MagicMock(spec=AIProvider),
        fix_validator=fix_validator
        if fix_validator is not None
        else MockFixValidator(),
        max_fix_attempts=max_fix_attempts,
    )


def _make_finding(**overrides: object) -> Finding:
    defaults: dict[str, object] = {
        "review_id": uuid4(),
        "severity": EvidenceSeverity.BLOCKING,
        "title": "Sample finding",
        "description": "Sample finding description",
        "is_fixable": True,
    }
    defaults.update(overrides)
    return Finding(**defaults)  # type: ignore[arg-type]


def _make_fix_attempt(**overrides: object) -> FixAttempt:
    defaults: dict[str, object] = {
        "finding_id": uuid4(),
        "patch": "--- a\n+++ b\n",
        "attempt_number": 1,
    }
    defaults.update(overrides)
    return FixAttempt(**defaults)  # type: ignore[arg-type]


def _make_validation_result(
    status: ValidationStatus, **overrides: object
) -> ValidationResult:
    defaults: dict[str, object] = {
        "status": status,
        "tool": "mock_validator",
        "message": "sample validation message",
    }
    defaults.update(overrides)
    return ValidationResult(**defaults)  # type: ignore[arg-type]


def test_build_review_graph_returns_a_compiled_runnable_graph() -> None:
    nodes = _make_nodes()

    compiled = build_review_graph(nodes)

    assert isinstance(compiled, CompiledStateGraph)
    assert hasattr(compiled, "invoke")


def test_build_review_graph_registers_exactly_the_five_expected_nodes() -> None:
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
    fix_validator = MagicMock(spec=FixValidator)

    nodes = ReviewWorkflowNodes(
        ruff_tool=ruff_tool,
        pytest_tool=pytest_tool,
        ai_provider=ai_provider,
        fix_validator=fix_validator,
        max_fix_attempts=3,
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
    nodes.validate_fixes = MagicMock(
        side_effect=lambda state: (
            call_order.append(VALIDATE_FIXES) or {"fix_attempts": ()}
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
        VALIDATE_FIXES,
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


def test_build_review_graph_wires_conditional_edges_after_validate_fixes() -> None:
    nodes = _make_nodes()

    compiled = build_review_graph(nodes)

    edges = compiled.get_graph().edges
    assert any(
        edge.source == PROPOSE_FIXES
        and edge.target == VALIDATE_FIXES
        and not edge.conditional
        for edge in edges
    )
    assert any(
        edge.source == VALIDATE_FIXES
        and edge.target == PROPOSE_FIXES
        and edge.conditional
        and edge.data == ROUTE_RETRY
        for edge in edges
    )
    assert any(
        edge.source == VALIDATE_FIXES
        and edge.target == MAKE_DECISION
        and edge.conditional
        and edge.data == ROUTE_DECISION
        for edge in edges
    )


def test_build_review_graph_retries_propose_fixes_after_a_failed_validation() -> None:
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
    ai_provider.propose_fix.side_effect = ["patch-1", "patch-2"]
    fix_validator = MagicMock(spec=FixValidator)
    fix_validator.validate.side_effect = [
        (_make_validation_result(ValidationStatus.FAILED),),
        (_make_validation_result(ValidationStatus.PASSED),),
    ]
    nodes = _make_nodes(
        ruff_tool=ruff_tool,
        pytest_tool=pytest_tool,
        ai_provider=ai_provider,
        fix_validator=fix_validator,
        max_fix_attempts=3,
    )
    compiled = build_review_graph(nodes)

    result = compiled.invoke(_make_state())

    assert ai_provider.propose_fix.call_count == 2
    assert fix_validator.validate.call_count == 2
    assert len(result["fix_attempts"]) == 2
    first_attempt, second_attempt = result["fix_attempts"]
    assert first_attempt.attempt_number == 1
    assert first_attempt.validation_results[0].status == ValidationStatus.FAILED
    assert second_attempt.attempt_number == 2
    assert second_attempt.validation_results[0].status == ValidationStatus.PASSED
    assert isinstance(result["decision"], Decision)


def test_build_review_graph_does_not_retry_after_a_passed_validation() -> None:
    finding = Finding(
        review_id=uuid4(),
        severity=EvidenceSeverity.BLOCKING,
        title="Failing test",
        description="`test_checkout` fails",
        is_fixable=True,
    )
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.analyze_code.return_value = (finding,)
    ai_provider.propose_fix.return_value = "--- a\n+++ b\n"
    fix_validator = MagicMock(spec=FixValidator)
    fix_validator.validate.return_value = (
        _make_validation_result(ValidationStatus.PASSED),
    )
    nodes = _make_nodes(
        ai_provider=ai_provider, fix_validator=fix_validator, max_fix_attempts=3
    )
    compiled = build_review_graph(nodes)

    result = compiled.invoke(_make_state())

    assert ai_provider.propose_fix.call_count == 1
    assert len(result["fix_attempts"]) == 1
    assert isinstance(result["decision"], Decision)


def test_build_review_graph_stops_retrying_once_max_fix_attempts_is_reached() -> None:
    finding = Finding(
        review_id=uuid4(),
        severity=EvidenceSeverity.BLOCKING,
        title="Failing test",
        description="`test_checkout` fails",
        is_fixable=True,
    )
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.analyze_code.return_value = (finding,)
    ai_provider.propose_fix.return_value = "--- a\n+++ b\n"
    fix_validator = MagicMock(spec=FixValidator)
    fix_validator.validate.return_value = (
        _make_validation_result(ValidationStatus.FAILED),
    )
    nodes = _make_nodes(
        ai_provider=ai_provider, fix_validator=fix_validator, max_fix_attempts=2
    )
    compiled = build_review_graph(nodes)

    result = compiled.invoke(_make_state())

    assert ai_provider.propose_fix.call_count == 2
    assert len(result["fix_attempts"]) == 2
    assert all(
        attempt.validation_results[0].status == ValidationStatus.FAILED
        for attempt in result["fix_attempts"]
    )
    assert isinstance(result["decision"], Decision)
    assert result["decision"].status == ReviewStatus.BLOCKED


def test_route_after_validation_decision_when_no_blocking_findings() -> None:
    findings = (_make_finding(severity=EvidenceSeverity.NON_BLOCKING),)
    state = _make_state(findings=findings, fix_attempts=())

    result = route_after_validation(state, max_fix_attempts=3)

    assert result == ROUTE_DECISION


def test_route_after_validation_decision_when_finding_not_fixable() -> None:
    findings = (_make_finding(severity=EvidenceSeverity.BLOCKING, is_fixable=False),)
    state = _make_state(findings=findings, fix_attempts=())

    result = route_after_validation(state, max_fix_attempts=3)

    assert result == ROUTE_DECISION


def test_route_after_validation_retry_when_attempt_missing() -> None:
    finding = _make_finding(severity=EvidenceSeverity.BLOCKING, is_fixable=True)
    state = _make_state(findings=(finding,), fix_attempts=())

    result = route_after_validation(state, max_fix_attempts=3)

    assert result == ROUTE_RETRY


def test_route_after_validation_retry_on_failed_validation() -> None:
    finding = _make_finding(severity=EvidenceSeverity.BLOCKING, is_fixable=True)
    attempt = _make_fix_attempt(
        finding_id=finding.id,
        attempt_number=1,
        validation_results=(_make_validation_result(ValidationStatus.FAILED),),
    )
    state = _make_state(findings=(finding,), fix_attempts=(attempt,))

    result = route_after_validation(state, max_fix_attempts=3)

    assert result == ROUTE_RETRY


def test_route_after_validation_retry_on_error_validation() -> None:
    finding = _make_finding(severity=EvidenceSeverity.BLOCKING, is_fixable=True)
    attempt = _make_fix_attempt(
        finding_id=finding.id,
        attempt_number=1,
        validation_results=(_make_validation_result(ValidationStatus.ERROR),),
    )
    state = _make_state(findings=(finding,), fix_attempts=(attempt,))

    result = route_after_validation(state, max_fix_attempts=3)

    assert result == ROUTE_RETRY


def test_route_after_validation_decision_when_latest_attempt_passed() -> None:
    finding = _make_finding(severity=EvidenceSeverity.BLOCKING, is_fixable=True)
    attempt = _make_fix_attempt(
        finding_id=finding.id,
        attempt_number=1,
        validation_results=(_make_validation_result(ValidationStatus.PASSED),),
    )
    state = _make_state(findings=(finding,), fix_attempts=(attempt,))

    result = route_after_validation(state, max_fix_attempts=3)

    assert result == ROUTE_DECISION


def test_route_after_validation_decision_when_max_attempts_reached() -> None:
    finding = _make_finding(severity=EvidenceSeverity.BLOCKING, is_fixable=True)
    attempt = _make_fix_attempt(
        finding_id=finding.id,
        attempt_number=2,
        validation_results=(_make_validation_result(ValidationStatus.FAILED),),
    )
    state = _make_state(findings=(finding,), fix_attempts=(attempt,))

    result = route_after_validation(state, max_fix_attempts=2)

    assert result == ROUTE_DECISION


def test_route_after_validation_rejects_invalid_max_fix_attempts() -> None:
    state = _make_state(findings=(), fix_attempts=())

    with pytest.raises(ValueError, match="max_fix_attempts"):
        route_after_validation(state, max_fix_attempts=0)


def test_build_review_graph_empty_patches_stop_at_max_fix_attempts() -> None:
    finding = _make_finding(
        severity=EvidenceSeverity.BLOCKING,
        is_fixable=True,
    )
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.analyze_code.return_value = (finding,)
    ai_provider.propose_fix.return_value = ""

    nodes = _make_nodes(
        ai_provider=ai_provider,
        fix_validator=MockFixValidator(),
        max_fix_attempts=2,
    )
    compiled = build_review_graph(nodes)

    result = compiled.invoke(_make_state())

    assert ai_provider.propose_fix.call_count == 2
    assert len(result["fix_attempts"]) == 2
    assert [attempt.attempt_number for attempt in result["fix_attempts"]] == [1, 2]
    assert all(attempt.patch == "" for attempt in result["fix_attempts"])
    assert all(
        attempt.validation_results[0].status == ValidationStatus.FAILED
        for attempt in result["fix_attempts"]
    )
    assert isinstance(result["decision"], Decision)
