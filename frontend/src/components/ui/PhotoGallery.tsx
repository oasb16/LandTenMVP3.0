"use client";

import * as React from "react";
import { X, ChevronLeft, ChevronRight } from "lucide-react";

type Photo = {
  url: string;
  photo_id: string;
};

type PhotoGalleryProps = {
  photos: Photo[];
  className?: string;
};

const cn = (...classes: Array<string | false | null | undefined>) =>
  classes.filter(Boolean).join(" ");

export const PhotoGallery: React.FC<PhotoGalleryProps> = ({ photos, className }) => {
  const [lightboxOpen, setLightboxOpen] = React.useState(false);
  const [currentIndex, setCurrentIndex] = React.useState(0);

  const openLightbox = (index: number) => {
    setCurrentIndex(index);
    setLightboxOpen(true);
  };

  const closeLightbox = () => {
    setLightboxOpen(false);
  };

  const goToPrevious = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : photos.length - 1));
  };

  const goToNext = () => {
    setCurrentIndex((prev) => (prev < photos.length - 1 ? prev + 1 : 0));
  };

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!lightboxOpen) return;
      if (e.key === "Escape") closeLightbox();
      if (e.key === "ArrowLeft") goToPrevious();
      if (e.key === "ArrowRight") goToNext();
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [lightboxOpen]);

  if (!photos || photos.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400">
        No photos available
      </div>
    );
  }

  return (
    <>
      {/* Gallery Grid */}
      <div className={cn("grid grid-cols-2 md:grid-cols-3 gap-4", className)}>
        {photos.map((photo, index) => (
          <button
            key={photo.photo_id}
            onClick={() => openLightbox(index)}
            className="relative aspect-square overflow-hidden rounded-lg border border-slate-700 hover:border-blue-500 transition-colors group"
          >
            <img
              src={photo.url}
              alt={`Photo ${index + 1}`}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
            />
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
          </button>
        ))}
      </div>

      {/* Lightbox */}
      {lightboxOpen && (
        <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center">
          {/* Close Button */}
          <button
            onClick={closeLightbox}
            className="absolute top-4 right-4 p-2 rounded-full bg-slate-800/80 hover:bg-slate-700 transition-colors"
          >
            <X className="w-6 h-6 text-slate-100" />
          </button>

          {/* Previous Button */}
          {photos.length > 1 && (
            <button
              onClick={goToPrevious}
              className="absolute left-4 p-2 rounded-full bg-slate-800/80 hover:bg-slate-700 transition-colors"
            >
              <ChevronLeft className="w-6 h-6 text-slate-100" />
            </button>
          )}

          {/* Image */}
          <div className="max-w-7xl max-h-[90vh] p-4">
            <img
              src={photos[currentIndex].url}
              alt={`Photo ${currentIndex + 1}`}
              className="max-w-full max-h-full object-contain rounded-lg"
            />
          </div>

          {/* Next Button */}
          {photos.length > 1 && (
            <button
              onClick={goToNext}
              className="absolute right-4 p-2 rounded-full bg-slate-800/80 hover:bg-slate-700 transition-colors"
            >
              <ChevronRight className="w-6 h-6 text-slate-100" />
            </button>
          )}

          {/* Counter */}
          <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 px-4 py-2 rounded-full bg-slate-800/80 text-slate-100 text-sm">
            {currentIndex + 1} / {photos.length}
          </div>
        </div>
      )}
    </>
  );
};
