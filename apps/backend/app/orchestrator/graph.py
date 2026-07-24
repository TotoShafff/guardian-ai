"""LangGraph wiring for the Guardian AI review workflow.

`build_review_graph()` assembles the currently implemented subset of the
review workflow described in `docs/ARCHITECTURE.md` Section 7: collect
deterministic evidence, run the Semantic Analysis Agent, propose fixes for
eligible findings, then consolidate everything into a `Decision`. Parallel
evidence gathering, conditional fix/validate routing, retries, patch
validation, and persistence checkpoints are added in a later stage (see
`docs/ROADMAP.md` Stage 6). This module only wires nodes together — it
never instantiates `RuffTool`, `PytestTool`, an `AIProvider`, or a
repository itself; those dependencies are supplied by the caller through an
already-constructed `ReviewWorkflowNodes`.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.orchestrator.nodes import ReviewWorkflowNodes
from app.orchestrator.state import ReviewWorkflowState

#: Stable node names, used both to build and to inspect the compiled graph.
COLLECT_EVIDENCE = "collect_evidence"
SEMANTIC_ANALYSIS = "semantic_analysis"
PROPOSE_FIXES = "propose_fixes"
MAKE_DECISION = "make_decision"


def build_review_graph(nodes: ReviewWorkflowNodes) -> CompiledStateGraph:
    """Build and compile the review workflow graph from an existing `nodes` instance.

    The graph is a fixed, linear sequence with no branching:
    `START -> collect_evidence -> semantic_analysis -> propose_fixes ->
    make_decision -> END`. No conditional edges, retries, loops, or
    checkpoints are added at this stage.
    """
    graph = StateGraph(ReviewWorkflowState)

    graph.add_node(COLLECT_EVIDENCE, nodes.collect_deterministic_evidence)
    graph.add_node(SEMANTIC_ANALYSIS, nodes.analyze_semantically)
    graph.add_node(PROPOSE_FIXES, nodes.propose_fixes)
    graph.add_node(MAKE_DECISION, nodes.make_decision)

    graph.add_edge(START, COLLECT_EVIDENCE)
    graph.add_edge(COLLECT_EVIDENCE, SEMANTIC_ANALYSIS)
    graph.add_edge(SEMANTIC_ANALYSIS, PROPOSE_FIXES)
    graph.add_edge(PROPOSE_FIXES, MAKE_DECISION)
    graph.add_edge(MAKE_DECISION, END)

    return graph.compile()
