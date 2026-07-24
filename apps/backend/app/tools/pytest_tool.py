"""Deterministic Pytest analysis tool adapter.

Runs Pytest as a subprocess against a target path and normalizes failed
tests from its `--tb=short` text report into the domain `Evidence` shape
(see `docs/ARCHITECTURE.md` Section 8). This adapter never passes `--fix`-like
flags, never writes to the analyzed files, and only ever reads Pytest's own
stdout report.

Parsing is intentionally narrow: it only recognizes the standard `FAILURES`
section produced by `--tb=short`, and only extracts a `test_failure` Evidence
item per failing test. Setup/collection errors (Pytest's separate `ERRORS`
section) and warnings are out of scope and never produce Evidence here — see
`_find_failures_section()` below.
"""

import re
import subprocess
import sys
from pathlib import Path
from uuid import UUID

from app.domain.models import Evidence, EvidenceSeverity, EvidenceSource

#: Sensible default timeout for a single Pytest invocation, matching the
#: application-wide default in `app.config.settings.Settings.tool_timeout_seconds`.
DEFAULT_TIMEOUT_SECONDS = 30

# Pytest exit codes that are not "tests ran, some failed/none collected" —
# see https://docs.pytest.org/en/stable/reference/exit-codes.html.
_EXIT_OK = 0
_EXIT_TESTS_FAILED = 1
_EXIT_NO_TESTS_COLLECTED = 5

# Matches the body of the "===== FAILURES =====" section, up to the next
# "==== ... ====" section header (e.g. "short test summary info") or the end
# of the output.
_FAILURES_SECTION_RE = re.compile(
    r"^={3,} FAILURES ={3,}$\n(?P<body>.*?)(?=^={3,} .+ ={3,}$|\Z)",
    re.MULTILINE | re.DOTALL,
)
# Matches one per-test header inside the FAILURES section, e.g.
# "_________________________ test_add_fails _________________________".
_TEST_HEADER_RE = re.compile(r"^_{3,} (?P<name>.+?) _{3,}$", re.MULTILINE)
# Matches a short-traceback frame line, e.g.
# "C:\...\test_sample.py:10: in test_add_fails". The first match in a block
# is the outermost frame (the line inside the test function itself).
_LOCATION_RE = re.compile(r"^(?P<file>.+):(?P<line>\d+): in .+$", re.MULTILINE)
# Matches the first exception summary line, e.g. "E   assert 3 == 4".
_EXCEPTION_LINE_RE = re.compile(r"^E\s+(?P<message>.*)$", re.MULTILINE)


class PytestToolError(Exception):
    """Base class for all `PytestTool` errors."""


class PytestExecutionError(PytestToolError):
    """Raised when the Pytest subprocess exits with an unexpected status code."""


class PytestTimeoutError(PytestToolError):
    """Raised when the Pytest subprocess does not finish within the configured timeout."""


class PytestOutputParseError(PytestToolError):
    """Raised when Pytest reports failures but they cannot be reliably parsed."""


class PytestTool:
    """Runs Pytest against a target path and returns normalized `Evidence`."""

    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        self._timeout_seconds = timeout_seconds

    def analyze(self, target_path: Path, review_id: UUID) -> list[Evidence]:
        """Run Pytest against `target_path` and return failed tests as `Evidence`.

        Raises `ValueError` for an invalid `target_path`, `PytestTimeoutError`
        if Pytest does not finish in time, `PytestExecutionError` for any
        exit code outside `{0, 1, 5}`, and `PytestOutputParseError` if exit
        code 1 is reported but no failure could be reliably parsed from it.
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
            "pytest",
            str(target_path),
            "--tb=short",
            "--quiet",
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
            raise PytestTimeoutError(
                f"Pytest did not complete within {self._timeout_seconds} seconds"
            ) from exc

        if result.returncode == _EXIT_OK:
            return []
        if result.returncode == _EXIT_NO_TESTS_COLLECTED:
            return []
        if result.returncode == _EXIT_TESTS_FAILED:
            return self._parse_failures(result.stdout, review_id)

        fallback_message = (
            result.stderr.strip()
            or result.stdout.strip()
            or f"Pytest exited with unexpected code {result.returncode}"
        )
        raise PytestExecutionError(fallback_message)

    @classmethod
    def _parse_failures(cls, stdout: str, review_id: UUID) -> list[Evidence]:
        """Parse the `FAILURES` section of `stdout` into `test_failure` Evidence.

        Raises `PytestOutputParseError` when Pytest exits with failed tests or
        execution errors but the supported `FAILURES` structure cannot be parsed.
        """
        section_match = _FAILURES_SECTION_RE.search(stdout)
        if section_match is None:
            raise PytestOutputParseError(
                "Pytest exited with code 1 but no parseable FAILURES section was found"
            )

        blocks = cls._split_into_blocks(section_match.group("body"))
        if not blocks:
            raise PytestOutputParseError(
                "Pytest reported failures but no individual failure block could be parsed"
            )

        return [cls._to_evidence(name, block, review_id) for name, block in blocks]

    @staticmethod
    def _split_into_blocks(section_body: str) -> list[tuple[str, str]]:
        """Split a FAILURES section body into (test_name, block_text) pairs."""
        headers = list(_TEST_HEADER_RE.finditer(section_body))
        blocks: list[tuple[str, str]] = []
        for index, header in enumerate(headers):
            start = header.end()
            end = (
                headers[index + 1].start()
                if index + 1 < len(headers)
                else len(section_body)
            )
            blocks.append((header.group("name").strip(), section_body[start:end]))
        return blocks

    @staticmethod
    def _to_evidence(test_name: str, block: str, review_id: UUID) -> Evidence:
        """Convert one parsed failure block into a `test_failure` Evidence item."""
        location_match = _LOCATION_RE.search(block)
        exception_match = _EXCEPTION_LINE_RE.search(block)

        file_path = location_match.group("file").strip() if location_match else None
        line_start = int(location_match.group("line")) if location_match else None

        exception_message = (
            exception_match.group("message").strip() if exception_match else ""
        )
        message = exception_message or f"{test_name} failed"

        return Evidence(
            review_id=review_id,
            source=EvidenceSource.PYTEST,
            severity=EvidenceSeverity.BLOCKING,
            category="test_failure",
            message=message,
            file_path=file_path,
            line_start=line_start,
            line_end=line_start,
            suggested_fix=None,
            confidence=None,
        )
