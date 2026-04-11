"""
SYNTHESIZE node: Uses the LLM (Claude) to convert raw tool results into
structured SprintStatus or WeeklyRecap objects.
"""
import json
import logging
from datetime import datetime, date, timedelta

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from ..state import AgentState, WorkflowMode
from ..prompts import SPRINT_STATUS_FORMAT, WEEKLY_RECAP_FORMAT
from ...config import get_settings
from ...models import (
    SprintStatus, SprintIssue, SprintSummary,
    IssueStatus, IssueType,
    BlockerItem, BlockerReport, BlockerSeverity,
    TeamMember, MemberWorkload, TeamWorkload,
    VelocityRecord, RecapSection, WeeklyRecap,
)

logger = logging.getLogger(__name__)


def _get_llm() -> ChatAnthropic:
    settings = get_settings()
    return ChatAnthropic(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        anthropic_api_key=settings.anthropic_api_key,
    )


def _build_sprint_status_from_results(tool_results: dict, board_id: int, sprint_id: int) -> SprintStatus:
    """Reconstruct SprintStatus from raw MCP tool results (without LLM)."""
    sprint_raw = json.loads(tool_results.get("get_active_sprint", "{}"))
    issues_raw = json.loads(tool_results.get("get_sprint_issues", "[]"))
    if isinstance(issues_raw, dict) and "error" in issues_raw:
        issues_raw = []

    issues = []
    for i in issues_raw:
        try:
            issues.append(SprintIssue(**i))
        except Exception:
            pass

    done = sum(1 for i in issues if i.status == IssueStatus.DONE)
    in_prog = sum(1 for i in issues if i.status == IssueStatus.IN_PROGRESS)
    todo = sum(1 for i in issues if i.status == IssueStatus.TODO)
    blocked = sum(1 for i in issues if i.is_blocked)
    total_pts = sum(i.story_points or 0 for i in issues)
    done_pts = sum(i.story_points or 0 for i in issues if i.status == IssueStatus.DONE)
    pct = round(done / len(issues) * 100, 1) if issues else 0.0

    now = datetime.utcnow()
    return SprintStatus(
        sprint_id=sprint_raw.get("sprint_id", sprint_id),
        sprint_name=sprint_raw.get("sprint_name", f"Sprint {sprint_id}"),
        board_id=board_id,
        start_date=datetime.fromisoformat(sprint_raw["start_date"]) if sprint_raw.get("start_date") else now,
        end_date=datetime.fromisoformat(sprint_raw["end_date"]) if sprint_raw.get("end_date") else now,
        goal=sprint_raw.get("goal"),
        state=sprint_raw.get("state", "active"),
        total_issues=len(issues),
        completed_issues=done,
        in_progress_issues=in_prog,
        todo_issues=todo,
        blocked_issues=blocked,
        total_story_points=round(total_pts, 1),
        completed_story_points=round(done_pts, 1),
        remaining_story_points=round(total_pts - done_pts, 1),
        completion_percentage=pct,
        issues=issues,
    )


def synthesize_node(state: AgentState) -> AgentState:
    """
    Call the LLM to generate the report markdown, then populate structured output.
    For SprintStatus: also reconstruct the Pydantic object from tool results.
    For WeeklyRecap: build structured object + LLM-generated markdown.
    """
    mode = state["mode"]
    tool_results = state["tool_results"]
    board_id = state["board_id"]
    sprint_id = state.get("sprint_id") or 0

    # Build context string for LLM
    context_parts = []
    for tool_name, result in tool_results.items():
        context_parts.append(f"### {tool_name} result:\n{result}")
    context = "\n\n".join(context_parts)

    format_prompt = SPRINT_STATUS_FORMAT if mode == WorkflowMode.SPRINT_STATUS else WEEKLY_RECAP_FORMAT

    prompt = (
        f"Here are the Jira data results from the MCP tools:\n\n{context}\n\n"
        f"Now generate the report in this format:\n{format_prompt}"
    )

    try:
        llm = _get_llm()
        messages = state["messages"] + [HumanMessage(content=prompt)]
        response = llm.invoke(messages)
        markdown = response.content

        if mode == WorkflowMode.SPRINT_STATUS:
            sprint_status = _build_sprint_status_from_results(tool_results, board_id, sprint_id)
            # Attach LLM markdown as a special field (stored in fetched_at comment — we use raw)
            return {
                **state,
                "sprint_status": sprint_status,
                "messages": messages + [response],
                "_report_markdown": markdown,  # carried forward for delivery
            }

        else:  # WEEKLY_RECAP
            sprint_raw = json.loads(tool_results.get("get_active_sprint", "{}"))
            velocity_raw = json.loads(tool_results.get("get_sprint_velocity", "[]"))
            blockers_raw = json.loads(tool_results.get("get_blockers", "{}"))
            workload_raw = json.loads(tool_results.get("get_team_workload", "{}"))

            velocity_records = []
            if isinstance(velocity_raw, list):
                for v in velocity_raw:
                    try:
                        velocity_records.append(VelocityRecord(**v))
                    except Exception:
                        pass

            avg_velocity = (
                sum(v.velocity for v in velocity_records) / len(velocity_records)
                if velocity_records else 0.0
            )

            now = datetime.utcnow()
            end_date_str = sprint_raw.get("end_date")
            end_dt = datetime.fromisoformat(end_date_str) if end_date_str else now
            days_remaining = max(0, (end_dt - now).days)

            sprint_summary = SprintSummary(
                sprint_id=sprint_raw.get("sprint_id", sprint_id),
                sprint_name=sprint_raw.get("sprint_name", f"Sprint {sprint_id}"),
                completion_percentage=sprint_raw.get("completion_percentage", 0.0),
                velocity=round(avg_velocity, 1),
                blockers_count=blockers_raw.get("total_blockers", 0) if isinstance(blockers_raw, dict) else 0,
                days_remaining=days_remaining,
            )

            today = date.today()
            recap = WeeklyRecap(
                week_start=today - timedelta(days=today.weekday()),
                week_end=today,
                sprint_summary=sprint_summary,
                executive_summary="",  # filled from markdown parse
                velocity_trend=velocity_records,
                raw_markdown=markdown,
            )

            return {
                **state,
                "weekly_recap": recap,
                "messages": messages + [response],
                "_report_markdown": markdown,
            }

    except Exception as exc:
        logger.error("SYNTHESIZE node failed: %s", exc)
        return {**state, "error": f"LLM synthesis failed: {exc}"}
