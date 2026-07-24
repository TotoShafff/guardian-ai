"""Unit tests for `ReviewWorkflowNodes`.

`RuffTool`, `PytestTool`, and `AIProvider` are always mocked: no test here
invokes a real Ruff/Pytest process, requires PostgreSQL/SQLite/Docker/
network access, or touches the persistence layer.
"""

from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

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
from app.orchestrator.nodes import ReviewWorkflowNodes
from app.orchestrator.state import ReviewWorkflowState
from app.providers.base import AIProvider
from app.tools.pytest_tool import PytestTool
from app.tools.ruff_tool import RuffTool


def _make_evidence(source: EvidenceSource, **overrides: object) -> Evidence:
    defaults: dict[str, object] = {
        "review_id": uuid4(),
        "source": source,
        "severity": EvidenceSeverity.BLOCKING,
        "category": "test_failure" if source == EvidenceSource.PYTEST else "F401",
        "message": "sample message",
    }
    defaults.update(overrides)
    return Evidence(**defaults)  # type: ignore[arg-type]


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


def test_collect_evidence_calls_ruff_with_target_and_review_id() -> None:
    ruff_tool = MagicMock(spec=RuffTool)
    ruff_tool.analyze.return_value = []
    pytest_tool = MagicMock(spec=PytestTool)
    pytest_tool.analyze.return_value = []
    nodes = _make_nodes(ruff_tool=ruff_tool, pytest_tool=pytest_tool)
    state = _make_state()

    nodes.collect_deterministic_evidence(state)

    ruff_tool.analyze.assert_called_once_with(state["target_path"], state["review"].id)


def test_collect_evidence_calls_pytest_with_target_and_review_id() -> None:
    ruff_tool = MagicMock(spec=RuffTool)
    ruff_tool.analyze.return_value = []
    pytest_tool = MagicMock(spec=PytestTool)
    pytest_tool.analyze.return_value = []
    nodes = _make_nodes(ruff_tool=ruff_tool, pytest_tool=pytest_tool)
    state = _make_state()

    nodes.collect_deterministic_evidence(state)

    pytest_tool.analyze.assert_called_once_with(
        state["target_path"], state["review"].id
    )


def test_collect_evidence_orders_ruff_before_pytest() -> None:
    ruff_item = _make_evidence(EvidenceSource.RUFF)
    pytest_item = _make_evidence(EvidenceSource.PYTEST)
    ruff_tool = MagicMock(spec=RuffTool)
    ruff_tool.analyze.return_value = [ruff_item]
    pytest_tool = MagicMock(spec=PytestTool)
    pytest_tool.analyze.return_value = [pytest_item]
    nodes = _make_nodes(ruff_tool=ruff_tool, pytest_tool=pytest_tool)
    state = _make_state()

    result = nodes.collect_deterministic_evidence(state)

    assert result["evidence"] == (ruff_item, pytest_item)


def test_collect_deterministic_evidence_returns_a_tuple() -> None:
    ruff_tool = MagicMock(spec=RuffTool)
    ruff_tool.analyze.return_value = [_make_evidence(EvidenceSource.RUFF)]
    pytest_tool = MagicMock(spec=PytestTool)
    pytest_tool.analyze.return_value = [_make_evidence(EvidenceSource.PYTEST)]
    nodes = _make_nodes(ruff_tool=ruff_tool, pytest_tool=pytest_tool)
    state = _make_state()

    result = nodes.collect_deterministic_evidence(state)

    assert isinstance(result, dict)
    assert set(result.keys()) == {"evidence"}
    assert isinstance(result["evidence"], tuple)


