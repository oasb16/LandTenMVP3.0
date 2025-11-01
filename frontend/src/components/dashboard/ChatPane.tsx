"use client";

import { useState, useRef, useEffect } from "react";
import { useStreamChat } from "@/contexts/StreamChatContext";
import { MessageResponse } from "stream-chat";
import { AIResponseParser } from "@/components/ai/AIResponseParser";
import { ActionCard } from "@/components/ai/ActionCard";

export function ChatPane() {
  const {
    activeChannel,
    messages,
    sendMessage,
    triggerAction,
    isSending,
    userInfo,
    agentEnabled,
  } = useStreamChat();

  const [inputText, setInputText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ============================================================================
  // SEND MESSAGE
  // ============================================================================

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!inputText.trim() || isSending) return;

    const text = inputText.trim();
    setInputText("");

    await sendMessage(text);
  };

  // ============================================================================
  // RENDER MESSAGE
  // ============================================================================

  const renderMessage = (message: MessageResponse) => {
    const isCurrentUser = message.user?.id === userInfo?.id;
    const isBot = message.user?.role === "admin" || message.user?.name?.startsWith("ai-");
    const userName = message.user?.name || message.user?.id || "Unknown";
    const timestamp = message.created_at
      ? new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      : "";

    // Check if message has card attachments
    const hasCard = message.attachments?.some((att) => att.type === "card" || att.type === "custom_card");

    return (
      <div
        key={message.id}
        className={`flex gap-3 mb-4 ${isCurrentUser && !isBot ? "flex-row-reverse" : ""}`}
      >
        {/* Avatar */}
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
            isBot
              ? "bg-emerald-600 text-white"
              : isCurrentUser
              ? "bg-blue-600 text-white"
              : "bg-slate-700 text-slate-300"
          }`}
        >
          {isBot ? "🤖" : userName[0]?.toUpperCase() || "?"}
        </div>

        {/* Message Content */}
        <div className={`flex-1 max-w-[70%] ${isCurrentUser && !isBot ? "items-end" : ""}`}>
          {/* Name & Time */}
          <div className={`flex items-center gap-2 mb-1 ${isCurrentUser && !isBot ? "justify-end" : ""}`}>
            <span className="text-xs font-medium text-slate-400">{userName}</span>
            <span className="text-xs text-slate-500">{timestamp}</span>
            {isBot && (
              <span className="text-[10px] bg-emerald-900/50 text-emerald-400 px-1.5 py-0.5 rounded">
                AI Assistant
              </span>
            )}
          </div>

          {/* Message Text */}
          {message.text && (
            <div
              className={`rounded-lg px-4 py-2 ${
                isBot
                  ? "bg-emerald-900/20 text-slate-200 border border-emerald-900/50"
                  : isCurrentUser
                  ? "bg-blue-600 text-white"
                  : "bg-slate-800 text-slate-200"
              }`}
            >
              {isBot ? (
                <AIResponseParser text={message.text} />
              ) : (
                <p className="text-sm whitespace-pre-wrap">{message.text}</p>
              )}
            </div>
          )}

          {/* Action Cards */}
          {hasCard && message.attachments && (
            <div className="mt-2">
              {message.attachments.map((attachment, idx) => {
                if (attachment.type === "card" || attachment.type === "custom_card") {
                  return (
                    <ActionCard
                      key={idx}
                      card={attachment as any}
                      onActionClick={triggerAction}
                    />
                  );
                }
                return null;
              })}
            </div>
          )}
        </div>
      </div>
    );
  };

  // ============================================================================
  // RENDER
  // ============================================================================

  if (!activeChannel) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4">💬</div>
          <h3 className="text-lg font-medium text-slate-300 mb-2">No Channel Selected</h3>
          <p className="text-sm text-slate-400">
            Select a conversation from the left to start chatting
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Channel Header */}
      <div className="px-4 py-3 border-b border-slate-800 bg-slate-900/30">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">
              {activeChannel.data?.name || activeChannel.id || "Conversation"}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {messages.length} messages {agentEnabled && "• Agent Active"}
            </p>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-slate-400">
              <p className="text-sm">No messages yet. Start the conversation!</p>
            </div>
          </div>
        ) : (
          <>
            {messages.map(renderMessage)}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Message Input */}
      <div className="border-t border-slate-800 bg-slate-900/30 p-4">
        <form onSubmit={handleSend} className="flex gap-2">
          <textarea
            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-600 resize-none"
            rows={2}
            placeholder={
              agentEnabled
                ? "Type your message (AI agent will respond)..."
                : "Type your message..."
            }
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend(e);
              }
            }}
          />
          <button
            type="submit"
            disabled={!inputText.trim() || isSending}
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-6 py-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSending ? "..." : "Send"}
          </button>
        </form>
        <p className="text-xs text-slate-500 mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
