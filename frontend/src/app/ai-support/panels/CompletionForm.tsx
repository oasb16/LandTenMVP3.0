/**
 * CompletionForm
 *
 * Phase 5: Job Completion
 * Stage "job_completion" → UI Mode "completion_form"
 * Contractor marks job as complete with summary and photos
 */

"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, Camera, Upload, X, CheckCircle } from "lucide-react";
import type { CompletionFormProps } from "@/types/ai-support";
import Image from "next/image";

export default function CompletionForm({
  jobId,
  jobTitle,
  workSummaryRequired,
  photosRequired,
  onSubmit,
  onCancel,
}: CompletionFormProps) {
  const [summary, setSummary] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return;

    const newFiles = Array.from(files).slice(0, 10 - selectedFiles.length);
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

  const validate = () => {
    const newErrors: Record<string, string> = {};

    if (workSummaryRequired && !summary.trim()) {
      newErrors.summary = "Work summary is required";
    } else if (summary.trim() && summary.trim().length < 20) {
      newErrors.summary = "Please provide a more detailed summary (at least 20 characters)";
    }

    if (photosRequired && selectedFiles.length === 0) {
      newErrors.photos = "At least one photo is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = () => {
    if (validate()) {
      onSubmit({ summary, photos: selectedFiles });
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col h-full"
    >
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-slate-100 mb-1">
          Mark Job as Complete
        </h3>
        <p className="text-sm text-slate-400">{jobTitle}</p>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {/* Work Summary */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              <span>
                Work Summary
                {workSummaryRequired && <span className="text-red-400 ml-1">*</span>}
              </span>
            </div>
          </label>
          <textarea
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            placeholder="Describe the work completed, any issues encountered, and recommendations for future maintenance..."
            rows={6}
            className={`
              w-full px-4 py-3 bg-slate-800/60 border rounded-xl
              text-slate-100 placeholder-slate-500
              focus:outline-none focus:ring-2 focus:ring-emerald-500/50
              resize-none
              ${errors.summary ? "border-red-500/50" : "border-slate-700/60"}
            `}
          />
          {errors.summary && (
            <p className="mt-1 text-sm text-red-400">{errors.summary}</p>
          )}
          {summary.trim() && (
            <p className="mt-1 text-xs text-slate-500">
              {summary.trim().length} characters
              {summary.trim().length < 20 && workSummaryRequired && (
                <span className="text-orange-400"> (minimum 20)</span>
              )}
            </p>
          )}
        </div>

        {/* Completion Photos */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            <div className="flex items-center gap-2">
              <Camera className="w-4 h-4" />
              <span>
                Completion Photos
                {photosRequired && <span className="text-red-400 ml-1">*</span>}
              </span>
            </div>
          </label>

          {/* Upload Zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`
              relative border-2 border-dashed rounded-xl p-6 cursor-pointer
              transition-all duration-200 mb-3
              ${isDragging
                ? "border-emerald-500 bg-emerald-500/10"
                : errors.photos
                  ? "border-red-500/50 bg-slate-800/40"
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

            <div className="flex flex-col items-center justify-center gap-2">
              {isDragging ? (
                <Camera className="w-10 h-10 text-emerald-400" />
              ) : (
                <Upload className="w-10 h-10 text-slate-400" />
              )}
              <div className="text-center">
                <p className="text-sm text-slate-100 font-medium">
                  {isDragging ? "Drop photos here" : "Upload completion photos"}
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Click or drag photos here (up to 10)
                </p>
              </div>
            </div>
          </div>

          {errors.photos && (
            <p className="mb-2 text-sm text-red-400">{errors.photos}</p>
          )}

          {/* Preview Grid */}
          {selectedFiles.length > 0 && (
            <div>
              <p className="text-xs text-slate-400 mb-2">
                {selectedFiles.length} photo{selectedFiles.length !== 1 ? "s" : ""} selected
              </p>
              <div className="grid grid-cols-3 gap-2">
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
                        sizes="150px"
                      />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemove(index);
                        }}
                        className="absolute top-1 right-1 bg-red-500 hover:bg-red-400 rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <X className="w-3 h-3 text-white" />
                      </button>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </div>
          )}
        </div>

        {/* Info Box */}
        <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-xl">
          <p className="text-sm text-blue-400">
            💡 Tip: Include before/after photos and document any additional work performed
          </p>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={onCancel}
          className="flex-1 px-4 py-3 bg-slate-700/60 hover:bg-slate-600/60 border border-slate-600/60 hover:border-slate-500/60 rounded-xl text-slate-200 font-semibold transition-all duration-200"
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          className="flex-1 px-4 py-3 bg-emerald-500 hover:bg-emerald-400 text-emerald-950 rounded-xl font-semibold shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 transition-all duration-200 flex items-center justify-center gap-2"
        >
          <CheckCircle className="w-4 h-4" />
          <span>Submit Completion</span>
        </button>
      </div>
    </motion.div>
  );
}
