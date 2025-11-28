/**
 * DiagnosisPanel
 *
 * Shows loading state while AI analyzes the issue
 */

"use client";

import { motion } from "framer-motion";
import type { DiagnosisPayload } from "@/types/ai-support";

interface DiagnosisPanelProps {
  data?: DiagnosisPayload;
}

export default function DiagnosisPanel({ data }: DiagnosisPanelProps) {
  const status = data?.status || "analyzing";
  const message = data?.message || "Analyzing your issue...";
  const progress = data?.progress;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="p-6 border-t bg-gradient-to-b from-blue-50 to-white dark:from-blue-900/10 dark:to-gray-950"
    >
      <div className="flex flex-col items-center justify-center py-8">
        {/* Animated Spinner */}
        {status === "analyzing" && (
          <motion.div
            className="relative w-16 h-16 mb-6"
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          >
            <div className="absolute inset-0 border-4 border-blue-200 dark:border-blue-900 rounded-full" />
            <div className="absolute inset-0 border-4 border-blue-600 dark:border-blue-400 rounded-full border-t-transparent" />
          </motion.div>
        )}

        {/* Success Icon */}
        {status === "complete" && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200 }}
            className="w-16 h-16 mb-6 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center"
          >
            <svg
              className="w-8 h-8 text-green-600 dark:text-green-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={3}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </motion.div>
        )}

        {/* Error Icon */}
        {status === "error" && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200 }}
            className="w-16 h-16 mb-6 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center"
          >
            <svg
              className="w-8 h-8 text-red-600 dark:text-red-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </motion.div>
        )}

        {/* Message */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-center"
        >
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
            {message}
          </h3>

          {status === "analyzing" && (
            <p className="text-sm text-gray-600 dark:text-gray-400">
              This usually takes a few seconds
            </p>
          )}
        </motion.div>

        {/* Progress Bar */}
        {typeof progress === "number" && (
          <motion.div
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: "100%" }}
            className="w-full max-w-xs mt-6"
          >
            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5 }}
                className="h-full bg-blue-600 dark:bg-blue-400"
              />
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 text-center mt-2">
              {progress}% complete
            </div>
          </motion.div>
        )}

        {/* Pulsing Dots Animation */}
        {status === "analyzing" && !progress && (
          <div className="flex gap-2 mt-4">
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="w-2 h-2 bg-blue-600 dark:bg-blue-400 rounded-full"
                animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
                transition={{
                  duration: 1,
                  repeat: Infinity,
                  delay: i * 0.2,
                }}
              />
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
