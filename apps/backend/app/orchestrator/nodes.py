"""Nodes of the Guardian AI review LangGraph workflow.

`ReviewWorkflowNodes` groups the workflow's node methods behind explicit,
constructor-injected dependencies (a `RuffTool`, a `PytestTool`, an
`AIProvider`, and a `FixValidator`), so the graph wiring (see
`app/orchestrator/graph.py`) can compose them without any node reaching
into global state, a database session, or a concrete tool/provider/
validator implementation.

Five nodes are implemented so far: `collect_deterministic_evidence`
(Ruff + Pytest), `analyze_semantically` (the AI provider), `propose_fixes`
(one bounded `AIProvider.propose_fix()` call per eligible finding),
`validate_fixes` (fills in `validation_results` for attempts not yet
validated), and `make_decision` (consolidates findings into a `Decision`).
Routing/conditional edges, retries, and a bounded fix-and-validate loop are
added in a later stage. No node mutates the `state` it receives — each
returns only the partial state update it is responsible for, matching the
convention LangGraph uses to merge node outputs into the graph's state.
"""

from dataclasses import replace

from app.domain.models import (
    Decision,
    EvidenceSeverity,
    Finding,
    FixAttempt,
    ReviewStatus,
)
from app.orchestrator.state import ReviewWorkflowState
from app.orchestrator.validation import FixValidator
from app.providers.base import AIProvider
from app.tools.pytest_tool import PytestTool
from app.tools.ruff_tool import RuffTool

#: `propose_fixes` always uses this attempt number: bounded retries with an
#: incrementing counter are added in a later stage (see `docs/DECISIONS.md` ADR-014).
_INITIAL_ATTEMPT_NUMBER = 1


