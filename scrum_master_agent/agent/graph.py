"""
LangGraph StateGraph for the Scrum Master Digital Worker.

Flow:  START → PLAN → FETCH → SYNTHESIZE → DELIVER → END
Error: FETCH failure (retry_count < 2) → PLAN (retry)
       FETCH failure (retry_count >= 2) → ERROR_END
"""
import logging
from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import plan_node, fetch_node, synthesize_node, deliver_node

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


def _route_after_fetch(state: AgentState) -> str:
    """Conditional edge: retry on error up to MAX_RETRIES, then give up."""
    if state.get("error"):
        retry_count = state.get("retry_count", 0) + 1
        if retry_count < MAX_RETRIES:
            logger.warning("FETCH failed (attempt %d/%d), retrying...", retry_count, MAX_RETRIES)
            return "plan"  # retry
        logger.error("FETCH failed after %d retries, aborting.", MAX_RETRIES)
        return "error_end"
    return "synthesize"


def _route_after_synthesize(state: AgentState) -> str:
    if state.get("error"):
        return "error_end"
    return "deliver"


def _error_end_node(state: AgentState) -> AgentState:
    """Terminal error node — logs the final error and stops."""
    logger.error("Agent terminated with error: %s", state.get("error"))
    return state


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("plan", plan_node)
    graph.add_node("fetch", fetch_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("deliver", deliver_node)
    graph.add_node("error_end", _error_end_node)

    graph.set_entry_point("plan")

    graph.add_edge("plan", "fetch")
    graph.add_conditional_edges("fetch", _route_after_fetch, {
        "synthesize": "synthesize",
        "plan": "plan",
        "error_end": "error_end",
    })
    graph.add_conditional_edges("synthesize", _route_after_synthesize, {
        "deliver": "deliver",
        "error_end": "error_end",
    })
    graph.add_edge("deliver", END)
    graph.add_edge("error_end", END)

    return graph


# Compiled graph — import this in workflows
compiled_graph = build_graph().compile()
