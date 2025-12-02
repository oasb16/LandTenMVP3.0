"use client";

import React, { useCallback } from "react";
import { MessageUIComponentProps, MessageSimple, useChannelStateContext } from "stream-chat-react";
import { CustomMessageUI } from "./CustomMessageUI";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";
import { useAISupportFlowContext } from "@/app/ai-support/context/AISupportFlowContext";

/**
 * Hybrid message component that conditionally renders:
 * - CustomMessageUI for AI messages (with flow stages, action cards, etc.)
 * - MessageSimple for regular user messages (with reactions, threads, etc.)
 *
 * This gives users the full Stream Chat experience for their own messages
 * while preserving the intelligent, custom rendering for AI responses.
 */
export function HybridMessage(props: MessageUIComponentProps) {
  const { triggerAction } = useStreamChat();
  const { sendIntent } = useAISupportFlowContext();
  const channelState = useChannelStateContext();
  const { message } = props;

  // Unified action handler that tries sendIntent first, falls back to triggerAction
  const handleAction = useCallback(async (actionValue: string) => {
    console.log("[HybridMessage] Action triggered:", actionValue);

    try {
      // If we're inside /ai-support with sendIntent available, use it
      // This routes actions through the orchestrator
      await sendIntent("user_action", { action: actionValue });
      console.log("[HybridMessage] ✅ Action routed through sendIntent");
    } catch (err) {
      // Fallback to triggerAction for /dashboard or when sendIntent fails
      console.log("[HybridMessage] Falling back to triggerAction");
      await triggerAction(actionValue);
    }
  }, [sendIntent, triggerAction]);

  // Defensive null check at top
  if (!message) {
    console.warn("[HybridMessage] No message provided, returning null");
    return null;
  }

  const actorId = message.user?.id ?? "";
  const actorName = message.user?.name ?? "";

  // Detect if this is an AI message
  const isAIMessage =
    actorId.startsWith("ai-") ||
    ["PropertyHelper", "PropertyManager", "JobAssistant", "LandTen Agent"].some((name) =>
      actorName.includes(name),
    );

  // Concise logging for debugging
  console.log("[HybridMessage] rendering:", message.id, message.text?.substring(0, 50));

  // For AI messages, use our custom rendering with flow stages and action cards
  if (isAIMessage) {
    // Get current user ID from channel state
    const currentUserId = Object.values(channelState?.members || {}).find((member) => member.user?.id)?.user?.id;
    return (
      <CustomMessageUI
        // Type assertion: MessageUIComponentProps.message is compatible with MessageResponse
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        message={message as any}
        currentUserId={currentUserId}
        onActionClick={handleAction}
      />
    );
  }

  // For regular messages, use Stream's default component with reactions, threads, etc.
  return <MessageSimple {...props} />;
}
