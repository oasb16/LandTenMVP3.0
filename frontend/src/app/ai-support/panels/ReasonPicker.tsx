/**
 * ReasonPicker (Selector)
 *
 * Amazon Spec: Stage "issue_select" → UI Mode "selector"
 * Simple string list of issue reasons (no severity badges, no complex metadata)
 */

"use client";

import { motion } from "framer-motion";
import type { ReasonPickerProps } from "@/types/ai-support";

export default function ReasonPicker({
  reasons,
  onSelect,
}: ReasonPickerProps) {
  if (!reasons || reasons.length === 0) {
    return (
      <div className="flex items-center justify-center p-8 text-slate-500">
        <p>No options available</p>
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
        <h3 className="text-lg font-semibold text-slate-100">
          What seems to be the issue?
        </h3>
        <p className="text-sm text-slate-400 mt-1">
          Select the option that best describes the problem
        </p>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto">
        {reasons.map((reason, index) => (
          <motion.button
            key={index}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            onClick={() => onSelect(reason)}
            className="group w-full p-4 bg-slate-800/60 hover:bg-slate-700/60 border border-slate-700/60 hover:border-emerald-500/40 rounded-xl shadow-sm transition-all duration-200 text-left"
          >
            <div className="flex items-center justify-between gap-3">
              <div className="flex-1 font-medium text-slate-100 group-hover:text-emerald-400 transition-colors">
                {reason}
              </div>
              <svg
                className="w-5 h-5 text-slate-500 group-hover:text-emerald-500 group-hover:translate-x-1 transition-all flex-shrink-0"
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
            </div>
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
}
