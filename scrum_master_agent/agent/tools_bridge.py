"""
LangChain-MCP bridge.
Launches the MCP server as a subprocess and exposes its tools as LangChain BaseTool objects.
"""
import sys
import logging
from typing import Optional
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

_mcp_tools: Optional[list] = None


async def get_mcp_tools() -> list:
    """
    Start the MCP server subprocess (stdio transport) and return its tools
    as a list of LangChain-compatible BaseTool objects.

    The client is cached so the subprocess is only launched once per process.
    """
    global _mcp_tools
    if _mcp_tools is not None:
        return _mcp_tools

    client = MultiServerMCPClient({
        "jira": {
            "command": sys.executable,
            "args": ["-m", "scrum_master_agent.mcp_server.server"],
            "transport": "stdio",
        }
    })

    _mcp_tools = await client.get_tools()
    logger.info("MCP tools loaded: %s", [t.name for t in _mcp_tools])
    return _mcp_tools


def reset_mcp_tools():
    """Force re-initialisation of MCP tools (useful in tests)."""
    global _mcp_tools
    _mcp_tools = None
