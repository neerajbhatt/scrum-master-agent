"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Zap, Clock, X } from "lucide-react";
import { AgentFlow } from "@/lib/types";
import AgentStepComponent from "./AgentStep";

export default function AgentFlowPanel({
  flow,
  onClose,
  compact = false,
}: {
  flow: AgentFlow;
  onClose?: () => void;
  compact?: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      className={`rounded-xl border border-border bg-card ${compact ? "p-3" : "p-4"}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-accent/15 flex items-center justify-center">
            <Zap className="w-3.5 h-3.5 text-accent-light" />
          </div>
          <span className={`font-semibold text-foreground ${compact ? "text-xs" : "text-sm"}`}>
            Agent Reasoning
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1 text-xs text-muted bg-card-hover px-2 py-0.5 rounded-full">
            <Clock className="w-3 h-3" />
            {(flow.totalDurationMs / 1000).toFixed(1)}s total
          </span>
          {onClose && (
            <button onClick={onClose} className="p-1 rounded hover:bg-card-hover text-muted hover:text-foreground transition-colors">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Steps */}
      <div className={compact ? "pl-0" : "pl-1"}>
        <AnimatePresence>
          {flow.steps.map((step, i) => (
            <AgentStepComponent
              key={step.id}
              step={step}
              index={i}
              isLast={i === flow.steps.length - 1}
            />
          ))}
        </AnimatePresence>
      </div>

      {/* Summary */}
      <div className="mt-2 pt-2 border-t border-border flex items-center gap-3">
        <span className="text-[10px] uppercase tracking-wider text-muted font-medium">
          {flow.steps.length} steps
        </span>
        <span className="text-[10px] text-muted">
          {flow.steps.filter((s) => s.status === "completed").length} completed
        </span>
      </div>
    </motion.div>
  );
}
