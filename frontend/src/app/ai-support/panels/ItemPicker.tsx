/**
 * ItemPicker (Gallery)
 *
 * Displays items (properties, units, etc.) for user selection
 */

"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import type { ItemPickerProps } from "@/types/ai-support";

export default function ItemPicker({
  items,
  title = "Which item is this about?",
  subtitle,
  allowSkip = false,
  onSelect,
  onSkip,
}: ItemPickerProps) {
  if (!items || items.length === 0) {
    return (
      <div className="p-6 text-center text-gray-500 dark:text-gray-400">
        <p>No items available</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="p-4 border-t bg-gray-50 dark:bg-gray-900 max-h-96 overflow-y-auto"
    >
      <div className="mb-4 sticky top-0 bg-gray-50 dark:bg-gray-900 pb-2 z-10">
        <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100">
          {title}
        </h3>
        {subtitle && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {subtitle}
          </p>
        )}
      </div>

      <div className="space-y-3">
        {items.map((item, index) => (
          <motion.button
            key={item.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            onClick={() => onSelect(item.id, item)}
            className="w-full p-3 bg-white dark:bg-gray-800 rounded-lg shadow-sm flex items-center gap-4 hover:shadow-md hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all duration-200 text-left border border-transparent hover:border-blue-300 dark:hover:border-blue-600"
          >
            {item.image && (
              <div className="relative w-16 h-16 flex-shrink-0 rounded-md overflow-hidden bg-gray-200 dark:bg-gray-700">
                <Image
                  src={item.image}
                  alt={item.title}
                  fill
                  className="object-cover"
                  sizes="64px"
                />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <div className="font-medium text-gray-900 dark:text-gray-100 truncate">
                {item.title}
              </div>
              {item.subtitle && (
                <div className="text-sm text-gray-600 dark:text-gray-400 truncate">
                  {item.subtitle}
                </div>
              )}
              {item.description && (
                <div className="text-xs text-gray-500 dark:text-gray-500 mt-1 line-clamp-2">
                  {item.description}
                </div>
              )}
            </div>
            <svg
              className="w-5 h-5 text-gray-400 flex-shrink-0"
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

      {allowSkip && onSkip && (
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: items.length * 0.05 + 0.2 }}
          onClick={onSkip}
          className="w-full mt-4 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
        >
          Skip this step
        </motion.button>
      )}
    </motion.div>
  );
}
