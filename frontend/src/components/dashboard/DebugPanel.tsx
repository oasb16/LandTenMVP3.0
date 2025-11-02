"use client";

import { useStreamChat } from "@/hooks/chat/StreamChatContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function DebugPanel() {
  const { activeChannel, messages, flowState, reasoningState, channels, user } = useStreamChat();

  if (process.env.NODE_ENV === "production") {
    return null;
  }

  return (
    <Card className="border border-purple-500/30 bg-slate-900/70 backdrop-blur">
      <CardHeader>
        <CardTitle className="text-xs font-semibold text-purple-300">🐛 Debug Panel (Dev Only)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-xs text-slate-300">
        <div>
          <span className="font-semibold text-purple-400">User:</span> {user?.id || "null"}
        </div>
        <div>
          <span className="font-semibold text-purple-400">Active Channel:</span>{" "}
          {activeChannel?.cid || "none"}
        </div>
        <div>
          <span className="font-semibold text-purple-400">Channels Count:</span> {channels.length}
        </div>
        <div>
          <span className="font-semibold text-purple-400">Messages Count:</span> {messages.length}
        </div>
        <div>
          <span className="font-semibold text-purple-400">Flow Stage:</span> {flowState?.stage || "null"}
        </div>
        <div>
          <span className="font-semibold text-purple-400">Incident ID:</span> {flowState?.incidentId || "null"}
        </div>
        <div>
          <span className="font-semibold text-purple-400">Reasoning Active:</span>{" "}
          {reasoningState.active ? "Yes" : "No"}
        </div>
        <div>
          <span className="font-semibold text-purple-400">Last Message ID:</span>{" "}
          {messages[messages.length - 1]?.id || "none"}
        </div>
      </CardContent>
    </Card>
  );
}
