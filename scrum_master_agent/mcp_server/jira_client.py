"""
Singleton Jira client wrapping atlassian-python-api.
All MCP tools import from this module — no tool calls Jira directly.
"""
import time
import logging
from typing import Any, Optional
from atlassian import Jira

from ..config import get_settings

logger = logging.getLogger(__name__)

# Standard fields to fetch for sprint issues
DEFAULT_ISSUE_FIELDS = [
    "summary", "status", "assignee", "issuetype", "priority",
    "labels", "story_points", "customfield_10016",  # story points (Jira Software)
    "customfield_10014",  # epic link
    "customfield_10020",  # sprint
    "flagged", "updated", "created", "duedate", "comment",
]


class JiraToolError(Exception):
    """Raised when a Jira API call fails after all retries."""
    pass


class JiraClient:
    """Thin wrapper around atlassian-python-api with retry logic."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = Jira(
            url=settings.jira_url,
            username=settings.jira_email,
            password=settings.jira_api_token,
            cloud=True,
        )

    def _retry(self, fn, *args, max_attempts: int = 3, **kwargs) -> Any:
        """Exponential backoff retry for Jira API calls."""
        for attempt in range(max_attempts):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                status = getattr(exc, "status_code", None) or getattr(exc, "response", None)
                is_retryable = "429" in str(exc) or "5" in str(getattr(status, "status_code", ""))
                if is_retryable and attempt < max_attempts - 1:
                    wait = 2 ** attempt
                    logger.warning("Jira API error (attempt %d/%d), retrying in %ds: %s",
                                   attempt + 1, max_attempts, wait, exc)
                    time.sleep(wait)
                else:
                    raise JiraToolError(f"Jira API call failed after {attempt + 1} attempt(s): {exc}") from exc

    def get_active_sprint(self, board_id: int) -> Optional[dict]:
        """Return the active sprint dict for a board, or None if no active sprint."""
        sprints = self._retry(
            self._client.get_all_sprints_from_board,
            board_id, state="active"
        )
        values = sprints.get("values", []) if isinstance(sprints, dict) else []
        return values[0] if values else None

    def get_sprint_issues(
        self,
        sprint_id: int,
        fields: Optional[list[str]] = None,
        max_results: int = 200,
    ) -> list[dict]:
        """Return all issues for a sprint."""
        field_str = ",".join(fields or DEFAULT_ISSUE_FIELDS)
        result = self._retry(
            self._client.get_sprint_issues,
            sprint_id,
            fields=field_str,
            maxResults=max_results,
        )
        if isinstance(result, dict):
            return result.get("issues", [])
        return result or []

    def search_jql(
        self,
        jql: str,
        fields: Optional[list[str]] = None,
        max_results: int = 100,
    ) -> list[dict]:
        """Run a JQL search and return matching issues."""
        field_str = ",".join(fields or DEFAULT_ISSUE_FIELDS)
        result = self._retry(
            self._client.jql,
            jql,
            fields=field_str,
            limit=max_results,
        )
        if isinstance(result, dict):
            return result.get("issues", [])
        return result or []

    def get_board_sprints(
        self,
        board_id: int,
        state: str = "closed",
        limit: int = 5,
    ) -> list[dict]:
        """Return recent sprints for a board (closed by default for velocity)."""
        result = self._retry(
            self._client.get_all_sprints_from_board,
            board_id, state=state
        )
        values = result.get("values", []) if isinstance(result, dict) else []
        return values[-limit:] if len(values) > limit else values

    def get_board(self, board_id: int) -> dict:
        """Return board metadata."""
        return self._retry(self._client.get_board, board_id)


_client: Optional[JiraClient] = None


def get_jira_client() -> JiraClient:
    global _client
    if _client is None:
        _client = JiraClient()
    return _client
