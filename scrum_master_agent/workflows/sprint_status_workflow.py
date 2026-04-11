"""
Sprint Status workflow — on-demand entry point.

Usage:
    python -m scrum_master_agent.workflows.sprint_status_workflow --board-id 1
    python -m scrum_master_agent.workflows.sprint_status_workflow --board-id 1 --delivery slack
"""
import sys
import json
import logging
import argparse

from ..agent import compiled_graph, WorkflowMode, AgentState
from ..models import SprintStatus
from ..config import get_settings

logger = logging.getLogger(__name__)


def run_sprint_status_query(
    board_id: int,
    delivery_target: str = "return",
) -> SprintStatus | None:
    """
    Run the Sprint Status agent workflow.

    Args:
        board_id: Jira board ID to query.
        delivery_target: "return" (default) | "slack" | "confluence"

    Returns:
        SprintStatus if successful, None on hard error.
    """
    initial_state: AgentState = {
        "mode": WorkflowMode.SPRINT_STATUS,
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
        logger.error("Sprint status workflow failed: %s", final_state["error"])
        return None

    return final_state.get("sprint_status")


def cli():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="Scrum Master Agent — Sprint Status")
    parser.add_argument("--board-id", type=int, default=None)
    parser.add_argument("--delivery", choices=["return", "slack", "confluence"], default="return")
    args = parser.parse_args()

    board_id = args.board_id or get_settings().jira_board_id
    result = run_sprint_status_query(board_id=board_id, delivery_target=args.delivery)

    if result:
        print(result.model_dump_json(indent=2))
    else:
        print("ERROR: Sprint status query failed. Check logs.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()
