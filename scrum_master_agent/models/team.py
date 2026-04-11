from typing import Optional
from pydantic import BaseModel, Field


class TeamMember(BaseModel):
    account_id: str
    display_name: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None


class MemberWorkload(BaseModel):
    member: TeamMember
    assigned_issues: int
    completed_issues: int
    in_progress_issues: int
    total_story_points: float = 0.0
    completed_story_points: float = 0.0
    completion_rate: float = 0.0  # completed / assigned


class TeamWorkload(BaseModel):
    sprint_id: int
    members: list[MemberWorkload] = Field(default_factory=list)
    unassigned_issues: int = 0
    total_members: int = 0


class VelocityRecord(BaseModel):
    sprint_id: int
    sprint_name: str
    committed_points: float
    completed_points: float
    velocity: float  # completed_points / committed_points * 100 (capped at 100)
