"use client";

import React, { useCallback, memo } from "react";
import { MessageCards } from "./MessageCards";
import type { StreamMessage } from "stream-chat";
import type { MessageUIComponentProps } from "stream-chat-react";

interface CustomMessageUIProps extends MessageUIComponentProps {
  onActionClick?: (actionValue: string) => void;
}

export const CustomMessageUI = memo(function CustomMessageUI({
  message,
  onActionClick,
}: CustomMessageUIProps) {
  // Guard against undefined messages (important for SSR)
  if (!message) return null;

  const handleActionClick = useCallback(
    (actionValue: string) => {
      if (onActionClick) onActionClick(actionValue);
    },
    [onActionClick]
  );

  const attachments = message.attachments || [];
  const cardAttachments = attachments.filter((att: any) =>
    ["incident", "discovery", "job", "bids", "approval", "completion"].includes(att.type)
  );

  const otherAttachments = attachments.filter(
    (att: any) =>
      !["incident", "discovery", "job", "bids", "approval", "completion"].includes(att.type)
  );

  return (
    <div className="custom-message-ui space-y-2 text-sm text-slate-200">
      {/* Message sender */}
      {message.user?.name && (
        <div className="text-xs text-slate-400">{message.user.name}</div>
      )}

      {/* Text content */}
      {message.text && (
        <div className="message-text bg-slate-800/50 px-3 py-2 rounded-lg whitespace-pre-wrap">
          {message.text}
        </div>
      )}

      {/* PropertyAI-style cards */}
      {cardAttachments.length > 0 && (
        <MessageCards
          message={message as StreamMessage}
          onActionClick={handleActionClick}
        />
      )}

      {/* Image & file attachments */}
      {otherAttachments.length > 0 && (
        <div className="message-attachments grid gap-2">
          {otherAttachments.map((att: any, idx: number) => {
            if (att.type === "image" && att.image_url) {
              return (
                <div key={idx} className="rounded-xl overflow-hidden border border-slate-700">
                  <img
                    src={att.image_url}
                    alt={att.title || "Attachment"}
                    className="w-full h-auto"
                  />
                </div>
              );
            }
            if (att.type === "file" && att.asset_url) {
              return (
                <a
                  key={idx}
                  href={att.asset_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:underline flex items-center gap-2"
                >
                  📎 {att.title || "File"}
                </a>
              );
            }
            return null;
          })}
        </div>
      )}
    </div>
  );
});
