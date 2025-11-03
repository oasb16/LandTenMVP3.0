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

  // Debug logging
  console.log("[HybridMessage] Rendering message:", {
    id: message?.id,
    text: message?.text?.substring(0, 50),
    userId: message?.user?.id,
    userName: message?.user?.name,
    hasMessage: !!message,
  });

  if (!message) {
    console.warn("[HybridMessage] No message provided, returning null");
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

  console.log("[HybridMessage] Message classification:", {
    id: message.id,
    actorId,
    actorName,
    isAIMessage,
    renderingWith: isAIMessage ? "CustomMessageUI" : "MessageSimple",
  });

  // For AI messages, use our custom rendering with flow stages and action cards
  if (isAIMessage) {
    // Get current user ID from channel state
    const currentUserId = Object.values(channelState?.members || {}).find((member) => member.user?.id)?.user?.id;
    console.log("[HybridMessage] Rendering AI message with CustomMessageUI");
    // Type assertion: MessageUIComponentProps.message is compatible with MessageResponse
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return (
      <CustomMessageUI
        message={message as any}
        currentUserId={currentUserId}
        onActionClick={triggerAction}
      />
    );
  }

  // For regular messages, use Stream's default component with reactions, threads, etc.
  console.log("[HybridMessage] Rendering regular message with MessageSimple");
  return <MessageSimple {...props} />;
}
