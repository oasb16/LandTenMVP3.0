"use client";

import React, { useState, useEffect } from 'react';
import { X, ChevronLeft, ChevronRight, Download } from 'lucide-react';

export interface GalleryImage {
  url?: string;
  image_url?: string;
  thumb_url?: string;
  fallback?: string;
  title?: string;
  alt?: string;
  aiAnalysis?: string;
}

export interface GalleryAttachmentProps {
  images: GalleryImage[];
}

/**
 * Gallery Attachment Component for displaying multiple images in chat
 *
 * Features:
 * - Grid layout (2-4 columns based on count)
 * - Click to open lightbox with navigation
 * - Keyboard navigation (Arrow keys, Escape)
 * - AI analysis display in lightbox
 * - Download option
 */
export const GalleryAttachment: React.FC<GalleryAttachmentProps> = ({ images }) => {
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  if (!images || images.length === 0) {
    return null;
  }

  // If only one image, show it in a simple layout
  if (images.length === 1) {
    const img = images[0];
    const imageUrl = img.url || img.image_url || img.thumb_url || img.fallback || '';
    return (
      <div className="relative max-w-md">
        <button
          onClick={() => {
            setCurrentIndex(0);
            setLightboxOpen(true);
          }}
          className="block w-full rounded-lg overflow-hidden border border-slate-700 hover:border-blue-500 transition-colors"
        >
          <img
            src={imageUrl}
            alt={img.alt || img.title || 'Image'}
            className="w-full h-auto object-cover"
            style={{ maxHeight: '400px' }}
          />
        </button>
        {img.title && (
          <p className="mt-2 text-sm text-slate-400 truncate">{img.title}</p>
        )}
      </div>
    );
  }

  const openLightbox = (index: number) => {
    setCurrentIndex(index);
    setLightboxOpen(true);
  };

  const closeLightbox = () => {
    setLightboxOpen(false);
  };

  const goToPrevious = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : images.length - 1));
  };

  const goToNext = () => {
    setCurrentIndex((prev) => (prev < images.length - 1 ? prev + 1 : 0));
  };

  // Keyboard navigation
  useEffect(() => {
    if (!lightboxOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeLightbox();
      if (e.key === 'ArrowLeft') goToPrevious();
      if (e.key === 'ArrowRight') goToNext();
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [lightboxOpen, currentIndex]);

  // Grid columns based on image count
  const gridCols = images.length === 2 ? 'grid-cols-2' : images.length === 3 ? 'grid-cols-3' : 'grid-cols-2 md:grid-cols-4';

  const handleDownload = async (imageUrl: string, title?: string) => {
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
      console.error('[GalleryAttachment] Download failed:', error);
    }
  };

  return (
    <>
      {/* Gallery Grid */}
      <div className={`grid ${gridCols} gap-2 max-w-2xl`}>
        {images.map((img, index) => {
          const imageUrl = img.url || img.image_url || img.thumb_url || img.fallback || '';
          const thumbnailUrl = img.thumb_url || imageUrl;

          return (
            <button
              key={index}
              onClick={() => openLightbox(index)}
              className="relative aspect-square overflow-hidden rounded-lg border border-slate-700 hover:border-blue-500 transition-colors group"
            >
              <img
                src={thumbnailUrl}
                alt={img.alt || img.title || `Image ${index + 1}`}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
              />
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />

              {/* AI Analysis Indicator */}
              {img.aiAnalysis && (
                <div className="absolute top-2 left-2 px-2 py-1 rounded bg-emerald-500/80 text-white text-xs font-semibold">
                  🤖 AI
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Image Counter */}
      <p className="mt-2 text-xs text-slate-400">
        {images.length} image{images.length > 1 ? 's' : ''}
      </p>

      {/* Lightbox */}
      {lightboxOpen && (
        <div className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center">
          {/* Close Button */}
          <button
            onClick={closeLightbox}
            className="absolute top-4 right-4 p-2 rounded-full bg-slate-800/80 hover:bg-slate-700 transition-colors z-10"
          >
            <X className="w-6 h-6 text-slate-100" />
          </button>

          {/* Previous Button */}
          {images.length > 1 && (
            <button
              onClick={goToPrevious}
              className="absolute left-4 p-2 rounded-full bg-slate-800/80 hover:bg-slate-700 transition-colors z-10"
            >
              <ChevronLeft className="w-6 h-6 text-slate-100" />
            </button>
          )}

          {/* Current Image */}
          <div className="max-w-7xl max-h-[90vh] p-4 flex items-center justify-center">
            <img
              src={images[currentIndex].url || images[currentIndex].image_url || images[currentIndex].thumb_url || ''}
              alt={images[currentIndex].alt || images[currentIndex].title || `Image ${currentIndex + 1}`}
              className="max-w-full max-h-full object-contain rounded-lg"
            />
          </div>

          {/* Next Button */}
          {images.length > 1 && (
            <button
              onClick={goToNext}
              className="absolute right-4 p-2 rounded-full bg-slate-800/80 hover:bg-slate-700 transition-colors z-10"
            >
              <ChevronRight className="w-6 h-6 text-slate-100" />
            </button>
          )}

          {/* Download Button */}
          <button
            onClick={() => {
              const img = images[currentIndex];
              const imageUrl = img.url || img.image_url || img.thumb_url || '';
              handleDownload(imageUrl, img.title);
            }}
            className="absolute bottom-20 right-4 px-4 py-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 transition-colors flex items-center gap-2"
          >
            <Download className="w-4 h-4 text-slate-100" />
            <span className="text-sm text-slate-100">Download</span>
          </button>

          {/* AI Analysis */}
          {images[currentIndex].aiAnalysis && (
            <div className="absolute bottom-4 left-4 max-w-md p-4 rounded-lg bg-slate-900/90 border border-emerald-500/30">
              <div className="flex items-start gap-2">
                <span className="text-emerald-400 text-sm font-semibold">🤖 AI Analysis:</span>
              </div>
              <p className="text-slate-200 text-sm mt-2 leading-relaxed">
                {images[currentIndex].aiAnalysis}
              </p>
            </div>
          )}

          {/* Counter */}
          <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 px-4 py-2 rounded-full bg-slate-800/80 text-slate-100 text-sm">
            {currentIndex + 1} / {images.length}
          </div>
        </div>
      )}
    </>
  );
};
