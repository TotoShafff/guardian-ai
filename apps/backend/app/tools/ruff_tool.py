"""Deterministic Ruff analysis tool adapter.

Runs Ruff as a subprocess against a target path and normalizes its JSON
diagnostics into the domain `Evidence` shape (see `docs/ARCHITECTURE.md`
Section 8). This adapter only ever runs `ruff check` (never `--fix`), reads
Ruff's own JSON report from stdout, and never writes to or otherwise
modifies the analyzed files.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

from app.domain.models import Evidence, EvidenceSeverity, EvidenceSource

#: Sensible default timeout for a single Ruff invocation, matching the
#: application-wide default in `app.config.settings.Settings.tool_timeout_seconds`.
DEFAULT_TIMEOUT_SECONDS = 30
_BLOCKING_RULE_PREFIXES = ("F", "E9")


class RuffToolError(Exception):
    """Base class for all `RuffTool` errors."""


class RuffExecutionError(RuffToolError):
    """Raised when the Ruff subprocess exits with an unexpected status code."""


class RuffTimeoutError(RuffToolError):
    """Raised when the Ruff subprocess does not finish within the configured timeout."""


class RuffOutputParseError(RuffToolError):
    """Raised when Ruff's stdout is not the expected JSON diagnostics array."""


class RuffTool:
    """Runs `ruff check` against a target path and returns normalized `Evidence`."""

    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        self._timeout_seconds = timeout_seconds

    def analyze(self, target_path: Path, review_id: UUID) -> list[Evidence]:
        """Run Ruff against `target_path` and return its diagnostics as `Evidence`.

        Raises `ValueError` for an invalid `target_path`, `RuffTimeoutError` if
        Ruff does not finish in time, `RuffExecutionError` for any unexpected
        Ruff exit code, and `RuffOutputParseError` if Ruff's stdout is not the
        expected JSON diagnostics array.
        """
        if not target_path.exists():
            raise ValueError(f"target_path does not exist: {target_path}")
        if not (target_path.is_file() or target_path.is_dir()):
            raise ValueError(
                f"target_path must be a file or a directory: {target_path}"
            )

        command = [
            sys.executable,
            "-m",
            "ruff",
            "check",
            str(target_path),
            "--output-format",
            "json",
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuffTimeoutError(
                f"Ruff did not complete within {self._timeout_seconds} seconds"
            ) from exc

        # Ruff's `check` command uses exit code 1 to mean "diagnostics were
        # found", not "execution failed" — only other codes are real errors
        # (e.g. 2 for a usage/configuration error).
        if result.returncode not in (0, 1):
            fallback_message = (
                result.stderr.strip()
                or f"Ruff exited with unexpected code {result.returncode}"
            )
            raise RuffExecutionError(fallback_message)

        diagnostics = self._parse_diagnostics(result.stdout)
        return [self._to_evidence(diagnostic, review_id) for diagnostic in diagnostics]

    @staticmethod
    def _parse_diagnostics(stdout: str) -> list[dict[str, Any]]:
        """Parse Ruff's stdout into a list of diagnostic dictionaries."""
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuffOutputParseError(f"Ruff output is not valid JSON: {exc}") from exc
        if not isinstance(payload, list):
            raise RuffOutputParseError(
                "Ruff output must be a JSON array of diagnostics"
            )
        return payload

    @staticmethod
    def _to_evidence(diagnostic: dict[str, Any], review_id: UUID) -> Evidence:
        """Convert one Ruff JSON diagnostic into a domain `Evidence` item."""
        location = diagnostic.get("location") or {}
        end_location = diagnostic.get("end_location") or {}
        fix = diagnostic.get("fix")

        # Ruff's own `severity` field is the simplest, most explicit signal
        # available: "error" is a real problem (blocking); anything else
        # (e.g. a formatting/style "warning") is non-blocking.
        code = str(diagnostic.get("code") or "unknown")

        severity = (
            EvidenceSeverity.BLOCKING
            if code.startswith(_BLOCKING_RULE_PREFIXES)
            else EvidenceSeverity.NON_BLOCKING
        )

        return Evidence(
            review_id=review_id,
            source=EvidenceSource.RUFF,
            severity=severity,
            category=code,
            message=str(diagnostic.get("message") or ""),
            file_path=diagnostic.get("filename"),
            line_start=location.get("row"),
            line_end=end_location.get("row"),
            suggested_fix=fix.get("message") if isinstance(fix, dict) else None,
            confidence=None,
        )
