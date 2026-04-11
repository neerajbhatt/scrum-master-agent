# CLAUDE.md — Scrum Master Digital Worker

This file gives Claude full context about this project so any new conversation
can pick up immediately without re-exploration.

---

## What This Project Is

A **Scrum Master Digital Worker** — an autonomous Python agent that replaces
manual sprint reporting. It reads Jira data through an MCP Server, reasons over
it with Claude Sonnet via LangGraph, and delivers Sprint Status reports and
Weekly Recaps to Slack (and optionally Confluence).

**Role modelled:** Scrum Master
**Job automated:** Prepare Sprint Status + Weekly Recap
**Blast radius:** Low (read-only Jira, outbound Slack webhook only)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent orchestration | LangGraph (StateGraph with 4 nodes) |
| LLM | Claude Sonnet 4.6 (via langchain-anthropic) |
| Tool protocol | MCP (Model Context Protocol) — stdio transport |
| MCP ↔ LangChain | langchain-mcp-adapters (MultiServerMCPClient) |
| Jira API | atlassian-python-api |
| Data models | Pydantic v2 |
| Config | pydantic-settings + .env |
| Scheduler | APScheduler (BlockingScheduler, Friday 17:00) |
| Delivery | slack-sdk (webhook), atlassian Confluence (optional) |
| Tests | pytest + pytest-asyncio |
| Python | 3.11+ (3.13 on dev machine) |

---

## Project Structure

```
D:\neeraj\scrum master\
├── CLAUDE.md                          ← this file
├── scrum_master_agent/                ← main package
│   ├── pyproject.toml
│   ├── .env.example                   ← copy to .env and fill credentials
│   ├── LLD.md                         ← full Low-Level Design document
│   ├── LLD_Scrum_Master_Digital_Worker.docx  ← Word version of LLD
│   ├── Architecture_Diagrams.docx     ← 4 architecture diagrams in Word
│   │
│   ├── config/settings.py             ← Pydantic BaseSettings singleton (get_settings())
│   │
│   ├── models/                        ← All Pydantic data models
│   │   ├── sprint.py                  ← IssueStatus, IssueType, SprintIssue, SprintStatus, SprintSummary
│   │   ├── blockers.py                ← BlockerSeverity, BlockerItem, BlockerReport
│   │   ├── team.py                    ← TeamMember, MemberWorkload, TeamWorkload, VelocityRecord
│   │   └── recap.py                   ← RecapSection, WeeklyRecap
│   │
│   ├── mcp_server/                    ← MCP Server (Jira tool layer)
│   │   ├── server.py                  ← Entry point — 7 tools registered via JSON-RPC
│   │   ├── jira_client.py             ← JiraClient singleton, _retry() backoff, get_jira_client()
│   │   └── tools/
│   │       ├── sprint_tools.py        ← get_active_sprint, get_sprint_issues, get_sprint_burndown
│   │       ├── blocker_tools.py       ← get_blockers (JQL + severity mapping)
│   │       ├── team_tools.py          ← get_team_workload (group by assignee)
│   │       ├── velocity_tools.py      ← get_sprint_velocity (N closed sprints)
│   │       └── search_tools.py        ← search_issues_by_jql
│   │
│   ├── agent/                         ← LangGraph agent
│   │   ├── state.py                   ← AgentState TypedDict, WorkflowMode enum
│   │   ├── graph.py                   ← StateGraph + compiled_graph (import this)
│   │   ├── tools_bridge.py            ← MultiServerMCPClient → LangChain tools (cached)
│   │   ├── nodes/
│   │   │   ├── plan_node.py           ← Sets tool_calls_planned, init messages
│   │   │   ├── fetch_node.py          ← Runs MCP tools (sprint first, rest parallel)
│   │   │   ├── synthesize_node.py     ← LLM call → SprintStatus or WeeklyRecap
│   │   │   └── deliver_node.py        ← Routes to Slack/Confluence/return
│   │   └── prompts/
│   │       ├── system_prompt.py       ← SYSTEM_PROMPT (Scrum Master persona)
│   │       ├── tool_use_prompt.py     ← Per-mode tool plans
│   │       └── output_format_prompt.py← Report format templates
│   │
│   ├── delivery/
│   │   ├── slack_delivery.py          ← SlackDelivery, Block Kit formatting
│   │   └── confluence_delivery.py     ← ConfluenceDelivery (optional)
│   │
│   ├── scheduler/
│   │   └── weekly_scheduler.py        ← APScheduler, weekly_recap_job(), --run-now flag
│   │
│   ├── workflows/                     ← Public entry points
│   │   ├── sprint_status_workflow.py  ← run_sprint_status_query(board_id, delivery_target)
│   │   └── weekly_recap_workflow.py   ← run_weekly_recap(board_id, delivery_target)
│   │
│   └── tests/
│       ├── conftest.py                ← mock_jira_client, mock_slack, sample fixtures
│       ├── unit/                      ← test_sprint_tools, blockers, team, velocity, models, delivery
│       └── integration/               ← test_sprint_status_workflow, test_weekly_recap_workflow
│
├── generate_lld_doc.py                ← Script: LLD.md → Word doc
└── generate_architecture_diagram.py   ← Script: 4 architecture diagrams → Word doc
```

---

## Two Workflows

### Sprint Status (On-Demand)
```
Trigger → PLAN (4 tools) → FETCH (parallel MCP calls) → SYNTHESIZE (Claude) → DELIVER → SprintStatus
Tools: get_active_sprint, get_sprint_issues, get_blockers, get_team_workload
```

