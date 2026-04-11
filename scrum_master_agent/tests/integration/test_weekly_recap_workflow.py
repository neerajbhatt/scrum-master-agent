"""
Integration test for the Weekly Recap workflow.
Uses mocked MCP tools and mocked LLM.
"""
import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock, MagicMock

from scrum_master_agent.models import WeeklyRecap


MOCK_SPRINT_RESULT = json.dumps({
    "sprint_id": 42, "sprint_name": "Sprint 7", "board_id": 1,
    "start_date": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
    "end_date": (datetime.now(timezone.utc) + timedelta(days=9)).isoformat(),
    "goal": "Ship auth", "state": "active",
    "total_issues": 0, "completed_issues": 0, "in_progress_issues": 0,
    "todo_issues": 0, "blocked_issues": 0,
    "total_story_points": 0.0, "completed_story_points": 0.0,
    "remaining_story_points": 0.0, "completion_percentage": 50.0,
    "issues": [], "fetched_at": datetime.utcnow().isoformat(),
})

MOCK_VELOCITY_RESULT = json.dumps([
    {"sprint_id": 40, "sprint_name": "Sprint 5", "committed_points": 30.0, "completed_points": 25.0, "velocity": 83.3},
    {"sprint_id": 41, "sprint_name": "Sprint 6", "committed_points": 28.0, "completed_points": 28.0, "velocity": 100.0},
])

MOCK_BURNDOWN_RESULT = json.dumps({
    "sprint_id": 42, "burndown": {"2026-04-07": 20.0, "2026-04-08": 15.0}, "total_points": 31.0,
})

MOCK_BLOCKERS_RESULT = json.dumps({
    "sprint_id": 42, "sprint_name": "Sprint 7",
    "total_blockers": 1, "critical_blockers": 0,
    "items": [{"issue_key": "PROJ-4", "summary": "Session timeout", "severity": "Medium", "days_blocked": 2}],
    "generated_at": datetime.utcnow().isoformat(),
})

MOCK_WORKLOAD_RESULT = json.dumps({
    "sprint_id": 42, "members": [], "unassigned_issues": 0, "total_members": 0,
})

MOCK_ISSUES_RESULT = json.dumps([])


def _make_mock_tool(name: str, return_value: str):
    tool = MagicMock()
    tool.name = name
    tool.ainvoke = AsyncMock(return_value=return_value)
    return tool


@pytest.fixture
def mock_mcp_tools_recap():
    tools = [
        _make_mock_tool("get_active_sprint", MOCK_SPRINT_RESULT),
        _make_mock_tool("get_sprint_issues", MOCK_ISSUES_RESULT),
        _make_mock_tool("get_blockers", MOCK_BLOCKERS_RESULT),
        _make_mock_tool("get_team_workload", MOCK_WORKLOAD_RESULT),
        _make_mock_tool("get_sprint_velocity", MOCK_VELOCITY_RESULT),
        _make_mock_tool("get_sprint_burndown", MOCK_BURNDOWN_RESULT),
    ]
    with patch("scrum_master_agent.agent.nodes.fetch_node.get_mcp_tools", return_value=tools):
        yield tools


@pytest.fixture
def mock_llm_recap():
    mock_response = MagicMock()
    mock_response.content = (
        "## Weekly Recap — Sprint 7 | Week ending 2026-04-11\n\n"
        "**Executive Summary:** Sprint is progressing well with 50% completion.\n\n"
        "### What We Accomplished\n- PROJ-1: User login (5 pts)\n\n"
        "### Blockers\n- PROJ-4: Session timeout (Medium)\n\n"
        "### Velocity\n| Sprint | Committed | Completed | Velocity |\n"
        "|--------|-----------|-----------|----------|\n"
        "| Sprint 5 | 30 | 25 | 83.3% |\n| Sprint 6 | 28 | 28 | 100% |\n\n"
        "### Risks\n1. One active blocker\n\n### Next Week\n- Resolve PROJ-4\n"
    )
    with patch("scrum_master_agent.agent.nodes.synthesize_node.ChatAnthropic") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_cls.return_value = mock_llm
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


def test_weekly_recap_workflow_returns_recap(
    mock_mcp_tools_recap, mock_llm_recap, mock_settings
):
    from scrum_master_agent.workflows.weekly_recap_workflow import run_weekly_recap
    result = run_weekly_recap(board_id=1, delivery_target="return")

    assert result is not None
    assert isinstance(result, WeeklyRecap)
    assert result.sprint_summary.sprint_id == 42


def test_weekly_recap_contains_velocity_trend(
    mock_mcp_tools_recap, mock_llm_recap, mock_settings
):
    from scrum_master_agent.workflows.weekly_recap_workflow import run_weekly_recap
    result = run_weekly_recap(board_id=1)

    assert len(result.velocity_trend) == 2
    assert result.velocity_trend[0].sprint_name == "Sprint 5"


def test_weekly_recap_markdown_populated(
    mock_mcp_tools_recap, mock_llm_recap, mock_settings
):
    from scrum_master_agent.workflows.weekly_recap_workflow import run_weekly_recap
    result = run_weekly_recap(board_id=1)

    assert result.raw_markdown is not None
    assert "Weekly Recap" in result.raw_markdown
