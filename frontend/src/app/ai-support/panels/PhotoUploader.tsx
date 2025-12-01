/**
 * PhotoUploader
 *
 * Phase 1: Tenant Photo Upload
 * Stage "photo_upload" → UI Mode "photo_uploader"
 * Allows tenants to upload photos of maintenance issues
 */

"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, X, Camera, CheckCircle } from "lucide-react";
import type { PhotoUploaderProps } from "@/types/ai-support";
import Image from "next/image";

export default function PhotoUploader({
  maxPhotos = 5,
  required = false,
  existingPhotos = [],
  onUpload,
  onSkip,
}: PhotoUploaderProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return;

    const newFiles = Array.from(files).slice(0, maxPhotos - selectedFiles.length);
    const newPreviews = newFiles.map((file) => URL.createObjectURL(file));

    setSelectedFiles((prev) => [...prev, ...newFiles]);
    setPreviewUrls((prev) => [...prev, ...newPreviews]);
  };

  const handleRemove = (index: number) => {
    URL.revokeObjectURL(previewUrls[index]);
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setPreviewUrls((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const handleUpload = () => {
    onUpload(selectedFiles);
  };

  const canUpload = selectedFiles.length > 0;
  const canSkip = !required && onSkip;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col h-full"
    >
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-slate-100">
          Add photos of the issue {required && <span className="text-red-400">*</span>}
        </h3>
        <p className="text-sm text-slate-400 mt-1">
          Photos help us understand the problem better (up to {maxPhotos} photos)
        </p>
      </div>

      {/* Upload Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          relative border-2 border-dashed rounded-xl p-8 mb-4 cursor-pointer
          transition-all duration-200
          ${isDragging
            ? "border-emerald-500 bg-emerald-500/10"
            : "border-slate-700/60 bg-slate-800/40 hover:border-emerald-500/50 hover:bg-slate-800/60"
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={(e) => handleFileSelect(e.target.files)}
          className="hidden"
        />

        <div className="flex flex-col items-center justify-center gap-3">
          {isDragging ? (
            <Camera className="w-12 h-12 text-emerald-400" />
          ) : (
            <Upload className="w-12 h-12 text-slate-400" />
          )}
          <div className="text-center">
            <p className="text-slate-100 font-medium">
              {isDragging ? "Drop photos here" : "Click to upload or drag and drop"}
            </p>
            <p className="text-sm text-slate-500 mt-1">
              PNG, JPG, HEIC up to 10MB each
            </p>
          </div>
        </div>
      </div>

      {/* Preview Grid */}
      {(selectedFiles.length > 0 || existingPhotos.length > 0) && (
        <div className="flex-1 overflow-y-auto mb-4">
          <h4 className="text-sm font-medium text-slate-300 mb-2">
            Selected Photos ({selectedFiles.length + existingPhotos.length}/{maxPhotos})
          </h4>
          <div className="grid grid-cols-2 gap-3">
            {/* Existing Photos */}
            {existingPhotos.map((url, index) => (
              <div
                key={`existing-${index}`}
                className="relative aspect-square rounded-lg overflow-hidden bg-slate-700 border border-slate-600"
              >
                <Image
                  src={url}
                  alt={`Existing photo ${index + 1}`}
                  fill
                  className="object-cover"
                  sizes="(max-width: 768px) 50vw, 200px"
                />
                <div className="absolute top-2 right-2 bg-emerald-500 rounded-full p-1">
                  <CheckCircle className="w-4 h-4 text-emerald-950" />
                </div>
              </div>
            ))}

            {/* New Photos */}
            <AnimatePresence>
              {previewUrls.map((url, index) => (
                <motion.div
                  key={url}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="relative aspect-square rounded-lg overflow-hidden bg-slate-700 border border-slate-600 group"
                >
                  <Image
                    src={url}
                    alt={`Preview ${index + 1}`}
                    fill
                    className="object-cover"
                    sizes="(max-width: 768px) 50vw, 200px"
                  />
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemove(index);
                    }}
                    className="absolute top-2 right-2 bg-red-500 hover:bg-red-400 rounded-full p-1.5 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X className="w-4 h-4 text-white" />
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        {canSkip && (
          <button
            onClick={onSkip}
            className="flex-1 px-4 py-3 bg-slate-700/60 hover:bg-slate-600/60 border border-slate-600/60 hover:border-slate-500/60 rounded-xl text-slate-200 font-semibold transition-all duration-200"
          >
            Skip for now
          </button>
        )}
        <button
          onClick={handleUpload}
          disabled={!canUpload}
          className={`
            ${canSkip ? "flex-1" : "w-full"} px-4 py-3 rounded-xl font-semibold
            shadow-lg transition-all duration-200
            ${canUpload
              ? "bg-emerald-500 hover:bg-emerald-400 text-emerald-950 shadow-emerald-500/20 hover:shadow-emerald-500/30"
              : "bg-slate-700/40 text-slate-500 cursor-not-allowed"
            }
          `}
        >
          {canUpload ? `Upload ${selectedFiles.length} photo${selectedFiles.length !== 1 ? "s" : ""}` : "Select photos to continue"}
        </button>
      </div>
    </motion.div>
  );
}
