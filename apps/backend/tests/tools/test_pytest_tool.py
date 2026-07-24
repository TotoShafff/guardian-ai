"""Unit tests for `PytestTool`.

`subprocess.run` is always mocked: no test invokes a real Pytest process,
requires PostgreSQL/SQLite/Docker/network access, or touches the
persistence layer. Fixture strings below mirror real `pytest --tb=short
--quiet` output (verified manually against a real Pytest run) closely
enough to exercise the parser realistically.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.domain.models import Evidence, EvidenceSeverity, EvidenceSource
from app.tools.pytest_tool import (
    PytestExecutionError,
    PytestOutputParseError,
    PytestTimeoutError,
    PytestTool,
)

_ONE_FAILURE_STDOUT = """.F                                                                       [100%]
================================== FAILURES ===================================
_______________________________ test_add_fails ________________________________
example/test_sample.py:10: in test_add_fails
    assert add(1, 2) == 4
E   assert 3 == 4
E    +  where 3 = add(1, 2)
=========================== short test summary info ===========================
FAILED example/test_sample.py::test_add_fails
1 failed, 1 passed in 0.18s
"""

_TWO_FAILURES_STDOUT = """FF                                                                        [100%]
================================== FAILURES ===================================
_______________________________ test_add_fails ________________________________
example/test_sample.py:10: in test_add_fails
    assert add(1, 2) == 4
E   assert 3 == 4
_________________________________ test_raises _________________________________
example/test_sample.py:14: in test_raises
    raise ValueError('boom')
E   ValueError: boom
=========================== short test summary info ===========================
FAILED example/test_sample.py::test_add_fails
FAILED example/test_sample.py::test_raises
2 failed in 0.18s
"""

_FAILURE_WITHOUT_LOCATION_STDOUT = """F                                                                         [100%]
================================== FAILURES ===================================
_______________________________ test_weird_failure _______________________________
Some custom output without a recognizable traceback location or exception line.
=========================== short test summary info ===========================
FAILED example/test_weird.py::test_weird_failure
1 failed in 0.05s
"""

_NO_FAILURES_SECTION_STDOUT = """E                                                                         [100%]
=================================== ERRORS ====================================
_________________ ERROR at setup of test_uses_broken_fixture __________________
example/test_error.py:6: in broken_fixture
    raise RuntimeError('fixture setup failed')
