"use client";

import { ChevronDown, Bell, RefreshCw } from "lucide-react";
import { useState } from "react";

export default function Header() {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 1500);
  };

  return (
    <header className="h-14 border-b border-border bg-[#0c1222]/80 backdrop-blur-sm flex items-center justify-between px-6 sticky top-0 z-10">
      <div className="flex items-center gap-4">
        {/* Project Selector */}
        <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-card hover:bg-card-hover border border-border text-sm transition-colors">
          <span className="w-2 h-2 rounded-full bg-accent" />
          <span className="font-medium">Platform Team</span>
          <ChevronDown className="w-3.5 h-3.5 text-muted" />
        </button>
        <span className="text-xs text-muted px-2 py-1 rounded bg-card border border-border">
          Sprint 24 &middot; Day 9/13
        </span>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handleRefresh}
          className="p-2 rounded-lg hover:bg-card text-muted hover:text-foreground transition-colors"
          title="Refresh data"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`} />
        </button>
        <button className="relative p-2 rounded-lg hover:bg-card text-muted hover:text-foreground transition-colors">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-danger" />
        </button>
        <div className="w-8 h-8 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center text-xs font-medium text-accent-light">
          NR
        </div>
      </div>
    </header>
  );
}
