from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class IssueStatus(str, Enum):
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    IN_REVIEW = "In Review"
    DONE = "Done"
    BLOCKED = "Blocked"


class IssueType(str, Enum):
    STORY = "Story"
    BUG = "Bug"
    TASK = "Task"
    EPIC = "Epic"
    SUBTASK = "Sub-task"


class SprintIssue(BaseModel):
    key: str
    summary: str
    issue_type: IssueType
    status: IssueStatus
    assignee: Optional[str] = None
    story_points: Optional[float] = None
    priority: str = "Medium"
    labels: list[str] = Field(default_factory=list)
    epic_name: Optional[str] = None
    updated: Optional[datetime] = None
    created: Optional[datetime] = None
    due_date: Optional[datetime] = None
    is_blocked: bool = False
    blocker_reason: Optional[str] = None


class SprintStatus(BaseModel):
    sprint_id: int
    sprint_name: str
    board_id: int
    start_date: datetime
    end_date: datetime
    goal: Optional[str] = None
    state: str  # "active" | "closed" | "future"
    total_issues: int
    completed_issues: int
    in_progress_issues: int
    todo_issues: int
    blocked_issues: int
    total_story_points: float = 0.0
    completed_story_points: float = 0.0
    remaining_story_points: float = 0.0
    completion_percentage: float = 0.0
    issues: list[SprintIssue] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class SprintSummary(BaseModel):
    """Lightweight sprint snapshot embedded in WeeklyRecap."""
    sprint_id: int
    sprint_name: str
    completion_percentage: float
    velocity: float
    blockers_count: int
    days_remaining: int