E   RuntimeError: fixture setup failed
=========================== short test summary info ===========================
ERROR example/test_error.py::test_uses_broken_fixture
1 error in 0.13s
"""

_MALFORMED_FAILURES_STDOUT = """================================== FAILURES ===================================
This section claims failures happened but has no recognizable test header.
"""


def _mock_completed_process(
    returncode: int, stdout: str = "", stderr: str = ""
) -> MagicMock:
    process = MagicMock(spec=subprocess.CompletedProcess)
    process.returncode = returncode
    process.stdout = stdout
    process.stderr = stderr
    return process


def test_analyze_returns_empty_list_on_exit_code_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "test_sample.py"
    target.write_text("def test_ok():\n    assert True\n")
    mock_run = MagicMock(return_value=_mock_completed_process(0, stdout="1 passed"))
    monkeypatch.setattr("app.tools.pytest_tool.subprocess.run", mock_run)

    result = PytestTool().analyze(target, uuid4())

    assert result == []
    mock_run.assert_called_once()


def test_analyze_returns_empty_list_on_exit_code_5_no_tests_collected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "empty_dir"
    target.mkdir()
    mock_run = MagicMock(
        return_value=_mock_completed_process(5, stdout="no tests ran in 0.00s")
    )
    monkeypatch.setattr("app.tools.pytest_tool.subprocess.run", mock_run)

    result = PytestTool().analyze(target, uuid4())

    assert result == []


def test_analyze_exit_code_1_maps_one_failed_test_into_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "test_sample.py"
    target.write_text("def test_add_fails():\n    assert False\n")
    review_id = uuid4()
    mock_run = MagicMock(
        return_value=_mock_completed_process(1, stdout=_ONE_FAILURE_STDOUT)
    )
    monkeypatch.setattr("app.tools.pytest_tool.subprocess.run", mock_run)

    [evidence] = PytestTool().analyze(target, review_id)

    assert isinstance(evidence, Evidence)
    assert evidence.review_id == review_id
    assert evidence.source == EvidenceSource.PYTEST
    assert evidence.severity == EvidenceSeverity.BLOCKING
    assert evidence.category == "test_failure"
    assert evidence.message == "assert 3 == 4"
    assert evidence.file_path == "example/test_sample.py"
    assert evidence.line_start == 10
    assert evidence.line_end == 10
    assert evidence.suggested_fix is None
    assert evidence.confidence is None


def test_analyze_multiple_failures_produce_multiple_evidence_items(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "test_sample.py"
    target.write_text("def test_a():\n    assert False\n")
    mock_run = MagicMock(
        return_value=_mock_completed_process(1, stdout=_TWO_FAILURES_STDOUT)
    )
    monkeypatch.setattr("app.tools.pytest_tool.subprocess.run", mock_run)

    result = PytestTool().analyze(target, uuid4())

    assert len(result) == 2
    assert all(item.category == "test_failure" for item in result)
    assert {item.message for item in result} == {"assert 3 == 4", "ValueError: boom"}
    assert all(item.line_start in (10, 14) for item in result)


def test_analyze_failure_without_reliable_location_leaves_file_and_line_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "test_weird.py"
    target.write_text("def test_weird_failure():\n    assert False\n")
    mock_run = MagicMock(
        return_value=_mock_completed_process(1, stdout=_FAILURE_WITHOUT_LOCATION_STDOUT)
    )
    monkeypatch.setattr("app.tools.pytest_tool.subprocess.run", mock_run)

    [evidence] = PytestTool().analyze(target, uuid4())

    assert evidence.file_path is None
    assert evidence.line_start is None
    assert evidence.line_end is None
    # No exception line was found either, so a safe fallback message is used.
    assert evidence.message == "test_weird_failure failed"


def test_analyze_exit_code_1_without_failures_section_raises_parse_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "test_error.py"
    target.write_text("def test_uses_broken_fixture():\n    assert True\n")
    mock_run = MagicMock(
        return_value=_mock_completed_process(
            1,
            stdout=_NO_FAILURES_SECTION_STDOUT,
        )
    )
    monkeypatch.setattr("app.tools.pytest_tool.subprocess.run", mock_run)

    with pytest.raises(PytestOutputParseError, match="no parseable FAILURES"):
        PytestTool().analyze(target, uuid4())


def test_analyze_raises_parse_error_when_failures_section_has_no_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "test_sample.py"
    target.write_text("def test_a():\n    assert False\n")
    mock_run = MagicMock(
        return_value=_mock_completed_process(1, stdout=_MALFORMED_FAILURES_STDOUT)
    )
    monkeypatch.setattr("app.tools.pytest_tool.subprocess.run", mock_run)

    with pytest.raises(PytestOutputParseError):
        PytestTool().analyze(target, uuid4())


def test_analyze_raises_value_error_for_missing_target_path() -> None:
    with pytest.raises(ValueError, match="does not exist"):
        PytestTool().analyze(Path("/nonexistent/path/test_example.py"), uuid4())


@pytest.mark.parametrize("timeout_seconds", [0, -1])
def test_constructor_raises_value_error_for_invalid_timeout(
    timeout_seconds: int,
) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        PytestTool(timeout_seconds=timeout_seconds)


def test_analyze_raises_pytest_timeout_error_on_subprocess_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "test_sample.py"
    target.write_text("def test_a():\n    assert True\n")
    mock_run = MagicMock(side_effect=subprocess.TimeoutExpired(cmd="pytest", timeout=5))
    monkeypatch.setattr("app.tools.pytest_tool.subprocess.run", mock_run)

    with pytest.raises(PytestTimeoutError):
        PytestTool(timeout_seconds=5).analyze(target, uuid4())


def test_analyze_raises_pytest_execution_error_for_unexpected_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "test_sample.py"
    target.write_text("def test_a():\n    assert True\n")
    mock_run = MagicMock(
        return_value=_mock_completed_process(
            2, stdout="", stderr="usage error: unrecognized arguments"
        )
    )
    monkeypatch.setattr("app.tools.pytest_tool.subprocess.run", mock_run)

    with pytest.raises(PytestExecutionError, match="usage error"):
        PytestTool().analyze(target, uuid4())


def test_analyze_execution_error_falls_back_to_stdout_then_generic_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "test_sample.py"
    target.write_text("def test_a():\n    assert True\n")
    mock_run = MagicMock(return_value=_mock_completed_process(2, stdout="", stderr=""))
    monkeypatch.setattr("app.tools.pytest_tool.subprocess.run", mock_run)

    with pytest.raises(PytestExecutionError, match="unexpected code 2"):
        PytestTool().analyze(target, uuid4())


def test_command_uses_sys_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "test_sample.py"
    target.write_text("def test_a():\n    assert True\n")
    mock_run = MagicMock(return_value=_mock_completed_process(0, stdout="1 passed"))
    monkeypatch.setattr("app.tools.pytest_tool.subprocess.run", mock_run)

    PytestTool().analyze(target, uuid4())

    (command,), _ = mock_run.call_args
    assert command[0] == sys.executable
    assert command[1:3] == ["-m", "pytest"]
    assert str(target) in command
    assert "--tb=short" in command
    assert "--quiet" in command


def test_shell_is_explicitly_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "test_sample.py"
    target.write_text("def test_a():\n    assert True\n")
    mock_run = MagicMock(return_value=_mock_completed_process(0, stdout="1 passed"))
    monkeypatch.setattr("app.tools.pytest_tool.subprocess.run", mock_run)

    PytestTool().analyze(target, uuid4())

    _, kwargs = mock_run.call_args
    assert kwargs.get("shell") is False


def test_check_is_explicitly_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "test_sample.py"
    target.write_text("def test_a():\n    assert True\n")
    mock_run = MagicMock(return_value=_mock_completed_process(0, stdout="1 passed"))
    monkeypatch.setattr("app.tools.pytest_tool.subprocess.run", mock_run)

    PytestTool().analyze(target, uuid4())

    _, kwargs = mock_run.call_args
    assert kwargs.get("check") is False


def test_analyze_passes_the_configured_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "test_sample.py"
    target.write_text("def test_a():\n    assert True\n")
    mock_run = MagicMock(return_value=_mock_completed_process(0, stdout="1 passed"))
    monkeypatch.setattr("app.tools.pytest_tool.subprocess.run", mock_run)

    PytestTool(timeout_seconds=7).analyze(target, uuid4())

    _, kwargs = mock_run.call_args
    assert kwargs.get("timeout") == 7


def test_pytest_tool_module_never_imports_persistence_or_database() -> None:
    import app.tools.pytest_tool as pytest_tool_module

    source = Path(pytest_tool_module.__file__).read_text(encoding="utf-8")

    assert "persistence" not in source
    assert "Session" not in source
    assert "sqlalchemy" not in source.lower()
