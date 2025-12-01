/**
 * IncidentDetailPanel
 *
 * Phase 2: Landlord Incident Triage
 * Stage "incident_detail" → UI Mode "incident_detail"
 * Shows full incident details with action buttons
 */

"use client";

import { motion } from "framer-motion";
import { Calendar, MapPin, AlertCircle, User } from "lucide-react";
import type { IncidentDetailPanelProps } from "@/types/ai-support";
import Image from "next/image";

export default function IncidentDetailPanel({
  incident,
  actions,
  onAction,
}: IncidentDetailPanelProps) {
  const getPriorityColor = (priority?: string) => {
    switch (priority?.toLowerCase()) {
      case "emergency":
        return "bg-red-500/20 text-red-400 border-red-500/30";
      case "urgent":
        return "bg-orange-500/20 text-orange-400 border-orange-500/30";
      case "routine":
        return "bg-blue-500/20 text-blue-400 border-blue-500/30";
      case "low":
        return "bg-slate-500/20 text-slate-400 border-slate-500/30";
      default:
        return "bg-slate-500/20 text-slate-400 border-slate-500/30";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "new":
      case "pending":
        return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
      case "in_progress":
        return "bg-blue-500/20 text-blue-400 border-blue-500/30";
      case "resolved":
        return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
      case "closed":
        return "bg-slate-500/20 text-slate-400 border-slate-500/30";
      default:
        return "bg-slate-500/20 text-slate-400 border-slate-500/30";
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
        <div className="flex items-start justify-between gap-4 mb-3">
          <h3 className="text-lg font-semibold text-slate-100 flex-1">
            {incident.title}
          </h3>
          <div className="flex gap-2">
            <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(incident.status)}`}>
              {incident.status.replace("_", " ").toUpperCase()}
            </span>
            {incident.priority && (
              <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getPriorityColor(incident.priority)}`}>
                {incident.priority.toUpperCase()}
              </span>
            )}
          </div>
        </div>

        {/* Meta Info */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex items-center gap-2 text-slate-400">
            <User className="w-4 h-4" />
            <span>{incident.reported_by}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400">
            <Calendar className="w-4 h-4" />
            <span>{new Date(incident.reported_at).toLocaleDateString()}</span>
          </div>
          {incident.location && (
            <div className="flex items-center gap-2 text-slate-400 col-span-2">
              <MapPin className="w-4 h-4" />
              <span>{incident.location}</span>
            </div>
          )}
        </div>
      </div>

      {/* Content Area - Scrollable */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {/* Category */}
        <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
          <label className="text-xs uppercase tracking-wider text-slate-500 block mb-2">
            Category
          </label>
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-emerald-400" />
            <span className="text-slate-100 font-medium">{incident.category}</span>
          </div>
        </div>

        {/* Description */}
        <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
          <label className="text-xs uppercase tracking-wider text-slate-500 block mb-2">
            Description
          </label>
          <p className="text-slate-100 leading-relaxed whitespace-pre-wrap">
            {incident.description}
          </p>
        </div>

        {/* Photos */}
        {incident.photos && incident.photos.length > 0 && (
          <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
            <label className="text-xs uppercase tracking-wider text-slate-500 block mb-3">
              Photos ({incident.photos.length})
            </label>
            <div className="grid grid-cols-2 gap-3">
              {incident.photos.map((photo, index) => (
                <div
                  key={index}
                  className="relative aspect-square rounded-lg overflow-hidden bg-slate-700 border border-slate-600"
                >
                  <Image
                    src={photo}
                    alt={`Incident photo ${index + 1}`}
                    fill
                    className="object-cover"
                    sizes="(max-width: 768px) 50vw, 200px"
                  />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      {actions && actions.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm text-slate-400 mb-2">Choose an action:</p>
          {actions.map((action, index) => (
            <motion.button
              key={action.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
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
