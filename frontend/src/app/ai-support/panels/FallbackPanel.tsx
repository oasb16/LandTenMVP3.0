/**
 * FallbackPanel
 *
 * Amazon Spec: UI Mode "fallback"
 * Displayed when chat is unavailable or an error occurs
 */

"use client";

import { motion } from "framer-motion";
import type { FallbackPanelProps } from "@/types/ai-support";

export default function FallbackPanel({
  error,
}: FallbackPanelProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col items-center justify-center p-8 text-center h-full"
    >
      <div className="w-16 h-16 bg-rose-500/20 rounded-full flex items-center justify-center mb-4">
        <svg
          className="w-8 h-8 text-rose-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      </div>

      <h3 className="text-lg font-semibold text-slate-100 mb-2">
        Something went wrong
      </h3>

      <p className="text-sm text-slate-400 mb-6 max-w-md">
        {error || "We're having trouble loading the support assistant right now."}
      </p>

      <div className="space-y-2">
        <button
          onClick={() => window.location.reload()}
          className="px-6 py-2 bg-emerald-500 hover:bg-emerald-400 text-emerald-950 rounded-lg font-semibold transition"
        >
          Try Again
        </button>

        <div className="text-xs text-slate-500">
          or <a href="/dashboard" className="text-emerald-400 hover:underline">return to dashboard</a>
        </div>
      </div>
    </motion.div>
  );
}
