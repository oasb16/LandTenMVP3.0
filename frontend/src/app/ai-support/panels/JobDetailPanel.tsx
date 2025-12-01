/**
 * JobDetailPanel
 *
 * Phase 4: Contractor Bidding
 * Stage "job_detail" → UI Mode "job_detail"
 * Shows full job details for contractors
 */

"use client";

import { motion } from "framer-motion";
import { Calendar, MapPin, DollarSign, Clock, AlertCircle, CheckCircle2, ArrowLeft } from "lucide-react";
import type { JobDetailPanelProps } from "@/types/ai-support";
import Image from "next/image";

export default function JobDetailPanel({
  job,
  canBid,
  existingBid,
  onBid,
  onBack,
}: JobDetailPanelProps) {
  const getUrgencyColor = (urgency: string) => {
    switch (urgency.toLowerCase()) {
      case "emergency":
        return "bg-red-500/20 text-red-400 border-red-500/30";
      case "urgent":
        return "bg-orange-500/20 text-orange-400 border-orange-500/30";
      case "normal":
        return "bg-blue-500/20 text-blue-400 border-blue-500/30";
      default:
        return "bg-slate-500/20 text-slate-400 border-slate-500/30";
    }
  };

  const getBidStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "pending":
        return "text-yellow-400";
      case "approved":
        return "text-emerald-400";
      case "rejected":
        return "text-red-400";
      default:
        return "text-slate-400";
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
      {/* Header with Back Button */}
      <div className="mb-4">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-slate-400 hover:text-slate-200 transition-colors mb-3"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm">Back to Jobs</span>
        </button>

        <div className="flex items-start justify-between gap-4">
          <h3 className="text-lg font-semibold text-slate-100 flex-1">
            {job.title}
          </h3>
          <span className={`px-3 py-1 rounded-full text-xs font-medium border whitespace-nowrap ${getUrgencyColor(job.urgency)}`}>
            {job.urgency.toUpperCase()}
          </span>
        </div>

        {/* Meta Info */}
        <div className="grid grid-cols-2 gap-2 mt-3 text-sm">
          <div className="flex items-center gap-2 text-slate-400">
            <Calendar className="w-4 h-4" />
            <span>Posted {new Date(job.posted_at).toLocaleDateString()}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400">
            <MapPin className="w-4 h-4" />
            <span>{job.location}</span>
          </div>
          {job.deadline && (
            <div className="flex items-center gap-2 text-slate-400 col-span-2">
              <Clock className="w-4 h-4" />
              <span>Deadline: {new Date(job.deadline).toLocaleDateString()}</span>
            </div>
          )}
        </div>
      </div>

      {/* Content Area - Scrollable */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {/* Budget */}
        {job.budget_range && (
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="w-5 h-5 text-emerald-400" />
              <label className="text-xs uppercase tracking-wider text-emerald-400 font-semibold">
                Budget Range
              </label>
            </div>
            <p className="text-xl font-bold text-emerald-400">
              {job.budget_range}
            </p>
          </div>
        )}

        {/* Category */}
        <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
          <label className="text-xs uppercase tracking-wider text-slate-500 block mb-2">
            Category
          </label>
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-blue-400" />
            <span className="text-slate-100 font-medium">{job.category}</span>
          </div>
        </div>

        {/* Description */}
        <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
          <label className="text-xs uppercase tracking-wider text-slate-500 block mb-2">
            Job Description
          </label>
          <p className="text-slate-100 leading-relaxed whitespace-pre-wrap">
            {job.description}
          </p>
        </div>

        {/* Requirements */}
        {job.requirements && job.requirements.length > 0 && (
          <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
            <label className="text-xs uppercase tracking-wider text-slate-500 block mb-3">
              Requirements
            </label>
            <ul className="space-y-2">
              {job.requirements.map((req, index) => (
                <li key={index} className="flex items-start gap-2 text-slate-100">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                  <span className="text-sm">{req}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Photos */}
        {job.photos && job.photos.length > 0 && (
          <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
            <label className="text-xs uppercase tracking-wider text-slate-500 block mb-3">
              Photos ({job.photos.length})
            </label>
            <div className="grid grid-cols-2 gap-3">
              {job.photos.map((photo, index) => (
                <div
                  key={index}
                  className="relative aspect-square rounded-lg overflow-hidden bg-slate-700 border border-slate-600"
                >
                  <Image
                    src={photo}
                    alt={`Job photo ${index + 1}`}
                    fill
                    className="object-cover"
                    sizes="(max-width: 768px) 50vw, 200px"
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Existing Bid Status */}
        {existingBid && (
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
            <label className="text-xs uppercase tracking-wider text-blue-400 block mb-2">
              Your Bid
            </label>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xl font-bold text-slate-100">
                  ${existingBid.price.toLocaleString()}
                </p>
                <p className={`text-sm font-medium ${getBidStatusColor(existingBid.status)}`}>
                  Status: {existingBid.status.toUpperCase()}
                </p>
              </div>
              {existingBid.status === "approved" && (
                <CheckCircle2 className="w-8 h-8 text-emerald-400" />
              )}
            </div>
          </div>
        )}
      </div>

      {/* Action Button */}
      {canBid && !existingBid && (
        <button
          onClick={onBid}
          className="w-full px-4 py-3 bg-emerald-500 hover:bg-emerald-400 text-emerald-950 rounded-xl font-semibold shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 transition-all duration-200"
        >
          Submit a Bid
        </button>
      )}

      {!canBid && !existingBid && (
        <div className="p-3 bg-slate-700/40 border border-slate-600/60 rounded-xl text-center">
          <p className="text-sm text-slate-400">
            You cannot bid on this job at this time
          </p>
        </div>
      )}
    </motion.div>
  );
}
