/**
 * ItemPicker (Gallery)
 *
 * Amazon Spec: Stage "item_select" → UI Mode "gallery"
 * Scrollable list of items (orders, maintenance requests, appliances, etc.)
 */

"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import type { ItemPickerProps } from "@/types/ai-support";

export default function ItemPicker({
  items,
  onSelect,
}: ItemPickerProps) {
  if (!items || items.length === 0) {
    return (
      <div className="flex items-center justify-center p-8 text-slate-500">
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
      className="flex flex-col h-full"
    >
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-slate-100">
          Which item is this about?
        </h3>
        <p className="text-sm text-slate-400 mt-1">
          Select the item you need help with
        </p>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto">
        {items.map((item, index) => (
          <motion.button
            key={item.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            onClick={() => onSelect(item.id)}
            className="w-full p-4 bg-slate-800/60 hover:bg-slate-700/60 border border-slate-700/60 hover:border-emerald-500/40 rounded-xl shadow-sm flex items-center gap-4 transition-all duration-200 text-left"
          >
            {item.image && (
              <div className="relative w-16 h-16 flex-shrink-0 rounded-lg overflow-hidden bg-slate-700">
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
              <div className="font-semibold text-slate-100 truncate">
                {item.title}
              </div>
              {item.subtitle && (
                <div className="text-sm text-slate-400 truncate mt-0.5">
                  {item.subtitle}
                </div>
              )}
            </div>
            <svg
              className="w-5 h-5 text-slate-500 flex-shrink-0"
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
