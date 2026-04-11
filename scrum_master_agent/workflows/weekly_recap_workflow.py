"""
Weekly Recap workflow — scheduled and on-demand entry point.

Usage:
    python -m scrum_master_agent.workflows.weekly_recap_workflow --board-id 1
    python -m scrum_master_agent.workflows.weekly_recap_workflow --board-id 1 --delivery slack --dry-run
"""
import sys
import logging
import argparse

from ..agent import compiled_graph, WorkflowMode, AgentState
from ..models import WeeklyRecap
from ..config import get_settings

logger = logging.getLogger(__name__)


def run_weekly_recap(
    board_id: int,
    delivery_target: str = "return",
) -> WeeklyRecap | None:
    """
    Run the Weekly Recap agent workflow.

    Args:
        board_id: Jira board ID to query.
        delivery_target: "return" | "slack" | "confluence"

    Returns:
        WeeklyRecap if successful, None on hard error.
    """
    initial_state: AgentState = {
        "mode": WorkflowMode.WEEKLY_RECAP,
        "board_id": board_id,
        "sprint_id": None,
        "messages": [],
        "tool_calls_planned": [],
        "tool_results": {},
        "sprint_status": None,
        "weekly_recap": None,
        "delivery_target": delivery_target,
        "error": None,
        "retry_count": 0,
    }

    final_state = compiled_graph.invoke(initial_state)

    if final_state.get("error"):
        logger.error("Weekly recap workflow failed: %s", final_state["error"])
        return None

    return final_state.get("weekly_recap")


def cli():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="Scrum Master Agent — Weekly Recap")
    parser.add_argument("--board-id", type=int, default=None)
    parser.add_argument("--delivery", choices=["return", "slack", "confluence"], default="return")
    parser.add_argument("--dry-run", action="store_true", help="Run without posting to Slack/Confluence")
    args = parser.parse_args()

    board_id = args.board_id or get_settings().jira_board_id
    delivery = "return" if args.dry_run else args.delivery

    result = run_weekly_recap(board_id=board_id, delivery_target=delivery)

    if result:
        if args.dry_run:
            print("=== DRY RUN — Weekly Recap Markdown ===")
            print(result.raw_markdown or "(no markdown generated)")
        else:
            print(result.model_dump_json(indent=2))
    else:
        print("ERROR: Weekly recap failed. Check logs.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()
