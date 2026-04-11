"""
AgentState — the shared state dict that flows through all LangGraph nodes.
"""
from enum import Enum
from typing import Any, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage

from ..models import SprintStatus, WeeklyRecap


class WorkflowMode(str, Enum):
    SPRINT_STATUS = "sprint_status"
    WEEKLY_RECAP = "weekly_recap"


class AgentState(TypedDict):
    mode: WorkflowMode
    board_id: int
    sprint_id: Optional[int]

    # LLM conversation history
    messages: list[BaseMessage]

    # Tool orchestration
    tool_calls_planned: list[str]      # tool names the PLAN node decided to call
    tool_results: dict[str, Any]       # tool_name → JSON string result

    # Structured outputs (populated by SYNTHESIZE node)
    sprint_status: Optional[SprintStatus]
    weekly_recap: Optional[WeeklyRecap]

    # Delivery
    delivery_target: str               # "slack" | "confluence" | "return"

    # Error handling
    error: Optional[str]
    retry_count: int
