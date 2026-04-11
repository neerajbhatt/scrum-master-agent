# Low-Level Design (LLD)
# Scrum Master Digital Worker — Sprint Status Agent

**Version:** 1.0
**Date:** 2026-04-11
**Author:** Scrum Master Agent Team
**Status:** Implemented

---

## Table of Contents

1. [Purpose & Scope](#1-purpose--scope)
2. [System Context](#2-system-context)
3. [Component Architecture](#3-component-architecture)
4. [File & Module Structure](#4-file--module-structure)
5. [Data Models](#5-data-models)
6. [MCP Server — Tool Specifications](#6-mcp-server--tool-specifications)
7. [Jira Client Layer](#7-jira-client-layer)
8. [LangGraph Agent — State Machine](#8-langgraph-agent--state-machine)
9. [Agent Node Specifications](#9-agent-node-specifications)
10. [Agent Prompts](#10-agent-prompts)
11. [LangChain-MCP Bridge](#11-langchain-mcp-bridge)
12. [Delivery Layer](#12-delivery-layer)
13. [Scheduler](#13-scheduler)
14. [Workflow Entry Points](#14-workflow-entry-points)
15. [Configuration & Secrets](#15-configuration--secrets)
16. [Error Handling & Retry Strategy](#16-error-handling--retry-strategy)
17. [Sequence Diagrams](#17-sequence-diagrams)
18. [Interface Contracts](#18-interface-contracts)
19. [Testing Strategy](#19-testing-strategy)
20. [Dependencies](#20-dependencies)
21. [Key Design Decisions](#21-key-design-decisions)

---

## 1. Purpose & Scope

### Problem Statement
Scrum Masters spend 30–60 minutes per sprint manually collecting Jira data, formatting it into
status reports, and distributing recaps to stakeholders. This is repetitive, error-prone, and
delays visibility into sprint health.

### Solution
An autonomous **Scrum Master Digital Worker** — a LangGraph-orchestrated agent that:
- Reads Jira sprint data through a dedicated MCP Server (read-only, blast radius = Low)
- Uses Claude Sonnet to reason over the data and generate structured reports
- Delivers formatted Sprint Status and Weekly Recap reports to Slack (and optionally Confluence)

### Operational Modes

| Mode | Trigger | Output |
|------|---------|--------|
| **Sprint Status** | On-demand (CLI, API, Slack command) | Structured snapshot: progress, blockers, team workload |
| **Weekly Recap** | Scheduled (every Friday 17:00 via APScheduler) | Full narrative: velocity trend, risks, recommendations |

### Core Contract
> The agent **never calls Jira directly**. All Jira access is mediated through MCP Server tools.
> This enforces a clean boundary and enables tool-level testing, retries, and observability.

---

## 2. System Context

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         External Systems                                 │
│                                                                         │
│   ┌──────────────────┐    ┌──────────────────┐    ┌─────────────────┐  │
│   │   Jira Cloud     │    │   Slack           │    │   Confluence    │  │
│   │  (read-only)     │    │  (webhook out)    │    │  (page create)  │  │
│   └────────▲─────────┘    └────────▲──────────┘    └────────▲────────┘  │
└────────────│──────────────────────│─────────────────────────│───────────┘
             │                      │                          │
┌────────────│──────────────────────│─────────────────────────│───────────┐
│            │      Scrum Master Digital Worker                │           │
│            │                      │                          │           │
│  ┌─────────┴──────┐  ┌────────────┴──────────────────────────┴───────┐  │
│  │   MCP Server   │  │              LangGraph Agent                  │  │
│  │  (Jira Tools)  │◀─│  PLAN → FETCH → SYNTHESIZE → DELIVER          │  │
│  └────────────────┘  └───────────────────────────────────────────────┘  │
│                                       ▲                                  │
│                       ┌──────────────┴──────────────┐                   │
│                       │  APScheduler   │  CLI / API  │                   │
│                       │  (weekly)      │  (on-demand)│                   │
│                       └─────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
```

**Actors:**
- **Scrum Master / User** — triggers on-demand queries; reviews generated reports
- **APScheduler** — fires the weekly recap job automatically every Friday
- **Jira Cloud** — source of truth for sprint/issue data (read-only access)
- **Slack** — primary delivery channel (incoming webhook)
- **Confluence** — optional secondary delivery (page creation)

---

## 3. Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Scrum Master Digital Worker                           │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                        LangGraph Agent                             │ │
│  │                                                                    │ │
│  │  ┌──────────┐    ┌──────────┐    ┌────────────┐    ┌──────────┐  │ │
│  │  │  PLAN    │───▶│  FETCH   │───▶│ SYNTHESIZE │───▶│ DELIVER  │  │ │
│  │  │ node     │    │  node    │    │   node     │    │  node    │  │ │
│  │  │          │    │          │    │            │    │          │  │ │
│  │  │ Decides  │    │ Calls    │    │ LLM        │    │ Slack /  │  │ │
│  │  │ tools to │    │ MCP in   │    │ generates  │    │ Conflu.  │  │ │
│  │  │ invoke   │    │ parallel │    │ report     │    │ / return │  │ │
│  │  └──────────┘    └──────────┘    └────────────┘    └──────────┘  │ │
│  │        ▲               │                                           │ │
│  │        │ retry         │ MCP Tool Calls                            │ │
│  │        └───────────────┘ (JSON-RPC 2.0 over stdio)                │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│  ┌─────────────────────────────────▼───────────────────────────────┐    │
│  │                    MCP Server (stdio / SSE)                     │    │
│  │                                                                 │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │    │
│  │  │ get_active_sprint│  │ get_sprint_issues│  │ get_blockers │  │    │
│  │  └──────────────────┘  └──────────────────┘  └──────────────┘  │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │    │
│  │  │get_team_workload │  │get_sprint_velocity│  │get_burndown  │  │    │
│  │  └──────────────────┘  └──────────────────┘  └──────────────┘  │    │
│  │  ┌──────────────────┐                                           │    │
│  │  │search_issues_jql │  JiraClient singleton (atlassian-python)  │    │
│  │  └──────────────────┘                                           │    │
│  └─────────────────────────────────┬───────────────────────────────┘    │
│                                    │ HTTPS REST                          │
│  ┌─────────────────────────────────▼───────────────────────────────┐    │
│  │                      Jira REST API                              │    │
│  │  GET /agile/1.0/board/{id}/sprint   GET /agile/1.0/sprint/{id} │    │
│  │  POST /api/3/search (JQL)                                       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌────────────────┐  ┌────────────────────┐  ┌───────────────────────┐ │
│  │ Delivery Layer │  │  Config / Settings  │  │  APScheduler          │ │
│  │ Slack Block Kit│  │  Pydantic + .env   │  │  Friday 17:00 cron    │ │
│  │ Confluence API │  │  Singleton pattern │  │  --run-now flag       │ │
│  └────────────────┘  └────────────────────┘  └───────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. File & Module Structure

```
scrum_master_agent/
│
├── pyproject.toml                        # Project metadata + all dependencies
├── .env.example                          # Template for required env vars
├── LLD.md                                # This document
│
├── config/
│   ├── __init__.py
│   └── settings.py                       # Pydantic BaseSettings — single source of truth
│                                         # Loaded once, cached as singleton via get_settings()
│
├── models/                               # All Pydantic data models
│   ├── __init__.py                       # Re-exports all models
│   ├── sprint.py                         # IssueStatus, IssueType, SprintIssue,
│   │                                     #   SprintStatus, SprintSummary
│   ├── blockers.py                       # BlockerSeverity, BlockerItem, BlockerReport
│   ├── team.py                           # TeamMember, MemberWorkload, TeamWorkload,
│   │                                     #   VelocityRecord
│   └── recap.py                          # RecapSection, WeeklyRecap
│
├── mcp_server/                           # MCP Server — Jira tool layer
│   ├── __init__.py
│   ├── server.py                         # MCP Server entry point
│   │                                     #   Registers 7 tools via @app.list_tools /
│   │                                     #   @app.call_tool decorators
│   │                                     #   Runs via stdio_server (dev) or SSE (prod)
│   ├── jira_client.py                    # JiraClient singleton wrapping atlassian-python-api
│   │                                     #   _retry() with exponential backoff
│   │                                     #   get_jira_client() singleton factory
│   └── tools/
│       ├── __init__.py
│       ├── sprint_tools.py               # get_active_sprint, get_sprint_issues,
│       │                                 #   get_sprint_burndown, _parse_issue()
│       ├── blocker_tools.py              # get_blockers (JQL + severity mapping)
│       ├── team_tools.py                 # get_team_workload (groups issues by assignee)
│       ├── velocity_tools.py             # get_sprint_velocity (N closed sprints)
│       └── search_tools.py              # search_issues_by_jql (arbitrary JQL)
│
├── agent/                                # LangGraph agent
│   ├── __init__.py                       # Exports compiled_graph, AgentState, WorkflowMode
│   ├── state.py                          # AgentState TypedDict, WorkflowMode enum
│   ├── graph.py                          # StateGraph definition + compiled_graph
│   │                                     #   Nodes: plan, fetch, synthesize, deliver, error_end
│   │                                     #   Conditional edges with retry logic
│   ├── tools_bridge.py                   # MultiServerMCPClient → LangChain BaseTool list
│   │                                     #   Cached singleton, reset_mcp_tools() for tests
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── plan_node.py                  # Injects tool plan into state messages
│   │   ├── fetch_node.py                 # Runs MCP tools (sprint first, rest parallel)
│   │   ├── synthesize_node.py            # LLM call → SprintStatus or WeeklyRecap
│   │   └── deliver_node.py               # Routes to Slack / Confluence / return
│   └── prompts/
│       ├── __init__.py
│       ├── system_prompt.py              # SYSTEM_PROMPT — Scrum Master persona
│       ├── tool_use_prompt.py            # SPRINT_STATUS_TOOL_PLAN, WEEKLY_RECAP_TOOL_PLAN
│       └── output_format_prompt.py       # SPRINT_STATUS_FORMAT, WEEKLY_RECAP_FORMAT
│
├── delivery/
│   ├── __init__.py
│   ├── slack_delivery.py                 # SlackDelivery class + Block Kit formatting
│   │                                     #   _progress_bar(), post_sprint_status(),
│   │                                     #   post_weekly_recap(), _format_*_blocks()
│   └── confluence_delivery.py            # ConfluenceDelivery.publish_recap() (optional)
│
├── scheduler/
│   ├── __init__.py
│   └── weekly_scheduler.py               # APScheduler BlockingScheduler
│                                         #   weekly_recap_job() → run_weekly_recap()
│                                         #   --run-now flag for immediate execution
│
├── workflows/                            # Public entry points
│   ├── __init__.py
│   ├── sprint_status_workflow.py         # run_sprint_status_query(board_id, delivery_target)
│   │                                     #   → SprintStatus | None
│   │                                     #   cli() with argparse
│   └── weekly_recap_workflow.py          # run_weekly_recap(board_id, delivery_target)
│                                         #   → WeeklyRecap | None
│                                         #   cli() with --dry-run flag
│
└── tests/
    ├── __init__.py
    ├── conftest.py                        # Fixtures: mock_jira_client, mock_slack,
    │                                      #   sample_sprint_raw, sample_issues_raw
    ├── unit/
    │   ├── __init__.py
    │   ├── test_sprint_tools.py           # get_active_sprint, get_sprint_issues,
    │   │                                  #   get_sprint_burndown
    │   ├── test_blocker_tools.py          # get_blockers + severity logic
    │   ├── test_team_tools.py             # get_team_workload + grouping
    │   ├── test_velocity_tools.py         # get_sprint_velocity
    │   ├── test_models.py                 # Pydantic model edge cases
    │   └── test_delivery.py              # Slack formatting + Block Kit
    └── integration/
        ├── __init__.py
        ├── test_sprint_status_workflow.py # Full workflow with mocked MCP + LLM
        └── test_weekly_recap_workflow.py  # Full workflow with mocked MCP + LLM
```

---

## 5. Data Models

All models are Pydantic v2. Serialisation: `.model_dump_json()` / `.model_dump(mode="json")`.

### 5.1 `models/sprint.py`

```
IssueStatus (str, Enum)
  TODO = "To Do"
  IN_PROGRESS = "In Progress"
  IN_REVIEW = "In Review"
  DONE = "Done"
  BLOCKED = "Blocked"

IssueType (str, Enum)
  STORY | BUG | TASK | EPIC | SUBTASK

SprintIssue (BaseModel)
  key:            str              # "PROJ-123"
  summary:        str
  issue_type:     IssueType
  status:         IssueStatus
  assignee:       Optional[str]    # displayName from Jira
  story_points:   Optional[float]  # customfield_10016 or customfield_10028
  priority:       str = "Medium"
  labels:         list[str] = []
  epic_name:      Optional[str]
  updated:        Optional[datetime]
  created:        Optional[datetime]
  due_date:       Optional[datetime]
  is_blocked:     bool = False     # True if status=BLOCKED or flagged or labels contains "blocked"
  blocker_reason: Optional[str]

SprintStatus (BaseModel)
  sprint_id:               int
  sprint_name:             str
  board_id:                int
  start_date:              datetime
  end_date:                datetime
  goal:                    Optional[str]
  state:                   str             # "active" | "closed" | "future"
  total_issues:            int
  completed_issues:        int
  in_progress_issues:      int
  todo_issues:             int
  blocked_issues:          int
  total_story_points:      float = 0.0
  completed_story_points:  float = 0.0
  remaining_story_points:  float = 0.0
  completion_percentage:   float = 0.0    # completed/total * 100
  issues:                  list[SprintIssue] = []
  fetched_at:              datetime = utcnow()

SprintSummary (BaseModel)           # lightweight — embedded in WeeklyRecap
  sprint_id:             int
  sprint_name:           str
  completion_percentage: float
  velocity:              float
  blockers_count:        int
  days_remaining:        int
```

### 5.2 `models/blockers.py`

```
BlockerSeverity (str, Enum)
  CRITICAL = "Critical"    # flagged=Impediment — blocks sprint goal or multiple people
  HIGH     = "High"        # status=Blocked — one person, no workaround
  MEDIUM   = "Medium"      # labels=blocked/impediment — partial workaround exists
  LOW      = "Low"         # minor impediment

BlockerItem (BaseModel)
  issue_key:           str
  summary:             str
  assignee:            Optional[str]
  severity:            BlockerSeverity = HIGH
  blocked_since:       Optional[datetime]
  blocker_description: Optional[str]
  days_blocked:        Optional[int]    # derived from updated timestamp
  suggested_action:    Optional[str]    # filled by LLM in SYNTHESIZE node

BlockerReport (BaseModel)
  sprint_id:        int
  sprint_name:      str
  total_blockers:   int
  critical_blockers: int
  items:            list[BlockerItem] = []
  generated_at:     datetime = utcnow()
```

### 5.3 `models/team.py`

```
TeamMember (BaseModel)
  account_id:   str
  display_name: str
  email:        Optional[str]
  avatar_url:   Optional[str]

MemberWorkload (BaseModel)
  member:                  TeamMember
  assigned_issues:         int
  completed_issues:        int
  in_progress_issues:      int
  total_story_points:      float = 0.0
  completed_story_points:  float = 0.0
  completion_rate:         float = 0.0    # completed_issues / assigned_issues

TeamWorkload (BaseModel)
  sprint_id:         int
  members:           list[MemberWorkload] = []
  unassigned_issues: int = 0
  total_members:     int = 0

VelocityRecord (BaseModel)
  sprint_id:        int
  sprint_name:      str
  committed_points: float
  completed_points: float
  velocity:         float    # completed / committed * 100
```

### 5.4 `models/recap.py`

```
RecapSection (BaseModel)
  title:   str
  content: str    # Markdown formatted section body

WeeklyRecap (BaseModel)
  generated_at:    datetime = utcnow()
  week_start:      date
  week_end:        date
  sprint_summary:  SprintSummary
  executive_summary: str              # 2-3 sentence LLM output
  sections:        list[RecapSection] = []
  blockers_report: Optional[BlockerReport] = None
  team_workload:   Optional[TeamWorkload] = None
  velocity_trend:  list[VelocityRecord] = []
  risks:           list[str] = []
  recommendations: list[str] = []
  raw_markdown:    Optional[str] = None    # full rendered output for delivery
```

---

## 6. MCP Server — Tool Specifications

The MCP Server (`mcp_server/server.py`) runs as a subprocess, exposes 7 tools via JSON-RPC 2.0,
and is consumed by the LangChain-MCP bridge in the agent.

All tools return **JSON strings** (success or `{"error": "..."}` on failure).

### Tool Registry

| Tool Name | Input Args | Returns | Jira Endpoint |
|-----------|-----------|---------|---------------|
| `get_active_sprint` | `board_id: int` | `SprintStatus` JSON | `GET /agile/1.0/board/{id}/sprint?state=active` |
| `get_sprint_issues` | `sprint_id: int`, `status_filter?: list[str]` | `list[SprintIssue]` JSON | `GET /agile/1.0/sprint/{id}/issue` |
| `get_sprint_burndown` | `sprint_id: int` | `{sprint_id, burndown: {date: pts}, total_points}` | Derived from issue `updated` timestamps |
| `get_blockers` | `sprint_id: int`, `board_id: int` | `BlockerReport` JSON | `POST /api/3/search` (JQL) |
| `get_team_workload` | `sprint_id: int` | `TeamWorkload` JSON | Via `get_sprint_issues` + group-by |
| `get_sprint_velocity` | `board_id: int`, `n_sprints: int = 5` | `list[VelocityRecord]` JSON | `GET /agile/1.0/board/{id}/sprint?state=closed` |
| `search_issues_by_jql` | `jql: str`, `max_results: int = 50` | `list[SprintIssue]` JSON | `POST /api/3/search` |

### Blocker Detection Logic (`get_blockers`)

JQL query:
```
sprint = {sprint_id} AND (
  status = "Blocked" OR
  labels in ("blocked", "impediment") OR
  flagged = "Impediment"
)
```

Severity mapping:
```
fields.flagged is set       → BlockerSeverity.CRITICAL
fields.status = "Blocked"  → BlockerSeverity.HIGH
"blocked" or "impediment"
  in fields.labels          → BlockerSeverity.MEDIUM
otherwise                   → BlockerSeverity.LOW
```

### Issue Parsing (`sprint_tools._parse_issue`)

Story points field resolution order:
1. `fields.customfield_10016` (Jira Software standard)
2. `fields.customfield_10028` (older Jira configurations)
3. `fields.story_points` (fallback)

Blocked detection:
```python
is_blocked = (
    status == IssueStatus.BLOCKED
    or bool(fields.get("flagged"))
    or "blocked" in [l.lower() for l in labels]
)
```

---

## 7. Jira Client Layer

**File:** `mcp_server/jira_client.py`

```
JiraClient
  __init__()
    → Jira(url, username=email, password=api_token, cloud=True)

  _retry(fn, *args, max_attempts=3, **kwargs) -> Any
    → Exponential backoff: sleep(2^attempt) on 429/5xx
    → Raises JiraToolError after max_attempts

  get_active_sprint(board_id) -> Optional[dict]
    → get_all_sprints_from_board(board_id, state="active")
    → Returns values[0] or None

  get_sprint_issues(sprint_id, fields=None, max_results=200) -> list[dict]
    → get_sprint_issues(sprint_id, fields=field_str, maxResults=max_results)

  search_jql(jql, fields=None, max_results=100) -> list[dict]
    → jql(jql, fields=field_str, limit=max_results)

  get_board_sprints(board_id, state="closed", limit=5) -> list[dict]
    → get_all_sprints_from_board(board_id, state=state)
    → Returns last `limit` items

  get_board(board_id) -> dict
    → get_board(board_id)

JiraToolError(Exception)
  → Raised after all retries exhausted

get_jira_client() -> JiraClient   # module-level singleton factory
```

**Default fields fetched for issues:**
```
summary, status, assignee, issuetype, priority, labels,
customfield_10016 (story points), customfield_10014 (epic link),
customfield_10020 (sprint), flagged, updated, created, duedate
```

---

## 8. LangGraph Agent — State Machine

### 8.1 AgentState (`agent/state.py`)

```python
class WorkflowMode(str, Enum):
    SPRINT_STATUS = "sprint_status"
    WEEKLY_RECAP  = "weekly_recap"

class AgentState(TypedDict):
    # Input
    mode:                WorkflowMode
    board_id:            int
    sprint_id:           Optional[int]      # resolved by fetch_node

    # LLM conversation history
    messages:            list[BaseMessage]

    # Tool orchestration
    tool_calls_planned:  list[str]          # set by plan_node
    tool_results:        dict[str, Any]     # tool_name → JSON str, set by fetch_node

    # Structured outputs (set by synthesize_node)
    sprint_status:       Optional[SprintStatus]
    weekly_recap:        Optional[WeeklyRecap]

    # Delivery
    delivery_target:     str               # "slack" | "confluence" | "return"

    # Error handling
    error:               Optional[str]
    retry_count:         int
```

### 8.2 Graph Definition (`agent/graph.py`)

```
Nodes:    plan | fetch | synthesize | deliver | error_end
Entry:    plan

Edges:
  plan        → fetch          (always)
  fetch       → synthesize     (if no error)
              → plan           (error, retry_count < 2)
              → error_end      (error, retry_count >= 2)
  synthesize  → deliver        (if no error)
              → error_end      (if error)
  deliver     → END
  error_end   → END

MAX_RETRIES = 2
```

```
 START
   │
   ▼
┌──────┐     ┌───────┐     ┌────────────┐     ┌─────────┐
│ PLAN │────▶│ FETCH │────▶│ SYNTHESIZE │────▶│ DELIVER │──▶ END
└──────┘     └───┬───┘     └────────────┘     └─────────┘
               ◀─┘  (retry, count < 2)
               │
               ▼  (retry exhausted OR synthesis error)
           ┌─────────┐
           │ERROR_END│──▶ END
           └─────────┘
```

---

## 9. Agent Node Specifications

### 9.1 PLAN Node (`agent/nodes/plan_node.py`)

**Responsibility:** Initialise LLM message history and set `tool_calls_planned`.

```
Input state fields used:  mode, board_id
Output state fields set:  tool_calls_planned, messages, error (cleared)

Tool plan by mode:
  SPRINT_STATUS → [get_active_sprint, get_sprint_issues, get_blockers, get_team_workload]
  WEEKLY_RECAP  → [get_active_sprint, get_sprint_issues, get_blockers,
                   get_team_workload, get_sprint_velocity, get_sprint_burndown]

Messages injected:
  1. SystemMessage(SYSTEM_PROMPT)
  2. HumanMessage("Board ID: {id}\nMode: {mode}\n{tool_plan_text}")
```

### 9.2 FETCH Node (`agent/nodes/fetch_node.py`)

**Responsibility:** Execute MCP tool calls. `get_active_sprint` runs first (resolves sprint_id),
remaining tools run in parallel via `asyncio.gather`.

```
Input state fields used:  tool_calls_planned, board_id, sprint_id
Output state fields set:  sprint_id (resolved), tool_results, messages (+ ToolMessages), error

Execution order:
  1. get_active_sprint(board_id)        → resolves sprint_id
  2. asyncio.gather(
       get_sprint_issues(sprint_id),
       get_blockers(sprint_id, board_id),
       get_team_workload(sprint_id),
       [get_sprint_velocity(board_id),  # weekly recap only
        get_sprint_burndown(sprint_id)]
     )

Error handling:
  - Tool errors stored as {"error": "..."} JSON in tool_results
  - Collects ALL errors, joins them into state["error"]
  - Retry logic in graph conditional edge (not in node itself)

Async handling:
  - asyncio.run() for top-level call
  - Falls back to loop.run_until_complete() if already inside event loop
```

### 9.3 SYNTHESIZE Node (`agent/nodes/synthesize_node.py`)

**Responsibility:** Call Claude Sonnet with all tool results and output format prompt.
Reconstruct structured Pydantic objects from the tool results (not from LLM output — LLM
generates the markdown narrative).

```
Input state fields used:  mode, tool_results, board_id, sprint_id, messages
Output state fields set:  sprint_status OR weekly_recap, messages, _report_markdown, error

LLM call:
  Model:   claude-sonnet-4-6 (from Settings)
  Temp:    0.1
  Prompt:  tool results as context + output format template

SprintStatus reconstruction:
  → _build_sprint_status_from_results(tool_results, board_id, sprint_id)
  → Parses issue list, computes aggregates (done/in_prog/todo/blocked counts, pts)
  → Does NOT rely on LLM to produce structured data (deterministic)

WeeklyRecap construction:
  → Builds SprintSummary from sprint + velocity results
  → Populates velocity_trend from get_sprint_velocity result
  → LLM generates raw_markdown which contains all sections
  → executive_summary, risks, recommendations extracted from markdown (or left for LLM)
```

### 9.4 DELIVER Node (`agent/nodes/deliver_node.py`)

**Responsibility:** Route the generated report to the configured delivery target.

```
delivery_target:
  "return"     → No external delivery. Caller reads sprint_status/weekly_recap from state.
  "slack"      → SlackDelivery.post_sprint_status() or post_weekly_recap()
  "confluence" → ConfluenceDelivery.publish_recap() (weekly recap only)

Error handling:
  - Delivery failure sets state["error"] but does NOT crash
  - Structured data still available in state for the caller
```

---

## 10. Agent Prompts

### 10.1 System Prompt

```
You are an expert Scrum Master Digital Worker. Your role is to analyze Jira sprint data
and produce clear, actionable Sprint Status reports and Weekly Recaps.

Guidelines:
- Be concise and data-driven. Lead with the numbers.
- Highlight blockers prominently with severity and a suggested next action.
- Use velocity trends to provide forward-looking risk assessments.
- Format all output in clean Markdown suitable for Slack or Confluence.
- Never fabricate data — only report what the tool results confirm.
- If data is missing or a tool returned an error, say so explicitly rather than guessing.
- Recommend specific actions (e.g. "escalate PROJ-42 to the engineering manager").
```

### 10.2 Sprint Status Output Format

```markdown
## Sprint Status: {sprint_name}
**As of:** {timestamp}  |  **Days Remaining:** {n}  |  **Goal:** {goal}

### Progress
- Total Issues: {n} | Done: {n} ({pct}%) | In Progress: {n} | Blocked: {n}
- Story Points: {done}/{total} ({pct}% complete)

### Blockers ({count})
| Issue | Summary | Assignee | Days Blocked | Severity | Suggested Action |
|-------|---------|----------|--------------|----------|-----------------|
| ...   | ...     | ...      | ...          | ...      | ...             |

### Team Workload
| Member   | Assigned | Done | In Progress | Points Done/Total |
|----------|----------|------|-------------|-------------------|
| ...      | ...      | ...  | ...         | ...               |

### Risk Assessment
1. [Risk derived from data]
2. [Risk derived from data]
```

### 10.3 Weekly Recap Output Format

```markdown
## Weekly Recap — {sprint_name} | Week ending {week_end}

**Executive Summary:** {2-3 sentences on sprint health}

### What We Accomplished
- PROJ-X: {summary} ({points} pts)

### Blockers & Impediments
- PROJ-Y: {summary} — Severity: HIGH — Action: {action}

### Velocity & Trend
| Sprint   | Committed | Completed | Velocity |
|----------|-----------|-----------|----------|
| Sprint N | 30        | 25        | 83.3%    |

### Risks & Recommendations
1. [Risk]: [Action]

### Next Week Focus
- [Priority item based on remaining work]
```

---

## 11. LangChain-MCP Bridge

**File:** `agent/tools_bridge.py`

```python
# Launch MCP server subprocess, get tools as LangChain BaseTool objects
async def get_mcp_tools() -> list[BaseTool]:
    client = MultiServerMCPClient({
        "jira": {
            "command": sys.executable,
            "args": ["-m", "scrum_master_agent.mcp_server.server"],
            "transport": "stdio",
        }
    })
    return await client.get_tools()
    # Returns: list of LangChain tools with .name, .ainvoke()

def reset_mcp_tools():    # for test isolation
    global _mcp_tools
    _mcp_tools = None
```

**Caching:** Tools are loaded once per process (module-level `_mcp_tools` singleton).
The MCP subprocess stays alive for the process lifetime.

**Tool invocation in fetch_node:**
```python
result = await tool.ainvoke({"sprint_id": 42, "board_id": 1})
# Returns JSON string from MCP tool
```

---

## 12. Delivery Layer

### 12.1 Slack (`delivery/slack_delivery.py`)

Uses `slack_sdk.webhook.WebhookClient` (no bot token required — incoming webhook only).

```
SlackDelivery
  __init__()
    → WebhookClient(settings.slack_webhook_url)

  post_sprint_status(status: SprintStatus, markdown: str) -> bool
    → _format_sprint_blocks(status, markdown)
    → client.send(blocks=blocks, text=fallback_text)
    → Returns True on 200, False otherwise

  post_weekly_recap(recap: WeeklyRecap, markdown: str) -> bool
    → _format_recap_blocks(recap, markdown)
    → client.send(blocks=blocks, text=fallback_text)

  _format_sprint_blocks(status, markdown) -> list[dict]
    Block structure:
    1. header    — "{health_emoji} Sprint Status: {sprint_name}"
    2. section   — fields: Days Remaining, Total Issues, Completed, Blocked
    3. section   — progress bar + story points
    4. divider
    5. section   — full markdown report (≤2900 chars due to Slack limit)
    6. context   — "Generated at {timestamp}"

  _format_recap_blocks(recap, markdown) -> list[dict]
    Block structure:
    1. header    — ":bar_chart: Weekly Recap — {sprint_name}"
    2. section   — fields: Week, Velocity, Completion, Blockers
    3. divider
    4. section   — full markdown (≤2900 chars)
    5. context   — generated_at

_progress_bar(pct: float, width=20) -> str
  → "`████████░░░░` 40%"  (text-based ASCII progress bar)
```

**Health emoji mapping:**
```
pct >= 70% → :white_check_mark:  (green)
pct >= 40% → :warning:           (yellow)
pct <  40% → :red_circle:        (red)
```

### 12.2 Confluence (`delivery/confluence_delivery.py`)

Optional — only instantiated when `CONFLUENCE_URL` is set.

```
ConfluenceDelivery
  __init__()
    → Confluence(url, username=email, password=api_token, cloud=True)

  publish_recap(recap: WeeklyRecap, markdown: str) -> bool
    → title = "Sprint Recap — {sprint_name} — Week {week_end}"
    → get_page_by_title(space_key, title)
    → update_page() if exists, else create_page()
    → Returns True on success
```

---

## 13. Scheduler

**File:** `scheduler/weekly_scheduler.py`

```
APScheduler BlockingScheduler
  Job: weekly_recap_job
  Trigger: cron
    day_of_week: settings.recap_day    (default: "fri")
    hour:        settings.recap_hour   (default: 17)
    minute:      settings.recap_minute (default: 0)

weekly_recap_job()
  → run_weekly_recap(board_id=settings.jira_board_id, delivery_target="slack")
  → Logs success or exception (never raises — scheduler keeps running)

CLI:
  python -m scrum_master_agent.scheduler.weekly_scheduler          # starts scheduler
  python -m scrum_master_agent.scheduler.weekly_scheduler --run-now # immediate execution
```

---

## 14. Workflow Entry Points

### 14.1 Sprint Status (`workflows/sprint_status_workflow.py`)

```python
def run_sprint_status_query(
    board_id: int,
    delivery_target: str = "return",   # "return" | "slack" | "confluence"
) -> SprintStatus | None:
    initial_state = AgentState(
        mode=WorkflowMode.SPRINT_STATUS,
        board_id=board_id,
        delivery_target=delivery_target,
        # all other fields initialised to empty/None/0
    )
    final_state = compiled_graph.invoke(initial_state)
    return final_state.get("sprint_status")  # None on error
```

CLI: `python -m scrum_master_agent.workflows.sprint_status_workflow --board-id 1 [--delivery slack]`

### 14.2 Weekly Recap (`workflows/weekly_recap_workflow.py`)

```python
def run_weekly_recap(
    board_id: int,
    delivery_target: str = "return",
) -> WeeklyRecap | None:
    initial_state = AgentState(
        mode=WorkflowMode.WEEKLY_RECAP,
        board_id=board_id,
        delivery_target=delivery_target,
    )
    final_state = compiled_graph.invoke(initial_state)
    return final_state.get("weekly_recap")
```

CLI: `python -m scrum_master_agent.workflows.weekly_recap_workflow --board-id 1 [--dry-run]`

`--dry-run` sets `delivery_target="return"` and prints `raw_markdown` to stdout.

---

## 15. Configuration & Secrets

**File:** `config/settings.py` — Pydantic `BaseSettings`, loaded from environment / `.env`.

```
Settings fields:

  # Jira (all required)
  jira_url:          str       # https://yourorg.atlassian.net
  jira_email:        str       # Service account email
  jira_api_token:    str       # Atlassian API token (not password)
  jira_board_id:     int       # Default board to monitor

  # LLM
  anthropic_api_key: str       # Required
  llm_model:         str       # Default: "claude-sonnet-4-6"
  llm_temperature:   float     # Default: 0.1

  # Slack
  slack_webhook_url: str       # Required
  slack_channel:     str       # Default: "#sprint-updates"

  # Confluence (all optional)
  confluence_url:           Optional[str]
  confluence_space_key:     Optional[str]
  confluence_parent_page_id: Optional[int]

  # MCP Server
  mcp_transport:     str       # "stdio" (dev) | "sse" (prod). Default: "stdio"
  mcp_server_port:   int       # SSE port. Default: 8080

  # Scheduler
  recap_day:         str       # Default: "fri"
  recap_hour:        int       # Default: 17
  recap_minute:      int       # Default: 0
```

**`.env.example`:**
```
JIRA_URL=https://yourorg.atlassian.net
JIRA_EMAIL=scrummaster@yourorg.com
JIRA_API_TOKEN=<atlassian_api_token>
JIRA_BOARD_ID=1
ANTHROPIC_API_KEY=sk-ant-...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_CHANNEL=#sprint-updates
```

**Singleton access:** `get_settings()` returns a cached `Settings` instance. Tests patch this.

---

## 16. Error Handling & Retry Strategy

### 16.1 Jira Client Retries

```
_retry(fn, max_attempts=3):
  attempt 0 → fail → sleep(1s)
  attempt 1 → fail → sleep(2s)
  attempt 2 → fail → raise JiraToolError
```

| HTTP Status | Action |
|-------------|--------|
| 401 | Fail fast — log + raise immediately (credentials invalid) |
| 404 | Raise JiraToolError with descriptive message |
| 429 | Retry with backoff (rate limit) |
| 5xx | Retry with backoff |
| Other | Raise immediately |

### 16.2 Agent-Level Retry (Graph)

```
fetch_node sets state["error"] if any tool returns {"error": ...}
graph conditional edge:
  error AND retry_count < MAX_RETRIES (2) → re-route to plan node
  error AND retry_count >= MAX_RETRIES   → route to error_end
```

### 16.3 Tool-Level Error Contract

Every MCP tool returns a JSON string. On error:
```json
{"error": "Human-readable error message"}
```
The fetch_node collects all errors and joins them into `state["error"]`.
The synthesize_node checks for `"error"` keys in tool_results and notes them in the report
rather than fabricating data.

### 16.4 Delivery Failure

Slack/Confluence failure → sets `state["error"]` but does NOT prevent the caller from
accessing `sprint_status` or `weekly_recap`. Callers can handle delivery failure separately.

### 16.5 Data Quality Edge Cases

| Situation | Handling |
|-----------|----------|
| No active sprint | `get_active_sprint` returns `{"error": "No active sprint"}` |
| Issue with no story points | `story_points = None` → treated as 0 in aggregates |
| Unassigned issue | `assignee = None` → counted in `unassigned_issues` |
| Empty sprint (0 issues) | Returns `SprintStatus` with all counts = 0 |
| LLM timeout | Retry once with truncated context (issue list dropped) |

---

## 17. Sequence Diagrams

### 17.1 Sprint Status Query (On-Demand)

```
User/CLI          Agent (LangGraph)          MCP Server          Jira API      Slack
   │                      │                       │                   │            │
   │──run_sprint_status──▶│                       │                   │            │
   │                      │                       │                   │            │
   │              ┌───────▼──────┐                │                   │            │
   │              │  PLAN node   │                │                   │            │
   │              │ sets tools:  │                │                   │            │
   │              │ [sprint,     │                │                   │            │
   │              │  issues,     │                │                   │            │
   │              │  blockers,   │                │                   │            │
   │              │  workload]   │                │                   │            │
   │              └───────┬──────┘                │                   │            │
   │                      │                       │                   │            │
   │              ┌───────▼──────┐                │                   │            │
   │              │  FETCH node  │                │                   │            │
   │              │ Step 1:      │──get_active────▶│                   │            │
   │              │  sprint_id   │  _sprint(1)    │──GET /sprint──────▶│            │
   │              │  resolved    │◀───sprint──────│◀──sprint dict─────│            │
   │              │              │                │                   │            │
   │              │ Step 2:      │──get_sprint────▶│                   │            │
   │              │  parallel    │  _issues(42)   │──GET /sprint/42───▶│            │
   │              │  tool calls  │──get_blockers──▶│  /issue           │            │
   │              │              │  (42, 1)       │──JQL search───────▶│            │
   │              │              │──get_team──────▶│                   │            │
   │              │              │  _workload(42) │ (reuses issues)   │            │
   │              │              │◀───all results─│◀──responses───────│            │
   │              └───────┬──────┘                │                   │            │
   │                      │                       │                   │            │
   │              ┌───────▼──────┐                                                 │
   │              │  SYNTHESIZE  │                                                 │
   │              │   node       │◀──────────────── Claude Sonnet ───────────────▶ │
   │              │ builds       │   (generates markdown report)                  │
   │              │ SprintStatus │                                                 │
   │              └───────┬──────┘                                                 │
   │                      │                                                         │
   │              ┌───────▼──────┐                                                 │
   │              │  DELIVER     │──────────────────────────────────────── POST ──▶│
   │              │   node       │                                         webhook  │
   │              └───────┬──────┘                                                 │
   │                      │                                                         │
   │◀──SprintStatus JSON──│                                                         │
```

### 17.2 Weekly Recap (Scheduled)

```
APScheduler     Agent (LangGraph)      MCP Server      Jira API    Slack   Confluence
     │                 │                    │               │          │        │
     │──Friday 17:00──▶│                    │               │          │        │
     │                 │── PLAN: 6 tools ──▶│               │          │        │
     │                 │── FETCH ──────────▶│               │          │        │
     │                 │                    │──6 Jira calls─▶│          │        │
     │                 │◀─ all 6 results ───│◀──responses───│          │        │
     │                 │── SYNTHESIZE ─────────────────────────────────│        │
     │                 │   Claude generates weekly recap markdown       │        │
     │                 │◀─ WeeklyRecap ─────────────────────────────────        │
     │                 │── DELIVER ────────────────────────────────────▶│        │
     │                 │                                                 │──POST─▶│
     │◀─ done ─────────│                                                          │
```

### 17.3 Error & Retry Flow

```
                 ┌──────┐      ┌───────┐      error + count<2
  START ────────▶│ PLAN │─────▶│ FETCH │─────────────────────┐
                 └──────┘      └───┬───┘                      │
                                   │ success               ◀──┘ (retry_count++)
                            ┌──────▼──────┐
                            │  SYNTHESIZE │
                            └──────┬──────┘
                                   │ success
                            ┌──────▼──────┐
                            │   DELIVER   │──▶ END
                            └─────────────┘

                 error + count>=2    synthesis error
                 ──────────────────────────────────▶ ERROR_END ──▶ END
```

---

## 18. Interface Contracts

| Boundary | Protocol | Format | Auth |
|----------|----------|--------|------|
| CLI → Workflow | Python function call | `AgentState` TypedDict | None |
| LangGraph ↔ Nodes | Python function call | `AgentState` TypedDict | None |
| Fetch Node → MCP Bridge | Python async/await | `BaseTool.ainvoke(dict)` | None |
| MCP Bridge → MCP Server | JSON-RPC 2.0 over stdio | `{"method": "tools/call", ...}` | None |
| MCP Server → Jira | HTTPS REST | JSON | Basic Auth (email + API token) |
| Synthesize → LLM | HTTPS | OpenAI-compatible messages | Anthropic API key |
| Deliver → Slack | HTTPS POST | Slack Block Kit JSON | Webhook URL (embedded secret) |
| Deliver → Confluence | HTTPS REST | XHTML storage format | Basic Auth |
| Scheduler → Workflow | Python function call | `board_id: int` | None |

---

## 19. Testing Strategy

### 19.1 Unit Tests (`tests/unit/`)

Each MCP tool is tested in isolation with `mock_jira_client` fixture:

| Test File | Coverage |
|-----------|----------|
| `test_sprint_tools.py` | `get_active_sprint` (success, no sprint, Jira error), `get_sprint_issues` (filter, points, blocked detection), `get_sprint_burndown` |
| `test_blocker_tools.py` | `get_blockers` (detection, severity mapping, error) |
| `test_team_tools.py` | `get_team_workload` (grouping, unassigned, completion rate) |
| `test_velocity_tools.py` | `get_sprint_velocity` (records structure, non-negative velocity) |
| `test_models.py` | Pydantic model defaults, edge cases (null assignee, zero velocity) |
| `test_delivery.py` | `_progress_bar`, Slack Block Kit structure, `post_sprint_status` returns True |

Run: `pytest tests/unit/ -v`

### 19.2 Integration Tests (`tests/integration/`)

Full workflow tests with mocked MCP tools and mocked LLM:

```python
# Fixtures provided:
mock_mcp_tools    → list of MagicMock tools with AsyncMock .ainvoke()
mock_llm_response → ChatAnthropic mocked with deterministic markdown
mock_settings     → Settings mocked with test values

# Assertions:
test_sprint_status_workflow_returns_sprint_status  → SprintStatus not None, sprint_id correct
test_sprint_status_workflow_computes_completion    → total=2, completed=1, pct=50.0
test_weekly_recap_workflow_returns_recap           → WeeklyRecap not None
test_weekly_recap_contains_velocity_trend         → 2 VelocityRecords
test_weekly_recap_markdown_populated              → raw_markdown contains "Weekly Recap"
```

Run: `pytest tests/integration/ -v`

### 19.3 Manual E2E Tests (against real Jira)

```bash
# 1. Verify MCP server tools are discoverable
mcp dev scrum_master_agent/mcp_server/server.py

# 2. Sprint status (prints JSON to stdout)
python -m scrum_master_agent.workflows.sprint_status_workflow --board-id 1

# 3. Weekly recap dry-run (prints markdown, no Slack post)
python -m scrum_master_agent.workflows.weekly_recap_workflow --board-id 1 --dry-run

# 4. Weekly recap to Slack
python -m scrum_master_agent.workflows.weekly_recap_workflow --board-id 1 --delivery slack

# 5. Scheduler immediate trigger
python -m scrum_master_agent.scheduler.weekly_scheduler --run-now
```

### 19.4 Smoke Test Checklist

- [ ] MCP server starts, lists 7 tools via `mcp dev`
- [ ] `get_active_sprint` returns valid SprintStatus JSON for real board
- [ ] `get_sprint_issues` returns correct issue count
- [ ] `get_blockers` correctly identifies flagged/blocked issues
- [ ] Full sprint status workflow completes in < 30 seconds
- [ ] Slack message appears in target channel with correct sprint name
- [ ] Weekly recap generates all 5 sections with no "None" artifacts
- [ ] Retry logic triggers on simulated Jira 429 (mock `_retry`)
- [ ] `--dry-run` prints markdown without posting to Slack

---

## 20. Dependencies

```toml
[tool.poetry.dependencies]
python              = "^3.11"
langgraph           = "^0.2"       # LangGraph state machine orchestration
langchain           = "^0.3"       # Base LangChain abstractions
langchain-anthropic = "^0.3"       # Claude Sonnet integration
langchain-mcp-adapters = "^0.1"    # MCP ↔ LangChain tool bridge
mcp                 = "^1.0"       # Model Context Protocol SDK
atlassian-python-api = "^3.41"     # Jira REST API client
pydantic            = "^2.0"       # Data validation and serialisation
pydantic-settings   = "^2.0"       # Settings from environment
apscheduler         = "^3.10"      # Cron scheduler (in-process)
slack-sdk           = "^3.27"      # Slack webhook client
python-dotenv       = "^1.0"       # .env file loading
httpx               = "^0.27"      # Async HTTP (used by LangChain internals)

[tool.poetry.dev-dependencies]
pytest              = "^8.0"
pytest-asyncio      = "^0.23"      # async test support
pytest-cov          = "^5.0"       # coverage reporting
respx               = "^0.21"      # mock httpx for integration tests
ruff                = "^0.4"       # linting
```

**Python version requirement:** 3.11+ (uses `list[X]` syntax, `X | Y` union types,
`TypedDict` improvements, `asyncio.run()` reliability fixes)

---

## 21. Key Design Decisions

| Decision | Choice | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| Orchestration | LangGraph | LangChain AgentExecutor, CrewAI | LangGraph gives explicit state, conditional edges, retry control, and human-in-loop capability. AgentExecutor is too opaque for production error handling. |
| LLM | Claude Sonnet 4.6 | GPT-4o, Gemini 1.5 | Best reasoning/cost balance; consistent with dev environment; no additional API setup. |
| MCP Transport | stdio (dev) / SSE (prod) | Direct function calls | stdio is zero-config for local dev; SSE scales for multi-agent and remote deployment. Keeps Jira logic cleanly separated from agent. |
| Jira Library | atlassian-python-api | jira-python, raw HTTPS | Most complete Agile API coverage; handles auth, pagination, and cloud vs server differences. |
| Scheduling | APScheduler (in-process) | Celery, AWS EventBridge, cron | No external broker needed; lightweight; integrates cleanly with Python process. |
| Output format | Pydantic → Markdown | Pure JSON, HTML | Pydantic ensures type safety and deterministic structure; Markdown renders in both Slack and Confluence; LLM narrative layer adds human-readable insight. |
| Issue parsing | From raw Jira fields | Via LLM extraction | Deterministic parsing is more reliable and testable than LLM extraction for structured data. LLM is only used for narrative generation. |
| Blast radius | Read-only Jira + Slack webhook out | Write-back to Jira | Eliminates risk of corrupting sprint data. Slack webhook is unidirectional — no risk of reading sensitive data from Slack. |
| Test strategy | Unit (mocked Jira) + Integration (mocked MCP + LLM) | Full E2E only | Unit tests run without credentials and are fast. Integration tests verify agent graph logic. E2E tests are manual to avoid hitting real Jira in CI. |

---

## Appendix A: Environment Setup

```bash
# 1. Clone / navigate to project
cd scrum_master_agent

# 2. Install dependencies (Python 3.11+)
poetry install

# 3. Copy and fill credentials
cp .env.example .env
# Edit .env with your Jira URL, email, API token, board ID, Slack webhook

# 4. Run tests (no credentials needed)
pytest tests/ -v --cov=scrum_master_agent

# 5. Verify MCP tools
mcp dev scrum_master_agent/mcp_server/server.py

# 6. First run
python -m scrum_master_agent.workflows.sprint_status_workflow --board-id 1 --dry-run
```

## Appendix B: Adding a New MCP Tool

1. Add handler function in `mcp_server/tools/<category>_tools.py`
2. Export from `mcp_server/tools/__init__.py`
3. Register in `mcp_server/server.py` TOOLS dict (name, handler, input schema)
4. Add to `agent/prompts/tool_use_prompt.py` if it should be called in a workflow
5. Update `agent/nodes/fetch_node.py` `_with_args()` to build correct args
6. Add unit tests in `tests/unit/test_<category>_tools.py`

## Appendix C: Glossary

| Term | Definition |
|------|-----------|
| MCP | Model Context Protocol — Anthropic's standard for exposing tools to LLMs |
| LangGraph | LangChain's stateful agent graph framework |
| Sprint Status | Point-in-time snapshot of a sprint: completion %, blockers, team workload |
| Weekly Recap | End-of-week narrative report: velocity trend, risks, recommendations |
| Digital Worker | Autonomous software agent that performs a human role's repetitive tasks |
| Blast Radius | Scope of unintended side-effects if the agent malfunctions (here: Low) |
| AgentState | Shared TypedDict that flows through all LangGraph nodes |
| JQL | Jira Query Language — SQL-like syntax for searching Jira issues |
