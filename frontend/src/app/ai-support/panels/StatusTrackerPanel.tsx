/**
 * StatusTrackerPanel
 *
 * Phase 5: Job Execution & Tracking
 * UI Mode "status_tracker"
 * Shows timeline of incident/job status updates
 */

"use client";

import { motion } from "framer-motion";
import { CheckCircle, Circle, Clock, User, Calendar } from "lucide-react";
import type { StatusTrackerPanelProps } from "@/types/ai-support";

export default function StatusTrackerPanel({
  entityType,
  entityId,
  title,
  currentStatus,
  timeline,
  nextActions,
  onAction,
}: StatusTrackerPanelProps) {
  const getStatusColor = (status: string) => {
    const lower = status.toLowerCase();
    if (lower.includes("complete") || lower.includes("resolved")) {
      return "text-emerald-400 bg-emerald-500/20 border-emerald-500/30";
    }
    if (lower.includes("progress") || lower.includes("active")) {
      return "text-blue-400 bg-blue-500/20 border-blue-500/30";
    }
    if (lower.includes("pending") || lower.includes("waiting")) {
      return "text-yellow-400 bg-yellow-500/20 border-yellow-500/30";
    }
    if (lower.includes("cancel") || lower.includes("reject")) {
      return "text-red-400 bg-red-500/20 border-red-500/30";
    }
    return "text-slate-400 bg-slate-500/20 border-slate-500/30";
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
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
        <div className="flex items-center gap-2 text-xs text-slate-500 mb-2">
          <span className="uppercase">{entityType}</span>
          <span>•</span>
          <span>#{entityId.slice(0, 8)}</span>
        </div>
        <h3 className="text-lg font-semibold text-slate-100 mb-2">
          {title}
        </h3>
        <div className={`inline-block px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(currentStatus)}`}>
          {currentStatus.replace("_", " ").toUpperCase()}
        </div>
      </div>

      {/* Timeline */}
      <div className="flex-1 overflow-y-auto mb-4">
        <h4 className="text-sm font-medium text-slate-400 mb-3 uppercase tracking-wider">
          Activity Timeline
        </h4>
        <div className="space-y-4 relative">
          {/* Vertical Line */}
          <div className="absolute left-4 top-2 bottom-2 w-0.5 bg-slate-700/60" />

          {timeline.map((event, index) => {
            const isLatest = index === 0;
            const isCompleted = event.status.toLowerCase().includes("complete") ||
                               event.status.toLowerCase().includes("resolved");

            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="relative pl-12"
              >
                {/* Icon */}
                <div className={`
                  absolute left-0 top-1 w-8 h-8 rounded-full border-2 flex items-center justify-center
                  ${isLatest
                    ? "bg-emerald-500 border-emerald-500"
                    : isCompleted
                      ? "bg-slate-800 border-emerald-500/50"
                      : "bg-slate-800 border-slate-600"
                  }
                `}>
                  {isCompleted ? (
                    <CheckCircle className={`w-4 h-4 ${isLatest ? "text-emerald-950" : "text-emerald-400"}`} />
                  ) : (
                    <Circle className={`w-3 h-3 ${isLatest ? "text-emerald-950" : "text-slate-500"}`} />
                  )}
                </div>

                {/* Content */}
                <div className={`
                  p-3 rounded-xl border
                  ${isLatest
                    ? "bg-slate-800/60 border-slate-600"
                    : "bg-slate-800/30 border-slate-700/40"
                  }
                `}>
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <h5 className={`font-semibold ${isLatest ? "text-slate-100" : "text-slate-300"}`}>
                      {event.status.replace("_", " ")}
                    </h5>
                    <span className="text-xs text-slate-500 whitespace-nowrap">
                      {formatDate(event.timestamp)}
                    </span>
                  </div>

                  <p className={`text-sm ${isLatest ? "text-slate-300" : "text-slate-400"} mb-2`}>
                    {event.description}
                  </p>

                  {event.actor && (
                    <div className="flex items-center gap-1.5 text-xs text-slate-500">
                      <User className="w-3 h-3" />
                      <span>{event.actor}</span>
                    </div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Next Actions */}
      {nextActions && nextActions.length > 0 && onAction && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
            Available Actions
          </h4>
          {nextActions.map((action, index) => (
            <motion.button
              key={action.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + index * 0.05 }}
              onClick={() => onAction(action.id)}
              className="w-full p-3 bg-emerald-500 hover:bg-emerald-400 text-emerald-950 rounded-xl font-semibold shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 transition-all duration-200 flex items-center justify-between"
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
      )}
    </motion.div>
  );
}
