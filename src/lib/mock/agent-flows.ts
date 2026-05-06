import { AgentFlow, AgentStep, ActivityItem, ChatMessage } from "../types";

export function createBlockerFetchFlow(): AgentFlow {
  return {
    id: "flow-1",
    query: "Fetch all current sprint blockers",
    startedAt: new Date().toISOString(),
    totalDurationMs: 2340,
    steps: [
      {
        id: "s1",
        tool: "natural_language_processor",
        label: "Parse Query",
        description: "Analyzing request to identify intent: fetch blockers for active sprint",
        status: "completed",
        durationMs: 120,
        request: '{ "input": "Fetch all current sprint blockers", "intent": "blocker_retrieval" }',
        response: '{ "intent": "blocker_retrieval", "filters": { "sprint": "current", "type": "blocker" } }',
      },
      {
        id: "s2",
        tool: "jira_rest_api",
        label: "Query Jira",
        description: 'Searching Jira for issues with type=blocker in Sprint 24 using JQL: project=PLAT AND type=Impediment AND sprint="Sprint 24"',
        status: "completed",
        durationMs: 850,
        request: 'GET /rest/api/3/search?jql=project%3DPLAT%20AND%20type%3DImpediment%20AND%20sprint%3D%22Sprint%2024%22',
        response: '{ "total": 5, "issues": [...] }',
      },
      {
        id: "s3",
        tool: "rally_web_services",
        label: "Query Rally",
        description: "Fetching Rally defects and blocked stories for current iteration via WSAPI",
        status: "completed",
        durationMs: 720,
        request: 'GET /slm/webservice/v2.0/defect?query=(Blocked = true)&fetch=Name,State,Owner',
        response: '{ "QueryResult": { "TotalResultCount": 3, "Results": [...] } }',
      },
      {
        id: "s4",
        tool: "data_aggregator",
        label: "Merge & Deduplicate",
        description: "Combining results from Jira and Rally, deduplicating cross-linked items, normalizing priority levels",
        status: "completed",
        durationMs: 180,
        request: '{ "jiraResults": 5, "rallyResults": 3, "dedupeKey": "externalLink" }',
        response: '{ "totalUnique": 8, "duplicatesRemoved": 0 }',
      },
      {
        id: "s5",
        tool: "data_aggregator",
        label: "Enrich & Rank",
        description: "Calculating age, attaching team member profiles, ranking by priority and age",
        status: "completed",
        durationMs: 470,
        request: '{ "operation": "enrich", "items": 8 }',
        response: '{ "enriched": 8, "criticalCount": 3, "avgAgeDays": 5.5 }',
      },
    ],
  };
}

export function createSprintReportFlow(): AgentFlow {
  return {
    id: "flow-2",
    query: "Generate sprint progress report",
    startedAt: new Date().toISOString(),
    totalDurationMs: 1980,
    steps: [
      {
        id: "s1",
        tool: "natural_language_processor",
        label: "Parse Query",
        description: "Identified intent: sprint report generation for active sprint",
        status: "completed",
        durationMs: 95,
      },
      {
        id: "s2",
        tool: "jira_rest_api",
        label: "Fetch Sprint Data",
        description: "Retrieving sprint board data including story points, status transitions, and completion metrics",
        status: "completed",
        durationMs: 680,
        request: "GET /rest/agile/1.0/board/42/sprint/24",
        response: '{ "sprint": { "id": 24, "state": "active", "goal": "..." } }',
      },
      {
        id: "s3",
        tool: "rally_web_services",
        label: "Fetch Iteration Data",
        description: "Pulling iteration cumulative flow data and accepted story counts",
        status: "completed",
        durationMs: 590,
        request: "GET /slm/webservice/v2.0/iteration?query=(Name = Sprint 24)",
        response: '{ "QueryResult": { "Results": [...] } }',
      },
      {
        id: "s4",
        tool: "data_aggregator",
        label: "Compute Metrics",
        description: "Calculating burndown, velocity, completion rate, and carryover items",
        status: "completed",
        durationMs: 250,
      },
      {
        id: "s5",
        tool: "chart_builder",
        label: "Build Visualizations",
        description: "Generating burndown chart, velocity trend, and sprint summary cards",
        status: "completed",
        durationMs: 365,
      },
    ],
  };
}

