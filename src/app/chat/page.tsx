"use client";

import ChatInterface from "@/components/chat/ChatInterface";

export default function ChatPage() {
  return (
    <div>
      <div className="mb-4">
        <h1 className="text-xl font-bold text-foreground">Ask the Agent</h1>
        <p className="text-sm text-muted mt-1">
          Query Jira &amp; Rally using natural language. Every response shows the tools and APIs used.
        </p>
      </div>
      <ChatInterface />
    </div>
  );
}
