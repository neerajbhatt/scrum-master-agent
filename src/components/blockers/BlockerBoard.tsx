"use client";

import { useState } from "react";
import { Blocker, BlockerStatus } from "@/lib/types";
import BlockerCard from "./BlockerCard";
import BlockerFilters, { FilterState } from "./BlockerFilters";
import AgentFlowPanel from "../agent/AgentFlowPanel";
import { createBlockerFetchFlow } from "@/lib/mock/agent-flows";
import { motion, AnimatePresence } from "framer-motion";
import { X, Zap } from "lucide-react";
import BlockerActions from "./BlockerActions";
import { getActionsForBlocker } from "@/lib/mock/actions";

const columns: { status: BlockerStatus; label: string; dotColor: string }[] = [
  { status: "new", label: "New", dotColor: "bg-blue-400" },
  { status: "in_progress", label: "In Progress", dotColor: "bg-warning" },
  { status: "escalated", label: "Escalated", dotColor: "bg-danger" },
  { status: "resolved", label: "Resolved", dotColor: "bg-success" },
];

export default function BlockerBoard({ blockers }: { blockers: Blocker[] }) {
  const [filters, setFilters] = useState<FilterState>({
    priority: "all",
    source: "all",
    assignee: "",
  });
  const [selectedBlocker, setSelectedBlocker] = useState<Blocker | null>(null);
  const [showFlow, setShowFlow] = useState(false);

  const filtered = blockers.filter((b) => {
    if (filters.priority !== "all" && b.priority !== filters.priority) return false;
    if (filters.source !== "all" && b.source !== filters.source) return false;
    return true;
  });

  return (
    <div>
      {/* Filters + Flow toggle */}
      <div className="flex items-center justify-between mb-4">
        <BlockerFilters filters={filters} onFilterChange={setFilters} />
        <button
          onClick={() => setShowFlow(!showFlow)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            showFlow
              ? "bg-accent/15 text-accent-light border border-accent/30"
              : "bg-card border border-border text-muted hover:text-foreground"
          }`}
        >
          <Zap className="w-3.5 h-3.5" />
          {showFlow ? "Hide" : "Show"} Agent Flow
        </button>
      </div>

      {/* Agent Flow Panel */}
      <AnimatePresence>
        {showFlow && (
          <div className="mb-4">
            <AgentFlowPanel flow={createBlockerFetchFlow()} onClose={() => setShowFlow(false)} />
          </div>
        )}
      </AnimatePresence>

      {/* Kanban Board */}
      <div className="grid grid-cols-4 gap-4">
        {columns.map((col) => {
          const colBlockers = filtered.filter((b) => b.status === col.status);
          return (
            <div key={col.status} className="space-y-3">
              {/* Column header */}
              <div className="flex items-center gap-2 px-1 pb-2 border-b border-border">
                <div className={`w-2 h-2 rounded-full ${col.dotColor}`} />
                <span className="text-sm font-medium text-foreground">{col.label}</span>
                <span className="text-xs text-muted bg-card-hover px-1.5 py-0.5 rounded-full">
                  {colBlockers.length}
                </span>
              </div>
              {/* Cards */}
              <div className="space-y-2.5">
                {colBlockers.map((blocker) => (
                  <BlockerCard
                    key={blocker.id}
                    blocker={blocker}
                    onClick={() => setSelectedBlocker(blocker)}
                  />
                ))}
                {colBlockers.length === 0 && (
                  <div className="text-xs text-muted text-center py-8 rounded-lg border border-dashed border-border">
                    No items
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Slide-over Detail Panel */}
      <AnimatePresence>
        {selectedBlocker && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedBlocker(null)}
              className="fixed inset-0 bg-black/50 z-40"
            />
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed right-0 top-0 h-full w-[480px] bg-card border-l border-border z-50 overflow-y-auto"
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-mono text-muted">{selectedBlocker.sourceId}</span>
                  <button
                    onClick={() => setSelectedBlocker(null)}
                    className="p-1.5 rounded-lg hover:bg-card-hover text-muted hover:text-foreground transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <h2 className="text-lg font-semibold text-foreground mb-2">{selectedBlocker.title}</h2>
                <p className="text-sm text-muted mb-4 leading-relaxed">{selectedBlocker.description}</p>

                <div className="grid grid-cols-2 gap-3 mb-6">
                  <div className="bg-background rounded-lg p-3">
                    <span className="text-[10px] uppercase tracking-wider text-muted">Status</span>
                    <p className="text-sm font-medium text-foreground mt-1 capitalize">
                      {selectedBlocker.status.replace("_", " ")}
                    </p>
                  </div>
                  <div className="bg-background rounded-lg p-3">
                    <span className="text-[10px] uppercase tracking-wider text-muted">Priority</span>
                    <p className="text-sm font-medium text-foreground mt-1 capitalize">{selectedBlocker.priority}</p>
                  </div>
                  <div className="bg-background rounded-lg p-3">
                    <span className="text-[10px] uppercase tracking-wider text-muted">Assignee</span>
                    <p className="text-sm font-medium text-foreground mt-1">{selectedBlocker.assignee.name}</p>
                  </div>
                  <div className="bg-background rounded-lg p-3">
                    <span className="text-[10px] uppercase tracking-wider text-muted">Age</span>
                    <p className="text-sm font-medium text-foreground mt-1">{selectedBlocker.ageDays} days</p>
                  </div>
                </div>

                {selectedBlocker.linkedItems.length > 0 && (
                  <div className="mb-6">
                    <h3 className="text-xs font-medium text-muted uppercase tracking-wider mb-2">Linked Items</h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedBlocker.linkedItems.map((item) => (
                        <span key={item} className="text-xs font-mono bg-background px-2 py-1 rounded border border-border text-accent-light">
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions Section */}
                {selectedBlocker.status !== "resolved" && (
                  <div className="mb-6">
                    <h3 className="text-xs font-medium text-muted uppercase tracking-wider mb-3">Suggested Actions</h3>
                    <BlockerActions actions={getActionsForBlocker(selectedBlocker.id)} />
                  </div>
                )}

                <div>
                  <h3 className="text-xs font-medium text-muted uppercase tracking-wider mb-3">How this was retrieved</h3>
                  <AgentFlowPanel flow={createBlockerFetchFlow()} compact />
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
