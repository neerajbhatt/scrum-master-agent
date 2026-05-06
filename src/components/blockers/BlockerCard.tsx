"use client";

import { Blocker } from "@/lib/types";
import { Clock, ExternalLink, Zap, ChevronRight } from "lucide-react";
import { getActionsForBlocker } from "@/lib/mock/actions";
import ToolBadge from "../agent/ToolBadge";

const priorityStyles = {
  critical: "border-l-danger bg-danger/5",
  high: "border-l-warning bg-warning/5",
  medium: "border-l-accent bg-accent/5",
  low: "border-l-muted bg-muted/5",
};

const priorityBadge = {
  critical: "bg-danger/15 text-danger",
  high: "bg-warning/15 text-warning",
  medium: "bg-accent/15 text-accent-light",
  low: "bg-muted/15 text-muted",
};

export default function BlockerCard({
  blocker,
  onClick,
}: {
  blocker: Blocker;
  onClick?: () => void;
}) {
  const actions = getActionsForBlocker(blocker.id);
  const recommendedCount = actions.filter((a) => a.urgency === "recommended").length;
  const agentActionCount = actions.filter((a) => a.category === "agent").length;

  return (
    <div
      onClick={onClick}
      className={`rounded-lg border border-border border-l-4 ${priorityStyles[blocker.priority]} p-3 cursor-pointer hover:border-accent/30 transition-all group`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className="text-sm font-medium text-foreground leading-tight group-hover:text-accent-light transition-colors line-clamp-2">
          {blocker.title}
        </h3>
      </div>

      {/* Source ID + Priority */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-mono text-muted flex items-center gap-1">
          <ExternalLink className="w-3 h-3" />
          {blocker.sourceId}
        </span>
        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium uppercase ${priorityBadge[blocker.priority]}`}>
          {blocker.priority}
        </span>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-1 mb-2.5">
        {blocker.tags.slice(0, 3).map((tag) => (
          <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-card-hover text-muted">
            {tag}
          </span>
        ))}
      </div>

      {/* Actions hint */}
      {blocker.status !== "resolved" && (
        <div className="flex items-center gap-1.5 mb-2.5 px-2 py-1.5 rounded-md bg-accent/5 border border-accent/10">
          <Zap className="w-3 h-3 text-accent-light flex-shrink-0" />
          <span className="text-[10px] text-accent-light font-medium">
            {agentActionCount} agent action{agentActionCount !== 1 ? "s" : ""}
          </span>
          {recommendedCount > 0 && (
            <>
              <span className="text-[10px] text-muted">&middot;</span>
              <span className="text-[10px] text-warning font-medium">
                {recommendedCount} recommended
              </span>
            </>
          )}
          <ChevronRight className="w-3 h-3 text-muted ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-border/50">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-full bg-accent/20 flex items-center justify-center text-[9px] font-medium text-accent-light">
            {blocker.assignee.avatar}
          </div>
          <span className="text-xs text-muted">{blocker.assignee.name.split(" ")[0]}</span>
        </div>
        <div className="flex items-center gap-2">
          <ToolBadge tool={blocker.source === "jira" ? "jira_rest_api" : "rally_web_services"} size="sm" />
          <span className="flex items-center gap-1 text-xs text-muted">
            <Clock className="w-3 h-3" />
            {blocker.ageDays}d
          </span>
        </div>
      </div>
    </div>
  );
}
