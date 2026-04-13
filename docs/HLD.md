# High Level Design (HLD)
# Scrum Master Digital Worker

**Version:** 1.0
**Date:** 2026-04-13
**Status:** Approved
**Related Documents:** [LLD.md](LLD.md) | [Architecture Design Document](ADD.md)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Business Context & Objectives](#2-business-context--objectives)
3. [Scope](#3-scope)
4. [System Overview](#4-system-overview)
5. [High-Level Architecture](#5-high-level-architecture)
6. [Key Components](#6-key-components)
7. [Operational Workflows](#7-operational-workflows)
8. [Integration Points](#8-integration-points)
9. [Data Overview](#9-data-overview)
10. [Non-Functional Requirements](#10-non-functional-requirements)
11. [Security Overview](#11-security-overview)
12. [Deployment Overview](#12-deployment-overview)
13. [Technology Stack Rationale](#13-technology-stack-rationale)
14. [Risks & Mitigations](#14-risks--mitigations)
15. [Future Roadmap](#15-future-roadmap)

---

## 1. Executive Summary

The **Scrum Master Digital Worker** is an autonomous AI agent that automates the most repetitive and time-consuming responsibilities of a Scrum Master: collecting sprint data, analysing team health, identifying blockers, and distributing structured reports to stakeholders.

The system connects to Jira (read-only) through a Model Context Protocol (MCP) Server, reasons over the collected data using Claude Sonnet, and delivers formatted reports to Slack and optionally Confluence — all without human intervention.

| Metric | Value |
|--------|-------|
| Time saved per sprint | 30–60 minutes |
| Report latency | < 2 minutes (on-demand) |
| Blast radius | Low (read-only Jira; outbound webhook only) |
| Estimated monthly cost | $1–12 |

---

## 2. Business Context & Objectives

### Problem
Scrum Masters spend 30–60 minutes per sprint cycle manually:
1. Querying Jira for issue statuses, blockers, and workload distribution
2. Interpreting velocity trends and burndown data
3. Writing Sprint Status reports and Weekly Recaps in a consistent format
4. Distributing those reports via Slack or Confluence

This is repetitive, error-prone, and creates a lag between sprint events and stakeholder visibility.

### Business Objectives

| # | Objective | Success Measure |
|---|-----------|----------------|
| 1 | Eliminate manual sprint reporting | Zero manual data collection per sprint |
| 2 | Deliver timely, consistent reports | Report delivered within 2 min of trigger |
| 3 | Surface blockers proactively | All P1/P2 blockers flagged automatically |
| 4 | Provide velocity trend analysis | 5-sprint rolling velocity in every recap |
| 5 | Reduce tool-switching for Scrum Master | Single Slack channel for all sprint info |

### Stakeholders

| Stakeholder | Interest |
|-------------|---------|
| Scrum Master | Reduced manual work; confident reports |
| Development Team | Visibility into their sprint health |
| Product Owner | Sprint progress and risk signals |
| Engineering Manager | Velocity trends and delivery predictability |

---

## 3. Scope

### In Scope
- Automated Sprint Status report (on-demand)
- Automated Weekly Recap (scheduled, every Friday 17:00)
- Jira data collection via MCP tools (read-only)
- Delivery to Slack (primary) and Confluence (secondary)
- CLI and Python API entry points
- Unit and integration test coverage

### Out of Scope (v1.0)
- Slack slash command (`/sprint-status`) — future
- Human-in-the-loop approval before posting — future
- Multi-board support — future
- Email delivery — future
- Web UI / dashboard — future
- Jira webhook triggers — future

---

## 4. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              External Systems                                │
│                                                                              │
│   ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐   │
│   │   Jira Cloud     │     │      Slack        │     │   Confluence     │   │
│   │   REST API       │     │  Incoming Webhook │     │   REST API       │   │
│   │  (read-only)     │     │  (outbound only)  │     │  (page create)   │   │
│   └────────▲─────────┘     └────────▲──────────┘     └────────▲─────────┘   │
└────────────│──────────────────────────│───────────────────────│─────────────┘
             │ Jira API                 │ Webhook POST           │ REST
┌────────────│──────────────────────────│───────────────────────│─────────────┐
│            │         SCRUM MASTER DIGITAL WORKER               │             │
│  ┌─────────┴──────────┐   ┌───────────┴──────────────────────────────────┐  │
│  │    MCP Server      │   │              LangGraph Agent                  │  │
│  │  7 Jira Tools      │◀──│  PLAN → FETCH → SYNTHESIZE → DELIVER         │  │
│  │  (stdio transport) │   │  (Claude Sonnet 4.6)                          │  │
│  └────────────────────┘   └───────────────────────────────────────────────┘  │
│                                            ▲                                 │
│                        ┌───────────────────┴──────────────────────┐         │
│                        │  Triggers                                  │         │
│                        │  • CLI (poetry run sprint-status/weekly)  │         │
│                        │  • Python API (workflow functions)         │         │
│                        │  • APScheduler (Friday 17:00)             │         │
│                        └──────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
```

The system consists of two primary subsystems:
- **MCP Server** — a thin tool-layer that wraps Jira API calls and exposes them as typed JSON-RPC tools
- **LangGraph Agent** — a 4-node state machine that plans, fetches, synthesizes, and delivers reports

---

## 5. High-Level Architecture

### Layered Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  TRIGGER LAYER        CLI  │  Python API  │  APScheduler          │
├──────────────────────────────────────────────────────────────────┤
│  WORKFLOW LAYER       SprintStatusWorkflow │ WeeklyRecapWorkflow   │
├──────────────────────────────────────────────────────────────────┤
│  AGENT LAYER          LangGraph StateGraph (4 nodes)              │
│                       PLAN → FETCH → SYNTHESIZE → DELIVER         │
├──────────────────────────────────────────────────────────────────┤
│  TOOL LAYER           MCP Server (7 tools, stdio transport)       │
│                       LangChain-MCP Bridge (tool adapter)         │
├──────────────────────────────────────────────────────────────────┤
│  DATA ACCESS LAYER    JiraClient (singleton, retry+backoff)       │
├──────────────────────────────────────────────────────────────────┤
│  EXTERNAL SYSTEMS     Jira Cloud │ Slack │ Confluence             │
└──────────────────────────────────────────────────────────────────┘
```

### Data Flow (High Level)

```
Trigger
  │
  ▼
Workflow Entry Point
  │  (board_id, mode, delivery_target)
  ▼
LangGraph Agent
  ├── PLAN node      → decide which 4–6 MCP tools to call
  ├── FETCH node     → call MCP tools in parallel → raw JSON results
  ├── SYNTHESIZE node→ Claude Sonnet reads raw data → markdown narrative
  └── DELIVER node   → format for target → POST to Slack / Confluence / return
```

---

## 6. Key Components

### 6.1 MCP Server

**Purpose:** Provides a strict tool boundary between the agent and Jira. The agent never calls Jira APIs directly.

**Tools exposed:**

| Tool | Purpose |
|------|---------|
| `get_active_sprint` | Fetch current sprint metadata |
| `get_sprint_issues` | List issues with optional status filter |
| `get_sprint_burndown` | Daily remaining points |
| `get_blockers` | Issues flagged as blocked (JQL-based) |
| `get_team_workload` | Issues grouped by assignee |
| `get_sprint_velocity` | Rolling velocity over N closed sprints |
| `search_issues_by_jql` | Ad-hoc JQL search |

**Key guarantee:** All tools return a JSON string. On error, they return `{"error": "..."}` — they never raise exceptions to the agent.

### 6.2 LangGraph Agent

**Purpose:** Orchestrates the full reporting pipeline as a deterministic state machine.

**Nodes:**

| Node | Responsibility |
|------|---------------|
| PLAN | Determine workflow mode and which tools to invoke |
| FETCH | Invoke MCP tools (sprint first, rest in parallel); manage retries |
| SYNTHESIZE | Feed raw tool results to Claude Sonnet; extract structured counts; generate markdown |
| DELIVER | Route output to Slack, Confluence, or caller |

**State machine:**
```
START → PLAN → FETCH → SYNTHESIZE → DELIVER → END
                ↑    ↓ (tool error, retry < 2)
                └────┘
                ↓ (retry ≥ 2 or synthesis error)
             ERROR_END → END
```

### 6.3 Delivery Layer

| Target | Mechanism | Format |
|--------|-----------|--------|
| Slack | Incoming Webhook | Block Kit (sections, dividers, markdown) |
| Confluence | REST API | Page with HTML-wrapped markdown |
| Return | Python return value | SprintStatus / WeeklyRecap Pydantic object |

### 6.4 Scheduler

APScheduler `BlockingScheduler` fires `weekly_recap_job()` every Friday at 17:00 local time. Supports `--run-now` flag for immediate testing without waiting for the schedule.

### 6.5 Configuration

Pydantic-settings reads all credentials and settings from a `.env` file (or environment variables). A single `get_settings()` singleton is used throughout. Tests patch this singleton — no credentials needed for testing.

---

## 7. Operational Workflows

### 7.1 Sprint Status (On-Demand)

**Trigger:** `poetry run sprint-status --board-id <ID> [--delivery slack|confluence|return]`

**Steps:**
1. Call `run_sprint_status_query(board_id, delivery_target)`
2. Agent runs: PLAN → FETCH (4 tools) → SYNTHESIZE → DELIVER
3. Report delivered to target within ~90 seconds

**Tools used:** `get_active_sprint`, `get_sprint_issues`, `get_blockers`, `get_team_workload`

**Output:** `SprintStatus` — progress %, blocker count, team workload, markdown narrative

### 7.2 Weekly Recap (Scheduled)

**Trigger:** APScheduler (Friday 17:00) or `--run-now`

**Steps:**
1. Scheduler calls `run_weekly_recap(board_id, delivery_target)`
2. Agent runs: PLAN → FETCH (6 tools) → SYNTHESIZE → DELIVER
3. Full narrative posted to Slack/Confluence

**Tools used:** all 4 Sprint Status tools + `get_sprint_velocity`, `get_sprint_burndown`

**Output:** `WeeklyRecap` — velocity trend, burndown analysis, risks, recommendations

### 7.3 Retry & Error Handling

- FETCH node retries up to 2 times on tool errors
- After 2 retries, graph routes to `ERROR_END`
- MCP tools surface errors as JSON (never raise), preserving agent stability

---

## 8. Integration Points

| System | Direction | Protocol | Auth | Access Level |
|--------|-----------|----------|------|-------------|
| Jira Cloud | Inbound (read) | REST/HTTPS | Basic Auth (email + API token) | Read-only: boards, sprints, issues |
| Slack | Outbound (write) | HTTPS POST | Webhook URL (secret) | Post to one channel |
| Confluence | Outbound (write) | REST/HTTPS | Basic Auth (email + API token) | Create/update pages in one space |
| Anthropic API | Outbound | HTTPS | API key | Claude Sonnet inference |
| MCP Server | Internal | stdio (subprocess) | None | All 7 tools |

---

## 9. Data Overview

### Primary Data Entities

| Entity | Source | Storage |
|--------|--------|---------|
| `SprintStatus` | Jira (via MCP) | In-memory (LangGraph state) |
| `WeeklyRecap` | Jira + Claude synthesis | In-memory |
| `SprintIssue` | Jira issues API | In-memory |
| `BlockerReport` | Jira JQL | In-memory |
| `TeamWorkload` | Jira issues API | In-memory |
| `VelocityRecord` | Jira closed sprints | In-memory |

**Important:** No persistent database. All data is fetched live from Jira at report time. Reports are delivered and discarded — no report history is stored (v1.0).

### Data Sensitivity

| Data | Classification | Notes |
|------|---------------|-------|
| Jira credentials | Secret | Stored in `.env`, never logged |
| Slack webhook URL | Secret | Stored in `.env` |
| Anthropic API key | Secret | Stored in `.env` |
| Sprint/issue data | Internal | Read-only; not persisted |
| Generated reports | Internal | Sent to Slack/Confluence only |

---

## 10. Non-Functional Requirements

### Performance

| Requirement | Target |
|-------------|--------|
| Sprint Status report latency | < 2 minutes end-to-end |
| Weekly Recap report latency | < 3 minutes end-to-end |
| MCP tool response time | < 10 seconds per tool call |
| Parallel tool execution | 3–5 tools in parallel (FETCH node) |

### Reliability

| Requirement | Target |
|-------------|--------|
| Tool failure tolerance | Retry up to 2× before graceful degradation |
| Scheduler reliability | APScheduler with misfire grace = 30 min |
| Jira API failures | Exponential backoff (3 retries, 2× multiplier) |
| Weekly schedule uptime | 99% (depends on hosting environment) |

### Maintainability

- All Jira access isolated behind MCP tool boundary
- Each layer independently testable (unit + integration)
- Pydantic models enforce strict data contracts at every layer
- Configuration fully externalised (no hardcoded credentials or board IDs)

### Observability

- Python `logging` module with structured log lines at INFO/DEBUG
- Tool errors surfaced in agent state (`error` field)
- Slack delivery confirmation logged
- Retry count tracked in agent state

### Scalability (v1.0 limits)

- Single board per run
- Single Slack channel
- No concurrent workflow executions (single-process APScheduler)

---

## 11. Security Overview

### Threat Model

| Threat | Mitigation |
|--------|-----------|
| Credential leakage | Secrets in `.env` (not committed); env vars in production |
| Unauthorised Jira writes | Jira token scoped read-only; no write API calls |
| Prompt injection via Jira data | Claude Sonnet system prompt constrains behaviour; tool results are structured JSON, not freeform text |
| Webhook abuse | Webhook URL treated as secret; HTTPS only |
| Dependency compromise | `pyproject.toml` pins major versions; `poetry.lock` checksums |

### Blast Radius Assessment: **LOW**

- Jira access: read-only
- Slack: outbound webhook only (no message reads, no user data)
- Confluence: page creation only
- No user data collected or stored

---

## 12. Deployment Overview

### Local Development

```bash
cd "D:\neeraj\scrum master\scrum_master_agent"
poetry install
cp .env.example .env   # fill credentials
poetry run sprint-status --board-id <ID>
```

### Production Options

| Platform | Notes |
|----------|-------|
| Docker container | Single container, env vars from secrets manager |
| Railway / Render | Free tier sufficient; set env vars in dashboard |
| VM / bare metal | Run `poetry run python -m scrum_master_agent.scheduler.weekly_scheduler` as a systemd service |

### Runtime Dependencies

- Python 3.11+
- Poetry (dependency management)
- Network access to Jira Cloud, Slack, Anthropic API
- No database
- No message queue
- No external cache

---

## 13. Technology Stack Rationale

| Technology | Choice | Why |
|------------|--------|-----|
| Agent orchestration | LangGraph | Deterministic state machine with clear node boundaries; retry/error paths explicit in graph; easy to test individual nodes |
| LLM | Claude Sonnet 4.6 | Long-context, strong instruction-following; cost-effective for structured output tasks |
| Tool protocol | MCP (Model Context Protocol) | Standard, transport-agnostic tool interface; decouples agent from Jira client; enables independent tool testing |
| MCP ↔ LangChain | langchain-mcp-adapters | Official bridge; converts MCP tools to LangChain `Tool` objects with zero glue code |
| Data models | Pydantic v2 | Strict validation; JSON (de)serialisation; IDE autocomplete across all layers |
| Config | pydantic-settings | `.env` file + env var override; type-safe settings singleton |
| Scheduler | APScheduler | Lightweight in-process scheduler; no Redis/Celery needed for a single weekly job |
| Jira client | atlassian-python-api | Official Atlassian SDK; handles auth, pagination, and REST client boilerplate |
| Delivery | slack-sdk | Official Slack SDK; Block Kit formatting for rich messages |
| Tests | pytest + pytest-asyncio | Async-compatible; fixtures for mock Jira/Slack; no real credentials needed |

---

## 14. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Jira API rate limiting | Medium | Medium | Exponential backoff in JiraClient; batch tool calls |
| Claude Sonnet API outage | Low | High | Graceful error in SYNTHESIZE node; no partial posts |
| Slack webhook URL rotation | Low | Medium | Store in env var; update without code change |
| Malformed Jira data causing synthesis errors | Low | Medium | Pydantic validation in MCP tools; `{"error": ...}` fallback |
| Scheduler misfire (host restart) | Medium | Low | `misfire_grace_time=1800`; missed jobs do not cascade |
| LLM hallucinating sprint metrics | Low | High | Deterministic metric extraction from raw tool results; LLM only writes narrative prose |

---

## 15. Future Roadmap

| Feature | Priority | Notes |
|---------|----------|-------|
| Slack slash command (`/sprint-status`) | High | Needs Slack app with slash command config |
| Human-in-the-loop approval | Medium | LangGraph `interrupt` node before DELIVER |
| Multi-board support | Medium | Pass list of `board_id`; aggregate or separate reports |
| Jira webhook trigger | Medium | Fire on sprint start/close events |
| Email delivery channel | Low | Add `email_delivery.py` alongside Slack |
| Web UI / report history | Low | Persist reports to DB; read via Flask/FastAPI dashboard |
| SSE transport for MCP | Low | Replace stdio with HTTP+SSE for remote MCP deployment |
| Confluence structured output | Low | Proper Confluence page template vs. wrapped markdown |
