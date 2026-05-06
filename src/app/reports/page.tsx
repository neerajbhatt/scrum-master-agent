"use client";

import { useState } from "react";
import BurndownChart from "@/components/reports/BurndownChart";
import VelocityChart from "@/components/reports/VelocityChart";
import SprintSummary from "@/components/reports/SprintSummary";
import AgentFlowPanel from "@/components/agent/AgentFlowPanel";
import { burndownData, velocityData, currentSprint } from "@/lib/mock/sprints";
import { createSprintReportFlow } from "@/lib/mock/agent-flows";
import { Zap } from "lucide-react";

export default function ReportsPage() {
  const [showFlow, setShowFlow] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">Sprint Reports</h1>
          <p className="text-sm text-muted mt-1">
            Sprint 24 &middot; {currentSprint.startDate} to {currentSprint.endDate}
          </p>
        </div>
        <button
          onClick={() => setShowFlow(!showFlow)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            showFlow
              ? "bg-accent/15 text-accent-light border border-accent/30"
              : "bg-card border border-border text-muted hover:text-foreground"
          }`}
        >
          <Zap className="w-3.5 h-3.5" />
          {showFlow ? "Hide" : "Show"} How Data Was Built
        </button>
      </div>

      {showFlow && (
        <AgentFlowPanel flow={createSprintReportFlow()} onClose={() => setShowFlow(false)} />
      )}

      {/* Sprint Summary Cards */}
      <SprintSummary sprint={currentSprint} />

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-card rounded-xl border border-border p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Burndown Chart</h2>
          <BurndownChart data={burndownData} />
        </div>
        <div className="bg-card rounded-xl border border-border p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Velocity Trend</h2>
          <VelocityChart data={velocityData} />
        </div>
      </div>
    </div>
  );
}