### Weekly Recap (Scheduled — every Friday 17:00)
```
APScheduler → PLAN (6 tools) → FETCH (parallel) → SYNTHESIZE (Claude) → DELIVER → WeeklyRecap
Tools: above + get_sprint_velocity, get_sprint_burndown
```

---

## LangGraph State Machine

```
START → PLAN → FETCH → SYNTHESIZE → DELIVER → END
               ↑  ↓ error (retry < 2)
               └──┘
               ↓ error (retry ≥ 2) or synthesis error
            ERROR_END → END
```

**AgentState key fields:**
- `mode` — WorkflowMode.SPRINT_STATUS or WEEKLY_RECAP
- `board_id` — Jira board ID
- `sprint_id` — resolved by fetch_node from get_active_sprint
- `tool_results` — dict of tool_name → JSON string
- `sprint_status` / `weekly_recap` — populated by synthesize_node
- `delivery_target` — "slack" | "confluence" | "return"
- `error` — set on tool failure; triggers retry logic
- `retry_count` — max 2 retries before ERROR_END

---

## MCP Server — 7 Tools

| Tool | Inputs | Output |
|------|--------|--------|
| `get_active_sprint` | `board_id` | SprintStatus JSON |
| `get_sprint_issues` | `sprint_id`, `status_filter?` | list[SprintIssue] JSON |
| `get_sprint_burndown` | `sprint_id` | {date: remaining_pts} |
| `get_blockers` | `sprint_id`, `board_id` | BlockerReport JSON |
| `get_team_workload` | `sprint_id` | TeamWorkload JSON |
| `get_sprint_velocity` | `board_id`, `n_sprints=5` | list[VelocityRecord] JSON |
| `search_issues_by_jql` | `jql`, `max_results=50` | list[SprintIssue] JSON |

All tools return `{"error": "..."}` JSON on failure (never raise to the agent).

---

## Key Design Rules (do not violate)

1. **Agent never calls Jira directly** — all Jira access through MCP tools only
2. **MCP tools never raise** — always return JSON string, errors as `{"error": "..."}`
3. **Deterministic data extraction** — SprintStatus/counts computed from raw tool results, NOT from LLM output. LLM only generates the markdown narrative.
4. **JiraClient is a singleton** — `get_jira_client()` — do not instantiate directly
5. **Settings is a singleton** — `get_settings()` — tests patch this
6. **MCP tools are cached** — `get_mcp_tools()` caches; call `reset_mcp_tools()` in tests

---

## Environment Variables Required

```bash
# Jira (all required)
JIRA_URL=https://yourorg.atlassian.net
JIRA_EMAIL=you@yourorg.com
JIRA_API_TOKEN=<Atlassian API token from id.atlassian.net/manage-api-tokens>
JIRA_BOARD_ID=<your board ID from Jira board URL>

# LLM
ANTHROPIC_API_KEY=sk-ant-...

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_CHANNEL=#sprint-updates

# Optional — Confluence
CONFLUENCE_URL=https://yourorg.atlassian.net/wiki
CONFLUENCE_SPACE_KEY=PROJ
CONFLUENCE_PARENT_PAGE_ID=123456
```

---

## Running the Project

```bash
cd "D:\neeraj\scrum master\scrum_master_agent"

# Install dependencies
poetry install

# Verify MCP server (lists 7 tools)
poetry run mcp dev scrum_master_agent/mcp_server/server.py

# Sprint Status — print JSON
poetry run sprint-status --board-id 1

# Sprint Status — post to Slack
poetry run sprint-status --board-id 1 --delivery slack

# Weekly Recap — dry run (markdown to stdout, no Slack post)
poetry run weekly-recap --board-id 1 --dry-run

# Weekly Recap — post to Slack
poetry run weekly-recap --board-id 1 --delivery slack

# Start scheduler (runs every Friday 17:00)
poetry run python -m scrum_master_agent.scheduler.weekly_scheduler

# Trigger scheduler immediately (for testing)
poetry run python -m scrum_master_agent.scheduler.weekly_scheduler --run-now

# Run all tests (no real Jira/Slack needed — all mocked)
poetry run pytest tests/ -v
```

---

## Documents Generated

| File | Description |
|------|-------------|
| `LLD.md` | Full Low-Level Design (21 sections, Markdown) |
| `LLD_Scrum_Master_Digital_Worker.docx` | Word version of LLD with cover page, tables, code blocks |
| `Architecture_Diagrams.docx` | 4 architecture diagrams: System, LangGraph FSM, MCP Tool Layer, Data Flow Sequence |

To regenerate the Word documents:
```bash
cd "D:\neeraj\scrum master"
python generate_lld_doc.py
python generate_architecture_diagram.py
```

---

## What Is NOT Yet Done (Future Work)

- [ ] Slack slash command trigger (`/sprint-status`) — currently CLI/API only
- [ ] Human-in-the-loop approval before posting (LangGraph interrupt node)
- [ ] Confluence structured output (currently wraps markdown in code block)
- [ ] SSE transport for MCP server (currently stdio only)
- [ ] Dashboard / web UI for report history
- [ ] Jira webhook trigger (fire on sprint start/end events)
- [ ] Multi-board support (currently single board_id per run)
- [ ] Email delivery channel

---

## Costs

| Service | Est. Monthly |
|---------|-------------|
| Anthropic API (Claude Sonnet) | ~$1–5 |
| Jira Cloud | Already paying |
| Slack Webhook | Free |
| Hosting (Railway/Render/Docker) | $0–7 |
| **Total** | **~$1–12/month** |