class ReviewWorkflowNodes:
    """Constructor-injected collection of the review workflow's node methods."""

    def __init__(
        self,
        ruff_tool: RuffTool,
        pytest_tool: PytestTool,
        ai_provider: AIProvider,
        fix_validator: FixValidator,
    ) -> None:
        self._ruff_tool = ruff_tool
        self._pytest_tool = pytest_tool
        self._ai_provider = ai_provider
        self._fix_validator = fix_validator

    def collect_deterministic_evidence(
        self,
        state: ReviewWorkflowState,
    ) -> dict[str, object]:
        """Run Ruff and Pytest against `state["target_path"]` and merge their evidence.

        Evidence is combined in a fixed order (Ruff first, then Pytest) so
        downstream nodes see a stable, reproducible ordering. Tool
        exceptions are not caught here — they propagate to the caller, which
        decides how a failed evidence-collection step affects the review
        (see `docs/ARCHITECTURE.md` Section 10 on degrading rather than
        crashing; that handling is added in a later stage). This method does
        not access the database and does not mutate `state`.
        """
        target_path = state["target_path"]
        review_id = state["review"].id

        ruff_evidence = self._ruff_tool.analyze(target_path, review_id)
        pytest_evidence = self._pytest_tool.analyze(target_path, review_id)

        return {"evidence": tuple(ruff_evidence) + tuple(pytest_evidence)}

    def analyze_semantically(
        self,
        state: ReviewWorkflowState,
    ) -> dict[str, object]:
        """Ask the AI provider for semantic findings given the code and evidence so far.

        This node only gathers findings from `AIProvider.analyze_code()`; it
        does not propose fixes — that is a later step in the workflow (see
        `docs/ROADMAP.md` Stage 6). This method does not access the database
        and does not mutate `state`.
        """
        code = state["code"]
        evidence = state["evidence"]

        findings = self._ai_provider.analyze_code(code, evidence)

        return {"findings": findings}

    def propose_fixes(
        self,
        state: ReviewWorkflowState,
    ) -> dict[str, object]:
        """Propose a fix for each blocking, fixable finding not yet attempted.

        Calls `AIProvider.propose_fix()` once per eligible finding (severity
        `BLOCKING` and `is_fixable=True`), in finding order, always with
        `attempt_number=1` — incrementing/bounded retries are added in a
        later stage. Findings for which the provider returns an empty
        string are skipped (no `FixAttempt` is created for them). New
        attempts are appended after `state["fix_attempts"]`. This method
        does not modify files, does not run any validation tool, and does
        not mutate `state`.
        """
        code = state["code"]
        findings = state["findings"]
        existing_attempts = state["fix_attempts"]

        eligible_findings = (
            finding
            for finding in findings
            if finding.severity == EvidenceSeverity.BLOCKING and finding.is_fixable
        )

        new_attempts: list[FixAttempt] = []
        for finding in eligible_findings:
            patch = self._ai_provider.propose_fix(
                code, finding, _INITIAL_ATTEMPT_NUMBER
            )
            if patch == "":
                continue
            new_attempts.append(
                FixAttempt(
                    finding_id=finding.id,
                    patch=patch,
                    attempt_number=_INITIAL_ATTEMPT_NUMBER,
                    validation_results=(),
                )
            )

        return {"fix_attempts": existing_attempts + tuple(new_attempts)}

    def validate_fixes(
        self,
        state: ReviewWorkflowState,
    ) -> dict[str, object]:
        """Fill in `validation_results` for every not-yet-validated fix attempt.

        Calls `FixValidator.validate(code, attempt.patch)` once per attempt
        whose `validation_results` tuple is still empty, in attempt order.
        Each validated attempt is replaced by a new `FixAttempt` carrying
        the same `id`, `finding_id`, `patch`, `attempt_number`, and
        `created_at`, with only `validation_results` updated; attempts that
        already have validation results are kept unchanged (same object).
        Validator exceptions are not caught here — they propagate to the
        caller. This method does not apply `patch` to any file, does not
        run Ruff or Pytest, and does not mutate `state` or the existing
        `FixAttempt` objects.
        """
        code = state["code"]
        fix_attempts = state["fix_attempts"]

        validated_attempts: list[FixAttempt] = []
        for attempt in fix_attempts:
            if attempt.validation_results:
                validated_attempts.append(attempt)
            else:
                validated_attempts.append(self._validate_attempt(code, attempt))

        return {"fix_attempts": tuple(validated_attempts)}

    def _validate_attempt(self, code: str, attempt: FixAttempt) -> FixAttempt:
        """Return a copy of `attempt` with freshly computed `validation_results`."""
        validation_results = self._fix_validator.validate(code, attempt.patch)
        return replace(attempt, validation_results=validation_results)

    def make_decision(
        self,
        state: ReviewWorkflowState,
    ) -> dict[str, object]:
        """Consolidate `state["findings"]` into a single `Decision`.

        The review is `BLOCKED` if at least one finding has `BLOCKING`
        severity, and `APPROVED` otherwise; every other severity
        (`NON_BLOCKING`, `INFO`) is treated as non-blocking. Finding order is
        preserved within each group, and `state["fix_attempts"]` is carried
        into the decision unchanged. This method does not mutate `state`.
        """
        findings = state["findings"]
        fix_attempts = state["fix_attempts"]

        blocking_findings = tuple(
            finding
            for finding in findings
            if finding.severity == EvidenceSeverity.BLOCKING
        )
        non_blocking_findings = tuple(
            finding
            for finding in findings
            if finding.severity != EvidenceSeverity.BLOCKING
        )

        status = ReviewStatus.BLOCKED if blocking_findings else ReviewStatus.APPROVED
        rationale = self._build_rationale(
            status, blocking_findings, non_blocking_findings
        )

        decision = Decision(
            status=status,
            rationale=rationale,
            blocking_findings=blocking_findings,
            non_blocking_findings=non_blocking_findings,
            fix_attempts=fix_attempts,
        )

        return {"decision": decision}

    @staticmethod
    def _build_rationale(
        status: ReviewStatus,
        blocking_findings: tuple[Finding, ...],
        non_blocking_findings: tuple[Finding, ...],
    ) -> str:
        """Build a concise, deterministic rationale summarizing the decision."""
        if status == ReviewStatus.APPROVED:
            summary = "no blocking findings"
        else:
            noun = "finding" if len(blocking_findings) == 1 else "findings"
            summary = f"{len(blocking_findings)} blocking {noun}"

        return (
            f"Review {status.value}: {summary} "
            f"({len(non_blocking_findings)} non-blocking finding(s))."
        )
