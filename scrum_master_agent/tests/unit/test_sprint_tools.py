"""Unit tests for sprint MCP tools."""
import json
import pytest
from unittest.mock import patch, MagicMock

from scrum_master_agent.mcp_server.tools.sprint_tools import (
    get_active_sprint,
    get_sprint_issues,
    get_sprint_burndown,
)
from scrum_master_agent.models import IssueStatus


class TestGetActiveSprint:
    def test_returns_sprint_status_json(self, mock_jira_client, sample_sprint_raw):
        result = json.loads(get_active_sprint(board_id=1))
        assert result["sprint_id"] == sample_sprint_raw["id"]
        assert result["sprint_name"] == sample_sprint_raw["name"]
        assert result["state"] == "active"

    def test_no_active_sprint_returns_error(self, mock_jira_client):
        mock_jira_client.get_active_sprint.return_value = None
        result = json.loads(get_active_sprint(board_id=999))
        assert "error" in result

    def test_jira_error_returns_error_json(self, mock_jira_client):
        from scrum_master_agent.mcp_server.jira_client import JiraToolError
        mock_jira_client.get_active_sprint.side_effect = JiraToolError("Connection refused")
        result = json.loads(get_active_sprint(board_id=1))
        assert "error" in result
        assert "Connection refused" in result["error"]


class TestGetSprintIssues:
    def test_returns_all_issues(self, mock_jira_client, sample_issues_raw):
        result = json.loads(get_sprint_issues(sprint_id=42))
        assert isinstance(result, list)
        assert len(result) == len(sample_issues_raw)

    def test_status_filter_works(self, mock_jira_client):
        result = json.loads(get_sprint_issues(sprint_id=42, status_filter=["Done"]))
        assert all(i["status"] == "Done" for i in result)

    def test_story_points_parsed(self, mock_jira_client):
        result = json.loads(get_sprint_issues(sprint_id=42))
        issues_with_points = [i for i in result if i["story_points"] is not None]
        assert len(issues_with_points) > 0

    def test_unassigned_issue_has_null_assignee(self, mock_jira_client):
        result = json.loads(get_sprint_issues(sprint_id=42))
        unassigned = [i for i in result if i["assignee"] is None]
        assert len(unassigned) >= 1  # PROJ-7

    def test_blocked_issue_flagged(self, mock_jira_client):
        result = json.loads(get_sprint_issues(sprint_id=42))
        blocked = [i for i in result if i["is_blocked"]]
        assert len(blocked) >= 1


class TestGetSprintBurndown:
    def test_returns_burndown_dict(self, mock_jira_client):
        result = json.loads(get_sprint_burndown(sprint_id=42))
        assert "burndown" in result
        assert "total_points" in result

    def test_total_points_positive(self, mock_jira_client):
        result = json.loads(get_sprint_burndown(sprint_id=42))
        assert result["total_points"] >= 0
