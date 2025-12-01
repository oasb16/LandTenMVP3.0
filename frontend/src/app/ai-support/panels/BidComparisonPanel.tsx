/**
 * BidComparisonPanel
 *
 * Phase 3: Landlord Job + Bids
 * Stage "bid_comparison" → UI Mode "bid_comparison"
 * Compare contractor bids side-by-side
 */

"use client";

import { motion } from "framer-motion";
import { Star, DollarSign, Calendar, Clock, CheckCircle, Package } from "lucide-react";
import type { BidComparisonPanelProps } from "@/types/ai-support";

export default function BidComparisonPanel({
  jobId,
  jobTitle,
  bids,
  onSelectBid,
}: BidComparisonPanelProps) {
  if (!bids || bids.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <p className="text-slate-400 mb-2">No bids received yet</p>
        <p className="text-sm text-slate-500">
          Contractors will submit their proposals soon
        </p>
      </div>
    );
  }

  // Sort bids by price (lowest first)
  const sortedBids = [...bids].sort((a, b) => a.price - b.price);
  const lowestPrice = sortedBids[0].price;

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
          Compare Bids
        </h3>
        <p className="text-sm text-slate-400">
          {jobTitle} • {bids.length} bid{bids.length !== 1 ? "s" : ""} received
        </p>
      </div>

      {/* Bids List */}
      <div className="flex-1 space-y-3 overflow-y-auto">
        {sortedBids.map((bid, index) => {
          const isLowest = bid.price === lowestPrice;

          return (
            <motion.div
              key={bid.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.08 }}
              className="relative"
            >
              {/* Best Value Badge */}
              {isLowest && bids.length > 1 && (
                <div className="absolute -top-2 left-4 z-10">
                  <div className="bg-emerald-500 text-emerald-950 px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" />
                    <span>BEST VALUE</span>
                  </div>
                </div>
              )}

              <div
                className={`
                  p-4 rounded-xl border transition-all duration-200 cursor-pointer
                  ${isLowest
                    ? "bg-emerald-500/10 border-emerald-500/30 hover:border-emerald-500/50"
                    : "bg-slate-800/60 border-slate-700/60 hover:border-slate-600/60"
                  }
                `}
                onClick={() => onSelectBid(bid.id)}
              >
                {/* Contractor Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h4 className="font-semibold text-slate-100 mb-1">
                      {bid.contractor_name}
                    </h4>
                    {bid.contractor_rating && (
                      <div className="flex items-center gap-1">
                        <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                        <span className="text-sm font-medium text-yellow-400">
                          {bid.contractor_rating.toFixed(1)}
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="text-right">
                    <div className={`text-2xl font-bold ${isLowest ? "text-emerald-400" : "text-slate-100"}`}>
                      ${bid.price.toLocaleString()}
                    </div>
                    {!isLowest && (
                      <div className="text-xs text-slate-500">
                        +${(bid.price - lowestPrice).toLocaleString()} vs lowest
                      </div>
                    )}
                  </div>
                </div>

                {/* Bid Details Grid */}
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div className="flex items-center gap-2 text-sm">
                    <Clock className="w-4 h-4 text-slate-400" />
                    <span className="text-slate-300">{bid.estimated_duration}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Calendar className="w-4 h-4 text-slate-400" />
                    <span className="text-slate-300">
                      Start: {new Date(bid.proposed_start_date).toLocaleDateString()}
                    </span>
                  </div>
                  {bid.materials_included !== undefined && (
                    <div className="flex items-center gap-2 text-sm col-span-2">
                      <Package className="w-4 h-4 text-slate-400" />
                      <span className="text-slate-300">
                        Materials {bid.materials_included ? "included" : "not included"}
                      </span>
                    </div>
                  )}
                </div>

                {/* Notes */}
                {bid.notes && (
                  <div className="pt-3 border-t border-slate-700/60">
                    <p className="text-sm text-slate-400 italic">
                      &quot;{bid.notes}&quot;
                    </p>
                  </div>
                )}

                {/* Select Button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectBid(bid.id);
                  }}
                  className={`
                    w-full mt-3 px-4 py-2 rounded-lg font-semibold transition-all duration-200
                    ${isLowest
                      ? "bg-emerald-500 hover:bg-emerald-400 text-emerald-950"
                      : "bg-slate-700 hover:bg-slate-600 text-slate-100"
                    }
                  `}
                >
                  Select This Bid
                </button>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Info Footer */}
      <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-xl">
        <p className="text-sm text-blue-400">
          💡 Tip: Consider both price and contractor rating when making your decision
        </p>
      </div>
    </motion.div>
  );
}
