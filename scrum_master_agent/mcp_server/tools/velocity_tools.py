"""
MCP tool: get_sprint_velocity — historical velocity across recent closed sprints.
"""
import json
import logging

from ...models import VelocityRecord
from ..jira_client import get_jira_client, JiraToolError
from .sprint_tools import _parse_issue

logger = logging.getLogger(__name__)


def get_sprint_velocity(board_id: int, n_sprints: int = 5) -> str:
    """
    MCP tool: Return velocity records for the last N closed sprints on a board.
    Velocity = completed_points / committed_points * 100 (%).
    Returns JSON array of VelocityRecord objects.
    """
    try:
        client = get_jira_client()
        closed_sprints = client.get_board_sprints(board_id, state="closed", limit=n_sprints)

        records: list[VelocityRecord] = []
        for sprint in closed_sprints:
            sprint_id = sprint["id"]
            sprint_name = sprint.get("name", f"Sprint {sprint_id}")

            raw_issues = client.get_sprint_issues(sprint_id)
            issues = [_parse_issue(r) for r in raw_issues]

            committed = sum(i.story_points or 0 for i in issues)
            completed = sum(
                i.story_points or 0 for i in issues
                if i.status.value == "Done"
            )
            velocity = round((completed / committed * 100), 1) if committed > 0 else 0.0

            records.append(VelocityRecord(
                sprint_id=sprint_id,
                sprint_name=sprint_name,
                committed_points=round(committed, 1),
                completed_points=round(completed, 1),
                velocity=velocity,
            ))

        return json.dumps([r.model_dump() for r in records])
    except JiraToolError as e:
        logger.error("get_sprint_velocity failed: %s", e)
        return json.dumps({"error": str(e)})
