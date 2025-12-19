"use client";

import React, { useEffect, useRef } from "react";
import { MessageList } from "stream-chat-react";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";
import { Loader2, ChevronUp } from "lucide-react";

export function MessageListWithPagination() {
  const { hasMoreMessages, loadingMore, loadMoreMessages } = useStreamChat();
  const messageListRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll to bottom on initial load
  useEffect(() => {
    const timer = setTimeout(() => {
      const messageList = document.querySelector('.str-chat__list');
      if (messageList) {
        messageList.scrollTop = 0;
      }
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  return (
    <div ref={messageListRef} className="relative flex-1 overflow-hidden">
      {/* Load More Button - WhatsApp Style */}
      {hasMoreMessages && (
        <div className="absolute top-0 left-0 right-0 z-10 flex justify-center pt-2 pb-1">
          <button
            onClick={loadMoreMessages}
            disabled={loadingMore}
            className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-white bg-slate-800/90 hover:bg-slate-700/90 border border-slate-600/50 rounded-full shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed backdrop-blur-sm"
            style={{
              minWidth: '120px',
            }}
          >
            {loadingMore ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                <span>Loading...</span>
              </>
            ) : (
              <>
                <ChevronUp className="h-3 w-3" />
                <span>Load More</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Stream Chat MessageList */}
      <MessageList
        disableDateSeparator={false}
        messageLimit={100} // Higher limit to accommodate pagination
        hideTypingIndicator={false}
      />
    </div>
  );
}
