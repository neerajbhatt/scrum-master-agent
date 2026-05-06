import { AgentToolType } from "@/lib/types";
import { Database, Globe, Layers, BarChart3, Brain, HardDrive } from "lucide-react";

const toolConfig: Record<AgentToolType, { label: string; color: string; icon: React.ComponentType<{ className?: string }> }> = {
  jira_rest_api: { label: "Jira REST API", color: "bg-blue-500/15 text-blue-400 border-blue-500/30", icon: Globe },
  rally_web_services: { label: "Rally WSAPI", color: "bg-orange-500/15 text-orange-400 border-orange-500/30", icon: Database },
  data_aggregator: { label: "Data Aggregator", color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30", icon: Layers },
  chart_builder: { label: "Chart Builder", color: "bg-purple-500/15 text-purple-400 border-purple-500/30", icon: BarChart3 },
  natural_language_processor: { label: "NLP Engine", color: "bg-pink-500/15 text-pink-400 border-pink-500/30", icon: Brain },
  cache_lookup: { label: "Cache", color: "bg-gray-500/15 text-gray-400 border-gray-500/30", icon: HardDrive },
};

export default function ToolBadge({ tool, size = "sm" }: { tool: AgentToolType; size?: "sm" | "md" }) {
  const config = toolConfig[tool];
  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 border rounded-full font-medium ${config.color} ${
        size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs"
      }`}
    >
      <Icon className={size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5"} />
      {config.label}
    </span>
  );
}
