"""
Shared test fixtures:
- mock_jira_client: replaces JiraClient singleton with a mock
- mock_slack: stubs SlackDelivery to not make real HTTP calls
- sample_sprint_raw: realistic raw Jira sprint dict
- sample_issues_raw: realistic raw Jira issue list
"""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Raw Jira data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def now():
    return datetime.now(timezone.utc)


@pytest.fixture
def sample_sprint_raw(now):
    start = now - timedelta(days=5)
    end = now + timedelta(days=9)
    return {
        "id": 42,
        "name": "Sprint 7",
        "state": "active",
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "goal": "Ship user auth feature",
    }


@pytest.fixture
def sample_issues_raw():
    def _make(key, summary, status, assignee, points, issue_type="Story", labels=None, flagged=False):
        return {
            "key": key,
            "fields": {
                "summary": summary,
                "status": {"name": status},
                "assignee": {"displayName": assignee, "accountId": f"uid-{assignee.lower().replace(' ', '-')}"} if assignee else None,
                "customfield_10016": points,
                "issuetype": {"name": issue_type},
                "priority": {"name": "Medium"},
                "labels": labels or [],
                "flagged": flagged,
                "updated": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                "created": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
                "duedate": None,
            },
        }

    return [
        _make("PROJ-1", "User login page", "Done", "Alice", 5),
        _make("PROJ-2", "OAuth integration", "In Progress", "Bob", 8),
        _make("PROJ-3", "Password reset", "To Do", "Alice", 3),
        _make("PROJ-4", "Session timeout", "Blocked", "Bob", 3, labels=["blocked"]),
        _make("PROJ-5", "2FA support", "Done", "Charlie", 5),
        _make("PROJ-6", "Audit logging", "In Progress", "Charlie", 5),
        _make("PROJ-7", "API rate limiting", "To Do", None, 2),
    ]


@pytest.fixture
def mock_jira_client(sample_sprint_raw, sample_issues_raw):
    """Patch JiraClient with a mock that returns fixture data."""
    mock = MagicMock()
    mock.get_active_sprint.return_value = sample_sprint_raw
    mock.get_sprint_issues.return_value = sample_issues_raw
    mock.search_jql.return_value = [sample_issues_raw[3]]  # PROJ-4 blocked
    mock.get_board_sprints.return_value = [
        {"id": 40, "name": "Sprint 5"},
        {"id": 41, "name": "Sprint 6"},
        {"id": 42, "name": "Sprint 7"},
    ]

    with patch("scrum_master_agent.mcp_server.jira_client._client", mock):
        with patch("scrum_master_agent.mcp_server.jira_client.JiraClient", return_value=mock):
            yield mock


@pytest.fixture
def mock_slack():
    """Patch SlackDelivery so no real HTTP calls are made."""
    with patch("scrum_master_agent.delivery.slack_delivery.WebhookClient") as mock_wh:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_wh.return_value.send.return_value = mock_response
        yield mock_wh
