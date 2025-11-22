"use client";

import React, { useState } from 'react';
import { Upload, X, CheckCircle2, AlertCircle, Loader2, Image as ImageIcon, File } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface PendingUpload {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress?: number;
  error?: string;
  previewUrl?: string;
}

interface OptimisticFileUploadProps {
  onUpload: (file: File) => Promise<{ url: string } | null>;
  onComplete?: (url: string) => void;
  accept?: string;
  maxSize?: number; // in bytes
}

export function OptimisticFileUpload({
  onUpload,
  onComplete,
  accept = 'image/*,video/*',
  maxSize = 10 * 1024 * 1024, // 10MB default
}: OptimisticFileUploadProps) {
  const [uploads, setUploads] = useState<PendingUpload[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileSelect = async (file: File) => {
    if (file.size > maxSize) {
      alert(`File size exceeds ${Math.round(maxSize / 1024 / 1024)}MB limit`);
      return;
    }

    const uploadId = `upload-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const previewUrl = file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined;

    // Step 1: Add pending upload immediately
    const newUpload: PendingUpload = {
      id: uploadId,
      file,
      status: 'pending',
      previewUrl,
    };

    setUploads(prev => [...prev, newUpload]);

    // Step 2: Start upload
    try {
      setUploads(prev =>
        prev.map(u => (u.id === uploadId ? { ...u, status: 'uploading' as const } : u))
      );

      const result = await onUpload(file);

      if (result?.url) {
        // Step 3: Mark as success
        setUploads(prev =>
          prev.map(u => (u.id === uploadId ? { ...u, status: 'success' as const } : u))
        );

        onComplete?.(result.url);

        // Remove after delay
        setTimeout(() => {
          setUploads(prev => prev.filter(u => u.id !== uploadId));
          if (previewUrl) URL.revokeObjectURL(previewUrl);
        }, 2000);
      } else {
        throw new Error('Upload failed');
      }
    } catch (error) {
      // Step 3: Mark as error
      setUploads(prev =>
        prev.map(u =>
          u.id === uploadId
            ? { ...u, status: 'error' as const, error: 'Upload failed. Tap to retry.' }
            : u
        )
      );
    }
  };

  const handleRetry = (uploadId: string) => {
    const upload = uploads.find(u => u.id === uploadId);
    if (upload) {
      handleFileSelect(upload.file);
      setUploads(prev => prev.filter(u => u.id !== uploadId));
    }
  };

  const handleRemove = (uploadId: string) => {
    const upload = uploads.find(u => u.id === uploadId);
    if (upload?.previewUrl) {
      URL.revokeObjectURL(upload.previewUrl);
    }
    setUploads(prev => prev.filter(u => u.id !== uploadId));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  };

  return (
    <div className="optimistic-file-upload">
      {/* File input trigger */}
      <label
        className="upload-trigger"
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept={accept}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFileSelect(file);
            e.target.value = ''; // Reset input
          }}
          className="hidden"
        />
        <div className={`upload-area ${isDragging ? 'dragging' : ''}`}>
          <Upload className="h-5 w-5" />
          <span className="text-sm">Attach file</span>
        </div>
      </label>

      {/* Pending uploads */}
      <AnimatePresence>
        {uploads.map((upload) => (
          <motion.div
            key={upload.id}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, height: 0 }}
            className="upload-item"
          >
            {/* Preview */}
            {upload.previewUrl ? (
              <div className="preview-image">
                <img src={upload.previewUrl} alt={upload.file.name} />
              </div>
            ) : (
              <div className="preview-file">
                <File className="h-6 w-6 text-gray-400" />
              </div>
            )}

            {/* Details */}
            <div className="upload-details">
              <div className="file-name">{upload.file.name}</div>
              <div className="file-size">{formatFileSize(upload.file.size)}</div>
              {upload.error && <div className="error-text">{upload.error}</div>}
            </div>

            {/* Status indicator */}
            <div className="status-indicator">
              {upload.status === 'pending' && (
                <div className="pending-spinner">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                </div>
              )}
              {upload.status === 'uploading' && (
                <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
              )}
              {upload.status === 'success' && (
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              )}
              {upload.status === 'error' && (
                <button onClick={() => handleRetry(upload.id)} className="retry-btn">
                  <AlertCircle className="h-5 w-5 text-red-600" />
                </button>
              )}
            </div>

            {/* Remove button */}
            {upload.status !== 'success' && (
              <button onClick={() => handleRemove(upload.id)} className="remove-btn">
                <X className="h-4 w-4" />
              </button>
            )}
          </motion.div>
        ))}
      </AnimatePresence>

      <style jsx>{`
        .upload-trigger {
          cursor: pointer;
        }

        .upload-area {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 1rem;
          background: #f3f4f6;
          border: 2px dashed #d1d5db;
          border-radius: 0.5rem;
          transition: all 0.2s;
        }

        .upload-area:hover {
          background: #e5e7eb;
          border-color: #9ca3af;
        }

        .upload-area.dragging {
          background: #dbeafe;
          border-color: #3b82f6;
        }

        .upload-item {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.75rem;
          background: white;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          margin-top: 0.5rem;
        }

        .preview-image {
          width: 48px;
          height: 48px;
          border-radius: 0.375rem;
          overflow: hidden;
          flex-shrink: 0;
        }

        .preview-image img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .preview-file {
          width: 48px;
          height: 48px;
          display: flex;
          align-items: center;
          justify-center;
          background: #f3f4f6;
          border-radius: 0.375rem;
          flex-shrink: 0;
        }

        .upload-details {
          flex: 1;
          min-width: 0;
        }

        .file-name {
          font-size: 0.875rem;
          font-weight: 500;
          color: #111827;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .file-size {
          font-size: 0.75rem;
          color: #6b7280;
        }

        .error-text {
          font-size: 0.75rem;
          color: #ef4444;
          margin-top: 0.25rem;
        }

        .status-indicator {
          flex-shrink: 0;
        }

        .retry-btn,
        .remove-btn {
          background: none;
          border: none;
          cursor: pointer;
          padding: 0.25rem;
          color: #6b7280;
          transition: color 0.2s;
        }

        .retry-btn:hover {
          color: #ef4444;
        }

        .remove-btn:hover {
          color: #111827;
        }

        /* Dark mode */
        :global(.str-chat__theme-dark) .upload-area {
          background: #374151;
          border-color: #4b5563;
        }

        :global(.str-chat__theme-dark) .upload-area:hover {
          background: #4b5563;
          border-color: #6b7280;
        }

        :global(.str-chat__theme-dark) .upload-item {
          background: #1f2937;
          border-color: #374151;
        }

        :global(.str-chat__theme-dark) .file-name {
          color: #f9fafb;
        }
      `}</style>
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
