"""
MCP tool: search_issues_by_jql — flexible JQL-based issue search.
"""
import json
import logging

from ..jira_client import get_jira_client, JiraToolError
from .sprint_tools import _parse_issue

logger = logging.getLogger(__name__)


def search_issues_by_jql(jql: str, max_results: int = 50) -> str:
    """
    MCP tool: Execute an arbitrary JQL query and return matching SprintIssue objects.
    Useful for ad-hoc queries (e.g. unresolved bugs, issues by epic, overdue items).
    Returns JSON array of SprintIssue objects.
    """
    try:
        client = get_jira_client()
        raw_issues = client.search_jql(jql, max_results=max_results)
        issues = [_parse_issue(r) for r in raw_issues]
        return json.dumps([i.model_dump(mode="json") for i in issues])
    except JiraToolError as e:
        logger.error("search_issues_by_jql failed (jql=%r): %s", jql, e)
        return json.dumps({"error": str(e)})
