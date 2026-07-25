"""Fix-validation abstraction for the Guardian AI review workflow.

`FixValidator` is the interface the `validate_fixes` workflow node depends
on to re-check a proposed patch (see `docs/ARCHITECTURE.md` Section 7 and
`docs/DECISIONS.md` ADR-014 for the bounded fix-and-validate loop this
interface will eventually support). A validator that actually applies a
patch and re-runs Ruff/Pytest against it is a later stage; `MockFixValidator`
here is a deterministic, dependency-free implementation used for tests and
for local runs without the real validation pipeline wired up yet.

This module has no framework or infrastructure imports: no FastAPI,
SQLAlchemy, LangGraph, repositories, subprocess, filesystem, or network
access.
"""

from abc import ABC, abstractmethod

from app.domain.models import ValidationResult, ValidationStatus

#: Tool name recorded on every `ValidationResult` produced by `MockFixValidator`.
_MOCK_VALIDATOR_TOOL_NAME = "mock_validator"


class FixValidator(ABC):
    """Common interface every fix-validation adapter must implement."""

    @abstractmethod
    def validate(
        self,
        code: str,
        patch: str,
    ) -> tuple[ValidationResult, ...]:
        """Validate `patch` proposed against `code`, returning one or more results."""
        raise NotImplementedError


class MockFixValidator(FixValidator):
    """Deterministic `FixValidator` requiring no subprocess, filesystem, or network I/O.

    `validate()` never applies `patch` to `code` or to any file; it only
    inspects `patch`'s text to decide pass/fail, so the same input always
    produces the same semantic output.
    """

    def validate(
        self,
        code: str,
        patch: str,
    ) -> tuple[ValidationResult, ...]:
        """Return a single deterministic `ValidationResult` based on `patch` alone.

        `code` is accepted for interface compatibility but is not inspected.
        An empty or whitespace-only `patch` is treated as failed; any other
        `patch` is treated as accepted.
        """
        if patch.strip() == "":
            return (
                ValidationResult(
                    status=ValidationStatus.FAILED,
                    tool=_MOCK_VALIDATOR_TOOL_NAME,
                message="El parche está vacío",
            ),
        )

        return (
            ValidationResult(
                status=ValidationStatus.PASSED,
                tool=_MOCK_VALIDATOR_TOOL_NAME,
                message=(
                    "El parche fue aceptado por la validación "
                    "determinística simulada."
                ),
            ),
        )
