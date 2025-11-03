"use client";

import { useEffect } from "react";
import { Loader2, WifiOff } from "lucide-react";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";
import { Chat, Channel, ChannelHeader, MessageList, MessageInput, Window, Thread } from "stream-chat-react";
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
    });
  }, [client, activeChannel, user]);

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
        <Channel channel={activeChannel} Message={HybridMessage}>
          <Window>
            <ChannelHeader />
            <MessageList />
            <MessageInput />
          </Window>
          <Thread />
        </Channel>
      </Chat>
    </div>
  );
}
