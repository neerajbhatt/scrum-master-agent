"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Sparkles } from "lucide-react";
import { ChatMessage as ChatMessageType } from "@/lib/types";
import { createChatResponseFlow, predefinedChatResponses } from "@/lib/mock/agent-flows";
import ChatMessageComponent from "./ChatMessage";
import { AnimatePresence } from "framer-motion";

const quickQueries = [
  "What are the top blockers this sprint?",
  "Show me sprint 24 progress",
  "How is the team doing?",
  "Which blockers need escalation?",
];

export default function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const handleSend = (query?: string) => {
    const text = query || input.trim();
    if (!text) return;

    const userMsg: ChatMessageType = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    // Simulate agent thinking
    setTimeout(() => {
      const flow = createChatResponseFlow(text);
      let response: ChatMessageType;

      if (text.toLowerCase().includes("blocker")) {
        response = { ...predefinedChatResponses.blockers, id: `msg-${Date.now()}`, agentFlow: flow, timestamp: new Date().toISOString() };
      } else if (text.toLowerCase().includes("sprint") || text.toLowerCase().includes("progress")) {
        response = { ...predefinedChatResponses.sprint, id: `msg-${Date.now()}`, agentFlow: flow, timestamp: new Date().toISOString() };
      } else if (text.toLowerCase().includes("team") || text.toLowerCase().includes("doing")) {
        response = { ...predefinedChatResponses.team, id: `msg-${Date.now()}`, agentFlow: flow, timestamp: new Date().toISOString() };
      } else {
        response = {
          id: `msg-${Date.now()}`,
          role: "agent",
          content: `I analyzed your query across Jira and Rally. Here's what I found:\n\nBased on the current Sprint 24 data, the team is making steady progress with **34 of 55 story points** completed. There are **7 active blockers** that need attention, with 3 at critical priority.\n\nWould you like me to drill deeper into any specific area?`,
          timestamp: new Date().toISOString(),
          agentFlow: flow,
        };
      }

      setIsTyping(false);
      setMessages((prev) => [...prev, response]);
    }, 1800);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-accent/15 border border-accent/30 flex items-center justify-center mb-4">
              <Sparkles className="w-8 h-8 text-accent-light" />
            </div>
            <h2 className="text-lg font-semibold text-foreground mb-2">Ask the Scrum Master Agent</h2>
            <p className="text-sm text-muted mb-6 max-w-md">
              I can query Jira and Rally to give you blocker reports, sprint progress, team workload, and more.
              Every response shows exactly which tools and APIs were used.
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              {quickQueries.map((q) => (
                <button
                  key={q}
                  onClick={() => handleSend(q)}
                  className="px-3 py-2 rounded-lg bg-card border border-border text-sm text-muted hover:text-foreground hover:border-accent/30 transition-all"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <AnimatePresence>
          {messages.map((msg) => (
            <ChatMessageComponent key={msg.id} message={msg} />
          ))}
        </AnimatePresence>

        {isTyping && (
          <div className="flex items-center gap-2 text-sm text-muted">
            <div className="flex gap-1">
              <div className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: "0ms" }} />
              <div className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: "150ms" }} />
              <div className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
            <span>Agent is thinking...</span>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-border p-4">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask about blockers, sprint progress, team workload..."
            className="flex-1 bg-card border border-border rounded-xl px-4 py-3 text-sm text-foreground placeholder-muted focus:outline-none focus:border-accent/50 transition-colors"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim()}
            className="px-4 py-3 rounded-xl bg-accent hover:bg-accent-light text-white font-medium text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
