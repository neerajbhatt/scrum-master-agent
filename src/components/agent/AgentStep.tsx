"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Check, Loader2, AlertCircle, ChevronDown, ChevronRight, Clock } from "lucide-react";
import { AgentStep as AgentStepType } from "@/lib/types";
import ToolBadge from "./ToolBadge";

export default function AgentStepComponent({
  step,
  index,
  isLast,
}: {
  step: AgentStepType;
  index: number;
  isLast: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  const statusIcon = {
    pending: <div className="w-3 h-3 rounded-full border-2 border-muted" />,
    running: <Loader2 className="w-4 h-4 text-accent animate-spin" />,
    completed: <Check className="w-3.5 h-3.5 text-success" />,
    error: <AlertCircle className="w-3.5 h-3.5 text-danger" />,
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.15, duration: 0.3 }}
      className="relative"
    >
      {/* Connector line */}
      {!isLast && (
        <div className="absolute left-[11px] top-8 bottom-0 w-px bg-border" />
      )}

      <div className="flex gap-3">
        {/* Status dot */}
        <div className="mt-1 flex-shrink-0 w-6 h-6 rounded-full bg-card border border-border flex items-center justify-center z-10">
          {statusIcon[step.status]}
        </div>

        {/* Content */}
        <div className="flex-1 pb-4">
          <div
            className="flex items-center gap-2 cursor-pointer group"
            onClick={() => setExpanded(!expanded)}
          >
            <span className="text-sm font-medium text-foreground group-hover:text-accent-light transition-colors">
              {step.label}
            </span>
            <ToolBadge tool={step.tool} />
            <span className="ml-auto flex items-center gap-1 text-xs text-muted">
              <Clock className="w-3 h-3" />
              {step.durationMs}ms
            </span>
            {(step.request || step.response) && (
              expanded ? (
                <ChevronDown className="w-3.5 h-3.5 text-muted" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-muted" />
              )
            )}
          </div>

          <p className="text-xs text-muted mt-1 leading-relaxed">{step.description}</p>

          {/* Expandable raw data */}
          {expanded && (step.request || step.response) && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              className="mt-2 space-y-2"
            >
              {step.request && (
                <div className="rounded-md bg-[#0c1222] border border-border p-2.5">
                  <span className="text-[10px] uppercase tracking-wider text-muted font-medium">Request</span>
                  <pre className="text-xs text-blue-300 mt-1 font-mono overflow-x-auto">{step.request}</pre>
                </div>
              )}
              {step.response && (
                <div className="rounded-md bg-[#0c1222] border border-border p-2.5">
                  <span className="text-[10px] uppercase tracking-wider text-muted font-medium">Response</span>
                  <pre className="text-xs text-emerald-300 mt-1 font-mono overflow-x-auto">{step.response}</pre>
                </div>
              )}
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
