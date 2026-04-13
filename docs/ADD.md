# Architecture Design Document (ADD)
# Scrum Master Digital Worker

**Version:** 1.0
**Date:** 2026-04-13
**Status:** Approved
**Related Documents:** [HLD.md](HLD.md) | [LLD.md](LLD.md)

---

## Table of Contents

1. [Purpose & Audience](#1-purpose--audience)
2. [Architecture Principles](#2-architecture-principles)
3. [System Architecture](#3-system-architecture)
4. [Component Architecture](#4-component-architecture)
5. [LangGraph State Machine Architecture](#5-langgraph-state-machine-architecture)
6. [MCP Tool Layer Architecture](#6-mcp-tool-layer-architecture)
7. [Data Architecture](#7-data-architecture)
8. [Integration Architecture](#8-integration-architecture)
9. [Security Architecture](#9-security-architecture)
10. [Deployment Architecture](#10-deployment-architecture)
11. [Architecture Decision Records (ADRs)](#11-architecture-decision-records-adrs)
12. [Cross-Cutting Concerns](#12-cross-cutting-concerns)
13. [Architecture Constraints](#13-architecture-constraints)

---

## 1. Purpose & Audience

This Architecture Design Document describes the **structural and behavioural architecture** of the Scrum Master Digital Worker. It covers:

- How the system is divided into components and layers
- The rationale for key architectural decisions (ADRs)
- How data flows between components
- Security and deployment architecture

**Audience:** Technical leads, senior engineers, reviewers extending or deploying this system.

**Companion documents:**
- **HLD** — business context, objectives, NFRs, and deployment overview
- **LLD** — module-level design, class signatures, sequence diagrams, and test strategy

---

## 2. Architecture Principles

These principles drove every significant design decision in this system.

| # | Principle | Application |
|---|-----------|-------------|
| P1 | **Strict layer boundaries** | Agent never calls Jira directly; all Jira access through MCP tool layer |
| P2 | **Errors as data, not exceptions** | MCP tools return `{"error": "..."}` JSON; never raise to the agent |
| P3 | **Deterministic metrics, generative narrative** | Sprint counts/percentages computed from raw data; LLM only writes prose |
| P4 | **Singletons for shared resources** | `get_jira_client()`, `get_settings()`, `get_mcp_tools()` — one instance per process |
| P5 | **Testability without credentials** | All external integrations injectable/mockable; tests need no real Jira or Slack |
| P6 | **Minimum blast radius** | Read-only Jira access; outbound-only Slack/Confluence; no persistent writes |
| P7 | **Explicit state, no hidden side effects** | LangGraph state dict is the single source of truth; all mutations through node return values |
| P8 | **Fail gracefully, surface clearly** | Retry logic in agent state; errors logged and surfaced, never silently swallowed |

---

## 3. System Architecture

### 3.1 C4 — Context Diagram

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│   ┌──────────────┐        ┌─────────────────────────────────┐                │
│   │ Scrum Master │───────▶│   Scrum Master Digital Worker   │                │
│   │   (Human)    │        │   (Python process)              │                │
│   └──────────────┘        └────────────┬────────────────────┘                │
│          ▲                             │ reads          │ posts              │
│          │ reviews report              ▼                ▼                   │
│   ┌──────┴──────┐          ┌──────────────┐   ┌────────────────────────┐   │
│   │    Slack    │◀─────────│  Jira Cloud  │   │  Slack / Confluence    │   │
│   │  #channel   │ report   │  (sprints,   │   │  (report destinations) │   │
│   └─────────────┘          │   issues)    │   └────────────────────────┘   │
│                             └──────────────┘                                │
│                                                                               │
│   ┌─────────────────────┐                                                    │
│   │   Anthropic API     │◀───── LLM inference (Claude Sonnet 4.6)           │
│   └─────────────────────┘                                                    │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 C4 — Container Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Scrum Master Digital Worker  [Python process]                               │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Trigger Layer                                                        │   │
│  │  ┌──────────────────┐  ┌───────────────────┐  ┌──────────────────┐  │   │
│  │  │  CLI Entry Point │  │  Python API        │  │  APScheduler     │  │   │
│  │  │  (sprint-status, │  │  (workflow funcs)  │  │  (Friday 17:00)  │  │   │
│  │  │  weekly-recap)   │  │                    │  │                  │  │   │
│  │  └────────┬─────────┘  └─────────┬──────────┘  └────────┬─────────┘  │   │
│  └───────────│──────────────────────│─────────────────────│─────────────┘   │
│              └──────────────────────┴─────────────────────┘                 │
│                                     │                                        │
│  ┌──────────────────────────────────▼───────────────────────────────────┐   │
│  │  Workflow Layer                                                        │   │
│  │  ┌─────────────────────────────┐  ┌──────────────────────────────┐   │   │
│  │  │  SprintStatusWorkflow       │  │  WeeklyRecapWorkflow          │   │   │
│  │  └───────────────┬─────────────┘  └──────────────┬───────────────┘   │   │
│  └──────────────────│─────────────────────────────────│──────────────────┘   │
│                     └─────────────────────────────────┘                     │
│                                     │                                        │
│  ┌──────────────────────────────────▼───────────────────────────────────┐   │
│  │  Agent Layer  [LangGraph StateGraph]                                   │   │
│  │                                                                        │   │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────────┐  ┌───────────────┐   │   │
│  │  │  PLAN    │─▶│  FETCH   │─▶│  SYNTHESIZE   │─▶│  DELIVER      │   │   │
│  │  │  node    │  │  node    │  │  node (LLM)   │  │  node         │   │   │
│  │  └──────────┘  └────┬─────┘  └───────────────┘  └───────┬───────┘   │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                         │                                     │              │
│  ┌──────────────────────▼──────────────────────┐             │              │
│  │  Tool Layer  [MCP Server + LangChain Bridge] │             │              │
│  │  7 Jira tools (stdio transport)              │             │              │
│  │  JiraClient singleton (retry + backoff)      │             │              │
│  └──────────────────────────────────────────────┘             │              │
│                                                                ▼              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Delivery Layer                                                       │    │
│  │  ┌──────────────────────┐      ┌──────────────────────────────┐     │    │
│  │  │  SlackDelivery       │      │  ConfluenceDelivery           │     │    │
│  │  │  (Block Kit webhook) │      │  (REST page create)          │     │    │
│  │  └──────────────────────┘      └──────────────────────────────┘     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Architecture

### 4.1 Component Responsibilities

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  COMPONENT              │  RESPONSIBILITY                                    │
├─────────────────────────┼───────────────────────────────────────────────────┤
│  config/settings.py     │  Pydantic-settings singleton; reads .env          │
│  models/                │  All Pydantic v2 data models; cross-layer DTOs    │
│  mcp_server/server.py   │  JSON-RPC entry point; registers 7 tools          │
│  mcp_server/jira_client │  Jira REST client singleton; retry + backoff      │
│  mcp_server/tools/*     │  One file per tool domain; pure functions         │
│  agent/state.py         │  AgentState TypedDict; WorkflowMode enum          │
│  agent/graph.py         │  StateGraph definition + compiled_graph           │
│  agent/tools_bridge.py  │  MultiServerMCPClient → LangChain tools (cached)  │
│  agent/nodes/*          │  4 node functions; read/write AgentState          │
│  agent/prompts/*        │  System prompt, tool-use prompt, output format    │
│  delivery/slack_*       │  Block Kit builder + webhook POST                 │
│  delivery/confluence_*  │  Confluence page create/update                    │
│  scheduler/             │  APScheduler BlockingScheduler; misfire handling  │
│  workflows/             │  Public API: two async entry-point functions      │
│  tests/                 │  conftest fixtures; unit + integration tests      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Dependency Graph

```
workflows/
    └── agent/graph.py
            ├── agent/nodes/plan_node.py
            ├── agent/nodes/fetch_node.py ──── agent/tools_bridge.py
            │                                       └── mcp_server/server.py
            │                                               ├── mcp_server/tools/*.py
            │                                               └── mcp_server/jira_client.py
            ├── agent/nodes/synthesize_node.py ── Anthropic API (via langchain-anthropic)
            └── agent/nodes/deliver_node.py
                    ├── delivery/slack_delivery.py
                    └── delivery/confluence_delivery.py

config/settings.py  ←── used by jira_client.py, delivery layers, scheduler
models/             ←── used by all layers (pure data, no dependencies)
```

---

## 5. LangGraph State Machine Architecture

### 5.1 State Definition

```python
# agent/state.py
class AgentState(TypedDict):
    mode: WorkflowMode           # SPRINT_STATUS | WEEKLY_RECAP
    board_id: int                # Jira board ID
    sprint_id: Optional[int]     # resolved by FETCH from get_active_sprint
    tool_results: dict           # tool_name → raw JSON string
    sprint_status: Optional[SprintStatus]    # populated by SYNTHESIZE
    weekly_recap: Optional[WeeklyRecap]      # populated by SYNTHESIZE
    delivery_target: str         # "slack" | "confluence" | "return"
    error: Optional[str]         # set on tool/synthesis failure
    retry_count: int             # 0–2; triggers ERROR_END at ≥ 2
    messages: list               # LangChain message history for LLM calls
```

### 5.2 State Machine Transitions

```
                   ┌─────────────────────────────────────────────┐
                   │                                              │
   START ──▶ PLAN ──▶ FETCH ──▶ SYNTHESIZE ──▶ DELIVER ──▶ END  │
                       │  ▲                                       │
                       │  │ error & retry_count < 2               │
                       └──┘                                       │
                       │                                          │
                       │ error & retry_count ≥ 2                  │
                       ▼                                          │
                  ERROR_END ──────────────────────────────▶ END  │
                                                                  │
                  SYNTHESIZE error (any) ─────────────────▶ END  │
                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Node Contracts

| Node | Input state fields read | Output state fields written |
|------|------------------------|----------------------------|
| PLAN | `mode`, `board_id` | `messages` (system + tool-use prompt) |
| FETCH | `board_id`, `sprint_id`, `mode`, `retry_count` | `tool_results`, `sprint_id`, `error`, `retry_count` |
| SYNTHESIZE | `tool_results`, `mode`, `messages` | `sprint_status` or `weekly_recap`, `error` |
| DELIVER | `sprint_status`/`weekly_recap`, `delivery_target` | — (side effects: HTTP calls) |

### 5.4 Parallel Execution in FETCH

```
FETCH node execution order:

Step 1 (sequential):  get_active_sprint(board_id)  → resolves sprint_id

Step 2 (parallel):    get_sprint_issues(sprint_id)  ─┐
                      get_blockers(sprint_id)        ─┼── asyncio.gather()
                      get_team_workload(sprint_id)   ─┘

Step 3 (if WEEKLY):   get_sprint_velocity(board_id) ─┐
                      get_sprint_burndown(sprint_id) ─┴── asyncio.gather()
```

---

## 6. MCP Tool Layer Architecture

### 6.1 Transport and Protocol

```
LangGraph FETCH node
      │
      │  LangChain ToolMessage (tool_name, args)
      ▼
langchain-mcp-adapters (MultiServerMCPClient)
      │
      │  MCP JSON-RPC over stdio
      ▼
mcp_server/server.py  (subprocess)
      │
      ▼
tool functions (sprint_tools, blocker_tools, etc.)
      │
      ▼
JiraClient.get_jira_client()  ← singleton
      │
      │  HTTPS REST
      ▼
Jira Cloud API
```

### 6.2 Tool Isolation Pattern

Each tool domain is a separate module under `mcp_server/tools/`. Tools are **pure functions** that:
1. Accept typed parameters (validated by MCP framework)
2. Call `JiraClient` methods
3. Serialize results to JSON string
4. Catch all exceptions → return `{"error": "message"}` JSON

This means no tool can crash the agent. The agent sees `{"error": ...}` in `tool_results`, sets `state["error"]`, and triggers the retry path.

### 6.3 JiraClient Resilience

```python
# Retry strategy in jira_client.py
_retry(
    func,
    max_retries=3,
    backoff_factor=2,     # wait: 1s, 2s, 4s
    exceptions=(JIRAError, ConnectionError, Timeout)
)
```

---

## 7. Data Architecture

### 7.1 Data Model Hierarchy

```
SprintStatus                    WeeklyRecap
├── sprint_id                   ├── sprint_id
├── sprint_name                 ├── sections: list[RecapSection]
├── board_id                    │   ├── RecapSection.title
├── completion_pct              │   └── RecapSection.content (markdown)
├── issues: list[SprintIssue]   ├── velocity_trend: list[VelocityRecord]
│   ├── issue_key               │   └── VelocityRecord.completed_points
│   ├── summary                 ├── burndown: dict[date, float]
│   ├── status: IssueStatus     └── narrative: str (markdown)
│   ├── issue_type: IssueType
│   └── assignee
├── blockers: BlockerReport
│   └── items: list[BlockerItem]
│       ├── severity: BlockerSeverity
│       └── description
└── team_workload: TeamWorkload
    └── members: list[MemberWorkload]
        ├── assignee
        └── issue_count
```

### 7.2 Data Flow and Transformation

```
Jira REST API (raw JSON)
      │
      ▼
atlassian-python-api objects
      │  JiraClient methods
      ▼
Serialized to JSON strings (in MCP tools)
      │  tool functions
      ▼
AgentState["tool_results"] dict  ← raw JSON strings, keyed by tool name
      │  synthesize_node
      ▼
Parsed JSON → Pydantic models (SprintStatus / WeeklyRecap)
      │  synthesize_node
      ▼
Markdown narrative (from Claude Sonnet)
      │  appended into Pydantic model
      ▼
Delivery Layer (Block Kit / Confluence page / return value)
```

**Key invariant:** Numeric metrics (completion %, blocker count, velocity) are computed from raw Pydantic-validated data — never extracted from LLM-generated text. This prevents hallucination of metrics.

### 7.3 State Lifetime

All data is **ephemeral** — it lives only in the LangGraph `AgentState` dict for the duration of one workflow run. There is no database, cache, or file persistence in v1.0.

---

## 8. Integration Architecture

### 8.1 Inbound Integration — Jira Cloud

```
Protocol:    HTTPS REST (Basic Auth: email + API token)
SDK:         atlassian-python-api
Access:      Read-only (boards, sprints, issues, custom fields)
Rate limits: Jira Cloud: 10 req/sec per user; handled by _retry() with backoff
Error codes: 401 (invalid token), 404 (board not found), 429 (rate limit)
```

**JQL patterns used:**

| Tool | JQL / API Method |
|------|-----------------|
| `get_active_sprint` | `board.get_sprints(board_id, state='active')` |
| `get_sprint_issues` | `jira.search_issues(f"sprint={sprint_id}")` |
| `get_blockers` | `jira.search_issues(f"sprint={sprint_id} AND labels=Blocked")` |
| `get_team_workload` | `get_sprint_issues` grouped by `issue.fields.assignee` |
| `get_sprint_velocity` | Last N closed sprints; sum `story_points` per sprint |
| `get_sprint_burndown` | `board.get_sprint_report(sprint_id)` |

### 8.2 Outbound Integration — Slack

```
Protocol:    HTTPS POST to Incoming Webhook URL
Auth:        Webhook URL is the secret (no OAuth)
Format:      Slack Block Kit JSON
SDK:         slack-sdk WebhookClient
On error:    Log and set state["error"]; do not retry (idempotency risk)
```

**Block Kit structure:**

```
[Header block]   Sprint Status: <Sprint Name>
[Section block]  Progress: 62% complete | 3 blockers | 5/8 team members active
[Divider]
[Section block]  🚨 Blockers  (P1/P2 items)
[Section block]  📋 Narrative (Claude Sonnet markdown → mrkdwn)
[Context block]  Generated by Scrum Master Digital Worker · <timestamp>
```

### 8.3 Outbound Integration — Confluence

```
Protocol:    HTTPS REST (Basic Auth: email + API token)
SDK:         atlassian-python-api ConfluenceClient
Operation:   Create or update page under parent page ID
Format:      Confluence Storage Format (HTML-wrapped markdown)
Auth scope:  Write to one space (CONFLUENCE_SPACE_KEY)
```

### 8.4 Outbound Integration — Anthropic API

```
Protocol:    HTTPS (via langchain-anthropic)
Model:       claude-sonnet-4-6
Usage:       Single LLM call per workflow run (in SYNTHESIZE node)
Input:       System prompt + tool-use prompt + tool results as user message
Output:      Markdown narrative (2000–4000 tokens typical)
Cost:        ~$0.003–0.01 per report
```

---

## 9. Security Architecture

### 9.1 Credential Management

```
Environment  ──▶  .env file (local dev)
Variables         OR environment variables (production)
     │
     ▼
pydantic-settings (get_settings())
     │
     ▼
Used by:
  JiraClient       ← JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN
  SlackDelivery    ← SLACK_WEBHOOK_URL
  ConfluenceDelivery ← CONFLUENCE_URL, CONFLUENCE_SPACE_KEY
  LangGraph Agent  ← ANTHROPIC_API_KEY (via ANTHROPIC_API_KEY env var)
```

**Rules:**
- `.env` is in `.gitignore` — never committed
- `.env.example` committed with placeholder values
- No credentials in logs (logging middleware strips headers)
- No credentials in agent state or LLM prompts

### 9.2 Jira Read-Only Enforcement

The architecture enforces read-only Jira access at three levels:
1. **API token scope** — Atlassian token configured with read-only permissions
2. **Code level** — `JiraClient` exposes only read methods (no `create_issue`, `transition_issue`)
3. **MCP tool level** — no tool accepts write parameters

### 9.3 Prompt Injection Defence

Jira issue summaries and descriptions are passed as structured JSON to the LLM, not as raw user-controlled strings interpolated into system prompts. The system prompt instructs Claude to treat tool results as data, not instructions.

### 9.4 Network Security

| Connection | Encryption | Auth |
|------------|-----------|------|
| Agent → Jira | TLS 1.2+ (HTTPS) | Basic Auth (API token) |
| Agent → Anthropic | TLS 1.2+ (HTTPS) | API key (Bearer) |
| Agent → Slack | TLS 1.2+ (HTTPS) | Webhook URL (secret) |
| Agent → Confluence | TLS 1.2+ (HTTPS) | Basic Auth (API token) |
| Agent → MCP Server | stdio (local IPC) | None (same process) |

---

## 10. Deployment Architecture

### 10.1 Process Model

```
┌──────────────────────────────────────────────────────────┐
│  Single Python Process                                    │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  APScheduler (BlockingScheduler)                   │  │
│  │  └── weekly_recap_job() → run_weekly_recap()       │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  MCP Server subprocess (stdio)                     │  │
│  │  Spawned by MultiServerMCPClient per workflow run  │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

On-demand (CLI) runs are independent short-lived processes. The scheduler run is a long-lived process that spawns the agent workflow each Friday.

### 10.2 Container Deployment (Recommended)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev
COPY scrum_master_agent/ ./scrum_master_agent/
CMD ["poetry", "run", "python", "-m",
     "scrum_master_agent.scheduler.weekly_scheduler"]
```

**Environment variables** injected at runtime (Docker secrets or platform env vars — not baked into image).

### 10.3 Platform Options

```
┌──────────────────┬────────────────────────────────────────────┐
│  Platform        │  Notes                                      │
├──────────────────┼────────────────────────────────────────────┤
│  Local (dev)     │  poetry run; .env file                      │
│  Docker (prod)   │  Single container; env from secrets manager │
│  Railway         │  Free/paid tier; env vars in dashboard      │
│  Render          │  Background worker type; env vars           │
│  systemd (VM)    │  ExecStart=poetry run ...; EnvironmentFile  │
└──────────────────┴────────────────────────────────────────────┘
```

### 10.4 No External Infrastructure Required

The system deliberately requires **zero external infrastructure** beyond the three SaaS integrations:

| Needed? | Component |
|---------|-----------|
| No | Database |
| No | Message queue (Kafka, RabbitMQ) |
| No | Cache (Redis) |
| No | Service mesh |
| No | Load balancer |
| Yes | Jira Cloud (existing) |
| Yes | Slack workspace (existing) |
| Yes | Anthropic API key ($) |

---

## 11. Architecture Decision Records (ADRs)

### ADR-001: Use MCP as the Tool Interface Layer

**Status:** Accepted

**Context:** The agent needs to call Jira APIs. Direct HTTP calls from agent code would couple the LLM orchestration layer to the Jira client layer, making each independently hard to test and modify.

**Decision:** Introduce an MCP Server as a strict boundary. The agent only knows about tool names and JSON schemas. The Jira client is entirely hidden behind the MCP layer.

**Consequences:**
- (+) Agent is independently testable by mocking MCP tool responses
- (+) MCP tools are independently testable without invoking the agent or LLM
- (+) MCP Server can be upgraded, replaced, or extended without touching agent code
- (-) Adds subprocess + stdio communication overhead (~50ms per tool call)
- (-) Requires `langchain-mcp-adapters` as a bridge dependency

---

### ADR-002: LangGraph for Agent Orchestration (vs. bare LangChain or custom code)

**Status:** Accepted

**Context:** The reporting pipeline has clear sequential phases with retry logic. Options: (1) bare Python async functions, (2) LangChain AgentExecutor, (3) LangGraph StateGraph.

**Decision:** LangGraph StateGraph.

**Consequences:**
- (+) State transitions are explicit and inspectable
- (+) Retry edges are declared in the graph, not scattered in try/except blocks
- (+) Graph can be extended with new nodes (e.g., human approval) without rewriting existing nodes
- (+) Built-in support for streaming and checkpointing (future)
- (-) Learning curve for developers unfamiliar with LangGraph
- (-) Adds langchain + langgraph as dependencies

---

### ADR-003: LLM Generates Narrative Only — Metrics Computed Deterministically

**Status:** Accepted

**Context:** Early prototypes fed raw Jira data to Claude and asked it to extract both the metrics and write the narrative. This produced hallucinated sprint counts in ~5% of runs.

**Decision:** SYNTHESIZE node computes all numeric metrics (completion %, blocker count, team utilisation) directly from the Pydantic-validated `tool_results` dict. Claude Sonnet is only asked to write the human-readable narrative section.

**Consequences:**
- (+) Zero hallucination risk on metrics
- (+) Reports are auditable — metric values are traceable to raw Jira data
- (+) Cheaper LLM calls (shorter prompts)
- (-) More Python code for metric extraction
- (-) Any new metric requires a code change (not just a prompt change)

---

### ADR-004: APScheduler (In-Process) vs. External Scheduler (Celery, Airflow)

**Status:** Accepted

**Context:** The weekly recap needs to run every Friday at 17:00. Options range from cron + shell script to Celery + Redis to Airflow.

**Decision:** APScheduler `BlockingScheduler` in-process.

**Consequences:**
- (+) Zero infrastructure: no Redis, no broker, no worker pool, no Airflow server
- (+) Simple deployment: one process, one container
- (+) `--run-now` flag enables instant testing without waiting for the schedule
- (-) No persistent job store: if the process restarts mid-week, no missed-job recovery beyond `misfire_grace_time`
- (-) Not suitable for distributed/multi-worker scenarios (acceptable for v1.0 single-board use)

---

### ADR-005: Pydantic v2 for All Data Models

**Status:** Accepted

**Context:** Data passes through multiple layers (Jira API → MCP tools → agent state → delivery). Each transformation is a potential source of runtime errors.

**Decision:** Define Pydantic v2 models for all entities. Use them as the single DTO layer across all module boundaries.

**Consequences:**
- (+) Runtime type validation at every layer boundary
- (+) Automatic JSON serialisation/deserialisation
- (+) IDE autocomplete and static analysis across the codebase
- (+) pydantic-settings reuses the same ecosystem for config
- (-) Adds pydantic as a dependency
- (-) V2 breaking changes from V1 require care when copy-pasting examples

---

### ADR-006: No Persistent Storage (v1.0)

**Status:** Accepted

**Context:** Reports could be stored in a database for history, auditing, and dashboard use. This adds infrastructure and operational complexity.

**Decision:** No database in v1.0. Reports are generated, delivered, and discarded.

**Consequences:**
- (+) Zero database infrastructure
- (+) No data migration concerns
- (+) Smaller blast radius (no persistent sensitive data)
- (-) No report history or search
- (-) If Slack/Confluence delivery fails, the report is lost (no retry from stored state)
- Future: add SQLite or PostgreSQL for report persistence

---

## 12. Cross-Cutting Concerns

### 12.1 Logging

- Python `logging` module with hierarchical logger names (`scrum_master_agent.agent`, `scrum_master_agent.mcp_server`, etc.)
- `INFO` level: workflow start/end, tool calls made, delivery target, Slack post status
- `DEBUG` level: raw tool results, LangGraph state transitions
- `ERROR` level: tool failures, LLM errors, delivery failures
- No credentials logged (webhook URLs, API keys never appear in log output)

### 12.2 Error Handling Strategy

```
Layer          Error Type                     Handling
─────────────────────────────────────────────────────────────────
JiraClient     Network/HTTP errors            Retry 3× with backoff; raise on final
MCP tools      All exceptions                 Catch all → return {"error": "msg"} JSON
FETCH node     Tool returns {"error":...}      Set state["error"]; increment retry_count
FETCH node     retry_count >= 2               Route to ERROR_END
SYNTHESIZE     Pydantic validation error       Set state["error"]; route to END
DELIVER        Slack webhook HTTP error        Log error; do not retry; return error state
DELIVER        Confluence API error            Log error; fall back to "return" mode
```

### 12.3 Testing Strategy

| Level | Scope | Mocks |
|-------|-------|-------|
| Unit (MCP tools) | Individual tool functions | `mock_jira_client` fixture |
| Unit (models) | Pydantic validation, serialisation | No mocks |
| Unit (delivery) | Block Kit builder, webhook call | `mock_slack` fixture |
| Unit (nodes) | Each LangGraph node function | Mocked tool results, mocked LLM |
| Integration | Full workflow (sprint_status, weekly_recap) | Mocked Jira + Slack; real LangGraph |

No tests require real Jira credentials or Slack access.

### 12.4 Configuration Management

```
Source of truth:  .env file (local) / environment variables (production)
                       │
                       ▼
              pydantic-settings Settings class
                       │
                       ▼  get_settings() singleton
              Used by:  JiraClient, SlackDelivery, ConfluenceDelivery, Scheduler
```

**Settings validation at startup:** missing required variables raise `ValidationError` immediately — not at the first API call.

---

## 13. Architecture Constraints

| Constraint | Reason | Impact |
|------------|--------|--------|
| Python 3.11+ required | LangGraph + pydantic v2 type features | Dev environment must meet this version |
| Single board per workflow run | Simplicity for v1.0 | Multi-board requires workflow loop in caller |
| MCP transport = stdio only | MCP library default; simplest setup | MCP server runs as subprocess; cannot be deployed remotely without SSE transport |
| LLM = Claude Sonnet 4.6 only | Hardcoded in `langchain-anthropic` config | Changing model requires settings update |
| No concurrent workflow runs | APScheduler single-thread; no queue | Overlapping triggers (e.g., manual + scheduled) will queue behind each other |
| Jira Cloud only | atlassian-python-api targets Cloud REST v2 | Jira Server/Data Center would need separate client |
