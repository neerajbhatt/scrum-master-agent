from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BlockerSeverity(str, Enum):
    CRITICAL = "Critical"   # Blocking multiple people / sprint goal
    HIGH = "High"           # Blocking one person, no workaround
    MEDIUM = "Medium"       # Has partial workaround
    LOW = "Low"             # Minor impediment


class BlockerItem(BaseModel):
    issue_key: str
    summary: str
    assignee: Optional[str] = None
    severity: BlockerSeverity = BlockerSeverity.HIGH
    blocked_since: Optional[datetime] = None
    blocker_description: Optional[str] = None
    days_blocked: Optional[int] = None
    suggested_action: Optional[str] = None  # filled by LLM synthesis


class BlockerReport(BaseModel):
    sprint_id: int
    sprint_name: str
    total_blockers: int
    critical_blockers: int
    items: list[BlockerItem] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
