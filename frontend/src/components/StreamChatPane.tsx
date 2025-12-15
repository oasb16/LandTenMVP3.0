"use client";

import { useEffect, useState, useCallback } from "react";
import { Loader2, WifiOff, Bot, BotOff, UserPlus } from "lucide-react";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";
import { Chat, Channel, ChannelHeader, MessageList, MessageInput, Window, Thread } from "stream-chat-react";
import "stream-chat-react/dist/css/v2/index.css";
import { CustomAttachment } from "./ai/CustomAttachment";

type Props = {
  className?: string;
  showEscalation?: boolean;
  onEscalate?: () => void;
};

export default function StreamChatPane({ className, showEscalation, onEscalate }: Props) {
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

  // Auto-scroll to bottom when channel or messages change
  useEffect(() => {
    if (!activeChannel) return;

    // Small delay to ensure DOM is ready
    const timer = setTimeout(() => {
      const messageList = document.querySelector('.str-chat__list');
      if (messageList) {
        // Scroll to bottom (top in reverse layout)
        messageList.scrollTop = 0;
      }
    }, 100);

    return () => clearTimeout(timer);
  }, [activeChannel, activeChannel?.state?.messages?.length]);

  const showEmptyState = !loading && !activeChannel;

  // Loading state
  if (loading) {
    return (
      <div
        className={`flex h-full flex-col rounded-2xl bg-slate-950/70 backdrop-blur ${className ?? ""}`.trim()}
        style={{ minHeight: 0 }}
      >
        <div className="flex flex-1 items-center justify-center text-slate-400">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Connecting to chat…
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className={`flex h-full flex-col rounded-2xl bg-slate-950/70 backdrop-blur ${className ?? ""}`.trim()}
        style={{ minHeight: 0 }}
      >
        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-sm text-rose-300">
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
        className={`flex h-full flex-col rounded-2xl bg-slate-950/70 backdrop-blur ${className ?? ""}`.trim()}
        style={{ minHeight: 0 }}
      >
        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-sm text-slate-300">
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
      className={`str-chat str-chat__theme-dark flex h-full flex-col ${className ?? ""}`.trim()}
      style={{
        // Force Stream components to use full height
        minHeight: 0,
      }}
    >
      <Chat client={client} theme="str-chat__theme-dark">
        <Channel channel={activeChannel} Attachment={CustomAttachment}>
          <Window>
            <ChannelHeader />

            <MessageList
              // Auto-scroll to newest messages
              disableDateSeparator={false}
              // Performance optimization
              messageLimit={50}
              // Hide typing indicator if needed
              hideTypingIndicator={false}
            />

            {/* Agent Toggle and Message Input Container */}
            <div
              className="flex flex-col border-t border-slate-800/70 bg-slate-950/80"
              style={{ flexShrink: 0 }}
            >
              {/* Escalation Button - shows during diagnosis */}
              {showEscalation && onEscalate && (
                <div className="px-4 py-2 border-b border-slate-700">
                  <button
                    onClick={onEscalate}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 hover:border-amber-500/60 rounded-lg text-amber-300 font-medium transition-all duration-200"
                  >
                    <UserPlus className="w-4 h-4" />
                    <span>Connect me to a human agent</span>
                  </button>
                </div>
              )}

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
  const {sendMessage, user, activeChannel } = useStreamChat();
  console.log("[MessageInputWithWebhook] Initialized with agentEnabled =", agentEnabled, user, activeChannel);
  const handleSubmit = useCallback(
    async (input: any) => {
      // Extract text from various possible input formats
      const messageText =
        typeof input === "string"
          ? input
          : typeof input?.message?.text === "string"
          ? input.message.text
          : typeof input?.text === "string"
          ? input.text
          : "";

      // 🔥 CRITICAL FIX: Extract attachments from input
      const attachments =
        input?.attachments ||
        input?.message?.attachments ||
        [];

      console.log("[MessageInputWithWebhook] ✅ Extracted from input:", {
        text: messageText.substring(0, 100),
        attachmentCount: attachments.length,
        attachments: attachments.map((a: any) => ({
          type: a.type,
          name: a.name,
          file_size: a.file_size,
          mime_type: a.mime_type,
        })),
      });

      // Allow empty text if we have attachments (photo-only messages)
      if (!messageText.trim() && attachments.length === 0) {
        console.warn("[MessageInputWithWebhook] ⚠️ No text or attachments in input:", input);
        return;
      }

      const text = messageText;

      console.log('[MessageInputWithWebhook] Sending:', text || '[Photo only]');
      console.log('[MessageInputWithWebhook] Agent:', agentEnabled ? 'ON' : 'OFF');
      console.log('[MessageInputWithWebhook] Attachments:', attachments.length);

      console.log("[MessageInputWithWebhook] Active channel before send:", activeChannel?.cid);
      console.log("[MessageInputWithWebhook] User before send:", user?.id);
      console.log("[MessageInputWithWebhook] Message payload:", {
        text,
        user,
        attachments,  // ✅ FIXED: Pass actual attachments
        mentioned_users: [],
        metadata: {
          agentEnabled,
          persona: (user as any)?.role || 'tenant',
        },
      });

      try {
        // ✅ Step 1: Send valid message to Stream with attachments
        const messagePayload = {
          text,
          attachments,  // ✅ FIXED: Include actual attachments
          mentioned_users: [],
          metadata: {
            agentEnabled,
            persona: (user as any)?.role || 'tenant',
          },
        };
        console.log("[MessageInputWithWebhook] Sending message to Stream:", messagePayload);
        const result = await sendMessage(text, messagePayload);
        console.log('[MessageInputWithWebhook] ✅ Sent to Stream:', result);

        // ✅ Step 2: Forward to AI webhook if enabled
        console.log("[MessageInputWithWebhook] Forwarding to AI webhook...");
        if (agentEnabled) {
          if (!activeChannel) {
            console.warn('[MessageInputWithWebhook] No activeChannel - aborting webhook');
            return;
          }

          const payload = {
            type: 'message.new',
            message: {
              text,
              attachments,  // ✅ FIXED: Include attachments in webhook payload
              user: {
                id: user?.id,
                name: user?.name,
                is_bot: false,
              },
              metadata: {
                agentEnabled: true,
                persona: (user as any)?.role || 'tenant',
              },
            },
            user: {
              id: user?.id,
              name: user?.name,
              is_bot: false,
            },
            channel_id: activeChannel!.cid || 'landten-default',
            channel_type: 'messaging',
          };

          const backendBase = process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/api$/, '') || window.location.origin;
          console.log("[MessageInputWithWebhook] Posting to webhook at", `${backendBase}/ai/stream-webhook`, "with payload:", payload);
          const res = await fetch(`${backendBase}/ai/stream-webhook`, {

            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });

          console.log('[MessageInputWithWebhook] 🤖 AI webhook response:', res.status);
        } else {
          console.log('[MessageInputWithWebhook] Agent disabled — skipping webhook');
        }

        // ✅ Step 3: Rehydrate channel so message list updates
        if (activeChannel?.watch) {
          await activeChannel.watch();
        }
        console.log('[MessageInputWithWebhook] ✅ Channel rehydrated');
      } catch (err) {
        console.error('[MessageInputWithWebhook] ❌ Send failed:', err);
      }
    },
    [sendMessage, activeChannel, user, agentEnabled],
  );

  return <MessageInput focus overrideSubmitHandler={handleSubmit} />;
}
