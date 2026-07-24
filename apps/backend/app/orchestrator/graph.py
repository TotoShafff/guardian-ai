"""LangGraph wiring for the Guardian AI review workflow.

`build_review_graph()` assembles the currently implemented subset of the
review workflow described in `docs/ARCHITECTURE.md` Section 7: collect
deterministic evidence, run the Semantic Analysis Agent, propose fixes for
eligible findings, validate them, and — via `route_after_validation` — either
loop back to `propose_fixes` for another bounded attempt or continue to the
Decision Agent. Parallel evidence gathering, persistence checkpoints, and a
validator that actually applies patches are added in a later stage (see
`docs/ROADMAP.md` Stage 6). This module only wires nodes together — it never
instantiates `RuffTool`, `PytestTool`, an `AIProvider`, a `FixValidator`, or
a repository itself; those dependencies (including `max_fix_attempts`) are
supplied by the caller through an already-constructed `ReviewWorkflowNodes`.
"""

from uuid import UUID

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.domain.models import EvidenceSeverity, Finding, FixAttempt, ValidationStatus
from app.orchestrator.nodes import ReviewWorkflowNodes
from app.orchestrator.state import ReviewWorkflowState

#: Stable node names, used both to build and to inspect the compiled graph.
COLLECT_EVIDENCE = "collect_evidence"
SEMANTIC_ANALYSIS = "semantic_analysis"
PROPOSE_FIXES = "propose_fixes"
VALIDATE_FIXES = "validate_fixes"
MAKE_DECISION = "make_decision"

#: Possible outcomes of `route_after_validation`, used as conditional-edge keys.
ROUTE_RETRY = "retry"
ROUTE_DECISION = "decision"


def build_review_graph(nodes: ReviewWorkflowNodes) -> CompiledStateGraph:
    """Build and compile the review workflow graph from an existing `nodes` instance.

    The graph is: `START -> collect_evidence -> semantic_analysis ->
    propose_fixes -> validate_fixes -> [route_after_validation] ->
    (propose_fixes | make_decision) -> END`. The conditional edge after
    `validate_fixes` loops back to `propose_fixes` while
    `route_after_validation` returns `"retry"`, and proceeds to
    `make_decision` once it returns `"decision"`. `nodes.max_fix_attempts`
    bounds the loop, so it always terminates (see `route_after_validation`).
    No persistence checkpoints are added at this stage.
    """
    graph = StateGraph(ReviewWorkflowState)

    graph.add_node(COLLECT_EVIDENCE, nodes.collect_deterministic_evidence)
    graph.add_node(SEMANTIC_ANALYSIS, nodes.analyze_semantically)
    graph.add_node(PROPOSE_FIXES, nodes.propose_fixes)
    graph.add_node(VALIDATE_FIXES, nodes.validate_fixes)
    graph.add_node(MAKE_DECISION, nodes.make_decision)

    graph.add_edge(START, COLLECT_EVIDENCE)
    graph.add_edge(COLLECT_EVIDENCE, SEMANTIC_ANALYSIS)
    graph.add_edge(SEMANTIC_ANALYSIS, PROPOSE_FIXES)
    graph.add_edge(PROPOSE_FIXES, VALIDATE_FIXES)
    graph.add_conditional_edges(
        VALIDATE_FIXES,
        lambda state: route_after_validation(state, nodes.max_fix_attempts),
        {ROUTE_RETRY: PROPOSE_FIXES, ROUTE_DECISION: MAKE_DECISION},
    )
    graph.add_edge(MAKE_DECISION, END)

    return graph.compile()


def route_after_validation(
    state: ReviewWorkflowState,
    max_fix_attempts: int,
) -> str:
    """Decide whether to retry fixing or move on to the Decision Agent.

    Returns `"retry"` when at least one blocking, fixable finding still
    needs a successful fix: its latest `FixAttempt` is missing, or has at
    least one `FAILED`/`ERROR` `ValidationResult` and has not yet reached
    `max_fix_attempts`. A finding whose latest attempt's validation results
    are all `PASSED`, or whose latest attempt number already equals
    `max_fix_attempts`, is never retried. Returns `"decision"` when no
    eligible finding needs a retry (including when there are no blocking
    findings at all). This function is pure and deterministic: it only
    reads `state` and `max_fix_attempts`, never mutates `state`, and
    performs no I/O.
    """
    if max_fix_attempts < 1:
        raise ValueError("max_fix_attempts must be at least 1")

    findings = state["findings"]
    fix_attempts = state["fix_attempts"]

    eligible_findings = (
        finding
        for finding in findings
        if finding.severity == EvidenceSeverity.BLOCKING and finding.is_fixable
    )

    for finding in eligible_findings:
        if _finding_needs_retry(finding, fix_attempts, max_fix_attempts):
            return ROUTE_RETRY

    return ROUTE_DECISION


def _finding_needs_retry(
    finding: Finding,
    fix_attempts: tuple[FixAttempt, ...],
    max_fix_attempts: int,
) -> bool:
    """Return whether `finding` still needs another bounded fix attempt."""
    latest_attempt = _latest_attempt_for_finding(fix_attempts, finding.id)
    if latest_attempt is None:
        return True
    if latest_attempt.attempt_number >= max_fix_attempts:
        return False
    if _attempt_fully_passed(latest_attempt):
        return False
    return any(
        result.status in (ValidationStatus.FAILED, ValidationStatus.ERROR)
        for result in latest_attempt.validation_results
    )


def _latest_attempt_for_finding(
    attempts: tuple[FixAttempt, ...],
    finding_id: UUID,
) -> FixAttempt | None:
    """Return the highest-`attempt_number` `FixAttempt` for `finding_id`, if any."""
    matching = [attempt for attempt in attempts if attempt.finding_id == finding_id]
    if not matching:
        return None
    return max(matching, key=lambda attempt: attempt.attempt_number)


def _attempt_fully_passed(attempt: FixAttempt) -> bool:
    """Return whether every `ValidationResult` on `attempt` has status `PASSED`."""
    return bool(attempt.validation_results) and all(
        result.status == ValidationStatus.PASSED
        for result in attempt.validation_results
    )