def test_collect_deterministic_evidence_does_not_mutate_the_incoming_state() -> None:
    ruff_tool = MagicMock(spec=RuffTool)
    ruff_tool.analyze.return_value = [_make_evidence(EvidenceSource.RUFF)]
    pytest_tool = MagicMock(spec=PytestTool)
    pytest_tool.analyze.return_value = [_make_evidence(EvidenceSource.PYTEST)]
    nodes = _make_nodes(ruff_tool=ruff_tool, pytest_tool=pytest_tool)
    state = _make_state()
    snapshot = dict(state)

    nodes.collect_deterministic_evidence(state)

    assert state == snapshot


def test_collect_deterministic_evidence_propagates_tool_exceptions_unchanged() -> None:
    class _FakeToolError(Exception):
        pass

    ruff_tool = MagicMock(spec=RuffTool)
    ruff_tool.analyze.side_effect = _FakeToolError("ruff blew up")
    pytest_tool = MagicMock(spec=PytestTool)
    nodes = _make_nodes(ruff_tool=ruff_tool, pytest_tool=pytest_tool)
    state = _make_state()

    with pytest.raises(_FakeToolError, match="ruff blew up"):
        nodes.collect_deterministic_evidence(state)

    pytest_tool.analyze.assert_not_called()


def test_analyze_semantically_passes_code_and_evidence_to_ai_provider() -> None:
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.analyze_code.return_value = ()
    nodes = _make_nodes(ai_provider=ai_provider)
    evidence = (_make_evidence(EvidenceSource.RUFF),)
    state = _make_state(code="def add(a, b):\n    return a + b\n", evidence=evidence)

    nodes.analyze_semantically(state)

    ai_provider.analyze_code.assert_called_once_with(state["code"], evidence)


def test_analyze_semantically_returns_provider_findings_unchanged() -> None:
    finding = Finding(
        review_id=uuid4(),
        severity=EvidenceSeverity.BLOCKING,
        title="Unused import",
        description="`os` is imported but never used",
        is_fixable=False,
    )
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.analyze_code.return_value = (finding,)
    nodes = _make_nodes(ai_provider=ai_provider)
    state = _make_state()

    result = nodes.analyze_semantically(state)

    assert result == {"findings": (finding,)}


def test_analyze_semantically_does_not_mutate_the_incoming_state() -> None:
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.analyze_code.return_value = ()
    nodes = _make_nodes(ai_provider=ai_provider)
    state = _make_state()
    snapshot = dict(state)

    nodes.analyze_semantically(state)

    assert state == snapshot


def test_make_decision_approves_when_there_are_no_blocking_findings() -> None:
    findings = (
        _make_finding(severity=EvidenceSeverity.NON_BLOCKING),
        _make_finding(severity=EvidenceSeverity.INFO),
    )
    nodes = _make_nodes()
    state = _make_state(findings=findings)

    result = nodes.make_decision(state)

    assert result["decision"].status == ReviewStatus.APPROVED


def test_make_decision_blocks_when_at_least_one_blocking_finding_exists() -> None:
    findings = (
        _make_finding(severity=EvidenceSeverity.NON_BLOCKING),
        _make_finding(severity=EvidenceSeverity.BLOCKING),
    )
    nodes = _make_nodes()
    state = _make_state(findings=findings)

    result = nodes.make_decision(state)

    assert result["decision"].status == ReviewStatus.BLOCKED


def test_make_decision_separates_blocking_and_non_blocking_findings() -> None:
    blocking = _make_finding(severity=EvidenceSeverity.BLOCKING)
    non_blocking = _make_finding(severity=EvidenceSeverity.NON_BLOCKING)
    info = _make_finding(severity=EvidenceSeverity.INFO)
    nodes = _make_nodes()
    state = _make_state(findings=(blocking, non_blocking, info))

    decision = nodes.make_decision(state)["decision"]

    assert decision.blocking_findings == (blocking,)
    assert decision.non_blocking_findings == (non_blocking, info)


