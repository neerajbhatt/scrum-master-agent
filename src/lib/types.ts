// ---- Blocker Types ----
export type BlockerStatus = "new" | "in_progress" | "escalated" | "resolved";
export type Priority = "critical" | "high" | "medium" | "low";
export type DataSource = "jira" | "rally";

export interface Blocker {
  id: string;
  title: string;
  description: string;
  status: BlockerStatus;
  priority: Priority;
  assignee: TeamMember;
  reporter: TeamMember;
  source: DataSource;
  sourceId: string; // e.g. JIRA-1234 or US12345
  sprint: string;
  createdAt: string;
  updatedAt: string;
  ageDays: number;
  tags: string[];
  linkedItems: string[];
}

export interface TeamMember {
  id: string;
  name: string;
  avatar: string; // initials-based
  role: string;
}

// ---- Sprint / Report Types ----
export interface Sprint {
  id: string;
  name: string;
  startDate: string;
  endDate: string;
  status: "active" | "completed" | "planned";
  totalPoints: number;
  completedPoints: number;
  committedItems: number;
  completedItems: number;
  carryoverItems: number;
}

export interface BurndownDataPoint {
  day: string;
  ideal: number;
  actual: number;
}

export interface VelocityDataPoint {
  sprint: string;
  committed: number;
  completed: number;
}

// ---- Agent Flow Types ----
export type AgentToolType =
  | "jira_rest_api"
  | "rally_web_services"
  | "data_aggregator"
  | "chart_builder"
  | "natural_language_processor"
  | "cache_lookup";

export type AgentStepStatus = "pending" | "running" | "completed" | "error";

export interface AgentStep {
  id: string;
  tool: AgentToolType;
  label: string;
  description: string;
  status: AgentStepStatus;
  durationMs: number;
  request?: string;
  response?: string;
}

export interface AgentFlow {
  id: string;
  query: string;
  steps: AgentStep[];
  totalDurationMs: number;
  startedAt: string;
}

// ---- Chat Types ----
export interface ChatMessage {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: string;
  agentFlow?: AgentFlow;
  richData?: RichDataCard[];
}

export interface RichDataCard {
  type: "blockers" | "sprint_summary" | "metric";
  title: string;
  data: Record<string, unknown>;
}

// ---- Blocker Action Types ----
export type ActionCategory = "agent" | "human";
export type ActionUrgency = "recommended" | "optional" | "info";

export interface BlockerAction {
  id: string;
  category: ActionCategory;
  label: string;
  description: string;
  urgency: ActionUrgency;
  icon: string; // lucide icon name key
  estimatedImpact?: string;
  tool?: AgentToolType; // which tool the agent would use
}

// ---- Activity Types ----
export interface ActivityItem {
  id: string;
  action: string;
  detail: string;
  tool: AgentToolType;
  timestamp: string;
}
