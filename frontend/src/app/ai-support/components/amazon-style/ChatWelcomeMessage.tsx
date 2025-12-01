/**
 * ChatWelcomeMessage - Amazon-style chat welcome
 *
 * First system message in chat with context chips
 */

"use client";

import { motion } from "framer-motion";
import { Bot, CheckCircle } from "lucide-react";

interface ChatWelcomeMessageProps {
  userName?: string;
  selectedItem?: string;
  selectedReason?: string;
  persona: string;
}

export default function ChatWelcomeMessage({
  userName,
  selectedItem,
  selectedReason,
  persona,
}: ChatWelcomeMessageProps) {
  const getWelcomeText = () => {
    if (persona === "tenant") {
      return "Hi, you're in the right place for property and maintenance support. I'm here to help resolve your issue quickly.";
    } else if (persona === "landlord") {
      return "Hi, welcome to your property management support. I can help you manage incidents, contractors, and property operations.";
    } else if (persona === "contractor") {
      return "Hi, I'm here to help you with job details, bidding, and work updates.";
    }
    return "Hi, I'm here to help you today.";
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-4"
    >
      {/* System Message Card */}
      <div className="flex gap-3">
        {/* Avatar */}
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center">
          <Bot className="w-5 h-5 text-emerald-950" />
        </div>

        {/* Content */}
        <div className="flex-1">
          {/* Welcome Text */}
          <div className="p-4 bg-slate-800/60 border border-slate-700/60 rounded-2xl rounded-tl-none">
            <p className="text-slate-100 leading-relaxed">{getWelcomeText()}</p>
          </div>

          {/* Context Chips */}
          {(selectedItem || selectedReason) && (
            <div className="flex flex-wrap gap-2 mt-3">
              {selectedItem && (
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700/40 border border-slate-600/60 rounded-full">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-xs text-slate-300">{selectedItem}</span>
                </div>
              )}
              {selectedReason && (
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700/40 border border-slate-600/60 rounded-full">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-xs text-slate-300">{selectedReason}</span>
                </div>
              )}
            </div>
          )}

          {/* Timestamp */}
          <p className="text-xs text-slate-500 mt-2">
            {new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </p>
        </div>
      </div>
    </motion.div>
  );
}
