"use client";

import { motion } from "framer-motion";
import { ChatMessage as ChatMessageType } from "@/lib/types";
import { Bot, User } from "lucide-react";
import AgentFlowPanel from "../agent/AgentFlowPanel";
import { useState } from "react";

export default function ChatMessageComponent({ message }: { message: ChatMessageType }) {
  const isAgent = message.role === "agent";
  const [showFlow, setShowFlow] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex gap-3 ${isAgent ? "" : "flex-row-reverse"}`}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${
          isAgent ? "bg-accent/20 border border-accent/30" : "bg-card border border-border"
        }`}
      >
        {isAgent ? (
          <Bot className="w-4 h-4 text-accent-light" />
        ) : (
          <User className="w-4 h-4 text-muted" />
        )}
      </div>

      {/* Message Content */}
      <div className={`max-w-[75%] space-y-2 ${isAgent ? "" : "text-right"}`}>
        <div
          className={`rounded-xl px-4 py-3 text-sm leading-relaxed ${
            isAgent
              ? "bg-card border border-border text-foreground"
              : "bg-accent/15 border border-accent/30 text-foreground"
          }`}
        >
          {/* Render markdown-like content */}
          <div
            className="prose-sm prose-invert"
            dangerouslySetInnerHTML={{
              __html: message.content
                .replace(/\*\*(.*?)\*\*/g, '<strong class="text-foreground">$1</strong>')
                .replace(/\n\n/g, "<br/><br/>")
                .replace(/\n- /g, "<br/>• ")
                .replace(/\n\|/g, "<br/>|"),
            }}
          />
        </div>

        {/* Rich data cards */}
        {message.richData?.map((card, i) => (
          <div key={i} className="bg-card rounded-lg border border-border p-3">
            <span className="text-[10px] uppercase tracking-wider text-muted font-medium">
              {card.title}
            </span>
            <div className="flex gap-3 mt-2">
              {Object.entries(card.data).map(([key, val]) => (
                <div key={key} className="text-center">
                  <p className="text-lg font-bold text-foreground">{String(val)}</p>
                  <p className="text-[10px] text-muted capitalize">{key}</p>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Agent flow toggle */}
        {isAgent && message.agentFlow && (
          <div>
            <button
              onClick={() => setShowFlow(!showFlow)}
              className="text-xs text-accent-light hover:text-accent transition-colors"
            >
              {showFlow ? "Hide" : "Show"} agent reasoning ({message.agentFlow.steps.length} steps, {(message.agentFlow.totalDurationMs / 1000).toFixed(1)}s)
            </button>
            {showFlow && (
              <div className="mt-2">
                <AgentFlowPanel flow={message.agentFlow} compact onClose={() => setShowFlow(false)} />
              </div>
            )}
          </div>
        )}

        <span className="text-[10px] text-muted">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>
    </motion.div>
  );
}
