"""
PLAN node: Decides which MCP tools to call based on workflow mode.
Injects the tool plan into state messages so the FETCH node knows what to run.
"""
import logging
from langchain_core.messages import SystemMessage, HumanMessage

from ..state import AgentState, WorkflowMode
from ..prompts import SYSTEM_PROMPT, SPRINT_STATUS_TOOL_PLAN, WEEKLY_RECAP_TOOL_PLAN

logger = logging.getLogger(__name__)

# Map mode → (tool names to call, planning prompt)
_TOOL_PLAN: dict[WorkflowMode, tuple[list[str], str]] = {
    WorkflowMode.SPRINT_STATUS: (
        ["get_active_sprint", "get_sprint_issues", "get_blockers", "get_team_workload"],
        SPRINT_STATUS_TOOL_PLAN,
    ),
    WorkflowMode.WEEKLY_RECAP: (
        ["get_active_sprint", "get_sprint_issues", "get_blockers",
         "get_team_workload", "get_sprint_velocity", "get_sprint_burndown"],
        WEEKLY_RECAP_TOOL_PLAN,
    ),
}


def plan_node(state: AgentState) -> AgentState:
    """Populate tool_calls_planned and initialise the LLM message history."""
    mode = state["mode"]
    tool_names, plan_text = _TOOL_PLAN[mode]

    logger.info("PLAN node: mode=%s, tools=%s", mode, tool_names)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Board ID: {state['board_id']}\n"
            f"Mode: {mode.value}\n\n"
            f"{plan_text}"
        )),
    ]

    return {
        **state,
        "tool_calls_planned": tool_names,
        "messages": messages,
        "error": None,  # clear any previous error on (re)plan
    }
