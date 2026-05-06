"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  AlertTriangle,
  BarChart3,
  MessageSquare,
  Bot,
  Settings,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/blockers", label: "Blockers", icon: AlertTriangle },
  { href: "/reports", label: "Sprint Reports", icon: BarChart3 },
  { href: "/chat", label: "Ask Agent", icon: MessageSquare },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-[#0c1222] border-r border-border flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="p-5 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-accent flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-foreground">Scrum Master</h1>
            <p className="text-xs text-muted">AI Agent Portal</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                isActive
                  ? "bg-accent/15 text-accent-light font-medium"
                  : "text-muted hover:text-foreground hover:bg-white/5"
              }`}
            >
              <item.icon className={`w-4.5 h-4.5 ${isActive ? "text-accent-light" : ""}`} />
              {item.label}
              {item.label === "Blockers" && (
                <span className="ml-auto text-xs bg-danger/20 text-danger px-1.5 py-0.5 rounded-full font-medium">
                  7
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-border">
        <div className="flex items-center gap-3 px-3 py-2 text-sm text-muted">
          <Settings className="w-4 h-4" />
          <span>Settings</span>
        </div>
        <div className="px-3 py-2 mt-1">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-success pulse-dot" />
            <span className="text-xs text-muted">Agent Online</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
