"use client";

import React, { useCallback } from 'react';
import { MessageCards } from './MessageCards';
import type { StreamMessage } from 'stream-chat';
import type { MessageUIComponentProps } from 'stream-chat-react';

interface CustomMessageUIProps extends MessageUIComponentProps {
  onActionClick?: (actionValue: string) => void;
}

export function CustomMessageUI(props: CustomMessageUIProps) {
  const { message, onActionClick } = props;

  const handleActionClick = useCallback((actionValue: string) => {
    if (onActionClick) {
      onActionClick(actionValue);
    }
  }, [onActionClick]);

  // Check if message has card attachments
  const hasCardAttachments = message.attachments?.some((att: any) =>
    ['incident', 'discovery', 'job', 'bids', 'approval', 'completion'].includes(att.type)
  );

  return (
    <div className="custom-message-ui">
      {/* Render default message content (text, images, etc.) */}
      {message.text && (
        <div className="message-text">
          {message.text}
        </div>
      )}

      {/* Render card attachments if present */}
      {hasCardAttachments && (
        <MessageCards
          message={message as StreamMessage}
          onActionClick={handleActionClick}
        />
      )}

      {/* Render other attachments (images, files) that are not cards */}
      {message.attachments && message.attachments.length > 0 && (
        <div className="message-attachments">
          {message.attachments
            .filter((att: any) => !['incident', 'discovery', 'job', 'bids', 'approval', 'completion'].includes(att.type))
            .map((att: any, idx: number) => {
              if (att.type === 'image' && att.image_url) {
                return (
                  <div key={idx} className="message-image">
                    <img src={att.image_url} alt={att.title || 'Attachment'} />
                  </div>
                );
              }
              if (att.type === 'file' && att.asset_url) {
                return (
                  <div key={idx} className="message-file">
                    <a href={att.asset_url} target="_blank" rel="noopener noreferrer">
                      📎 {att.title || 'File'}
                    </a>
                  </div>
                );
              }
              return null;
            })}
        </div>
      )}
    </div>
  );
}
