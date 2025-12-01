/**
 * TriagePanel
 *
 * Phase 2: Landlord Incident Triage
 * Stage "incident_triage" → UI Mode "triage_panel"
 * Classify and prioritize incidents
 */

"use client";

import { motion } from "framer-motion";
import { AlertTriangle, Clock, Wrench, Info } from "lucide-react";
import type { TriagePanelProps } from "@/types/ai-support";

export default function TriagePanel({
  incidentId,
  incidentSummary,
  classificationOptions,
  onClassify,
}: TriagePanelProps) {
  const getPriorityIcon = (priority: string) => {
    switch (priority.toLowerCase()) {
      case "emergency":
        return <AlertTriangle className="w-6 h-6" />;
      case "urgent":
        return <Clock className="w-6 h-6" />;
      case "routine":
        return <Wrench className="w-6 h-6" />;
      case "low":
        return <Info className="w-6 h-6" />;
      default:
        return <Info className="w-6 h-6" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case "emergency":
        return {
          bg: "bg-red-500/10 hover:bg-red-500/20",
          border: "border-red-500/30 hover:border-red-500/50",
          text: "text-red-400",
          icon: "text-red-400",
        };
      case "urgent":
        return {
          bg: "bg-orange-500/10 hover:bg-orange-500/20",
          border: "border-orange-500/30 hover:border-orange-500/50",
          text: "text-orange-400",
          icon: "text-orange-400",
        };
      case "routine":
        return {
          bg: "bg-blue-500/10 hover:bg-blue-500/20",
          border: "border-blue-500/30 hover:border-blue-500/50",
          text: "text-blue-400",
          icon: "text-blue-400",
        };
      case "low":
        return {
          bg: "bg-slate-500/10 hover:bg-slate-500/20",
          border: "border-slate-500/30 hover:border-slate-500/50",
          text: "text-slate-400",
          icon: "text-slate-400",
        };
      default:
        return {
          bg: "bg-slate-500/10 hover:bg-slate-500/20",
          border: "border-slate-500/30 hover:border-slate-500/50",
          text: "text-slate-400",
          icon: "text-slate-400",
        };
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col h-full"
    >
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-slate-100 mb-2">
          How would you classify this incident?
        </h3>
        <p className="text-sm text-slate-400">
          This helps us prioritize and route the issue appropriately
        </p>
      </div>

      {/* Incident Summary */}
      <div className="mb-4 p-4 bg-slate-800/40 border border-slate-700/60 rounded-xl">
        <label className="text-xs uppercase tracking-wider text-slate-500 block mb-2">
          Incident Summary
        </label>
        <p className="text-slate-100 leading-relaxed">
          {incidentSummary}
        </p>
      </div>

      {/* Classification Options */}
      <div className="flex-1 space-y-3 overflow-y-auto">
        {classificationOptions.map((option, index) => {
          const colors = getPriorityColor(option.priority);
          return (
            <motion.button
              key={option.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.08 }}
              onClick={() => onClassify(option.id)}
              className={`
                w-full p-4 rounded-xl border transition-all duration-200
                ${colors.bg} ${colors.border}
                text-left group
              `}
            >
              <div className="flex items-start gap-4">
                {/* Icon */}
                <div className={`flex-shrink-0 ${colors.icon}`}>
                  {getPriorityIcon(option.priority)}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <h4 className={`font-semibold ${colors.text}`}>
                      {option.label}
                    </h4>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors.text} bg-current/20`}>
                      {option.priority.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-sm text-slate-300">
                    {option.description}
                  </p>
                </div>

                {/* Arrow */}
                <svg
                  className={`w-5 h-5 flex-shrink-0 ${colors.icon} opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all`}
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
          );
        })}
      </div>
    </motion.div>
  );
}
