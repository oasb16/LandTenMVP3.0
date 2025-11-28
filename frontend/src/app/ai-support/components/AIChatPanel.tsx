/**
 * AIChatPanel
 *
 * Main chat panel that integrates Stream Chat UI with dynamic panels
 */

"use client";

import { useEffect } from "react";
import {
  Channel,
  MessageList,
  MessageInput,
  Window,
  Thread,
} from "stream-chat-react";
import type { Channel as ChannelType } from "stream-chat";

import AIDynamicPanel from "./AIDynamicPanel";
import type { UIMode, IntentType } from "@/types/ai-support";

interface AIChatPanelProps {
  channel: ChannelType | null;
  uiMode: UIMode;
  payload: Record<string, unknown>;
  sendIntent: (intent: IntentType, payload: Record<string, unknown>) => Promise<void>;
  initializing: boolean;
  error: string | null;
}

export default function AIChatPanel({
  channel,
  uiMode,
  payload,
  sendIntent,
  initializing,
  error,
}: AIChatPanelProps) {
  // Show loading state
  if (initializing) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 bg-gray-50 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4" />
        <p className="text-gray-600 dark:text-gray-400 text-sm">
          Initializing AI Support Assistant...
        </p>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 bg-red-50 dark:bg-red-900/20">
        <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4">
          <svg
            className="w-8 h-8 text-red-600 dark:text-red-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <h3 className="font-semibold text-red-900 dark:text-red-300 mb-2">
          Connection Error
        </h3>
        <p className="text-sm text-red-700 dark:text-red-400 text-center max-w-md">
          {error}
        </p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  // Show waiting state if no channel yet
  if (!channel) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 bg-gray-50 dark:bg-gray-900">
        <p className="text-gray-600 dark:text-gray-400 text-sm">
          Connecting to support channel...
        </p>
      </div>
    );
  }

  return (
    <Channel channel={channel}>
      <Window>
        <div className="flex flex-col h-full">
          {/* Message List */}
          <div className="flex-1 overflow-y-auto">
            <MessageList />
          </div>

          {/* Dynamic Panel - Shows above message input */}
          <AIDynamicPanel
            uiMode={uiMode}
            payload={payload}
            onAction={sendIntent}
          />

          {/* Message Input */}
          <div className="border-t border-gray-200 dark:border-gray-700">
            <MessageInput
              grow
              overrideSubmitHandler={async (message) => {
                const text = message.text?.trim();
                if (text) {
                  await sendIntent("user_message", { text });
                }
              }}
            />
          </div>
        </div>
      </Window>
      <Thread />
    </Channel>
  );
}
