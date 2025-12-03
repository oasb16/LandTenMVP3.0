/**
 * RufusWelcome - Rufus-style AI assistant welcome
 *
 * Shown in drawer before conversation starts
 * Wired to actual flows: maintenance, status, billing, chat
 */

"use client";

import { motion } from "framer-motion";
import { Sparkles, MessageCircle, FileText, Search, Settings } from "lucide-react";

interface RufusWelcomeProps {
  onQuickAction: (action: string) => void;
  onShowStatus: () => void;
}

export default function RufusWelcome({ onQuickAction, onShowStatus }: RufusWelcomeProps) {
  // Removed direct message sending - let parent handle via sendChatAndIntent

  const handleQuickAction = (actionId: string) => {
    if (actionId === "status") {
      onShowStatus();
    } else {
      onQuickAction(actionId);
    }
  };

  const quickActions = [
    {
      id: "maintenance",
      label: "Report Maintenance",
      icon: Settings,
      description: "Quick maintenance request",
    },
    {
      id: "status",
      label: "Check Status",
      icon: Search,
      description: "Track your requests",
    },
    {
      id: "billing",
      label: "Billing Help",
      icon: FileText,
      description: "Payment & billing",
    },
    {
      id: "chat",
      label: "Start Chat",
      icon: MessageCircle,
      description: "Talk to assistant",
    },
  ];

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 overflow-y-auto">
      {/* Header */}
      <div className="p-6 border-b border-slate-700/60">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-emerald-950" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100">AI Assistant</h2>
            <p className="text-sm text-emerald-400">Always here to help</p>
          </div>
        </div>

        <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
          <p className="text-sm text-slate-100 leading-relaxed">
            I'm your AI assistant powered by advanced language models. I can help you with
            property maintenance, billing questions, incident tracking, and more.
          </p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex-1 p-6">
        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
          Quick Actions
        </h3>

        <div className="grid grid-cols-2 gap-3">
          {quickActions.map((action, index) => {
            const Icon = action.icon;
            return (
              <motion.button
                key={action.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.05 }}
                onClick={() => handleQuickAction(action.id)}
                className="p-4 bg-slate-800/60 border border-slate-700/60 hover:border-emerald-500/50 rounded-xl transition-all duration-200 text-left group"
              >
                <div className="w-10 h-10 rounded-lg bg-slate-700/60 flex items-center justify-center mb-3 group-hover:bg-emerald-500/20 transition-colors">
                  <Icon className="w-5 h-5 text-emerald-400" />
                </div>
                <h4 className="font-semibold text-slate-100 mb-1 text-sm">
                  {action.label}
                </h4>
                <p className="text-xs text-slate-400">{action.description}</p>
              </motion.button>
            );
          })}
        </div>

        {/* Features List */}
        <div className="mt-8 p-4 bg-slate-800/40 border border-slate-700/60 rounded-xl">
          <h4 className="font-semibold text-slate-100 mb-3 text-sm">
            What I can help with:
          </h4>
          <ul className="space-y-2 text-sm text-slate-300">
            <li className="flex items-start gap-2">
              <span className="text-emerald-400">•</span>
              <span>Answer questions about your property and lease</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-400">•</span>
              <span>Help with maintenance requests and tracking</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-400">•</span>
              <span>Billing and payment assistance</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-400">•</span>
              <span>Connect you with the right resources</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Footer */}
      <div className="p-6 border-t border-slate-700/60">
        <p className="text-xs text-slate-500 text-center">
          Powered by advanced AI • Available 24/7
        </p>
      </div>
    </div>
  );
}
