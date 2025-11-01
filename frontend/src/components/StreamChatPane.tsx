"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Send, WifiOff } from "lucide-react";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";
import { CustomMessageUI } from "./ai/CustomMessageUI";

type Props = {
  className?: string;
};

export default function StreamChatPane({ className }: Props) {
  const {
    activeChannel,
    messages,
    loading,
    error,
    user,
    sendMessage,
    triggerAction,
  } = useStreamChat();

  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const messageEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, activeChannel?.cid]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = input.trim();
    if (!value || isSending || !activeChannel) return;
    try {
      setIsSending(true);
      await sendMessage(value);
      setInput("");
    } catch (err) {
      console.error("[StreamChatPane] Failed to send message", err);
    } finally {
      setIsSending(false);
    }
  };

  const handleAction = useCallback(
    async (actionValue: string) => {
      try {
        await triggerAction(actionValue);
      } catch (err) {
        console.error("[StreamChatPane] Failed to trigger action", err);
      }
    },
    [triggerAction],
  );

  const showEmptyState = !loading && !activeChannel;

  return (
    <div
      className={`flex h-full min-h-[360px] flex-col overflow-hidden rounded-2xl bg-slate-950/70 backdrop-blur ${className ?? ""}`.trim()}
    >
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {loading ? (
          <div className="flex h-full items-center justify-center text-slate-400">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Connecting to chat…
          </div>
        ) : error ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-sm text-rose-300">
            <WifiOff className="h-5 w-5" />
            <p className="max-w-sm text-center">{error}</p>
          </div>
        ) : showEmptyState ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-sm text-slate-300">
            <WifiOff className="h-5 w-5" />
            <p className="max-w-sm text-center">
              Select a conversation to view messages or start a new thread from the sidebar.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {messages.map((message) => {
              const createdAt = String(
                message.created_at ??
                  message.updated_at ??
                  message.id ??
                  `${message.cid}-fallback`,
              );
              return (
                <CustomMessageUI
                  key={message.id || `${message.cid}-${createdAt}`}
                  message={message}
                  currentUserId={user?.id}
                  onActionClick={handleAction}
                />
              );
            })}
            <div ref={messageEndRef} />
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="border-t border-slate-800/70 bg-slate-950/80 px-4 py-3">
        <fieldset className="flex items-center gap-3 rounded-full border border-slate-800/80 bg-slate-900/70 px-4 py-2 shadow-lg shadow-slate-950/40">
          <input
            className="flex-1 bg-transparent text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none"
            placeholder={activeChannel ? "Type a message…" : "Select a channel to begin"}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            disabled={!activeChannel || isSending}
          />
          <button
            type="submit"
            disabled={!activeChannel || isSending || !input.trim()}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-500 text-emerald-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          >
            {isSending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </fieldset>
      </form>
    </div>
  );
}
