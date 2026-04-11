"""
MCP Server entry point.
Registers all Jira tools and exposes them via stdio (dev) or SSE (prod).

Usage:
    python -m scrum_master_agent.mcp_server.server
    mcp dev scrum_master_agent/mcp_server/server.py
"""
import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .tools import (
    get_active_sprint,
    get_sprint_issues,
    get_sprint_burndown,
    get_blockers,
    get_team_workload,
    get_sprint_velocity,
    search_issues_by_jql,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Server("scrum-master-agent")

# ---------------------------------------------------------------------------
# Tool registry: maps tool name → (handler_fn, input_schema)
# ---------------------------------------------------------------------------
TOOLS: dict[str, tuple] = {
    "get_active_sprint": (
        get_active_sprint,
        {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer", "description": "Jira board ID"},
            },
            "required": ["board_id"],
        },
    ),
    "get_sprint_issues": (
        get_sprint_issues,
        {
            "type": "object",
            "properties": {
                "sprint_id": {"type": "integer", "description": "Sprint ID"},
                "status_filter": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of status names to filter (e.g. ['In Progress', 'Blocked'])",
                },
            },
            "required": ["sprint_id"],
        },
    ),
    "get_sprint_burndown": (
        get_sprint_burndown,
        {
            "type": "object",
            "properties": {
                "sprint_id": {"type": "integer", "description": "Sprint ID"},
            },
            "required": ["sprint_id"],
        },
    ),
    "get_blockers": (
        get_blockers,
        {
            "type": "object",
            "properties": {
                "sprint_id": {"type": "integer", "description": "Sprint ID"},
                "board_id": {"type": "integer", "description": "Board ID"},
            },
            "required": ["sprint_id", "board_id"],
        },
    ),
    "get_team_workload": (
        get_team_workload,
        {
            "type": "object",
            "properties": {
                "sprint_id": {"type": "integer", "description": "Sprint ID"},
            },
            "required": ["sprint_id"],
        },
    ),
    "get_sprint_velocity": (
        get_sprint_velocity,
        {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer", "description": "Jira board ID"},
                "n_sprints": {
                    "type": "integer",
                    "description": "Number of recent closed sprints to include (default 5)",
                    "default": 5,
                },
            },
            "required": ["board_id"],
        },
    ),
    "search_issues_by_jql": (
        search_issues_by_jql,
        {
            "type": "object",
            "properties": {
                "jql": {"type": "string", "description": "JQL query string"},
                "max_results": {
                    "type": "integer",
                    "description": "Max number of results (default 50)",
                    "default": 50,
                },
            },
            "required": ["jql"],
        },
    ),
}


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name=name, description=fn.__doc__ or name, inputSchema=schema)
        for name, (fn, schema) in TOOLS.items()
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name not in TOOLS:
        return [TextContent(type="text", text=f'{{"error": "Unknown tool: {name}"}}')]

    fn, _ = TOOLS[name]
    try:
        result = fn(**arguments)
    except Exception as exc:
        logger.exception("Tool %s raised an unexpected error", name)
        result = f'{{"error": "Unexpected error in {name}: {exc}"}}'

    return [TextContent(type="text", text=result)]


async def _run_stdio():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    asyncio.run(_run_stdio())


if __name__ == "__main__":
    main()
