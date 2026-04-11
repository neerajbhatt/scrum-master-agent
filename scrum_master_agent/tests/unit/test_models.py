"""Unit tests for Pydantic data models — edge cases."""
import pytest
from datetime import datetime, date

from scrum_master_agent.models import (
    SprintIssue, SprintStatus, IssueStatus, IssueType,
    BlockerItem, BlockerSeverity,
    TeamMember, MemberWorkload,
    VelocityRecord,
    RecapSection, WeeklyRecap, SprintSummary,
)


class TestSprintIssue:
    def test_defaults(self):
        issue = SprintIssue(
            key="PROJ-1",
            summary="Test",
            issue_type=IssueType.STORY,
            status=IssueStatus.TODO,
        )
        assert issue.assignee is None
        assert issue.story_points is None
        assert issue.is_blocked is False
        assert issue.labels == []

    def test_blocked_flag(self):
        issue = SprintIssue(
            key="PROJ-2",
            summary="Blocked task",
            issue_type=IssueType.TASK,
            status=IssueStatus.BLOCKED,
            is_blocked=True,
        )
        assert issue.is_blocked is True


class TestBlockerItem:
    def test_default_severity_is_high(self):
        item = BlockerItem(issue_key="PROJ-1", summary="blocker")
        assert item.severity == BlockerSeverity.HIGH

    def test_critical_severity(self):
        item = BlockerItem(
            issue_key="PROJ-2",
            summary="critical blocker",
            severity=BlockerSeverity.CRITICAL,
        )
        assert item.severity == BlockerSeverity.CRITICAL


class TestVelocityRecord:
    def test_zero_velocity_when_no_committed(self):
        # velocity=0 is valid when team committed nothing
        record = VelocityRecord(
            sprint_id=1,
            sprint_name="Sprint 1",
            committed_points=0,
            completed_points=0,
            velocity=0.0,
        )
        assert record.velocity == 0.0


class TestWeeklyRecap:
    def test_minimal_construction(self):
        summary = SprintSummary(
            sprint_id=1,
            sprint_name="Sprint 1",
            completion_percentage=50.0,
            velocity=80.0,
            blockers_count=2,
            days_remaining=5,
        )
        recap = WeeklyRecap(
            week_start=date(2026, 4, 6),
            week_end=date(2026, 4, 11),
            sprint_summary=summary,
            executive_summary="Sprint is on track.",
        )
        assert recap.sprint_summary.sprint_name == "Sprint 1"
        assert recap.risks == []
        assert recap.recommendations == []
