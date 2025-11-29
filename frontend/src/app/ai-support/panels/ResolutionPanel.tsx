/**
 * ResolutionPanel
 *
 * Amazon Spec: Stage "resolution" → UI Mode "resolution"
 * Final actions user can take after diagnosis (simple summary + action buttons)
 */

"use client";

import { motion } from "framer-motion";
import type { ResolutionPanelProps } from "@/types/ai-support";

export default function ResolutionPanel({
  summary,
  actions,
  onAction
}: ResolutionPanelProps) {
  if (!actions || actions.length === 0) {
    return (
      <div className="flex items-center justify-center p-8 text-slate-500">
        <p>No resolution options available</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col h-full"
    >
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-slate-100 mb-3">
          Here&apos;s what we found
        </h3>

        {/* Summary */}
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl mb-4">
          <p className="text-slate-100 leading-relaxed">
            {summary}
          </p>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex-1 space-y-3 overflow-y-auto">
        <p className="text-sm text-slate-400 mb-2">
          Choose an action to proceed:
        </p>
        {actions.map((action, index) => (
          <motion.button
            key={action.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.08 }}
            onClick={() => onAction(action.id)}
            className="w-full p-4 bg-emerald-500 hover:bg-emerald-400 text-emerald-950 rounded-xl font-semibold shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 transition-all duration-200 flex items-center justify-between gap-3"
          >
            <span>{action.label}</span>
            <svg
              className="w-5 h-5 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
}
