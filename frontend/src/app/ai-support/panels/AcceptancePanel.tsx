/**
 * AcceptancePanel
 *
 * Phase 5: Job Execution
 * Stage "job_acceptance" → UI Mode "job_acceptance"
 * Contractor accepts or declines approved job
 */

"use client";

import { motion } from "framer-motion";
import { CheckCircle2, DollarSign, Calendar, Clock, FileText, XCircle, ArrowLeft } from "lucide-react";
import type { AcceptancePanelProps } from "@/types/ai-support";

export default function AcceptancePanel({
  jobId,
  jobTitle,
  approvedBid,
  terms,
  onAccept,
  onDecline,
  onBack,
}: AcceptancePanelProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col h-full"
    >
      {/* Back Button (Optional) */}
      {onBack && (
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-slate-400 hover:text-slate-200 transition-colors mb-3"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm">Back</span>
        </button>
      )}

      {/* Header */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="bg-emerald-500 rounded-full p-2">
            <CheckCircle2 className="w-6 h-6 text-emerald-950" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-100">
              Your Bid Was Approved!
            </h3>
            <p className="text-sm text-slate-400">{jobTitle}</p>
          </div>
        </div>

        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
          <p className="text-sm text-emerald-400">
            ✓ The property owner has selected your bid and is ready to move forward
          </p>
        </div>
      </div>

      {/* Content Area - Scrollable */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {/* Approved Bid Details */}
        <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
          <h4 className="text-xs uppercase tracking-wider text-slate-500 mb-3">
            Approved Bid Details
          </h4>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-400">
                <DollarSign className="w-4 h-4" />
                <span className="text-sm">Contract Amount</span>
              </div>
              <span className="text-xl font-bold text-emerald-400">
                ${approvedBid.price.toLocaleString()}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-400">
                <Clock className="w-4 h-4" />
                <span className="text-sm">Estimated Duration</span>
              </div>
              <span className="text-slate-100 font-medium">
                {approvedBid.estimated_duration}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-400">
                <Calendar className="w-4 h-4" />
                <span className="text-sm">Proposed Start Date</span>
              </div>
              <span className="text-slate-100 font-medium">
                {new Date(approvedBid.start_date).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>

        {/* Terms & Conditions */}
        {terms && terms.length > 0 && (
          <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <FileText className="w-4 h-4 text-slate-400" />
              <h4 className="text-xs uppercase tracking-wider text-slate-500">
                Terms & Conditions
              </h4>
            </div>

            <ul className="space-y-2">
              {terms.map((term, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-slate-300">
                  <CheckCircle2 className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                  <span>{term}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Next Steps Info */}
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
          <h4 className="text-sm font-medium text-blue-400 mb-2">
            What happens next?
          </h4>
          <ul className="space-y-2 text-sm text-slate-300">
            <li className="flex items-start gap-2">
              <span className="text-blue-400 font-bold">1.</span>
              <span>Accept the job to confirm your commitment</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-400 font-bold">2.</span>
              <span>You&apos;ll receive the property owner&apos;s contact information</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-400 font-bold">3.</span>
              <span>Start work on the agreed date</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-400 font-bold">4.</span>
              <span>Mark the job complete when finished</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="space-y-3">
        <button
          onClick={onAccept}
          className="w-full px-4 py-4 bg-emerald-500 hover:bg-emerald-400 text-emerald-950 rounded-xl font-bold shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 transition-all duration-200 flex items-center justify-center gap-2"
        >
          <CheckCircle2 className="w-5 h-5" />
          <span>Accept Job & Start Work</span>
        </button>

        <button
          onClick={onDecline}
          className="w-full px-4 py-3 bg-slate-700/60 hover:bg-slate-600/60 border border-slate-600/60 hover:border-red-500/60 rounded-xl text-slate-200 hover:text-red-400 font-semibold transition-all duration-200 flex items-center justify-center gap-2"
        >
          <XCircle className="w-4 h-4" />
          <span>Decline Job</span>
        </button>

        <p className="text-xs text-center text-slate-500">
          By accepting, you agree to complete the work as described
        </p>
      </div>
    </motion.div>
  );
}
