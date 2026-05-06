"use client";

import BlockerBoard from "@/components/blockers/BlockerBoard";
import { mockBlockers } from "@/lib/mock/blockers";

export default function BlockersPage() {
  const activeCount = mockBlockers.filter((b) => b.status !== "resolved").length;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-foreground">Blocker Dashboard</h1>
        <p className="text-sm text-muted mt-1">
          {activeCount} active blockers in Sprint 24 &middot; Sourced from Jira &amp; Rally
        </p>
      </div>
      <BlockerBoard blockers={mockBlockers} />
    </div>
  );
}
