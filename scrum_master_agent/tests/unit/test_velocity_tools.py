"""Unit tests for velocity MCP tool."""
import json
import pytest

from scrum_master_agent.mcp_server.tools.velocity_tools import get_sprint_velocity


class TestGetSprintVelocity:
    def test_returns_velocity_records(self, mock_jira_client):
        result = json.loads(get_sprint_velocity(board_id=1, n_sprints=3))
        assert isinstance(result, list)
        assert len(result) <= 3

    def test_velocity_fields_present(self, mock_jira_client):
        result = json.loads(get_sprint_velocity(board_id=1))
        for record in result:
            assert "sprint_name" in record
            assert "committed_points" in record
            assert "completed_points" in record
            assert "velocity" in record

    def test_velocity_non_negative(self, mock_jira_client):
        result = json.loads(get_sprint_velocity(board_id=1))
        for record in result:
            assert record["velocity"] >= 0
