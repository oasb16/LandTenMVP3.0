"use client";

import { useCallback, useRef, useEffect } from "react";
import { Loader2, WifiOff, Send } from "lucide-react";
import { useContractorChat } from "./ContractorChatProvider";

type Props = {
  className?: string;
};

export default function ContractorChatPane({ className }: Props) {
  const { client, activeChannel, messages, loading, error, sendMessage } = useContractorChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      const input = inputRef.current;
      if (!input || !input.value.trim()) return;

      const text = input.value;
      input.value = "";

      try {
        await sendMessage(text, {
          metadata: {
            agentEnabled: true, // Always enable agent for contractor onboarding
          },
        });
      } catch (err) {
        console.error("Failed to send message:", err);
      }
    },
    [sendMessage]
  );

  // Loading state
  if (loading) {
    return (
      <div className={`flex h-full flex-col items-center justify-center bg-gray-50 ${className ?? ""}`.trim()}>
        <Loader2 className="h-8 w-8 animate-spin text-blue-600 mb-2" />
        <p className="text-sm text-gray-600">Connecting to chat...</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={`flex h-full flex-col items-center justify-center bg-gray-50 ${className ?? ""}`.trim()}>
        <WifiOff className="h-8 w-8 text-red-600 mb-2" />
        <p className="text-sm text-red-600 text-center max-w-sm">{error}</p>
      </div>
    );
  }

  // Empty state
  if (!client || !activeChannel) {
    return (
      <div className={`flex h-full flex-col items-center justify-center bg-gray-50 ${className ?? ""}`.trim()}>
        <p className="text-sm text-gray-600">No chat available</p>
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full ${className ?? ""}`.trim()}>
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {messages.map((msg) => {
          const isBot = msg.user?.id?.startsWith("ai-") || msg.user?.name?.toLowerCase().includes("assistant");

          return (
            <div
              key={msg.id}
              className={`flex ${isBot ? "justify-start" : "justify-end"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  isBot
                    ? "bg-white border border-gray-200 text-gray-900"
                    : "bg-blue-600 text-white"
                }`}
              >
                {isBot && (
                  <p className="text-xs font-medium text-gray-500 mb-1">
                    HomeAI Assistant
                  </p>
                )}
                <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
                <p className="text-xs mt-1 opacity-70">
                  {new Date(msg.created_at!).toLocaleTimeString()}
                </p>
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200 bg-white">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            placeholder="Type your message..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
