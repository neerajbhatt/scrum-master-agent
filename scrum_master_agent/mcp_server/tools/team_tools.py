"""
MCP tool: get_team_workload — summarise per-member workload for a sprint.
"""
import json
import logging
from collections import defaultdict

from ...models import TeamMember, MemberWorkload, TeamWorkload, IssueStatus
from ..jira_client import get_jira_client, JiraToolError
from .sprint_tools import _parse_issue

logger = logging.getLogger(__name__)


def get_team_workload(sprint_id: int) -> str:
    """
    MCP tool: Return per-member workload summary for a sprint.
    Aggregates assigned/completed/in-progress issues and story points per assignee.
    Returns JSON-serialised TeamWorkload.
    """
    try:
        client = get_jira_client()
        raw_issues = client.get_sprint_issues(sprint_id)
        issues = [_parse_issue(r) for r in raw_issues]

        # Group by assignee
        by_member: dict[str, dict] = defaultdict(lambda: {
            "display_name": "",
            "account_id": "",
            "assigned": [],
        })

        unassigned = 0
        # Pull raw assignee account IDs too
        raw_by_key = {r["key"]: r for r in raw_issues}

        for issue in issues:
            if not issue.assignee:
                unassigned += 1
                continue
            raw = raw_by_key.get(issue.key, {})
            assignee_data = raw.get("fields", {}).get("assignee") or {}
            account_id = assignee_data.get("accountId", issue.assignee)
            by_member[account_id]["display_name"] = issue.assignee
            by_member[account_id]["account_id"] = account_id
            by_member[account_id]["assigned"].append(issue)

        workloads: list[MemberWorkload] = []
        for account_id, data in by_member.items():
            member_issues = data["assigned"]
            done = [i for i in member_issues if i.status == IssueStatus.DONE]
            in_prog = [i for i in member_issues if i.status == IssueStatus.IN_PROGRESS]
            total_pts = sum(i.story_points or 0 for i in member_issues)
            done_pts = sum(i.story_points or 0 for i in done)
            rate = (len(done) / len(member_issues)) if member_issues else 0.0

            workloads.append(MemberWorkload(
                member=TeamMember(
                    account_id=account_id,
                    display_name=data["display_name"],
                ),
                assigned_issues=len(member_issues),
                completed_issues=len(done),
                in_progress_issues=len(in_prog),
                total_story_points=round(total_pts, 1),
                completed_story_points=round(done_pts, 1),
                completion_rate=round(rate, 2),
            ))

        workload = TeamWorkload(
            sprint_id=sprint_id,
            members=workloads,
            unassigned_issues=unassigned,
            total_members=len(workloads),
        )
        return workload.model_dump_json()
    except JiraToolError as e:
        logger.error("get_team_workload failed: %s", e)
        return json.dumps({"error": str(e)})
