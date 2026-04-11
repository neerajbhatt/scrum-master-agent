"""
MCP tools: get_active_sprint, get_sprint_issues, get_sprint_burndown
"""
import json
import logging
from datetime import datetime
from typing import Optional

from ...models import SprintStatus, SprintIssue, IssueStatus, IssueType
from ..jira_client import get_jira_client, JiraToolError

logger = logging.getLogger(__name__)


def _parse_issue(raw: dict) -> SprintIssue:
    """Parse a raw Jira issue dict into a SprintIssue model."""
    fields = raw.get("fields", {})

    # Story points: try customfield_10016 first, then customfield_10028
    story_points = (
        fields.get("customfield_10016")
        or fields.get("customfield_10028")
        or fields.get("story_points")
    )

    # Status
    status_name = fields.get("status", {}).get("name", "To Do")
    try:
        status = IssueStatus(status_name)
    except ValueError:
        status = IssueStatus.TODO

    # Issue type
    type_name = fields.get("issuetype", {}).get("name", "Task")
    try:
        issue_type = IssueType(type_name)
    except ValueError:
        issue_type = IssueType.TASK

    # Assignee
    assignee_data = fields.get("assignee") or {}
    assignee = assignee_data.get("displayName")

    # Epic name
    epic_name = fields.get("customfield_10014") or fields.get("epic", {}).get("name")

    # Blocked detection: flagged field or status
    is_blocked = (
        status == IssueStatus.BLOCKED
        or bool(fields.get("flagged"))
        or "blocked" in [l.lower() for l in (fields.get("labels") or [])]
    )

    return SprintIssue(
        key=raw["key"],
        summary=fields.get("summary", ""),
        issue_type=issue_type,
        status=status,
        assignee=assignee,
        story_points=float(story_points) if story_points is not None else None,
        priority=fields.get("priority", {}).get("name", "Medium"),
        labels=fields.get("labels") or [],
        epic_name=epic_name,
        updated=_parse_datetime(fields.get("updated")),
        created=_parse_datetime(fields.get("created")),
        due_date=_parse_datetime(fields.get("duedate")),
        is_blocked=is_blocked,
    )


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:26], fmt[:len(value)])
        except ValueError:
            continue
    return None


def get_active_sprint(board_id: int) -> str:
    """
    MCP tool: Fetch the active sprint for a Jira board.
    Returns JSON-serialised SprintStatus (without issue list).
    """
    try:
        client = get_jira_client()
        raw = client.get_active_sprint(board_id)
        if not raw:
            return json.dumps({"error": f"No active sprint found for board {board_id}"})

        start_str = raw.get("startDate", "")
        end_str = raw.get("endDate", "")
        now = datetime.utcnow()

        status = SprintStatus(
            sprint_id=raw["id"],
            sprint_name=raw["name"],
            board_id=board_id,
            start_date=_parse_datetime(start_str) or now,
            end_date=_parse_datetime(end_str) or now,
            goal=raw.get("goal"),
            state=raw.get("state", "active"),
            total_issues=0,
            completed_issues=0,
            in_progress_issues=0,
            todo_issues=0,
            blocked_issues=0,
        )
        return status.model_dump_json()
    except JiraToolError as e:
        logger.error("get_active_sprint failed: %s", e)
        return json.dumps({"error": str(e)})


def get_sprint_issues(sprint_id: int, status_filter: Optional[list[str]] = None) -> str:
    """
    MCP tool: Fetch all issues in a sprint, optionally filtered by status.
    Returns JSON array of SprintIssue objects.
    """
    try:
        client = get_jira_client()
        raw_issues = client.get_sprint_issues(sprint_id)
        issues = [_parse_issue(r) for r in raw_issues]

        if status_filter:
            filter_set = {s.lower() for s in status_filter}
            issues = [i for i in issues if i.status.value.lower() in filter_set]

        return json.dumps([i.model_dump(mode="json") for i in issues])
    except JiraToolError as e:
        logger.error("get_sprint_issues failed: %s", e)
        return json.dumps({"error": str(e)})


def get_sprint_burndown(sprint_id: int) -> str:
    """
    MCP tool: Return a simplified burndown — remaining story points per day.
    Derived from issue update timestamps (approximation).
    Returns JSON dict {date_str: remaining_points}.
    """
    try:
        client = get_jira_client()
        raw_issues = client.get_sprint_issues(sprint_id)
        issues = [_parse_issue(r) for r in raw_issues]

        total_points = sum(i.story_points or 0 for i in issues)
        remaining = total_points

        # Build daily series: group completed issues by date
        daily: dict[str, float] = {}
        for issue in sorted(issues, key=lambda x: x.updated or datetime.utcnow()):
            if issue.status == IssueStatus.DONE and issue.updated and issue.story_points:
                day = issue.updated.strftime("%Y-%m-%d")
                daily[day] = daily.get(day, 0) + (issue.story_points or 0)

        burndown: dict[str, float] = {}
        for day in sorted(daily):
            remaining -= daily[day]
            burndown[day] = round(max(remaining, 0), 1)

        return json.dumps({"sprint_id": sprint_id, "burndown": burndown, "total_points": total_points})
    except JiraToolError as e:
        logger.error("get_sprint_burndown failed: %s", e)
        return json.dumps({"error": str(e)})
