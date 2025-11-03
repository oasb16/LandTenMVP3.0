"use client";

import React from "react";
import { MessageUIComponentProps, MessageSimple, useChannelStateContext } from "stream-chat-react";
import { CustomMessageUI } from "./CustomMessageUI";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";

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
  const channelState = useChannelStateContext();
  const { message } = props;

  if (!message) {
    return null;
  }

  const actorId = message.user?.id ?? "";
  const actorName = message.user?.name ?? "";

  // Detect if this is an AI message
  const isAIMessage =
    actorId.startsWith("ai-") ||
    actorName.includes("PropertyHelper") ||
    actorName.includes("PropertyManager") ||
    actorName.includes("JobAssistant") ||
    actorName.includes("LandTen Agent");

  // For AI messages, use our custom rendering with flow stages and action cards
  if (isAIMessage) {
    // Get current user ID from channel state
    const currentUserId = Object.values(channelState?.members || {}).find((member) => member.user?.id)?.user?.id;
    return (
      <CustomMessageUI
        message={message as any}
        currentUserId={currentUserId}
        onActionClick={triggerAction}
      />
    );
  }

  // For regular messages, use Stream's default component with reactions, threads, etc.
  return <MessageSimple {...props} />;
}
