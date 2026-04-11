"""
Slack delivery — posts Sprint Status and Weekly Recap reports via Slack webhook.
Uses Slack Block Kit for rich formatting.
"""
import logging
from datetime import datetime
from slack_sdk.webhook import WebhookClient
from slack_sdk.errors import SlackApiError

from ..config import get_settings
from ..models import SprintStatus, WeeklyRecap

logger = logging.getLogger(__name__)


def _progress_bar(pct: float, width: int = 20) -> str:
    """Return a text-based progress bar, e.g. '████████░░░░ 40%'."""
    filled = int(pct / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"`{bar}` {pct:.0f}%"


class SlackDelivery:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = WebhookClient(settings.slack_webhook_url)
        self._channel = settings.slack_channel

    def post_sprint_status(self, status: SprintStatus, markdown: str) -> bool:
        """Post a Sprint Status report to Slack."""
        blocks = self._format_sprint_blocks(status, markdown)
        try:
            response = self._client.send(blocks=blocks, text=f"Sprint Status: {status.sprint_name}")
            if response.status_code != 200:
                logger.error("Slack post failed: %s", response.body)
                return False
            logger.info("Sprint status posted to Slack")
            return True
        except SlackApiError as e:
            logger.error("Slack API error: %s", e)
            return False

    def post_weekly_recap(self, recap: WeeklyRecap, markdown: str) -> bool:
        """Post a Weekly Recap to Slack."""
        blocks = self._format_recap_blocks(recap, markdown)
        sprint_name = recap.sprint_summary.sprint_name
        try:
            response = self._client.send(blocks=blocks, text=f"Weekly Recap: {sprint_name}")
            if response.status_code != 200:
                logger.error("Slack post failed: %s", response.body)
                return False
            logger.info("Weekly recap posted to Slack")
            return True
        except SlackApiError as e:
            logger.error("Slack API error: %s", e)
            return False

    def _format_sprint_blocks(self, status: SprintStatus, markdown: str) -> list[dict]:
        """Build Slack Block Kit payload for Sprint Status."""
        days_remaining = max(0, (status.end_date - datetime.utcnow()).days)
        health_emoji = ":white_check_mark:" if status.completion_percentage >= 70 else (
            ":warning:" if status.completion_percentage >= 40 else ":red_circle:"
        )

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{health_emoji} Sprint Status: {status.sprint_name}"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Days Remaining:* {days_remaining}"},
                    {"type": "mrkdwn", "text": f"*Total Issues:* {status.total_issues}"},
                    {"type": "mrkdwn", "text": f"*Completed:* {status.completed_issues} ({status.completion_percentage:.0f}%)"},
                    {"type": "mrkdwn", "text": f"*Blocked:* {status.blocked_issues}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Progress:* {_progress_bar(status.completion_percentage)}\n"
                            f"*Story Points:* {status.completed_story_points}/{status.total_story_points}",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": markdown[:2900]},  # Slack 3000-char limit
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"}],
            },
        ]
        return blocks

    def _format_recap_blocks(self, recap: WeeklyRecap, markdown: str) -> list[dict]:
        """Build Slack Block Kit payload for Weekly Recap."""
        summary = recap.sprint_summary
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f":bar_chart: Weekly Recap — {summary.sprint_name}"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Week:* {recap.week_start} → {recap.week_end}"},
                    {"type": "mrkdwn", "text": f"*Velocity:* {summary.velocity}%"},
                    {"type": "mrkdwn", "text": f"*Completion:* {summary.completion_percentage:.0f}%"},
                    {"type": "mrkdwn", "text": f"*Blockers:* {summary.blockers_count}"},
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": markdown[:2900]},
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"Generated at {recap.generated_at.strftime('%Y-%m-%d %H:%M UTC')}"}],
            },
        ]
        return blocks
