"""Unit tests for `MockProvider`.

`MockProvider` is a pure, deterministic implementation of `AIProvider`: no
test here requires PostgreSQL, SQLite, Docker, network access, or an API
key, and none of them mock `subprocess`/HTTP because `MockProvider` never
performs I/O.
"""

from pathlib import Path
from uuid import uuid4

import pytest

from app.domain.models import Evidence, EvidenceSeverity, EvidenceSource, Finding
from app.providers.base import AIProvider
from app.providers.mock import MockProvider


def _make_evidence(**overrides: object) -> Evidence:
    defaults: dict[str, object] = {
        "review_id": uuid4(),
        "source": EvidenceSource.RUFF,
        "severity": EvidenceSeverity.BLOCKING,
        "category": "F401",
        "message": "`os` imported but unused",
        "file_path": "app/example.py",
        "line_start": 1,
    }
    defaults.update(overrides)
    return Evidence(**defaults)  # type: ignore[arg-type]


def test_mock_provider_satisfies_the_ai_provider_abstraction() -> None:
    provider = MockProvider()

    assert isinstance(provider, AIProvider)


def test_analyze_code_returns_one_finding_per_evidence_item() -> None:
    evidence = (_make_evidence(), _make_evidence(category="F841"))

    findings = MockProvider().analyze_code("print('hi')", evidence)

    assert len(findings) == len(evidence)
    assert all(isinstance(finding, Finding) for finding in findings)


def test_analyze_code_preserves_review_id() -> None:
    review_id = uuid4()
    evidence = (_make_evidence(review_id=review_id),)

    [finding] = MockProvider().analyze_code("code", evidence)

    assert finding.review_id == review_id


def test_analyze_code_copies_evidence_id_into_evidence_ids() -> None:
    item = _make_evidence()

    [finding] = MockProvider().analyze_code("code", (item,))

    assert finding.evidence_ids == (item.id,)


def test_analyze_code_preserves_severity() -> None:
    item = _make_evidence(severity=EvidenceSeverity.NON_BLOCKING)

    [finding] = MockProvider().analyze_code("code", (item,))

    assert finding.severity == EvidenceSeverity.NON_BLOCKING


def test_analyze_code_marks_fixable_evidence_as_fixable() -> None:
    item = _make_evidence(suggested_fix="Remove unused import")

    [finding] = MockProvider().analyze_code("code", (item,))

    assert finding.is_fixable is True


def test_analyze_code_marks_non_fixable_evidence_as_non_fixable() -> None:
    item = _make_evidence(suggested_fix=None)

    [finding] = MockProvider().analyze_code("code", (item,))

    assert finding.is_fixable is False


def test_analyze_code_uses_category_and_message_in_title_and_description() -> None:
    item = _make_evidence(category="F401", message="`os` imported but unused")

    [finding] = MockProvider().analyze_code("code", (item,))

    assert "F401" in finding.title
    assert "imported but unused" in finding.title
    assert "F401" in finding.description
    assert "imported but unused" in finding.description


def test_analyze_code_preserves_input_order() -> None:
    evidence = tuple(_make_evidence(category=f"CODE{i}") for i in range(5))

    findings = MockProvider().analyze_code("code", evidence)

    assert [f.evidence_ids[0] for f in findings] == [e.id for e in evidence]
    assert [f.title for f in findings] == [
        MockProvider._build_title(e) for e in evidence
    ]


def test_analyze_code_returns_empty_tuple_for_empty_evidence() -> None:
    findings = MockProvider().analyze_code("code", ())

    assert findings == ()


@pytest.mark.parametrize("attempt_number", [0, -1])
def test_propose_fix_rejects_attempt_number_below_one(attempt_number: int) -> None:
    finding = Finding(
        review_id=uuid4(),
        severity=EvidenceSeverity.BLOCKING,
        title="Unused import",
        description="`os` is imported but never used",
        is_fixable=True,
    )

    with pytest.raises(ValueError, match="attempt_number"):
        MockProvider().propose_fix("code", finding, attempt_number)


def test_propose_fix_returns_empty_string_for_non_fixable_finding() -> None:
    finding = Finding(
        review_id=uuid4(),
        severity=EvidenceSeverity.BLOCKING,
        title="Design smell",
        description="Only a human/LLM judgment call, no mechanical fix exists",
        is_fixable=False,
    )

    result = MockProvider().propose_fix("code", finding, attempt_number=1)

    assert result == ""


def test_propose_fix_returns_deterministic_diff_like_text_for_fixable_finding() -> None:
    finding = Finding(
        review_id=uuid4(),
        severity=EvidenceSeverity.BLOCKING,
        title="Unused import",
        description="`os` is imported but never used",
        is_fixable=True,
    )

    result = MockProvider().propose_fix("code", finding, attempt_number=2)

    assert finding.title in result
    assert "2" in result
    assert "TODO" in result
    assert result.startswith("--- a/")
    assert "+++ b/" in result
    assert "\n-" in result
    assert "\n+" in result


def _semantic_finding_fields(finding: Finding) -> tuple[object, ...]:
    """Fields expected to be identical across calls (excludes id/created_at)."""
    return (
        finding.review_id,
        finding.evidence_ids,
        finding.severity,
        finding.title,
        finding.description,
        finding.is_fixable,
    )


def test_repeated_calls_with_the_same_input_return_the_same_output() -> None:
    provider = MockProvider()
    evidence = (_make_evidence(),)

    findings_1 = provider.analyze_code("code", evidence)
    findings_2 = provider.analyze_code("code", evidence)

    assert [_semantic_finding_fields(f) for f in findings_1] == [
        _semantic_finding_fields(f) for f in findings_2
    ]

    finding = findings_1[0]
    fix_1 = provider.propose_fix("code", finding, attempt_number=1)
    fix_2 = MockProvider().propose_fix("code", finding, attempt_number=1)

    assert fix_1 == fix_2


def test_provider_modules_never_import_network_database_tools_or_vendor_sdks() -> None:
    import ast

    import app.providers.base as base_module
    import app.providers.mock as mock_module

    forbidden_root_modules = {
        "sqlalchemy",
        "subprocess",
        "requests",
        "httpx",
        "socket",
        "openai",
        "anthropic",
        "fastapi",
        "langgraph",
        "app.persistence",
        "app.tools",
    }

    for module in (base_module, mock_module):
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
