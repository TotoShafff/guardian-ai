"""Unit tests for `RuffTool`.

`subprocess.run` is always mocked: no test invokes the real Ruff
executable, requires PostgreSQL/Docker/network access, or touches the
persistence layer.
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.domain.models import Evidence, EvidenceSeverity, EvidenceSource
from app.tools.ruff_tool import (
    RuffExecutionError,
    RuffOutputParseError,
    RuffTimeoutError,
    RuffTool,
)

_ONE_DIAGNOSTIC = {
    "cell": None,
    "code": "F401",
    "end_location": {"column": 10, "row": 1},
    "filename": "/repo/example.py",
    "fix": {
        "applicability": "safe",
        "edits": [],
        "message": "Remove unused import: `os`",
    },
    "location": {"column": 8, "row": 1},
    "message": "`os` imported but unused",
    "name": "unused-import",
    "noqa_row": 1,
    "url": "https://docs.astral.sh/ruff/rules/unused-import",
}


def _mock_completed_process(
    returncode: int, stdout: str = "", stderr: str = ""
) -> MagicMock:
    process = MagicMock(spec=subprocess.CompletedProcess)
    process.returncode = returncode
    process.stdout = stdout
    process.stderr = stderr
    return process


def test_analyze_returns_empty_list_when_no_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "clean.py"
    target.write_text("x = 1\n")
    mock_run = MagicMock(return_value=_mock_completed_process(0, stdout="[]"))
    monkeypatch.setattr("app.tools.ruff_tool.subprocess.run", mock_run)

    result = RuffTool().analyze(target, uuid4())

    assert result == []
    mock_run.assert_called_once()


def test_analyze_returncode_1_with_one_diagnostic_is_not_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "bad.py"
    target.write_text("import os\n")
    stdout = json.dumps([_ONE_DIAGNOSTIC])
    mock_run = MagicMock(return_value=_mock_completed_process(1, stdout=stdout))
    monkeypatch.setattr("app.tools.ruff_tool.subprocess.run", mock_run)

    result = RuffTool().analyze(target, uuid4())

    assert len(result) == 1
    assert isinstance(result[0], Evidence)


def test_analyze_maps_ruff_json_fields_into_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "bad.py"
    target.write_text("import os\n")
    review_id = uuid4()
    stdout = json.dumps([_ONE_DIAGNOSTIC])
    mock_run = MagicMock(return_value=_mock_completed_process(1, stdout=stdout))
    monkeypatch.setattr("app.tools.ruff_tool.subprocess.run", mock_run)

    [evidence] = RuffTool().analyze(target, review_id)

    assert evidence.review_id == review_id
    assert evidence.source == EvidenceSource.RUFF
    assert evidence.severity == EvidenceSeverity.BLOCKING
    assert evidence.category == "F401"
    assert evidence.message == "`os` imported but unused"
    assert evidence.file_path == "/repo/example.py"
    assert evidence.line_start == 1
    assert evidence.line_end == 1
    assert evidence.suggested_fix == "Remove unused import: `os`"
    assert evidence.confidence is None


def test_analyze_maps_style_rule_to_non_blocking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "bad.py"
    target.write_text("x = 1\n")

    diagnostic = {
        **_ONE_DIAGNOSTIC,
        "code": "I001",
        "fix": None,
    }
    stdout = json.dumps([diagnostic])
    mock_run = MagicMock(return_value=_mock_completed_process(1, stdout=stdout))
    monkeypatch.setattr("app.tools.ruff_tool.subprocess.run", mock_run)

    [evidence] = RuffTool().analyze(target, uuid4())

    assert evidence.category == "I001"
    assert evidence.severity == EvidenceSeverity.NON_BLOCKING
    assert evidence.suggested_fix is None


def test_analyze_raises_value_error_for_missing_target_path() -> None:
    with pytest.raises(ValueError, match="does not exist"):
        RuffTool().analyze(Path("/nonexistent/path/example.py"), uuid4())


@pytest.mark.parametrize("timeout_seconds", [0, -1])
def test_constructor_raises_value_error_for_invalid_timeout(
    timeout_seconds: int,
) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        RuffTool(timeout_seconds=timeout_seconds)


def test_analyze_raises_ruff_timeout_error_on_subprocess_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "example.py"
    target.write_text("x = 1\n")
    mock_run = MagicMock(side_effect=subprocess.TimeoutExpired(cmd="ruff", timeout=5))
    monkeypatch.setattr("app.tools.ruff_tool.subprocess.run", mock_run)

    with pytest.raises(RuffTimeoutError):
        RuffTool(timeout_seconds=5).analyze(target, uuid4())


def test_analyze_raises_ruff_execution_error_for_unexpected_return_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "example.py"
    target.write_text("x = 1\n")
    mock_run = MagicMock(
        return_value=_mock_completed_process(
            2, stdout="", stderr="ruff: invalid configuration"
        )
    )
    monkeypatch.setattr("app.tools.ruff_tool.subprocess.run", mock_run)

    with pytest.raises(RuffExecutionError, match="invalid configuration"):
        RuffTool().analyze(target, uuid4())


def test_analyze_execution_error_falls_back_when_stderr_is_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "example.py"
    target.write_text("x = 1\n")
    mock_run = MagicMock(return_value=_mock_completed_process(2, stdout="", stderr=""))
    monkeypatch.setattr("app.tools.ruff_tool.subprocess.run", mock_run)

    with pytest.raises(RuffExecutionError, match="unexpected code 2"):
        RuffTool().analyze(target, uuid4())


def test_analyze_raises_ruff_output_parse_error_for_malformed_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "example.py"
    target.write_text("x = 1\n")
    mock_run = MagicMock(
        return_value=_mock_completed_process(0, stdout="not valid json")
    )
    monkeypatch.setattr("app.tools.ruff_tool.subprocess.run", mock_run)

    with pytest.raises(RuffOutputParseError):
        RuffTool().analyze(target, uuid4())


def test_no_subprocess_call_uses_shell_true(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "example.py"
    target.write_text("x = 1\n")
    mock_run = MagicMock(return_value=_mock_completed_process(0, stdout="[]"))
    monkeypatch.setattr("app.tools.ruff_tool.subprocess.run", mock_run)

    RuffTool().analyze(target, uuid4())

    _, kwargs = mock_run.call_args
    assert kwargs.get("shell") is not True


def test_command_uses_sys_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "example.py"
    target.write_text("x = 1\n")
    mock_run = MagicMock(return_value=_mock_completed_process(0, stdout="[]"))
    monkeypatch.setattr("app.tools.ruff_tool.subprocess.run", mock_run)

    RuffTool().analyze(target, uuid4())

    (command,), _ = mock_run.call_args
    assert command[0] == sys.executable
    assert command[1:3] == ["-m", "ruff"]
    assert command[3] == "check"
    assert str(target) in command
    assert "--output-format" in command
    assert "json" in command
    assert "--fix" not in command


def test_analyze_passes_the_configured_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "example.py"
    target.write_text("x = 1\n")
    mock_run = MagicMock(return_value=_mock_completed_process(0, stdout="[]"))
    monkeypatch.setattr("app.tools.ruff_tool.subprocess.run", mock_run)

    RuffTool(timeout_seconds=7).analyze(target, uuid4())

    _, kwargs = mock_run.call_args
    assert kwargs.get("timeout") == 7


def test_ruff_tool_module_never_imports_persistence_or_database() -> None:
    import app.tools.ruff_tool as ruff_tool_module

    source = Path(ruff_tool_module.__file__).read_text(encoding="utf-8")

    assert "persistence" not in source
    assert "Session" not in source
    assert "sqlalchemy" not in source.lower()
