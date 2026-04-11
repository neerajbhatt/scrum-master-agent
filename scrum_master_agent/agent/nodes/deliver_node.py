"""
DELIVER node: Routes the generated report to the appropriate output channel.
"""
import logging

from ..state import AgentState, WorkflowMode
from ...delivery.slack_delivery import SlackDelivery

logger = logging.getLogger(__name__)


def deliver_node(state: AgentState) -> AgentState:
    """Post report to Slack, Confluence, or return in-state (for API callers)."""
    target = state.get("delivery_target", "return")
    mode = state["mode"]
    markdown = state.get("_report_markdown", "")

    if target == "return":
        # Caller will read sprint_status or weekly_recap from state directly
        logger.info("DELIVER: returning result in-state (no external delivery)")
        return state

    if target == "slack":
        try:
            delivery = SlackDelivery()
            if mode == WorkflowMode.SPRINT_STATUS and state.get("sprint_status"):
                delivery.post_sprint_status(state["sprint_status"], markdown)
            elif mode == WorkflowMode.WEEKLY_RECAP and state.get("weekly_recap"):
                delivery.post_weekly_recap(state["weekly_recap"], markdown)
            else:
                logger.warning("DELIVER: no structured output to deliver")
        except Exception as exc:
            logger.error("Slack delivery failed: %s", exc)
            return {**state, "error": f"Slack delivery failed: {exc}"}

    if target == "confluence":
        try:
            from ...delivery.confluence_delivery import ConfluenceDelivery
            delivery = ConfluenceDelivery()
            if mode == WorkflowMode.WEEKLY_RECAP and state.get("weekly_recap"):
                delivery.publish_recap(state["weekly_recap"], markdown)
        except Exception as exc:
            logger.error("Confluence delivery failed: %s", exc)
            return {**state, "error": f"Confluence delivery failed: {exc}"}

    return state
