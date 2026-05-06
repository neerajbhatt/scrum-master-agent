"use client";

import { Sprint } from "@/lib/types";
import { Target, CheckCircle2, ArrowRight, AlertTriangle } from "lucide-react";

export default function SprintSummary({ sprint }: { sprint: Sprint }) {
  const completionPct = Math.round((sprint.completedPoints / sprint.totalPoints) * 100);

  return (
    <div className="grid grid-cols-4 gap-4">
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-lg bg-accent/15 flex items-center justify-center">
            <Target className="w-4 h-4 text-accent-light" />
          </div>
          <span className="text-xs text-muted font-medium">Committed</span>
        </div>
        <p className="text-2xl font-bold text-foreground">{sprint.totalPoints}</p>
        <p className="text-xs text-muted mt-1">{sprint.committedItems} items</p>
      </div>

      <div className="bg-card rounded-xl border border-border p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-lg bg-success/15 flex items-center justify-center">
            <CheckCircle2 className="w-4 h-4 text-success" />
          </div>
          <span className="text-xs text-muted font-medium">Completed</span>
        </div>
        <p className="text-2xl font-bold text-foreground">{sprint.completedPoints}</p>
        <p className="text-xs text-muted mt-1">{sprint.completedItems} items</p>
      </div>

      <div className="bg-card rounded-xl border border-border p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-lg bg-accent/15 flex items-center justify-center">
            <ArrowRight className="w-4 h-4 text-accent-light" />
          </div>
          <span className="text-xs text-muted font-medium">Progress</span>
        </div>
        <p className="text-2xl font-bold text-foreground">{completionPct}%</p>
        <div className="w-full h-1.5 bg-background rounded-full mt-2">
          <div
            className="h-full bg-accent rounded-full transition-all"
            style={{ width: `${completionPct}%` }}
          />
        </div>
      </div>

      <div className="bg-card rounded-xl border border-border p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-lg bg-warning/15 flex items-center justify-center">
            <AlertTriangle className="w-4 h-4 text-warning" />
          </div>
          <span className="text-xs text-muted font-medium">Carryover Risk</span>
        </div>
        <p className="text-2xl font-bold text-foreground">{sprint.carryoverItems}</p>
        <p className="text-xs text-muted mt-1">items at risk</p>
      </div>
    </div>
  );
}
