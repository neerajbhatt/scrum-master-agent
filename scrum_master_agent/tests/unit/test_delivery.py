"""Unit tests for Slack delivery formatting."""
import pytest
from datetime import datetime, date, timedelta, timezone
from unittest.mock import patch, MagicMock

from scrum_master_agent.models import (
    SprintStatus, SprintSummary, WeeklyRecap
)
from scrum_master_agent.delivery.slack_delivery import SlackDelivery, _progress_bar


class TestProgressBar:
    def test_full_bar(self):
        bar = _progress_bar(100)
        assert "100" in bar
        assert "░" not in bar

    def test_empty_bar(self):
        bar = _progress_bar(0)
        assert "0" in bar
        assert "█" not in bar

    def test_partial_bar(self):
        bar = _progress_bar(50)
        assert "█" in bar
        assert "░" in bar


class TestSlackDelivery:
    @pytest.fixture
    def delivery(self, mock_slack):
        with patch("scrum_master_agent.delivery.slack_delivery.get_settings") as mock_settings:
            settings = MagicMock()
            settings.slack_webhook_url = "https://hooks.slack.com/test"
            settings.slack_channel = "#test"
            mock_settings.return_value = settings
            yield SlackDelivery()

    @pytest.fixture
    def sample_sprint_status(self):
        now = datetime.now(timezone.utc)
        return SprintStatus(
            sprint_id=42,
            sprint_name="Sprint 7",
            board_id=1,
            start_date=now - timedelta(days=5),
            end_date=now + timedelta(days=9),
            goal="Ship auth",
            state="active",
            total_issues=7,
            completed_issues=2,
            in_progress_issues=2,
            todo_issues=2,
            blocked_issues=1,
            total_story_points=31.0,
            completed_story_points=10.0,
            completion_percentage=28.6,
        )

    def test_post_sprint_status_returns_true(self, delivery, sample_sprint_status, mock_slack):
        result = delivery.post_sprint_status(sample_sprint_status, "## Sprint Status\nAll good.")
        assert result is True

    def test_format_sprint_blocks_has_header(self, delivery, sample_sprint_status):
        blocks = delivery._format_sprint_blocks(sample_sprint_status, "## Report")
        header_blocks = [b for b in blocks if b.get("type") == "header"]
        assert len(header_blocks) == 1
        assert "Sprint 7" in header_blocks[0]["text"]["text"]

    def test_post_weekly_recap_returns_true(self, delivery, mock_slack):
        summary = SprintSummary(
            sprint_id=42, sprint_name="Sprint 7",
            completion_percentage=50.0, velocity=80.0,
            blockers_count=1, days_remaining=5,
        )
        recap = WeeklyRecap(
            week_start=date(2026, 4, 6),
            week_end=date(2026, 4, 11),
            sprint_summary=summary,
            executive_summary="Sprint is on track.",
        )
        result = delivery.post_weekly_recap(recap, "## Weekly Recap\nContent here.")
        assert result is True
