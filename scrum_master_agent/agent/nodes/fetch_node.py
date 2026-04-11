"""
FETCH node: Executes the MCP tool calls planned by the PLAN node.
Calls get_active_sprint first to resolve sprint_id, then remaining tools in parallel.
"""
import json
import asyncio
import logging
from typing import Any

from langchain_core.messages import ToolMessage

from ..state import AgentState
from ..tools_bridge import get_mcp_tools

logger = logging.getLogger(__name__)


async def _call_tool(tools_by_name: dict, name: str, args: dict) -> tuple[str, str]:
    """Call a single MCP tool and return (name, result_json)."""
    tool = tools_by_name.get(name)
    if tool is None:
        return name, json.dumps({"error": f"Tool '{name}' not found in MCP server"})
    try:
        result = await tool.ainvoke(args)
        return name, result if isinstance(result, str) else json.dumps(result)
    except Exception as exc:
        logger.error("Tool %s failed: %s", name, exc)
        return name, json.dumps({"error": str(exc)})


async def _fetch_all(state: AgentState) -> dict[str, Any]:
    """Run all planned tool calls. get_active_sprint runs first to resolve sprint_id."""
    tools = await get_mcp_tools()
    tools_by_name = {t.name: t for t in tools}

    board_id = state["board_id"]
    planned = state["tool_calls_planned"]
    results: dict[str, str] = {}

    # Step 1: always resolve sprint first if needed
    sprint_id = state.get("sprint_id")
    if "get_active_sprint" in planned:
        _, sprint_result = await _call_tool(tools_by_name, "get_active_sprint", {"board_id": board_id})
        results["get_active_sprint"] = sprint_result

        parsed = json.loads(sprint_result)
        if "error" not in parsed:
            sprint_id = parsed.get("sprint_id")

    # Step 2: run remaining tools in parallel (they need sprint_id)
    remaining = [t for t in planned if t != "get_active_sprint"]
    if remaining and sprint_id is None:
        error_msg = "Cannot call sprint tools: no active sprint found"
        logger.warning(error_msg)
        for name in remaining:
            results[name] = json.dumps({"error": error_msg})
        return results, sprint_id

    async def _with_args(name: str) -> tuple[str, str]:
        args: dict = {}
        if name in ("get_sprint_issues", "get_sprint_burndown", "get_team_workload"):
            args = {"sprint_id": sprint_id}
        elif name == "get_blockers":
            args = {"sprint_id": sprint_id, "board_id": board_id}
        elif name == "get_sprint_velocity":
            args = {"board_id": board_id, "n_sprints": 5}
        return await _call_tool(tools_by_name, name, args)

    parallel_results = await asyncio.gather(*[_with_args(n) for n in remaining])
    for name, result in parallel_results:
        results[name] = result

    return results, sprint_id


def fetch_node(state: AgentState) -> AgentState:
    """Synchronous wrapper — runs the async fetch in the event loop."""
    try:
        results, sprint_id = asyncio.run(_fetch_all(state))
    except RuntimeError:
        # Already inside an event loop (e.g. Jupyter / tests)
        loop = asyncio.get_event_loop()
        results, sprint_id = loop.run_until_complete(_fetch_all(state))

    # Check for any hard errors
    errors = [
        f"{name}: {json.loads(r).get('error')}"
        for name, r in results.items()
        if isinstance(r, str) and "error" in json.loads(r)
    ]
    error_msg = "; ".join(errors) if errors else None

    # Append tool results as messages for the LLM context
    tool_messages = [
        ToolMessage(content=result, tool_call_id=name, name=name)
        for name, result in results.items()
    ]

    return {
        **state,
        "sprint_id": sprint_id,
        "tool_results": results,
        "messages": state["messages"] + tool_messages,
        "error": error_msg,
        "retry_count": state.get("retry_count", 0),
    }
