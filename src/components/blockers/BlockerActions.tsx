"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BlockerAction } from "@/lib/types";
import ToolBadge from "../agent/ToolBadge";
import {
  Bot,
  User,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Loader2,
  Sparkles,
  ArrowUpCircle,
  Zap,
} from "lucide-react";

const urgencyStyles = {
  recommended: "border-warning/30 bg-warning/5",
  optional: "border-border bg-background/50",
  info: "border-border bg-background/30",
};

const urgencyBadge = {
  recommended: "bg-warning/15 text-warning",
  optional: "bg-muted/15 text-muted",
  info: "bg-blue-500/15 text-blue-400",
};

export default function BlockerActions({ actions }: { actions: BlockerAction[] }) {
  const agentActions = actions.filter((a) => a.category === "agent");
  const humanActions = actions.filter((a) => a.category === "human");

  return (
    <div className="space-y-5">
      {/* Agent Actions */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5 rounded-md bg-accent/15 flex items-center justify-center">
            <Bot className="w-3 h-3 text-accent-light" />
          </div>
          <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">
            Agent Actions
          </h3>
          <span className="text-[10px] text-muted bg-card-hover px-1.5 py-0.5 rounded-full">
            {agentActions.length}
          </span>
        </div>
        <div className="space-y-2">
          {agentActions.map((action) => (
            <ActionCard key={action.id} action={action} />
          ))}
        </div>
      </div>

      {/* Human Actions */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5 rounded-md bg-emerald-500/15 flex items-center justify-center">
            <User className="w-3 h-3 text-emerald-400" />
          </div>
          <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">
            Recommended for You
          </h3>
          <span className="text-[10px] text-muted bg-card-hover px-1.5 py-0.5 rounded-full">
            {humanActions.length}
          </span>
        </div>
        <div className="space-y-2">
          {humanActions.map((action) => (
            <ActionCard key={action.id} action={action} />
          ))}
        </div>
      </div>
    </div>
  );
}

function ActionCard({ action }: { action: BlockerAction }) {
  const [expanded, setExpanded] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [done, setDone] = useState(false);

  const handleExecute = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (done) return;
    setExecuting(true);
    setTimeout(() => {
      setExecuting(false);
      setDone(true);
    }, 2000);
  };

  return (
    <motion.div
      layout
      className={`rounded-lg border ${urgencyStyles[action.urgency]} p-3 transition-all ${
        done ? "opacity-60" : ""
      }`}
    >
      <div
        className="flex items-start gap-2.5 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Expand icon */}
        <div className="mt-0.5 flex-shrink-0">
          {expanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-muted" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-muted" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-foreground">{action.label}</span>
            <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-semibold uppercase ${urgencyBadge[action.urgency]}`}>
              {action.urgency}
            </span>
          </div>

          {/* Expanded content */}
          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <p className="text-xs text-muted mt-1.5 leading-relaxed">{action.description}</p>

                {action.estimatedImpact && (
                  <div className="flex items-center gap-1.5 mt-2 text-xs text-emerald-400">
                    <Sparkles className="w-3 h-3" />
                    <span>Impact: {action.estimatedImpact}</span>
                  </div>
                )}

                {action.tool && (
                  <div className="mt-2">
                    <ToolBadge tool={action.tool} size="sm" />
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Action button */}
        <button
          onClick={handleExecute}
          disabled={executing || done}
          className={`flex-shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-all ${
            done
              ? "bg-success/15 text-success border border-success/30"
              : executing
              ? "bg-accent/15 text-accent-light border border-accent/30"
              : action.category === "agent"
              ? "bg-accent/10 text-accent-light border border-accent/20 hover:bg-accent/20"
              : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20"
          }`}
        >
          {done ? (
            <>
              <CheckCircle2 className="w-3 h-3" />
              Done
            </>
          ) : executing ? (
            <>
              <Loader2 className="w-3 h-3 animate-spin" />
              Running
            </>
          ) : action.category === "agent" ? (
            <>
              <Zap className="w-3 h-3" />
              Run
            </>
          ) : (
            <>
              <ArrowUpCircle className="w-3 h-3" />
              Act
            </>
          )}
        </button>
      </div>
    </motion.div>
  );
}
