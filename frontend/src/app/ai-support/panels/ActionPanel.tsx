/**
 * ActionPanel (CTA Panel)
 *
 * Initial "How can we help?" panel with action options
 */

"use client";

import { motion } from "framer-motion";
import type { ActionPanelProps } from "@/types/ai-support";

export default function ActionPanel({
  options,
  title = "How can we help?",
  subtitle,
  onSelect,
}: ActionPanelProps) {
  if (!options || options.length === 0) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="p-4 border-t bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-950"
    >
      <div className="mb-4">
        <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100">
          {title}
        </h3>
        {subtitle && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {subtitle}
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3">
        {options.map((option, index) => (
          <motion.button
            key={option.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            onClick={() => onSelect(option.id)}
            className="group relative p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm text-left hover:shadow-md hover:border-blue-300 dark:hover:border-blue-600 transition-all duration-200"
          >
            <div className="flex items-start gap-3">
              {option.icon && (
                <span className="text-2xl flex-shrink-0 group-hover:scale-110 transition-transform">
                  {option.icon}
                </span>
              )}
              <div className="flex-1">
                <div className="font-medium text-gray-900 dark:text-gray-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                  {option.label}
                </div>
                {option.description && (
                  <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {option.description}
                  </div>
                )}
              </div>
              <svg
                className="w-5 h-5 text-gray-400 group-hover:text-blue-500 group-hover:translate-x-1 transition-all"
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
