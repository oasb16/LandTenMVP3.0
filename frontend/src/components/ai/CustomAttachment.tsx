"use client";

/* eslint-disable @typescript-eslint/no-explicit-any */

import React from 'react';
import { Attachment as StreamAttachment } from 'stream-chat-react';
import type { AttachmentProps } from 'stream-chat-react';
import { MessageCards } from './MessageCards';
import { ImageAttachment } from './ImageAttachment';
import { GalleryAttachment } from './GalleryAttachment';
import { FileAttachment } from './FileAttachment';

interface CustomAttachmentProps extends AttachmentProps {
  onActionClick?: (actionValue: string) => void;
}

/**
 * Custom Attachment component for Stream Chat
 *
 * Handles multiple attachment types:
 * - PropertyAI cards (incident, discovery, job, bids, approval, completion)
 * - Images (single)
 * - Gallery (multiple images)
 * - Files (documents, PDFs, etc.)
 * - Video/Audio (delegates to Stream's default player)
 * - Scraped content (delegates to Stream's Card component)
 *
 * Includes AI vision analysis display for images
 */
export const CustomAttachment: React.FC<CustomAttachmentProps> = ({
  attachments,
  onActionClick
}) => {
  if (!attachments || attachments.length === 0) {
    return null;
  }

  console.log('[CustomAttachment] Processing attachments:', {
    total: attachments.length,
    types: attachments.map((a: any) => a.type || 'unknown'),
    details: attachments.map((a: any) => ({
      type: a.type,
      mime_type: a.mime_type,
      title: a.title,
      hasUrl: !!a.url || !!a.image_url || !!a.asset_url,
      aiAnalysis: a.ai_analysis ? 'present' : 'none',
    })),
  });

  // 1. Separate PropertyAI cards
  const cardAttachments = attachments.filter((att: any) =>
    ["incident", "discovery", "job", "bids", "approval", "completion"].includes(att.type)
  );

  // 2. Separate images
  const imageAttachments = attachments.filter((att: any) =>
    att.type === 'image' ||
    (att.mime_type && att.mime_type.startsWith('image/')) ||
    (att.url && /\.(jpg|jpeg|png|gif|webp|bmp|svg|heic|tiff)$/i.test(att.url))
  );

  // 3. Separate files
  const fileAttachments = attachments.filter((att: any) =>
    att.type === 'file' ||
    (att.mime_type && !att.mime_type.startsWith('image/') && !att.mime_type.startsWith('video/') && !att.mime_type.startsWith('audio/'))
  );

  // 4. Everything else (video, audio, scraped content) - delegate to Stream
  const streamAttachments = attachments.filter((att: any) =>
    !["incident", "discovery", "job", "bids", "approval", "completion"].includes(att.type) &&
    att.type !== 'image' &&
    att.type !== 'file' &&
    !imageAttachments.includes(att) &&
    !fileAttachments.includes(att)
  );

  console.log('[CustomAttachment] Categorized:', {
    cards: cardAttachments.length,
    images: imageAttachments.length,
    files: fileAttachments.length,
    stream: streamAttachments.length,
  });

  return (
    <div className="flex flex-col gap-3">
      {/* 1. Render PropertyAI interactive cards */}
      {cardAttachments.length > 0 && (
        <div className="propertyai-cards">
          {cardAttachments.map((attachment: any, index: number) => (
            <div key={`card-${index}`} className="propertyai-card-wrapper">
              <MessageCards
                message={{ attachments: [attachment] } as any}
                onActionClick={onActionClick || (() => {})}
              />
            </div>
          ))}
        </div>
      )}

      {/* 2. Render images (single or gallery) */}
      {imageAttachments.length > 0 && (
        <>
          {imageAttachments.length === 1 ? (
            <ImageAttachment
              key="image-0"
              url={imageAttachments[0].url || imageAttachments[0].image_url || imageAttachments[0].asset_url}
              thumb_url={imageAttachments[0].thumb_url}
              title={imageAttachments[0].title}
              alt={imageAttachments[0].text}
              aiAnalysis={imageAttachments[0].ai_analysis}
              aiAnalysisError={imageAttachments[0].ai_analysis_error}
            />
          ) : (
            <GalleryAttachment
              key="gallery"
              images={imageAttachments.map((img: any) => ({
                url: img.url || img.image_url || img.asset_url,
                thumb_url: img.thumb_url,
                title: img.title,
                alt: img.text,
                aiAnalysis: img.ai_analysis,
              }))}
            />
          )}
        </>
      )}

      {/* 3. Render files */}
      {fileAttachments.length > 0 && (
        <div className="flex flex-col gap-2">
          {fileAttachments.map((file: any, index: number) => (
            <FileAttachment
              key={`file-${index}`}
              url={file.url || file.asset_url}
              title={file.title}
              text={file.text}
              file_size={file.file_size}
              mime_type={file.mime_type}
            />
          ))}
        </div>
      )}

      {/* 4. Render video/audio/scraped content using Stream's default renderer */}
      {streamAttachments.length > 0 && (
        <StreamAttachment attachments={streamAttachments} />
      )}

      <style jsx>{`
        .propertyai-cards {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .propertyai-card-wrapper {
          width: 100%;
          max-width: 600px;
        }
      `}</style>
    </div>
  );
};
