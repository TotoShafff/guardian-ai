"""Unit tests for `FixValidator` / `MockFixValidator`.

`MockFixValidator` is a pure, deterministic implementation: no test here
requires PostgreSQL, SQLite, Docker, network access, an API key, a real
file, or a subprocess.
"""

from pathlib import Path

from app.domain.models import ValidationResult, ValidationStatus
from app.orchestrator.validation import FixValidator, MockFixValidator

_SAMPLE_CODE = "def add(a, b):\n    return a + b\n"
_SAMPLE_PATCH = (
    "--- a/add.py\n+++ b/add.py\n@@ -1,2 +1,2 @@\n-def add(a, b):\n+def add(a, b):\n"
)


def test_mock_fix_validator_satisfies_the_fix_validator_abstraction() -> None:
    validator = MockFixValidator()

    assert isinstance(validator, FixValidator)


def test_validate_returns_failed_for_an_empty_patch() -> None:
    validator = MockFixValidator()

    [result] = validator.validate(_SAMPLE_CODE, "")

    assert isinstance(result, ValidationResult)
    assert result.status == ValidationStatus.FAILED


def test_validate_returns_failed_for_a_whitespace_only_patch() -> None:
    validator = MockFixValidator()

    [result] = validator.validate(_SAMPLE_CODE, "   \n\t  ")

    assert result.status == ValidationStatus.FAILED


def test_validate_returns_passed_for_a_non_empty_patch() -> None:
    validator = MockFixValidator()

    [result] = validator.validate(_SAMPLE_CODE, _SAMPLE_PATCH)

    assert result.status == ValidationStatus.PASSED


def test_validate_uses_the_mock_validator_tool_name_for_both_outcomes() -> None:
    validator = MockFixValidator()

    [failed_result] = validator.validate(_SAMPLE_CODE, "")
    [passed_result] = validator.validate(_SAMPLE_CODE, _SAMPLE_PATCH)

    assert failed_result.tool == "mock_validator"
    assert passed_result.tool == "mock_validator"


def test_validate_uses_the_expected_message_for_an_empty_patch() -> None:
    validator = MockFixValidator()

    [result] = validator.validate(_SAMPLE_CODE, "")

    assert result.message == "El parche está vacío"


def test_validate_uses_the_expected_message_for_a_non_empty_patch() -> None:
    validator = MockFixValidator()

    [result] = validator.validate(_SAMPLE_CODE, _SAMPLE_PATCH)

    assert result.message == (
        "El parche fue aceptado por la validación determinística simulada."
    )


def test_validate_returns_exactly_one_result() -> None:
    validator = MockFixValidator()

    results = validator.validate(_SAMPLE_CODE, _SAMPLE_PATCH)

    assert len(results) == 1


def test_validate_is_deterministic_across_repeated_calls() -> None:
    validator = MockFixValidator()

    first_call = validator.validate(_SAMPLE_CODE, _SAMPLE_PATCH)
    second_call = validator.validate(_SAMPLE_CODE, _SAMPLE_PATCH)

    assert first_call == second_call


def test_validate_does_not_modify_code_or_patch_arguments() -> None:
    validator = MockFixValidator()
    code = _SAMPLE_CODE
    patch = _SAMPLE_PATCH

    validator.validate(code, patch)

    assert code == _SAMPLE_CODE
    assert patch == _SAMPLE_PATCH


def test_validation_module_avoids_io_and_infrastructure_imports() -> None:
    import ast

    import app.orchestrator.validation as validation_module

    forbidden_root_modules = {
        "subprocess",
        "socket",
        "requests",
        "httpx",
        "sqlalchemy",
        "fastapi",
        "os",
        "pathlib",
    }

    source = Path(validation_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)

    for forbidden in forbidden_root_modules:
        assert forbidden not in imported_modules, (
            f"validation module unexpectedly imports '{forbidden}'"
        )
