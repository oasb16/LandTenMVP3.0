"use client";

import { useState, useCallback } from "react";
import { useStreamChat } from "@/contexts/StreamChatContext";
import { Channel as StreamChannel } from "stream-chat";

export function ConversationList() {
  const {
    channels,
    activeChannel,
    selectChannel,
    refreshChannels,
    userInfo,
  } = useStreamChat();

  const [showNewConversation, setShowNewConversation] = useState(false);
  const [participantInput, setParticipantInput] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ============================================================================
  // CREATE NEW CONVERSATION
  // ============================================================================

  const handleCreateConversation = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (!userInfo) {
        setError("User not loaded");
        return;
      }

      const participants = participantInput
        .split(/[\s,]+/)
        .map((entry) => entry.trim())
        .filter((entry) => entry.length > 0 && entry !== userInfo.email);

      if (participants.length === 0) {
        setError("Add at least one participant email");
        return;
      }

      setIsCreating(true);
      setError(null);

      try {
        const res = await fetch("/api/chat/thread", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            creator: userInfo.email,
            participants,
            include_agent: true,
            persona: userInfo.persona,
          }),
        });

        const payload = await res.json();

        if (!res.ok) {
          throw new Error(payload?.error || payload?.detail || "Failed to create conversation");
        }

        // Refresh channel list
        await refreshChannels();

        // Clear form
        setParticipantInput("");
        setShowNewConversation(false);
      } catch (err) {
        console.error("[ConversationList] Create error:", err);
        setError(err instanceof Error ? err.message : "Failed to create conversation");
      } finally {
        setIsCreating(false);
      }
    },
    [userInfo, participantInput, refreshChannels]
  );

  // ============================================================================
  // RENDER CHANNEL ITEM
  // ============================================================================

  const renderChannel = (channel: StreamChannel) => {
    const isActive = activeChannel?.id === channel.id;
    const channelName = channel.data?.name || channel.id || "Unnamed";
    const lastMessage = channel.state.messages[channel.state.messages.length - 1];
    const lastMessageText = lastMessage?.text || "No messages yet";
    const lastMessageTime = lastMessage?.created_at
      ? new Date(lastMessage.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      : "";

    const unreadCount = channel.state.unreadCount || 0;

    return (
      <button
        key={channel.cid}
        onClick={() => selectChannel(channel)}
        className={`w-full text-left px-4 py-3 border-b border-slate-800 transition-colors ${
          isActive
            ? "bg-emerald-900/30 border-l-4 border-l-emerald-500"
            : "hover:bg-slate-800/50"
        }`}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="font-medium text-slate-200 truncate">{channelName}</div>
            <div className="text-sm text-slate-400 truncate mt-1">{lastMessageText}</div>
          </div>
          <div className="flex flex-col items-end gap-1 shrink-0">
            {lastMessageTime && (
              <span className="text-xs text-slate-500">{lastMessageTime}</span>
            )}
            {unreadCount > 0 && (
              <span className="bg-emerald-600 text-white text-xs font-bold rounded-full px-2 py-0.5">
                {unreadCount}
              </span>
            )}
          </div>
        </div>
      </button>
    );
  };

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-800">
        <h2 className="text-lg font-semibold text-white mb-3">Conversations</h2>

        <button
          onClick={() => setShowNewConversation(!showNewConversation)}
          className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-4 rounded transition-colors"
        >
          {showNewConversation ? "Cancel" : "+ New Conversation"}
        </button>

        {/* New Conversation Form */}
        {showNewConversation && (
          <form onSubmit={handleCreateConversation} className="mt-3 space-y-2">
            <textarea
              className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-600"
              rows={3}
              placeholder="Enter participant emails (comma or space separated)"
              value={participantInput}
              onChange={(e) => setParticipantInput(e.target.value)}
            />
            {error && (
              <div className="text-xs text-red-400 bg-red-950 border border-red-800 rounded px-2 py-1">
                {error}
              </div>
            )}
            <button
              type="submit"
              disabled={isCreating}
              className="w-full bg-slate-700 hover:bg-slate-600 text-white font-medium py-2 px-4 rounded transition-colors disabled:opacity-50"
            >
              {isCreating ? "Creating..." : "Create"}
            </button>
          </form>
        )}
      </div>

      {/* Channels List */}
      <div className="flex-1 overflow-y-auto">
        {channels.length === 0 ? (
          <div className="p-4 text-center text-slate-400 text-sm">
            No conversations yet. Create one to get started!
          </div>
        ) : (
          channels.map(renderChannel)
        )}
      </div>

      {/* Refresh Button */}
      <div className="p-3 border-t border-slate-800">
        <button
          onClick={refreshChannels}
          className="w-full text-sm text-slate-400 hover:text-slate-200 py-2 transition-colors"
        >
          🔄 Refresh
        </button>
      </div>
    </div>
  );
}
