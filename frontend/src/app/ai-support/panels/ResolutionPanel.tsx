/**
 * ResolutionPanel
 *
 * Displays resolution options and summary after diagnosis
 */

"use client";

import { motion } from "framer-motion";
import type { ResolutionPanelProps } from "@/types/ai-support";

const severityColors = {
  low: "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-800 dark:text-green-300",
  medium: "bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800 text-yellow-800 dark:text-yellow-300",
  high: "bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800 text-orange-800 dark:text-orange-300",
  urgent: "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-800 dark:text-red-300",
};

const actionTypeStyles = {
  primary: "bg-blue-600 hover:bg-blue-700 text-white",
  secondary: "bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100",
  danger: "bg-red-600 hover:bg-red-700 text-white",
};

export default function ResolutionPanel({ data, onAction }: ResolutionPanelProps) {
  if (!data || !data.actions || data.actions.length === 0) {
    return (
      <div className="p-6 text-center text-gray-500 dark:text-gray-400">
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
      className="p-4 border-t bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-950"
    >
      <div className="mb-4">
        <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100 mb-3">
          Here&apos;s what we can do
        </h3>

        {/* Severity Badge */}
        {data.severity && (
          <div
            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium mb-3 ${
              severityColors[data.severity]
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
            {data.severity.charAt(0).toUpperCase() + data.severity.slice(1)} Priority
          </div>
        )}

        {/* Summary */}
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg mb-4">
          <p className="text-gray-800 dark:text-gray-200 leading-relaxed">
            {data.summary}
          </p>
        </div>

        {/* Diagnosis Details */}
        {data.diagnosis && (
          <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-lg mb-4 text-sm">
            <div className="font-medium text-gray-700 dark:text-gray-300 mb-1">
              Diagnosis
            </div>
            <div className="text-gray-600 dark:text-gray-400">
              {data.diagnosis}
            </div>
          </div>
        )}

        {/* Estimates */}
        {(data.estimated_time || data.estimated_cost) && (
          <div className="flex gap-3 mb-4">
            {data.estimated_time && (
              <div className="flex-1 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                  Estimated Time
                </div>
                <div className="font-semibold text-gray-900 dark:text-gray-100">
                  {data.estimated_time}
                </div>
              </div>
            )}
            {data.estimated_cost && (
              <div className="flex-1 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                  Estimated Cost
                </div>
                <div className="font-semibold text-gray-900 dark:text-gray-100">
                  {data.estimated_cost}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="space-y-3">
        {data.actions.map((action, index) => (
          <motion.button
            key={action.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            onClick={() => onAction(action.id)}
            className={`w-full p-4 rounded-lg font-medium shadow-sm hover:shadow-md transition-all duration-200 flex items-center justify-between gap-3 ${
              actionTypeStyles[action.type]
            }`}
          >
            <div className="flex items-center gap-3">
              {action.icon && <span className="text-xl">{action.icon}</span>}
              <div className="text-left">
                <div className="font-semibold">{action.label}</div>
                {action.description && (
                  <div className="text-sm opacity-90 mt-0.5">
                    {action.description}
                  </div>
                )}
              </div>
            </div>
            {action.requires_confirmation && (
              <span className="text-xs opacity-75 bg-black/10 dark:bg-white/10 px-2 py-1 rounded">
                Confirm
              </span>
            )}
          </motion.button>
        ))}
      </div>

      {/* Help Text */}
      <div className="mt-4 text-center text-xs text-gray-500 dark:text-gray-400">
        Need more help? You can escalate to a human agent at any time.
      </div>
    </motion.div>
  );
}
