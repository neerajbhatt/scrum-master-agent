"""Unit tests for team workload MCP tool."""
import json
import pytest

from scrum_master_agent.mcp_server.tools.team_tools import get_team_workload


class TestGetTeamWorkload:
    def test_returns_workload(self, mock_jira_client):
        result = json.loads(get_team_workload(sprint_id=42))
        assert "members" in result
        assert "unassigned_issues" in result

    def test_members_present(self, mock_jira_client):
        result = json.loads(get_team_workload(sprint_id=42))
        names = [m["member"]["display_name"] for m in result["members"]]
        assert "Alice" in names
        assert "Bob" in names
        assert "Charlie" in names

    def test_unassigned_counted(self, mock_jira_client):
        result = json.loads(get_team_workload(sprint_id=42))
        assert result["unassigned_issues"] >= 1  # PROJ-7 has no assignee

    def test_completion_rate_between_0_and_1(self, mock_jira_client):
        result = json.loads(get_team_workload(sprint_id=42))
        for member in result["members"]:
            assert 0.0 <= member["completion_rate"] <= 1.0
