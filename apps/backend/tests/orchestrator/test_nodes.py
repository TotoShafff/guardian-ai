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
    Evidence,
    EvidenceSeverity,
    EvidenceSource,
    Finding,
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


def test_collect_deterministic_evidence_orders_ruff_evidence_before_pytest_evidence() -> (
    None
):
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


def test_orchestrator_modules_never_import_persistence_database_or_web_frameworks() -> (
    None
):
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
