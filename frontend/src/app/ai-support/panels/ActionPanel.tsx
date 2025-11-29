/**
 * ActionPanel (CTA Panel)
 *
 * Amazon Spec: Stage "intro" → UI Mode "cta_panel"
 * Large button menu: "What do you need help with?"
 */

"use client";

import { motion } from "framer-motion";
import type { ActionPanelProps } from "@/types/ai-support";

export default function ActionPanel({
  options,
  onSelect,
}: ActionPanelProps) {
  if (!options || options.length === 0) {
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
          How can we help you today?
        </h3>
        <p className="text-sm text-slate-400 mt-1">
          Select the option that best describes what you need
        </p>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto">
        {options.map((option, index) => (
          <motion.button
            key={option.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.08 }}
            onClick={() => onSelect(option.id)}
            className="group w-full p-4 bg-slate-800/60 hover:bg-slate-700/60 border border-slate-700/60 hover:border-emerald-500/40 rounded-xl shadow-sm text-left transition-all duration-200"
          >
            <div className="flex items-start gap-3">
              {option.icon && (
                <span className="text-2xl flex-shrink-0 group-hover:scale-110 transition-transform">
                  {option.icon}
                </span>
              )}
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-slate-100 group-hover:text-emerald-400 transition-colors">
                  {option.label}
                </div>
                {option.description && (
                  <div className="text-sm text-slate-400 mt-1">
                    {option.description}
                  </div>
                )}
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
