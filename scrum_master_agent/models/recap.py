from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field

from .sprint import SprintSummary
from .blockers import BlockerReport
from .team import TeamWorkload, VelocityRecord


class RecapSection(BaseModel):
    title: str
    content: str  # Markdown formatted


class WeeklyRecap(BaseModel):
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    week_start: date
    week_end: date
    sprint_summary: SprintSummary
    executive_summary: str  # 2-3 sentence LLM-generated summary
    sections: list[RecapSection] = Field(default_factory=list)
    blockers_report: Optional[BlockerReport] = None
    team_workload: Optional[TeamWorkload] = None
    velocity_trend: list[VelocityRecord] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    raw_markdown: Optional[str] = None  # final rendered output for delivery
