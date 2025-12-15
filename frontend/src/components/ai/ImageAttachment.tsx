"use client";

import React, { useState } from 'react';
import { X, Download, ZoomIn } from 'lucide-react';

export interface ImageAttachmentProps {
  url?: string;
  image_url?: string;
  thumb_url?: string;
  fallback?: string;
  title?: string;
  alt?: string;
  aiAnalysis?: string;  // AI-generated analysis from GPT-4o Vision
  aiAnalysisError?: string;
}

/**
 * Image Attachment Component for displaying single images in chat
 *
 * Features:
 * - Lazy loading with blur placeholder
 * - Click to expand in lightbox
 * - AI analysis badge (if available)
 * - Download option
 * - Responsive sizing
 */
export const ImageAttachment: React.FC<ImageAttachmentProps> = ({
  url,
  image_url,
  thumb_url,
  fallback,
  title,
  alt,
  aiAnalysis,
  aiAnalysisError,
}) => {
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);

  // Determine the image URL to display (priority: url > image_url > thumb_url > fallback)
  const imageUrl = url || image_url || thumb_url || fallback || '';
  const thumbnailUrl = thumb_url || imageUrl;

  if (!imageUrl) {
    console.warn('[ImageAttachment] No image URL provided');
    return null;
  }

  const handleDownload = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = title || 'image.jpg';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (error) {
      console.error('[ImageAttachment] Download failed:', error);
    }
  };

  return (
    <>
      {/* Image Container */}
      <div className="relative max-w-md group">
        <button
          onClick={() => setLightboxOpen(true)}
          className="relative block w-full rounded-lg overflow-hidden border border-slate-700 hover:border-blue-500 transition-colors"
        >
          {/* Loading placeholder */}
          {!imageLoaded && (
            <div className="absolute inset-0 bg-slate-800 animate-pulse" />
          )}

          {/* Image */}
          <img
            src={thumbnailUrl}
            alt={alt || title || 'Uploaded image'}
            className={`w-full h-auto object-cover transition-all duration-300 ${
              imageLoaded ? 'opacity-100' : 'opacity-0'
            }`}
            onLoad={() => setImageLoaded(true)}
            style={{ maxHeight: '400px' }}
          />

          {/* Hover Overlay */}
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
            <ZoomIn className="w-8 h-8 text-white drop-shadow-lg" />
          </div>
        </button>

        {/* Download Button */}
        <button
          onClick={handleDownload}
          className="absolute top-2 right-2 p-2 rounded-full bg-slate-900/80 hover:bg-slate-800 transition-colors opacity-0 group-hover:opacity-100"
          title="Download image"
        >
          <Download className="w-4 h-4 text-slate-100" />
        </button>

        {/* AI Analysis Badge */}
        {aiAnalysis && (
          <div className="mt-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
            <div className="flex items-start gap-2">
              <span className="text-emerald-400 text-xs font-semibold">🤖 AI Analysis:</span>
            </div>
            <p className="text-slate-300 text-sm mt-1 leading-relaxed">{aiAnalysis}</p>
          </div>
        )}

        {/* AI Analysis Error */}
        {aiAnalysisError && !aiAnalysis && (
          <div className="mt-2 p-2 rounded-lg bg-amber-500/10 border border-amber-500/30">
            <p className="text-amber-300 text-xs">⚠️ AI analysis unavailable</p>
          </div>
        )}

        {/* Title */}
        {title && (
          <p className="mt-2 text-sm text-slate-400 truncate">{title}</p>
        )}
      </div>

      {/* Lightbox */}
      {lightboxOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center p-4"
          onClick={() => setLightboxOpen(false)}
        >
          {/* Close Button */}
          <button
            onClick={() => setLightboxOpen(false)}
            className="absolute top-4 right-4 p-2 rounded-full bg-slate-800/80 hover:bg-slate-700 transition-colors"
          >
            <X className="w-6 h-6 text-slate-100" />
          </button>

          {/* Full Image */}
          <img
            src={imageUrl}
            alt={alt || title || 'Uploaded image'}
            className="max-w-full max-h-[90vh] object-contain rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />

          {/* Download Button in Lightbox */}
          <button
            onClick={handleDownload}
            className="absolute bottom-4 right-4 px-4 py-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 transition-colors flex items-center gap-2"
          >
            <Download className="w-4 h-4 text-slate-100" />
            <span className="text-sm text-slate-100">Download</span>
          </button>

          {/* AI Analysis in Lightbox */}
          {aiAnalysis && (
            <div className="absolute bottom-4 left-4 max-w-md p-4 rounded-lg bg-slate-900/90 border border-emerald-500/30">
              <div className="flex items-start gap-2">
                <span className="text-emerald-400 text-sm font-semibold">🤖 AI Analysis:</span>
              </div>
              <p className="text-slate-200 text-sm mt-2 leading-relaxed">{aiAnalysis}</p>
            </div>
          )}
        </div>
      )}
    </>
  );
};
