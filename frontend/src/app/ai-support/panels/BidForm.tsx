/**
 * BidForm
 *
 * Phase 4: Contractor Bidding
 * Stage "bid_submission" → UI Mode "bid_form"
 * Form for contractors to submit bids
 */

"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { DollarSign, Calendar, Clock, FileText, AlertCircle } from "lucide-react";
import type { BidFormProps } from "@/types/ai-support";

export default function BidForm({
  jobId,
  jobTitle,
  suggestedPriceRange,
  onSubmit,
  onCancel,
}: BidFormProps) {
  const [price, setPrice] = useState("");
  const [duration, setDuration] = useState("");
  const [startDate, setStartDate] = useState("");
  const [notes, setNotes] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const newErrors: Record<string, string> = {};

    if (!price || parseFloat(price) <= 0) {
      newErrors.price = "Please enter a valid price";
    } else if (suggestedPriceRange) {
      const priceNum = parseFloat(price);
      if (priceNum < suggestedPriceRange.min) {
        newErrors.price = `Price is below suggested range ($${suggestedPriceRange.min})`;
      } else if (priceNum > suggestedPriceRange.max) {
        newErrors.price = `Price is above suggested range ($${suggestedPriceRange.max})`;
      }
    }

    if (!duration.trim()) {
      newErrors.duration = "Please enter estimated duration";
    }

    if (!startDate) {
      newErrors.startDate = "Please select a start date";
    } else {
      const selected = new Date(startDate);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      if (selected < today) {
        newErrors.startDate = "Start date cannot be in the past";
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      onSubmit({
        price: parseFloat(price),
        duration,
        startDate,
        notes,
      });
    }
  };

  const isPriceInRange = () => {
    if (!suggestedPriceRange || !price) return null;
    const priceNum = parseFloat(price);
    if (isNaN(priceNum)) return null;
    return priceNum >= suggestedPriceRange.min && priceNum <= suggestedPriceRange.max;
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
        <h3 className="text-lg font-semibold text-slate-100 mb-1">
          Submit Your Bid
        </h3>
        <p className="text-sm text-slate-400">{jobTitle}</p>
      </div>

      {/* Suggested Price Range */}
      {suggestedPriceRange && (
        <div className="mb-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-xl">
          <div className="flex items-center gap-2 mb-1">
            <AlertCircle className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-blue-400">Suggested Budget Range</span>
          </div>
          <p className="text-sm text-slate-300">
            ${suggestedPriceRange.min.toLocaleString()} - ${suggestedPriceRange.max.toLocaleString()}
          </p>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 space-y-4 overflow-y-auto mb-4">
          {/* Price */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              <div className="flex items-center gap-2">
                <DollarSign className="w-4 h-4" />
                <span>Your Price *</span>
              </div>
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
              <input
                type="number"
                step="0.01"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                placeholder="0.00"
                className={`
                  w-full pl-8 pr-4 py-3 bg-slate-800/60 border rounded-xl
                  text-slate-100 placeholder-slate-500
                  focus:outline-none focus:ring-2 focus:ring-emerald-500/50
                  ${errors.price ? "border-red-500/50" : "border-slate-700/60"}
                  ${isPriceInRange() === true ? "border-emerald-500/50" : ""}
                  ${isPriceInRange() === false ? "border-orange-500/50" : ""}
                `}
              />
            </div>
            {errors.price && (
              <p className="mt-1 text-sm text-red-400">{errors.price}</p>
            )}
            {isPriceInRange() === true && (
              <p className="mt-1 text-sm text-emerald-400">✓ Within suggested range</p>
            )}
            {isPriceInRange() === false && !errors.price && (
              <p className="mt-1 text-sm text-orange-400">⚠ Outside suggested range</p>
            )}
          </div>

          {/* Estimated Duration */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span>Estimated Duration *</span>
              </div>
            </label>
            <input
              type="text"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              placeholder="e.g., 2-3 days, 1 week"
              className={`
                w-full px-4 py-3 bg-slate-800/60 border rounded-xl
                text-slate-100 placeholder-slate-500
                focus:outline-none focus:ring-2 focus:ring-emerald-500/50
                ${errors.duration ? "border-red-500/50" : "border-slate-700/60"}
              `}
            />
            {errors.duration && (
              <p className="mt-1 text-sm text-red-400">{errors.duration}</p>
            )}
          </div>

          {/* Start Date */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                <span>Proposed Start Date *</span>
              </div>
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              min={new Date().toISOString().split("T")[0]}
              className={`
                w-full px-4 py-3 bg-slate-800/60 border rounded-xl
                text-slate-100
                focus:outline-none focus:ring-2 focus:ring-emerald-500/50
                ${errors.startDate ? "border-red-500/50" : "border-slate-700/60"}
              `}
            />
            {errors.startDate && (
              <p className="mt-1 text-sm text-red-400">{errors.startDate}</p>
            )}
          </div>

          {/* Additional Notes */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4" />
                <span>Additional Notes (Optional)</span>
              </div>
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Share any additional details about your approach, materials, or qualifications..."
              rows={4}
              className="w-full px-4 py-3 bg-slate-800/60 border border-slate-700/60 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 resize-none"
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 px-4 py-3 bg-slate-700/60 hover:bg-slate-600/60 border border-slate-600/60 hover:border-slate-500/60 rounded-xl text-slate-200 font-semibold transition-all duration-200"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="flex-1 px-4 py-3 bg-emerald-500 hover:bg-emerald-400 text-emerald-950 rounded-xl font-semibold shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 transition-all duration-200"
          >
            Submit Bid
          </button>
        </div>
      </form>
    </motion.div>
  );
}
