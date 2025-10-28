"use client";

import React from 'react';
import { Attachment as StreamAttachment } from 'stream-chat-react';
import type { AttachmentProps } from 'stream-chat-react';
import { MessageCards } from './MessageCards';

interface CustomAttachmentProps extends AttachmentProps {
  onActionClick?: (actionValue: string) => void;
}

/**
 * Custom Attachment component for PropertyAI interactive cards
 *
 * This component integrates with Stream Chat's attachment rendering pipeline
 * to display custom card types (incident, discovery, job, bids, approval, completion)
 *
 * Usage: Pass this component to Channel's `Attachment` prop
 */
export const CustomAttachment: React.FC<CustomAttachmentProps> = ({
  attachments,
  onActionClick
}) => {
  if (!attachments || attachments.length === 0) {
    return null;
  }

  // Separate PropertyAI cards from standard attachments
  const cardAttachments = attachments.filter((att: any) =>
    ["incident", "discovery", "job", "bids", "approval", "completion"].includes(att.type)
  );

  const standardAttachments = attachments.filter((att: any) =>
    !["incident", "discovery", "job", "bids", "approval", "completion"].includes(att.type)
  );

  console.log('[CustomAttachment] Rendering attachments:', {
    total: attachments.length,
    cardCount: cardAttachments.length,
    standardCount: standardAttachments.length,
    cardTypes: cardAttachments.map((a: any) => a.type)
  });

  return (
    <>
      {/* Render PropertyAI interactive cards */}
      {cardAttachments.length > 0 && (
        <div className="propertyai-cards">
          {cardAttachments.map((attachment: any, index: number) => (
            <div key={index} className="propertyai-card-wrapper">
              <MessageCards
                message={{ attachments: [attachment] } as any}
                onActionClick={onActionClick || (() => {})}
              />
            </div>
          ))}
        </div>
      )}

      {/* Render standard attachments using Stream's default renderer */}
      {standardAttachments.length > 0 && (
        <StreamAttachment attachments={standardAttachments} />
      )}

      <style jsx>{`
        .propertyai-cards {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          margin: 0.5rem 0;
          width: 100%;
        }

        .propertyai-card-wrapper {
          width: 100%;
          max-width: 600px;
        }
      `}</style>
    </>
  );
};
