"use client";

import { useEffect, useState, useCallback } from "react";
import { Loader2, WifiOff, Bot, BotOff } from "lucide-react";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";
import { Chat, Channel, ChannelHeader, MessageList, MessageInput, Window, Thread, useChannelActionContext } from "stream-chat-react";
import { HybridMessage } from "./ai/HybridMessage";
import "stream-chat-react/dist/css/v2/index.css";

type Props = {
  className?: string;
};

export default function StreamChatPane({ className }: Props) {
  const {
    client,
    activeChannel,
    loading,
    error,
    user,
  } = useStreamChat();

  // Agent toggle state with localStorage persistence
  const [agentEnabled, setAgentEnabled] = useState(true);

  // Load agent enabled state from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('agentEnabled');
    if (saved !== null) {
      setAgentEnabled(saved === 'true');
      console.log("[StreamChatPane] Loaded agent state from localStorage:", saved === 'true');
    }
  }, []);

  // Save agent enabled state to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('agentEnabled', agentEnabled.toString());
    console.log("[StreamChatPane] Agent mode", agentEnabled ? "ENABLED" : "DISABLED");
  }, [agentEnabled]);

  // ====== COMPREHENSIVE DEBUG LOGGING ======
  useEffect(() => {
    console.log("[StreamChatPane] 🟢 COMPONENT MOUNTED");
    console.log("[StreamChatPane] Context values:", {
      hasClient: !!client,
      hasActiveChannel: !!activeChannel,
      activeChannelCid: activeChannel?.cid,
      hasUser: !!user,
      userId: user?.id,
      loading,
      error,
      agentEnabled,
    });
    return () => {
      console.log("[StreamChatPane] 🔴 COMPONENT UNMOUNTED");
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on mount/unmount

  // Log active channel changes
  useEffect(() => {
    console.log("[StreamChatPane] Active channel changed:", activeChannel?.cid);
  }, [activeChannel?.cid]);

  // Log context changes
  useEffect(() => {
    console.log("[StreamChatPane] Context update:", {
      hasClient: !!client,
      activeChannel: activeChannel?.cid,
      userDefined: !!user,
      agentEnabled,
    });
  }, [client, activeChannel, user, agentEnabled]);

  // Log channel state for debugging (must be before early returns)
  useEffect(() => {
    if (activeChannel) {
      console.log("[StreamChatPane] Active channel state:", {
        cid: activeChannel.cid,
        messageCount: activeChannel.state.messages?.length || 0,
        messages: activeChannel.state.messages?.slice(0, 3).map(m => ({
          id: m.id,
          text: m.text?.substring(0, 50),
          userId: m.user?.id,
        })),
      });
    }
  }, [activeChannel, activeChannel?.state?.messages?.length]);

  const showEmptyState = !loading && !activeChannel;

  // Loading state
  if (loading) {
    return (
      <div
        className={`flex h-full min-h-[360px] flex-col overflow-hidden rounded-2xl bg-slate-950/70 backdrop-blur ${className ?? ""}`.trim()}
      >
        <div className="flex h-full items-center justify-center text-slate-400">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Connecting to chat…
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className={`flex h-full min-h-[360px] flex-col overflow-hidden rounded-2xl bg-slate-950/70 backdrop-blur ${className ?? ""}`.trim()}
      >
        <div className="flex h-full flex-col items-center justify-center gap-2 text-sm text-rose-300">
          <WifiOff className="h-5 w-5" />
          <p className="max-w-sm text-center">{error}</p>
        </div>
      </div>
    );
  }

  // Empty state (no channel selected)
  if (showEmptyState) {
    return (
      <div
        className={`flex h-full min-h-[360px] flex-col overflow-hidden rounded-2xl bg-slate-950/70 backdrop-blur ${className ?? ""}`.trim()}
      >
        <div className="flex h-full flex-col items-center justify-center gap-2 text-sm text-slate-300">
          <WifiOff className="h-5 w-5" />
          <p className="max-w-sm text-center">
            Select a conversation to view messages or start a new thread from the sidebar.
          </p>
        </div>
      </div>
    );
  }

  // Main chat UI using Stream SDK components
  if (!client || !activeChannel) {
    return null;
  }

  return (
    <div
      className={`str-chat str-chat__theme-dark flex h-full min-h-[360px] flex-col overflow-hidden rounded-2xl bg-slate-950/70 backdrop-blur ${className ?? ""}`.trim()}
    >
      <Chat client={client} theme="str-chat__theme-dark">
        <Channel channel={activeChannel}>
          <Window>
            <ChannelHeader />
            <MessageList MessageUIComponent={HybridMessage} />

            {/* Agent Toggle and Message Input Container */}
            <div className="flex flex-col border-t border-slate-800/70 bg-slate-950/80">
              {/* Agent Toggle Bar */}
              <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800/50">
                <div className="flex items-center gap-2">
                  {agentEnabled ? (
                    <Bot className="h-4 w-4 text-emerald-400" />
                  ) : (
                    <BotOff className="h-4 w-4 text-slate-500" />
                  )}
                  <span className="text-xs font-medium text-slate-300">
                    PropertyAI Agent
                  </span>
                </div>

                <button
                  onClick={() => setAgentEnabled(!agentEnabled)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    agentEnabled
                      ? 'bg-emerald-500 hover:bg-emerald-600'
                      : 'bg-slate-700 hover:bg-slate-600'
                  }`}
                  aria-label="Toggle PropertyAI Agent"
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      agentEnabled ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>

              {/* Message Input with Custom Submit Handler */}
              <MessageInputWithWebhook agentEnabled={agentEnabled} />
            </div>
          </Window>
          <Thread />
        </Channel>
      </Chat>
    </div>
  );
}

/**
 * Custom MessageInput wrapper that intercepts message submissions
 * and forwards to AI webhook when agent is enabled.
 */
function MessageInputWithWebhook({ agentEnabled }: { agentEnabled: boolean }) {
  const { sendMessage } = useChannelActionContext();
  const { user, activeChannel } = useStreamChat();

  const handleSubmit = useCallback(
    async (text: string) => {
      if (!text?.trim() || !activeChannel) {
        console.warn('[MessageInputWithWebhook] Missing text or channel');
        return;
      }

      console.log('[MessageInputWithWebhook] Sending:', text.substring(0, 50));
      console.log('[MessageInputWithWebhook] Agent:', agentEnabled ? 'ON' : 'OFF');

      try {
        // 1. Send message normally to Stream with metadata
        await sendMessage({
          text,
          metadata: {
            agentEnabled,
            persona: user?.role || 'tenant',
          },
        });

        console.log('[MessageInputWithWebhook] ✅ Sent to Stream');

        // 2. Forward to AI webhook only if agent enabled
        if (agentEnabled) {
          console.log('[MessageInputWithWebhook] 🤖 Triggering AI webhook');

          const payload = {
            type: 'message.new',
            message: {
              text,
              user: {
                id: user?.id,
                name: user?.name,
                is_bot: false,
              },
              metadata: {
                agentEnabled: true,
                persona: user?.role || 'tenant',
              },
            },
            user: {
              id: user?.id,
              name: user?.name,
              is_bot: false,
            },
            channel_id: activeChannel.id || 'landten-default',
            channel_type: 'messaging',
          };

          const res = await fetch('http://localhost:8080/ai/stream-webhook', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });

          console.log('[MessageInputWithWebhook] 🤖 AI webhook response:', res.status);
        } else {
          console.log('[MessageInputWithWebhook] Agent disabled - skipping webhook');
        }

        // 3. Refresh channel to see new messages
        await activeChannel.watch();
        console.log('[MessageInputWithWebhook] ✅ Channel rehydrated');
      } catch (err) {
        console.error('[MessageInputWithWebhook] ❌ Send failed:', err);
      }
    },
    [sendMessage, activeChannel, user, agentEnabled],
  );

  return <MessageInput focus overrideSubmitHandler={handleSubmit} />;
}
