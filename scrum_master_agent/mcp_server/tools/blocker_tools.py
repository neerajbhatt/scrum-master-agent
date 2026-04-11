"""
MCP tool: get_blockers — fetch blocked/flagged issues from a sprint.
"""
import json
import logging
from datetime import datetime, timezone

from ...models import BlockerItem, BlockerReport, BlockerSeverity
from ..jira_client import get_jira_client, JiraToolError

logger = logging.getLogger(__name__)


def _compute_days_blocked(fields: dict) -> int:
    """Estimate days blocked from the issue's updated or created date."""
    updated_str = fields.get("updated") or fields.get("created")
    if not updated_str:
        return 0
    try:
        updated = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return max(0, (now - updated).days)
    except Exception:
        return 0


def _determine_severity(fields: dict) -> BlockerSeverity:
    labels = [l.lower() for l in (fields.get("labels") or [])]
    flagged = fields.get("flagged") or fields.get("customfield_10021")
    status_name = fields.get("status", {}).get("name", "")

    if flagged:
        return BlockerSeverity.CRITICAL
    if status_name.lower() == "blocked":
        return BlockerSeverity.HIGH
    if "blocked" in labels or "impediment" in labels:
        return BlockerSeverity.MEDIUM
    return BlockerSeverity.LOW


def get_blockers(sprint_id: int, board_id: int) -> str:
    """
    MCP tool: Return all blocked/flagged issues in the given sprint.
    Severity: flagged=Impediment → CRITICAL, status=Blocked → HIGH, labels=blocked → MEDIUM.
    Returns JSON-serialised BlockerReport.
    """
    try:
        client = get_jira_client()

        # JQL: issues in sprint that are blocked or flagged
        jql = (
            f'sprint = {sprint_id} AND ('
            f'status = "Blocked" OR '
            f'labels in ("blocked", "impediment") OR '
            f'flagged = "Impediment"'
            f')'
        )
        raw_issues = client.search_jql(jql, max_results=100)

        items: list[BlockerItem] = []
        for raw in raw_issues:
            fields = raw.get("fields", {})
            assignee_data = fields.get("assignee") or {}
            severity = _determine_severity(fields)
            days_blocked = _compute_days_blocked(fields)

            items.append(BlockerItem(
                issue_key=raw["key"],
                summary=fields.get("summary", ""),
                assignee=assignee_data.get("displayName"),
                severity=severity,
                days_blocked=days_blocked,
                blocker_description=fields.get("customfield_10023"),  # impediment description if set
            ))

        critical_count = sum(1 for i in items if i.severity == BlockerSeverity.CRITICAL)

        report = BlockerReport(
            sprint_id=sprint_id,
            sprint_name=f"Sprint {sprint_id}",  # name filled by agent from sprint context
            total_blockers=len(items),
            critical_blockers=critical_count,
            items=items,
        )
        return report.model_dump_json()
    except JiraToolError as e:
        logger.error("get_blockers failed: %s", e)
        return json.dumps({"error": str(e)})
