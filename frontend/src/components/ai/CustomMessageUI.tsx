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
    ["incident", "discovery", "job", "bids", "approval", "completion","actions"].includes(att.type)
  );

  // Safely check if message and user exist
  if (!message) {
    return null;
  }

  // Check if message has card attachments
  const hasCardAttachments = message.attachments?.some((att: any) =>
    ['incident', 'discovery', 'job', 'bids', 'approval', 'completion','actions'].includes(att.type)
  );

  // Check if this is an AI bot message
  const isAIMessage = message.user?.id?.startsWith('ai-') ||
                      message.user?.name?.includes('PropertyHelper') ||
                      message.user?.name?.includes('PropertyManager') ||
                      message.user?.name?.includes('JobAssistant') ||
                      message.user?.name?.includes('LandTen Agent') ||
                      message.type === 'ai-message' ||
                      message.type === 'agent' ||
                      message.type === 'card';

  // Get message text safely
  const messageText = message.text || '';

  // Filter out action messages from being displayed as regular text
  const isActionMessage = messageText.startsWith('action:') || messageText.includes('@agent action:');

  return (
    <div className="custom-message-wrapper">
      {/* Render message text if present and not an action message */}
      {messageText && !isActionMessage && (
        <div
          className={`message-text-bubble ${isAIMessage ? 'ai-message' : 'user-message'}`}
          style={{
            padding: '0.75rem 1rem',
            borderRadius: '1rem',
            marginBottom: hasCardAttachments ? '0.5rem' : '0',
            maxWidth: '100%',
            wordBreak: 'break-word',
            ...(isAIMessage ? {
              background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
              color: '#ffffff',
              borderBottomLeftRadius: '0.25rem',
            } : {
              background: '#1f2937',
              color: '#f3f4f6',
              borderBottomRightRadius: '0.25rem',
            })
          }}
        >
          {messageText}
        </div>
      )}

      {/* Render card attachments if present */}
      {hasCardAttachments && (
        <div className="message-cards-wrapper" style={{ marginTop: messageText && !isActionMessage ? '0.5rem' : '0' }}>
          <MessageCards
            message={message as StreamMessage}
            onActionClick={handleActionClick}
          />
        </div>
      )}

      {/* Render other attachments (images, files) that are not cards */}
      {message.attachments && message.attachments.length > 0 && (
        <div className="message-attachments-wrapper" style={{ marginTop: '0.5rem' }}>
          {message.attachments
            .filter((att: any) => !['incident', 'discovery', 'job', 'bids', 'approval', 'completion'].includes(att.type))
            .map((att: any, idx: number) => {
              if (att.type === 'image' && att.image_url) {
                return (
                  <div
                    key={idx}
                    className="message-image-attachment"
                    style={{
                      borderRadius: '0.75rem',
                      overflow: 'hidden',
                      maxWidth: '100%',
                      marginTop: idx > 0 ? '0.5rem' : '0'
                    }}
                  >
                    <img
                      src={att.image_url}
                      alt={att.title || 'Attachment'}
                      style={{
                        width: '100%',
                        height: 'auto',
                        display: 'block',
                        maxHeight: '300px',
                        objectFit: 'cover'
                      }}
                    />
                  </div>
                );
              }
              if (att.type === 'file' && att.asset_url) {
                return (
                  <div
                    key={idx}
                    className="message-file-attachment"
                    style={{
                      padding: '0.75rem 1rem',
                      background: '#f3f4f6',
                      borderRadius: '0.5rem',
                      marginTop: idx > 0 ? '0.5rem' : '0',
                      border: '1px solid #e5e7eb'
                    }}
                  >
                    <a
                      href={att.asset_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        color: '#3b82f6',
                        textDecoration: 'none',
                        fontSize: '0.875rem',
                        fontWeight: '500',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem'
                      }}
                    >
                      <span style={{ fontSize: '1.25rem' }}>📎</span>
                      <span>{att.title || 'File'}</span>
                    </a>
                  </div>
                );
              }
              return null;
            })}
        </div>
      )}

      {/* Inline styles for consistent rendering - works in both SSR and CSR */}
      <style jsx>{`
        .custom-message-wrapper {
          display: flex;
          flex-direction: column;
          width: 100%;
        }

        .message-text-bubble {
          font-size: 0.9375rem;
          line-height: 1.5;
          transition: transform 0.1s ease;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
        }

        .ai-message {
          animation: slideInLeft 0.2s ease-out;
        }

        .user-message {
          animation: slideInRight 0.2s ease-out;
        }

        @keyframes slideInLeft {
          from {
            opacity: 0;
            transform: translateX(-10px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }

        @keyframes slideInRight {
          from {
            opacity: 0;
            transform: translateX(10px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }

        .message-cards-wrapper {
          width: 100%;
          animation: fadeInUp 0.3s ease-out;
        }

        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .message-image-attachment {
          transition: transform 0.2s ease;
        }

        .message-image-attachment:hover {
          transform: scale(1.02);
          cursor: pointer;
        }

        .message-file-attachment {
          transition: all 0.2s ease;
        }

        .message-file-attachment:hover {
          background: #e5e7eb;
          transform: translateX(2px);
        }

        /* Dark mode support for Stream Chat theme */
        :global(.str-chat__theme-dark) .message-file-attachment {
          background: #374151;
          border-color: #4b5563;
        }

        :global(.str-chat__theme-dark) .message-file-attachment:hover {
          background: #4b5563;
        }

        :global(.str-chat__theme-dark) .message-file-attachment a {
          color: #60a5fa;
        }
      `}</style>
    </div>
  );
});