def test_make_decision_preserves_finding_order_within_each_group() -> None:
    blocking_first = _make_finding(severity=EvidenceSeverity.BLOCKING, title="first")
    non_blocking = _make_finding(severity=EvidenceSeverity.NON_BLOCKING, title="second")
    blocking_second = _make_finding(severity=EvidenceSeverity.BLOCKING, title="third")
    nodes = _make_nodes()
    state = _make_state(findings=(blocking_first, non_blocking, blocking_second))

    decision = nodes.make_decision(state)["decision"]

    assert decision.blocking_findings == (blocking_first, blocking_second)
    assert decision.non_blocking_findings == (non_blocking,)


def test_make_decision_preserves_existing_fix_attempts() -> None:
    fix_attempt = _make_fix_attempt()
    nodes = _make_nodes()
    state = _make_state(findings=(), fix_attempts=(fix_attempt,))

    decision = nodes.make_decision(state)["decision"]

    assert decision.fix_attempts == (fix_attempt,)


def test_make_decision_returns_only_the_decision_update() -> None:
    nodes = _make_nodes()
    state = _make_state(findings=(_make_finding(),))

    result = nodes.make_decision(state)

    assert isinstance(result, dict)
    assert set(result.keys()) == {"decision"}
    assert isinstance(result["decision"], Decision)


def test_make_decision_does_not_mutate_the_incoming_state() -> None:
    nodes = _make_nodes()
    state = _make_state(
        findings=(_make_finding(),), fix_attempts=(_make_fix_attempt(),)
    )
    snapshot = dict(state)

    nodes.make_decision(state)

    assert state == snapshot


def test_propose_fixes_calls_provider_only_for_blocking_and_fixable_findings() -> None:
    blocking_fixable = _make_finding(
        severity=EvidenceSeverity.BLOCKING, is_fixable=True
    )
    blocking_not_fixable = _make_finding(
        severity=EvidenceSeverity.BLOCKING, is_fixable=False
    )
    non_blocking_fixable = _make_finding(
        severity=EvidenceSeverity.NON_BLOCKING, is_fixable=True
    )
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.propose_fix.return_value = "--- patch ---"
    nodes = _make_nodes(ai_provider=ai_provider)
    state = _make_state(
        findings=(blocking_fixable, blocking_not_fixable, non_blocking_fixable)
    )

    nodes.propose_fixes(state)

    ai_provider.propose_fix.assert_called_once_with(state["code"], blocking_fixable, 1)


def test_propose_fixes_uses_attempt_number_one() -> None:
    finding = _make_finding(severity=EvidenceSeverity.BLOCKING, is_fixable=True)
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.propose_fix.return_value = "--- patch ---"
    nodes = _make_nodes(ai_provider=ai_provider)
    state = _make_state(findings=(finding,))

    nodes.propose_fixes(state)

    _, _, attempt_number = ai_provider.propose_fix.call_args.args
    assert attempt_number == 1


def test_propose_fixes_does_not_call_provider_for_non_blocking_findings() -> None:
    non_blocking = _make_finding(
        severity=EvidenceSeverity.NON_BLOCKING, is_fixable=True
    )
    ai_provider = MagicMock(spec=AIProvider)
    nodes = _make_nodes(ai_provider=ai_provider)
    state = _make_state(findings=(non_blocking,))

    nodes.propose_fixes(state)

    ai_provider.propose_fix.assert_not_called()


def test_propose_fixes_does_not_call_provider_for_non_fixable_findings() -> None:
    non_fixable = _make_finding(severity=EvidenceSeverity.BLOCKING, is_fixable=False)
    ai_provider = MagicMock(spec=AIProvider)
    nodes = _make_nodes(ai_provider=ai_provider)
    state = _make_state(findings=(non_fixable,))

    nodes.propose_fixes(state)

    ai_provider.propose_fix.assert_not_called()