export function createChatResponseFlow(query: string): AgentFlow {
  const isBlockerQuery = query.toLowerCase().includes("blocker");
  const isSprintQuery = query.toLowerCase().includes("sprint") || query.toLowerCase().includes("velocity");

  const steps: AgentStep[] = [
    {
      id: "cs1",
      tool: "natural_language_processor",
      label: "Understand Query",
      description: `Parsing: "${query}"`,
      status: "completed",
      durationMs: 110,
    },
    {
      id: "cs2",
      tool: "cache_lookup",
      label: "Check Cache",
      description: "Looking for recent data that matches this query to avoid redundant API calls",
      status: "completed",
      durationMs: 45,
      response: '{ "hit": false }',
    },
  ];

  if (isBlockerQuery) {
    steps.push(
      {
        id: "cs3",
        tool: "jira_rest_api",
        label: "Search Jira Blockers",
        description: "Querying Jira for impediments and blocked issues in current sprint",
        status: "completed",
        durationMs: 780,
        request: "GET /rest/api/3/search?jql=type=Impediment AND sprint=currentSprint()",
        response: '{ "total": 5 }',
      },
      {
        id: "cs4",
        tool: "rally_web_services",
        label: "Search Rally Blockers",
        description: "Querying Rally for blocked user stories and defects",
        status: "completed",
        durationMs: 650,
      }
    );
  } else if (isSprintQuery) {
    steps.push({
      id: "cs3",
      tool: "jira_rest_api",
      label: "Fetch Sprint Metrics",
      description: "Pulling sprint board data, story points, and completion status",
      status: "completed",
      durationMs: 720,
    });
  } else {
    steps.push(
      {
        id: "cs3",
        tool: "jira_rest_api",
        label: "Query Jira",
        description: "Running adaptive search based on query context",
        status: "completed",
        durationMs: 600,
      },
      {
        id: "cs4",
        tool: "rally_web_services",
        label: "Query Rally",
        description: "Cross-referencing with Rally for additional context",
        status: "completed",
        durationMs: 500,
      }
    );
  }

  steps.push({
    id: "cs-final",
    tool: "data_aggregator",
    label: "Format Response",
    description: "Aggregating results and formatting for display",
    status: "completed",
    durationMs: 200,
  });

  return {
    id: `flow-chat-${Date.now()}`,
    query,
    startedAt: new Date().toISOString(),
    totalDurationMs: steps.reduce((sum, s) => sum + s.durationMs, 0),
    steps,
  };
}

export const recentActivity: ActivityItem[] = [
  {
    id: "a1",
    action: "Fetched blockers",
    detail: "Retrieved 8 blockers from Jira and Rally for Sprint 24",
    tool: "jira_rest_api",
    timestamp: "2026-05-06T10:30:00Z",
  },
  {
    id: "a2",
    action: "Updated sprint report",
    detail: "Generated burndown and velocity charts with latest data",
    tool: "chart_builder",
    timestamp: "2026-05-06T10:15:00Z",
  },
  {
    id: "a3",
    action: "Synced Rally data",
    detail: "Pulled 3 blocked stories and 2 defects from Rally iteration",
    tool: "rally_web_services",
    timestamp: "2026-05-06T09:45:00Z",
  },
  {
    id: "a4",
    action: "Escalation alert",
    detail: "Auto-escalated PLAT-2847 — blocker age exceeded 7 days with critical priority",
    tool: "data_aggregator",
    timestamp: "2026-05-06T09:00:00Z",
  },
  {
    id: "a5",
    action: "Cross-reference check",
    detail: "Verified dependency links between Jira PLAT-2860 and Rally DE4521",
    tool: "data_aggregator",
    timestamp: "2026-05-06T08:30:00Z",
  },
];

export const predefinedChatResponses: Record<string, ChatMessage> = {
  blockers: {
    id: "msg-resp-1",
    role: "agent",
    content: "I found **8 blockers** in Sprint 24. Here's the breakdown:\n\n- **3 Critical**: CI/CD pipeline (8d), Search API regression (7d), SSO token issues (2d)\n- **3 High**: API rate limiting (6d), DB migration conflict (4d), Library version mismatch (5d)\n- **1 Medium**: Design handoff incomplete (3d)\n- **1 Resolved**: Rally sync job (fixed)\n\nThe most urgent is the **CI/CD pipeline blocker** (PLAT-2847) — it's been escalated and is 8 days old. The **search API regression** (PLAT-2860) is also critical and affecting production latency.",
    timestamp: new Date().toISOString(),
    richData: [
      {
        type: "metric",
        title: "Blocker Summary",
        data: { critical: 3, high: 3, medium: 1, resolved: 1, avgAge: "5.5 days" },
      },
    ],
  },
  sprint: {
    id: "msg-resp-2",
    role: "agent",
    content: "**Sprint 24 Progress Report:**\n\nWe're on Day 9 of 13. The team has completed **34 of 55 points** (62%). At current velocity, we're tracking slightly behind the ideal burndown.\n\n- **Committed**: 18 items (55 pts)\n- **Completed**: 11 items (34 pts)\n- **In Progress**: 4 items (13 pts)\n- **Carryover Risk**: 3 items (8 pts)\n\nVelocity trend over last 4 sprints averages **46.3 pts**, suggesting we may carry over some work.",
    timestamp: new Date().toISOString(),
    richData: [
      {
        type: "sprint_summary",
        title: "Sprint 24",
        data: { progress: 62, completed: 34, total: 55, daysLeft: 4 },
      },
    ],
  },
  team: {
    id: "msg-resp-3",
    role: "agent",
    content: "**Team Workload Analysis for Sprint 24:**\n\n| Member | Assigned | Blocked | Status |\n|--------|----------|---------|--------|\n| Sarah Chen | 3 items | 1 (SSO) | Actively working on auth fix |\n| James Wilson | 4 items | 2 (DB, Search) | Needs support on ES migration |\n| Priya Patel | 3 items | 1 (Design) | Waiting on UX team |\n| Mike Torres | 2 items | 1 (Rate limit) | Testing workaround |\n| Emma Davis | 3 items | 1 (CI/CD) | Escalated to cloud team |\n| Alex Kim | 3 items | 1 (Library) | Coordinating version bump |\n\nJames Wilson has the heaviest blocker load — consider pairing him with Alex on the Elasticsearch query migration.",
    timestamp: new Date().toISOString(),
  },
};
