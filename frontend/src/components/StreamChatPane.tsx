"use client";

import { useEffect, useState, useCallback } from "react";
import { Loader2, WifiOff, UserPlus } from "lucide-react";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";
import { Chat, Channel, MessageList, MessageInput, Window, Thread } from "stream-chat-react";
import "stream-chat-react/dist/css/v2/index.css";
import { HybridMessage } from "./ai/HybridMessage";
import { CustomChannelHeader } from "./ai/CustomChannelHeader";
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

  const [agentEnabled, setAgentEnabled] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem('agentEnabled');
    if (saved !== null) {
      setAgentEnabled(saved === 'true');
      console.log("[StreamChatPane] Loaded agent state from localStorage:", saved === 'true');
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('agentEnabled', agentEnabled.toString());
    console.log("[StreamChatPane] Agent mode", agentEnabled ? "ENABLED" : "DISABLED");
  }, [agentEnabled]);

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
  }, []);

  useEffect(() => {
    console.log("[StreamChatPane] Active channel changed:", activeChannel?.cid);
  }, [activeChannel?.cid]);

  useEffect(() => {
    console.log("[StreamChatPane] Context update:", {
      hasClient: !!client,
      activeChannel: activeChannel?.cid,
      userDefined: !!user,
      agentEnabled,
    });
  }, [client, activeChannel, user, agentEnabled]);

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

  useEffect(() => {
    if (!activeChannel) return;

    const timer = setTimeout(() => {
      const messageList = document.querySelector('.str-chat__list');
      if (messageList) {
        messageList.scrollTop = 0;
      }
    }, 100);

    return () => clearTimeout(timer);
  }, [activeChannel, activeChannel?.state?.messages?.length]);

  const handleActionClick = useCallback((actionValue: string) => {
    console.log('[StreamChatPane] CustomAttachment action:', actionValue);
  }, []);

  const showEmptyState = !loading && !activeChannel;

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

  if (!client || !activeChannel) {
    return null;
  }

  return (
    <div
      className={`str-chat str-chat__theme-dark flex h-full flex-col ${className ?? ""}`.trim()}
      style={{ minHeight: 0 }}
    >
      <Chat client={client} theme="str-chat__theme-dark">
        <Channel
          channel={activeChannel}
          Attachment={(props) => (
            <CustomAttachment {...props} onActionClick={handleActionClick} />
          )}
        >
          <Window>
            <CustomChannelHeader
              agentEnabled={agentEnabled}
              onAgentToggle={setAgentEnabled}
            />

            <MessageList
              Message={HybridMessage}
              disableDateSeparator={false}
              messageLimit={50}
              hideTypingIndicator={false}
            />

            <div
              className="flex flex-col border-t border-slate-800/70 bg-slate-950/80"
              style={{ flexShrink: 0 }}
            >
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

              <MessageInputWithWebhook agentEnabled={agentEnabled} />
            </div>
          </Window>
          <Thread />
        </Channel>
      </Chat>
    </div>
  );
}

function MessageInputWithWebhook({ agentEnabled }: { agentEnabled: boolean }) {
  const { sendMessage, user, activeChannel } = useStreamChat();

  const handleSubmit = useCallback(
    async (input: any) => {
      const messageText =
        typeof input === "string"
          ? input
          : typeof input?.message?.text === "string"
          ? input.message.text
          : typeof input?.text === "string"
          ? input.text
          : "";

      if (!messageText.trim()) {
        console.warn("[MessageInputWithWebhook] ⚠️ No valid text extracted from input:", input);
        return;
      }

      const text = messageText;

      console.log('[MessageInputWithWebhook] Sending:', text);
      console.log('[MessageInputWithWebhook] Agent:', agentEnabled ? 'ON' : 'OFF');

      try {
        const result = await sendMessage(text);
        console.log('[MessageInputWithWebhook] ✅ Sent to Stream:', result);

        if (agentEnabled) {
          if (!activeChannel) {
            console.warn('[MessageInputWithWebhook] No activeChannel - aborting webhook');
            return;
          }

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
                persona: (user as any)?.role || 'tenant',
              },
            },
            user: {
              id: user?.id,
              name: user?.name,
              is_bot: false,
            },
            channel_id: activeChannel.cid || 'landten-default',
            channel_type: 'messaging',
          };

          const backendBase = process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/api$/, '') || window.location.origin;
          const res = await fetch(`${backendBase}/ai/stream-webhook`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });

          console.log('[MessageInputWithWebhook] 🤖 AI webhook response:', res.status);
        } else {
          console.log('[MessageInputWithWebhook] Agent disabled — skipping webhook');
        }

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
