"use client";

import { mockBlockers } from "@/lib/mock/blockers";
import { currentSprint, velocityData } from "@/lib/mock/sprints";
import { recentActivity } from "@/lib/mock/agent-flows";
import {
  AlertTriangle,
  TrendingUp,
  Target,
  Activity,
  ArrowRight,
  Zap,
} from "lucide-react";
import Link from "next/link";
import ToolBadge from "@/components/agent/ToolBadge";

export default function DashboardHome() {
  const activeBlockers = mockBlockers.filter((b) => b.status !== "resolved");
  const criticalCount = activeBlockers.filter((b) => b.priority === "critical").length;
  const completionPct = Math.round(
    (currentSprint.completedPoints / currentSprint.totalPoints) * 100
  );
  const avgVelocity = Math.round(
    velocityData.slice(0, -1).reduce((sum, v) => sum + v.completed, 0) / (velocityData.length - 1)
  );

  const summaryCards = [
    {
      title: "Active Blockers",
      value: activeBlockers.length,
      subtitle: `${criticalCount} critical`,
      icon: AlertTriangle,
      iconBg: "bg-danger/15",
      iconColor: "text-danger",
      href: "/blockers",
      accent: criticalCount > 0 ? "border-danger/30" : "border-border",
    },
    {
      title: "Sprint Progress",
      value: `${completionPct}%`,
      subtitle: `${currentSprint.completedPoints}/${currentSprint.totalPoints} pts`,
      icon: Target,
      iconBg: "bg-accent/15",
      iconColor: "text-accent-light",
      href: "/reports",
      accent: "border-border",
    },
    {
      title: "Avg Velocity",
      value: avgVelocity,
      subtitle: "pts/sprint (last 4)",
      icon: TrendingUp,
      iconBg: "bg-success/15",
      iconColor: "text-success",
      href: "/reports",
      accent: "border-border",
    },
    {
      title: "Agent Queries Today",
      value: 12,
      subtitle: "5 Jira + 4 Rally + 3 hybrid",
      icon: Activity,
      iconBg: "bg-purple-500/15",
      iconColor: "text-purple-400",
      href: "/chat",
      accent: "border-border",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page title */}
      <div>
        <h1 className="text-xl font-bold text-foreground">Dashboard</h1>
        <p className="text-sm text-muted mt-1">
          Sprint 24 overview &middot; Day 9 of 13
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4">
        {summaryCards.map((card) => (
          <Link
            key={card.title}
            href={card.href}
            className={`bg-card rounded-xl border ${card.accent} p-4 hover:bg-card-hover transition-all group`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className={`w-10 h-10 rounded-lg ${card.iconBg} flex items-center justify-center`}>
                <card.icon className={`w-5 h-5 ${card.iconColor}`} />
              </div>
              <ArrowRight className="w-4 h-4 text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            <p className="text-2xl font-bold text-foreground">{card.value}</p>
            <p className="text-xs text-muted mt-0.5">{card.subtitle}</p>
            <p className="text-[10px] text-muted mt-2 uppercase tracking-wider font-medium">{card.title}</p>
          </Link>
        ))}
      </div>

      {/* Two column: Recent Activity + Quick Blockers */}
      <div className="grid grid-cols-5 gap-6">
        {/* Recent Agent Activity */}
        <div className="col-span-3 bg-card rounded-xl border border-border p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-accent-light" />
              <h2 className="text-sm font-semibold text-foreground">Recent Agent Activity</h2>
            </div>
            <Link href="/chat" className="text-xs text-accent-light hover:text-accent transition-colors">
              View all
            </Link>
          </div>
          <div className="space-y-3">
            {recentActivity.map((item) => (
              <div
                key={item.id}
                className="flex items-start gap-3 p-3 rounded-lg bg-background/50 border border-border/50"
              >
                <div className="mt-0.5">
                  <ToolBadge tool={item.tool} size="sm" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground">{item.action}</p>
                  <p className="text-xs text-muted mt-0.5 truncate">{item.detail}</p>
                </div>
                <span className="text-[10px] text-muted whitespace-nowrap">
                  {new Date(item.timestamp).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Critical Blockers */}
        <div className="col-span-2 bg-card rounded-xl border border-border p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-danger" />
              <h2 className="text-sm font-semibold text-foreground">Critical Blockers</h2>
            </div>
            <Link href="/blockers" className="text-xs text-accent-light hover:text-accent transition-colors">
              View all
            </Link>
          </div>
          <div className="space-y-2.5">
            {activeBlockers
              .filter((b) => b.priority === "critical")
              .map((blocker) => (
                <div
                  key={blocker.id}
                  className="p-3 rounded-lg bg-danger/5 border border-danger/20"
                >
                  <p className="text-sm font-medium text-foreground leading-tight line-clamp-2">
                    {blocker.title}
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-[10px] font-mono text-muted">{blocker.sourceId}</span>
                    <span className="text-[10px] text-muted">&middot;</span>
                    <span className="text-[10px] text-muted">{blocker.ageDays}d old</span>
                    <span className="text-[10px] text-muted">&middot;</span>
                    <span className="text-[10px] text-muted">{blocker.assignee.name}</span>
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
