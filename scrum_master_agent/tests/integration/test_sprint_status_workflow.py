"""
Integration test for the Sprint Status workflow.
Uses mocked MCP tools (via patching tools_bridge) and mocked LLM.
"""
import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock, MagicMock

from scrum_master_agent.agent.state import WorkflowMode
from scrum_master_agent.models import SprintStatus, IssueStatus


MOCK_SPRINT_RESULT = json.dumps({
    "sprint_id": 42,
    "sprint_name": "Sprint 7",
    "board_id": 1,
    "start_date": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
    "end_date": (datetime.now(timezone.utc) + timedelta(days=9)).isoformat(),
    "goal": "Ship auth",
    "state": "active",
    "total_issues": 0,
    "completed_issues": 0,
    "in_progress_issues": 0,
    "todo_issues": 0,
    "blocked_issues": 0,
    "total_story_points": 0.0,
    "completed_story_points": 0.0,
    "remaining_story_points": 0.0,
    "completion_percentage": 0.0,
    "issues": [],
    "fetched_at": datetime.utcnow().isoformat(),
})

MOCK_ISSUES_RESULT = json.dumps([
    {
        "key": "PROJ-1", "summary": "User login", "issue_type": "Story",
        "status": "Done", "assignee": "Alice", "story_points": 5.0,
        "priority": "Medium", "labels": [], "is_blocked": False,
    },
    {
        "key": "PROJ-2", "summary": "OAuth", "issue_type": "Story",
        "status": "In Progress", "assignee": "Bob", "story_points": 8.0,
        "priority": "High", "labels": [], "is_blocked": False,
    },
])

MOCK_BLOCKERS_RESULT = json.dumps({
    "sprint_id": 42, "sprint_name": "Sprint 7",
    "total_blockers": 0, "critical_blockers": 0, "items": [],
    "generated_at": datetime.utcnow().isoformat(),
})

MOCK_WORKLOAD_RESULT = json.dumps({
    "sprint_id": 42, "members": [], "unassigned_issues": 0, "total_members": 0,
})


def _make_mock_tool(name: str, return_value: str):
    tool = MagicMock()
    tool.name = name
    tool.ainvoke = AsyncMock(return_value=return_value)
    return tool


@pytest.fixture
def mock_mcp_tools():
    tools = [
        _make_mock_tool("get_active_sprint", MOCK_SPRINT_RESULT),
        _make_mock_tool("get_sprint_issues", MOCK_ISSUES_RESULT),
        _make_mock_tool("get_blockers", MOCK_BLOCKERS_RESULT),
        _make_mock_tool("get_team_workload", MOCK_WORKLOAD_RESULT),
    ]
    with patch("scrum_master_agent.agent.nodes.fetch_node.get_mcp_tools", return_value=tools):
        yield tools


@pytest.fixture
def mock_llm_response():
    mock_response = MagicMock()
    mock_response.content = "## Sprint Status: Sprint 7\n**Days Remaining:** 9\n### Progress\n- Done: 1 (50%)"
    with patch("scrum_master_agent.agent.nodes.synthesize_node.ChatAnthropic") as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_llm_cls.return_value = mock_llm
        yield mock_llm


@pytest.fixture
def mock_settings():
    with patch("scrum_master_agent.agent.nodes.synthesize_node.get_settings") as mock:
        settings = MagicMock()
        settings.llm_model = "claude-sonnet-4-6"
        settings.llm_temperature = 0.1
        settings.anthropic_api_key = "sk-test"
        mock.return_value = settings
        yield settings


def test_sprint_status_workflow_returns_sprint_status(
    mock_mcp_tools, mock_llm_response, mock_settings
):
    from scrum_master_agent.workflows.sprint_status_workflow import run_sprint_status_query
    result = run_sprint_status_query(board_id=1, delivery_target="return")

    assert result is not None
    assert isinstance(result, SprintStatus)
    assert result.sprint_id == 42
    assert result.sprint_name == "Sprint 7"


def test_sprint_status_workflow_computes_completion(
    mock_mcp_tools, mock_llm_response, mock_settings
):
    from scrum_master_agent.workflows.sprint_status_workflow import run_sprint_status_query
    result = run_sprint_status_query(board_id=1)

    assert result.total_issues == 2
    assert result.completed_issues == 1
    assert result.completion_percentage == 50.0
