"use client";

import { Priority, DataSource } from "@/lib/types";
import { Filter, X } from "lucide-react";

interface FilterState {
  priority: Priority | "all";
  source: DataSource | "all";
  assignee: string;
}

export default function BlockerFilters({
  filters,
  onFilterChange,
}: {
  filters: FilterState;
  onFilterChange: (f: FilterState) => void;
}) {
  const hasActiveFilters = filters.priority !== "all" || filters.source !== "all" || filters.assignee !== "";

  return (
    <div className="flex items-center gap-3 flex-wrap">
      <div className="flex items-center gap-1.5 text-sm text-muted">
        <Filter className="w-4 h-4" />
        <span className="font-medium">Filters</span>
      </div>

      {/* Priority */}
      <select
        value={filters.priority}
        onChange={(e) => onFilterChange({ ...filters, priority: e.target.value as Priority | "all" })}
        className="bg-card border border-border rounded-lg px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent"
      >
        <option value="all">All Priorities</option>
        <option value="critical">Critical</option>
        <option value="high">High</option>
        <option value="medium">Medium</option>
        <option value="low">Low</option>
      </select>

      {/* Source */}
      <select
        value={filters.source}
        onChange={(e) => onFilterChange({ ...filters, source: e.target.value as DataSource | "all" })}
        className="bg-card border border-border rounded-lg px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent"
      >
        <option value="all">All Sources</option>
        <option value="jira">Jira</option>
        <option value="rally">Rally</option>
      </select>

      {/* Clear */}
      {hasActiveFilters && (
        <button
          onClick={() => onFilterChange({ priority: "all", source: "all", assignee: "" })}
          className="flex items-center gap-1 text-xs text-accent-light hover:text-accent transition-colors"
        >
          <X className="w-3 h-3" />
          Clear
        </button>
      )}
    </div>
  );
}

export type { FilterState };