def test_propose_fixes_creates_a_fix_attempt_for_a_non_empty_patch() -> None:
    finding = _make_finding(severity=EvidenceSeverity.BLOCKING, is_fixable=True)
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.propose_fix.return_value = "--- a\n+++ b\n"
    nodes = _make_nodes(ai_provider=ai_provider)
    state = _make_state(findings=(finding,))

    result = nodes.propose_fixes(state)

    [attempt] = result["fix_attempts"]
    assert isinstance(attempt, FixAttempt)
    assert attempt.finding_id == finding.id
    assert attempt.patch == "--- a\n+++ b\n"
    assert attempt.attempt_number == 1


def test_propose_fixes_skips_empty_patches() -> None:
    finding = _make_finding(severity=EvidenceSeverity.BLOCKING, is_fixable=True)
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.propose_fix.return_value = ""
    nodes = _make_nodes(ai_provider=ai_provider)
    state = _make_state(findings=(finding,))

    result = nodes.propose_fixes(state)

    assert result["fix_attempts"] == ()


def test_propose_fixes_preserves_eligible_finding_order() -> None:
    first = _make_finding(severity=EvidenceSeverity.BLOCKING, is_fixable=True)
    second = _make_finding(severity=EvidenceSeverity.BLOCKING, is_fixable=True)
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.propose_fix.side_effect = ["patch-1", "patch-2"]
    nodes = _make_nodes(ai_provider=ai_provider)
    state = _make_state(findings=(first, second))

    result = nodes.propose_fixes(state)

    finding_ids = [attempt.finding_id for attempt in result["fix_attempts"]]
    assert finding_ids == [first.id, second.id]


def test_propose_fixes_appends_after_existing_fix_attempts() -> None:
    existing = _make_fix_attempt()
    finding = _make_finding(severity=EvidenceSeverity.BLOCKING, is_fixable=True)
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.propose_fix.return_value = "--- patch ---"
    nodes = _make_nodes(ai_provider=ai_provider)
    state = _make_state(findings=(finding,), fix_attempts=(existing,))

    result = nodes.propose_fixes(state)

    assert result["fix_attempts"][0] == existing
    assert len(result["fix_attempts"]) == 2


def test_propose_fixes_returns_only_the_fix_attempts_update() -> None:
    ai_provider = MagicMock(spec=AIProvider)
    nodes = _make_nodes(ai_provider=ai_provider)
    state = _make_state(findings=())

    result = nodes.propose_fixes(state)

    assert isinstance(result, dict)
    assert set(result.keys()) == {"fix_attempts"}
    assert isinstance(result["fix_attempts"], tuple)


def test_propose_fixes_leaves_validation_results_empty() -> None:
    finding = _make_finding(severity=EvidenceSeverity.BLOCKING, is_fixable=True)
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.propose_fix.return_value = "--- patch ---"
    nodes = _make_nodes(ai_provider=ai_provider)
    state = _make_state(findings=(finding,))

    result = nodes.propose_fixes(state)

    [attempt] = result["fix_attempts"]
    assert attempt.validation_results == ()


def test_propose_fixes_does_not_mutate_the_incoming_state() -> None:
    finding = _make_finding(severity=EvidenceSeverity.BLOCKING, is_fixable=True)
    ai_provider = MagicMock(spec=AIProvider)
    ai_provider.propose_fix.return_value = "--- patch ---"
    nodes = _make_nodes(ai_provider=ai_provider)
    state = _make_state(findings=(finding,))
    snapshot = dict(state)

    nodes.propose_fixes(state)

    assert state == snapshot


def test_orchestrator_modules_avoid_forbidden_imports() -> None:
    import ast

    import app.orchestrator.nodes as nodes_module
    import app.orchestrator.state as state_module

    forbidden_root_modules = {
        "sqlalchemy",
        "fastapi",
        "requests",
        "httpx",
        "socket",
        "app.persistence",
    }

    for module in (nodes_module, state_module):
        source = Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)

        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.add(node.module)

        for forbidden in forbidden_root_modules:
            assert forbidden not in imported_modules, (
                f"{module.__name__} unexpectedly imports '{forbidden}'"
            )
