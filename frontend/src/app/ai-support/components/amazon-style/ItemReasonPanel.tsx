/**
 * ItemReasonPanel - Amazon-style Item + Reason Selection
 *
 * Left: Item card
 * Right: Reason list
 */

"use client";

import { motion } from "framer-motion";
import { ArrowLeft, ChevronRight } from "lucide-react";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";

interface ItemReasonPanelProps {
  itemId: string;
  itemType: string;
  itemTitle: string;
  itemSubtitle?: string;
  persona: string;
  onBack: () => void;
  onSelectReason: (reasonId: string, reasonLabel: string) => void;
}

export default function ItemReasonPanel({
  itemId,
  itemType,
  itemTitle,
  itemSubtitle,
  persona,
  onBack,
  onSelectReason,
}: ItemReasonPanelProps) {
  const { activeChannel } = useStreamChat();

  const handleReasonClick = async (reasonId: string, reasonLabel: string) => {
    // Send the reason label as a user message into chat
    if (activeChannel) {
      try {
        await activeChannel.sendMessage({ text: reasonLabel });
      } catch (err) {
        console.error("[ItemReasonPanel] Failed to send message:", err);
      }
    }

    // Then call the original handler
    onSelectReason(reasonId, reasonLabel);
  };
  const getReasons = () => {
    // Tenant reasons
    if (persona === "tenant") {
      if (itemType === "property") {
        return [
          { id: "maintenance", label: "Request maintenance or repair" },
          { id: "billing", label: "Billing or payment question" },
          { id: "lease", label: "Lease or contract question" },
          { id: "noise", label: "Noise complaint" },
          { id: "access", label: "Access or key issue" },
          { id: "other", label: "My issue isn't listed" },
        ];
      } else if (itemType === "incident") {
        return [
          { id: "status", label: "Check status of my request" },
          { id: "worse", label: "Issue has gotten worse" },
          { id: "resolved", label: "Issue is now resolved" },
          { id: "info", label: "Provide additional information" },
          { id: "speak", label: "Speak to someone" },
        ];
      } else if (itemType === "billing") {
        return [
          { id: "pay", label: "Make a payment" },
          { id: "dispute", label: "Dispute a charge" },
          { id: "late", label: "Late fee question" },
          { id: "autopay", label: "Set up autopay" },
          { id: "receipt", label: "Get payment receipt" },
        ];
      }
    }

    // Landlord reasons
    if (persona === "landlord") {
      if (itemType === "incident") {
        return [
          { id: "triage", label: "Review and prioritize incident" },
          { id: "assign", label: "Assign to contractor" },
          { id: "communicate", label: "Communicate with tenant" },
          { id: "close", label: "Close incident" },
          { id: "escalate", label: "Escalate issue" },
        ];
      } else if (itemType === "job") {
        return [
          { id: "bids", label: "Review contractor bids" },
          { id: "approve", label: "Approve work" },
          { id: "status", label: "Check job status" },
          { id: "contact", label: "Contact contractor" },
          { id: "close", label: "Mark job complete" },
        ];
      } else if (itemType === "property") {
        return [
          { id: "incidents", label: "View open incidents" },
          { id: "jobs", label: "View active jobs" },
          { id: "tenants", label: "Manage tenants" },
          { id: "financials", label: "View financials" },
          { id: "maintenance", label: "Schedule maintenance" },
        ];
      }
    }

    // Contractor reasons
    if (persona === "contractor") {
      if (itemType === "available_job") {
        return [
          { id: "details", label: "View full job details" },
          { id: "bid", label: "Submit a bid" },
          { id: "questions", label: "Ask questions about job" },
          { id: "decline", label: "Not interested" },
        ];
      } else if (itemType === "assigned_job") {
        return [
          { id: "start", label: "Mark work as started" },
          { id: "update", label: "Update progress" },
          { id: "parts", label: "Request parts or materials" },
          { id: "complete", label: "Mark job complete" },
          { id: "issue", label: "Report an issue" },
        ];
      }
    }

    return [
      { id: "help", label: "Get help" },
      { id: "other", label: "Something else" },
    ];
  };

  const reasons = getReasons();

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-700/60 bg-slate-800/40 backdrop-blur-sm px-6 py-4">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-slate-400 hover:text-slate-200 transition-colors mb-3"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm">Back to items</span>
        </button>
        <h2 className="text-xl font-semibold text-slate-100">
          How can we help with this?
        </h2>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-6 py-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Item Card */}
            <div className="lg:col-span-1">
              <div className="p-4 bg-slate-800/60 border border-slate-700/60 rounded-xl sticky top-0">
                <h3 className="font-semibold text-slate-100 mb-1">
                  {itemTitle}
                </h3>
                {itemSubtitle && (
                  <p className="text-sm text-slate-400">{itemSubtitle}</p>
                )}
                <div className="mt-3 pt-3 border-t border-slate-700/60">
                  <p className="text-xs uppercase tracking-wider text-slate-500">
                    {itemType.replace("_", " ")}
                  </p>
                </div>
              </div>
            </div>

            {/* Right: Reason List */}
            <div className="lg:col-span-2">
              <div className="space-y-2">
                {reasons.map((reason, index) => (
                  <motion.button
                    key={reason.id}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    onClick={() => handleReasonClick(reason.id, reason.label)}
                    className="w-full p-4 bg-slate-800/60 border border-slate-700/60 hover:border-emerald-500/50 rounded-xl transition-all duration-200 flex items-center justify-between group text-left"
                  >
                    <span className="font-medium text-slate-100">
                      {reason.label}
                    </span>
                    <ChevronRight className="w-5 h-5 text-slate-500 group-hover:text-emerald-400 transition-colors" />
                  </motion.button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
