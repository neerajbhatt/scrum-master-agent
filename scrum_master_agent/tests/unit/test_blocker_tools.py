"""Unit tests for blocker MCP tool."""
import json
import pytest

from scrum_master_agent.mcp_server.tools.blocker_tools import get_blockers
from scrum_master_agent.models import BlockerSeverity


class TestGetBlockers:
    def test_returns_blocker_report(self, mock_jira_client):
        result = json.loads(get_blockers(sprint_id=42, board_id=1))
        assert "total_blockers" in result
        assert "items" in result

    def test_blocked_issue_included(self, mock_jira_client):
        result = json.loads(get_blockers(sprint_id=42, board_id=1))
        keys = [item["issue_key"] for item in result["items"]]
        assert "PROJ-4" in keys

    def test_critical_count_accurate(self, mock_jira_client):
        result = json.loads(get_blockers(sprint_id=42, board_id=1))
        critical = [i for i in result["items"] if i["severity"] == BlockerSeverity.CRITICAL]
        assert result["critical_blockers"] == len(critical)

    def test_jira_error_returns_error_json(self, mock_jira_client):
        from scrum_master_agent.mcp_server.jira_client import JiraToolError
        mock_jira_client.search_jql.side_effect = JiraToolError("timeout")
        result = json.loads(get_blockers(sprint_id=42, board_id=1))
        assert "error" in result
