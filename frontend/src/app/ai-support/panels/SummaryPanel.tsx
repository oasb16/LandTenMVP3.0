"use client";

import { motion } from "framer-motion";
import type { SummaryPanelProps } from "@/types/ai-support";
import { Edit2, CheckCircle } from "lucide-react";

export default function SummaryPanel({
  summary,
  onConfirm,
  onEdit,
}: SummaryPanelProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col h-full p-6"
    >
      <div className="mb-6">
        <h3 className="text-xl font-semibold text-slate-100 mb-2">
          Let me confirm what we&apos;re addressing
        </h3>
        <p className="text-sm text-slate-400">
          Please review the details below before we proceed
        </p>
      </div>

      <div className="flex-1 bg-slate-800/40 border border-slate-700/60 rounded-xl p-5 space-y-4 overflow-y-auto">
        <div className="space-y-1">
          <label className="text-xs uppercase tracking-wider text-slate-500">
            Category
          </label>
          <div className="text-slate-100 font-medium">
            {summary.selected_cta_label}
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs uppercase tracking-wider text-slate-500">
            Property/Item
          </label>
          <div className="text-slate-100 font-medium">
            {summary.selected_item_title}
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs uppercase tracking-wider text-slate-500">
            Issue Description
          </label>
          <div className="text-slate-100 font-medium">
            {summary.selected_reason}
          </div>
        </div>

        {(summary.severity || summary.urgency) && (
          <div className="flex gap-3">
            {summary.severity && (
              <div className="space-y-1">
                <label className="text-xs uppercase tracking-wider text-slate-500">
                  Severity
                </label>
                <div className="inline-block px-3 py-1 rounded-full bg-amber-500/20 text-amber-400 text-sm font-medium">
                  {summary.severity}
                </div>
              </div>
            )}
            {summary.urgency && (
              <div className="space-y-1">
                <label className="text-xs uppercase tracking-wider text-slate-500">
                  Urgency
                </label>
                <div className="inline-block px-3 py-1 rounded-full bg-blue-500/20 text-blue-400 text-sm font-medium">
                  {summary.urgency}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="mt-6 grid grid-cols-2 gap-3">
        <button
          onClick={onEdit}
          className="flex items-center justify-center gap-2 px-4 py-3 bg-slate-700/60 hover:bg-slate-600/60 border border-slate-600/60 hover:border-slate-500/60 rounded-xl text-slate-200 font-semibold transition-all duration-200"
        >
          <Edit2 className="w-4 h-4" />
          <span>Edit</span>
        </button>

        <button
          onClick={onConfirm}
          className="flex items-center justify-center gap-2 px-4 py-3 bg-emerald-500 hover:bg-emerald-400 rounded-xl text-emerald-950 font-semibold shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 transition-all duration-200"
        >
          <CheckCircle className="w-4 h-4" />
          <span>Confirm</span>
        </button>
      </div>
    </motion.div>
  );
}
