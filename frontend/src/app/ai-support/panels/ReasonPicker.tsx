/**
 * ReasonPicker (Selector)
 *
 * Displays issue/reason options for user selection
 */

"use client";

import { motion } from "framer-motion";
import type { ReasonPickerProps } from "@/types/ai-support";

const severityColors = {
  low: "bg-green-100 dark:bg-green-900/30 border-green-300 dark:border-green-700 text-green-800 dark:text-green-300",
  medium: "bg-yellow-100 dark:bg-yellow-900/30 border-yellow-300 dark:border-yellow-700 text-yellow-800 dark:text-yellow-300",
  high: "bg-orange-100 dark:bg-orange-900/30 border-orange-300 dark:border-orange-700 text-orange-800 dark:text-orange-300",
  urgent: "bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-700 text-red-800 dark:text-red-300",
};

const severityLabels = {
  low: "Low",
  medium: "Medium",
  high: "High",
  urgent: "Urgent",
};

export default function ReasonPicker({
  reasons,
  title = "What seems to be the issue?",
  subtitle,
  selectedItem,
  onSelect,
}: ReasonPickerProps) {
  if (!reasons || reasons.length === 0) {
    return (
      <div className="p-6 text-center text-gray-500 dark:text-gray-400">
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
      className="p-4 border-t bg-gray-50 dark:bg-gray-900"
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
        {selectedItem && (
          <div className="mt-2 p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
            <div className="text-xs text-blue-600 dark:text-blue-400 font-medium">
              Selected: {selectedItem.title}
            </div>
          </div>
        )}
      </div>

      <div className="space-y-3 max-h-80 overflow-y-auto">
        {reasons.map((reason, index) => (
          <motion.button
            key={reason.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            onClick={() => onSelect(reason.id, reason)}
            className="group w-full p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md hover:border-blue-300 dark:hover:border-blue-600 transition-all duration-200 text-left"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="font-medium text-gray-900 dark:text-gray-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                  {reason.label}
                </div>
                {reason.description && (
                  <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {reason.description}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                {reason.severity && (
                  <span
                    className={`text-xs px-2 py-1 rounded-full font-medium ${
                      severityColors[reason.severity]
                    }`}
                  >
                    {severityLabels[reason.severity]}
                  </span>
                )}
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
            </div>
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
}
