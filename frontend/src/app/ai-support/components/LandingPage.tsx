/**
 * AI Support Landing Page
 *
 * Inspired by proposed1.jsx - shows hero section with state visualization
 * Integrates with real backend via useAISupportFlow hook
 */

"use client";

import { MessageSquare } from "lucide-react";
import { motion } from "framer-motion";
import type { Stage, UIMode, FlowState } from "@/types/ai-support";

interface LandingPageProps {
  onLaunch: () => void;
  sessionId: string | null;
  persona: string;
  stage: Stage;
  uiMode: UIMode;
  flowState: FlowState | null;
  isDrawerOpen: boolean;
}

export default function LandingPage({
  onLaunch,
  sessionId,
  persona,
  stage,
  uiMode,
  flowState,
  isDrawerOpen,
}: LandingPageProps) {
  const stages: Stage[] = ["intro", "item_select", "issue_select", "summary", "diagnosis", "resolution"];
  const currentStageIndex = stages.indexOf(stage);

  return (
    <div className="space-y-6">
      {/* Hero Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-br from-slate-900/90 via-slate-800/80 to-slate-900/90 rounded-3xl border border-slate-700/50 p-8 backdrop-blur-xl shadow-2xl"
      >
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-blue-500 rounded-2xl flex items-center justify-center shadow-lg shadow-emerald-500/20">
                <MessageSquare className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-slate-50">
                  AI Support Assistant
                </h1>
                <p className="text-sm text-emerald-400 font-medium">
                  Amazon-style guided support flow
                </p>
              </div>
            </div>
            <p className="text-slate-300 text-base max-w-2xl">
              Get instant help with maintenance issues, track requests, and troubleshoot problems.
              Our AI assistant guides you through every step with smart, contextual support.
            </p>
          </div>

          <button
            onClick={onLaunch}
            disabled={isDrawerOpen}
            className="px-8 py-4 bg-gradient-to-r from-emerald-500 to-blue-500 text-white rounded-2xl font-semibold hover:from-emerald-400 hover:to-blue-400 transition-all shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-3 group"
          >
            <MessageSquare className="w-5 h-5 group-hover:scale-110 transition-transform" />
            <span>{isDrawerOpen ? "Assistant Open" : "Launch Assistant"}</span>
          </button>
        </div>

        {/* Session Info */}
        <div className="flex items-center gap-4 text-sm text-slate-400 pt-4 border-t border-slate-700/50">
          <span className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isDrawerOpen ? 'bg-emerald-500 animate-pulse' : 'bg-slate-500'}`} />
            {isDrawerOpen ? 'Active Session' : 'Ready to Start'}
          </span>
          {sessionId && (
            <span className="text-xs">
              Session: {sessionId.split('-').slice(-1)[0]}
            </span>
          )}
          <span className="text-xs">
            Persona: <span className="font-semibold text-emerald-400">{persona}</span>
          </span>
        </div>
      </motion.div>

      {/* Flow State Visualization */}
      {isDrawerOpen && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-slate-900/70 rounded-2xl border border-slate-700/50 p-6 backdrop-blur-lg"
        >
          <h2 className="text-lg font-semibold mb-4 text-slate-100 flex items-center gap-2">
            <div className="w-3 h-3 bg-emerald-500 rounded-full animate-pulse" />
            Flow Progress
          </h2>

          {/* Stage Progress Bar */}
          <div className="mb-6">
            <div className="flex items-center justify-between">
              {stages.map((s, idx) => (
                <div key={s} className="flex items-center flex-1">
                  <div className="flex flex-col items-center min-w-[80px]">
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm transition-all ${
                        stage === s
                          ? 'bg-emerald-500 text-white scale-110 shadow-lg ring-4 ring-emerald-500/30'
                          : currentStageIndex > idx
                          ? 'bg-blue-500 text-white'
                          : 'bg-slate-700 text-slate-400'
                      }`}
                    >
                      {currentStageIndex > idx ? '✓' : idx + 1}
                    </div>
                    <span className="text-xs mt-2 text-slate-400 capitalize text-center">
                      {s.replace('_', ' ')}
                    </span>
                  </div>
                  {idx < stages.length - 1 && (
                    <div
                      className={`flex-1 h-1 mx-2 rounded transition-all ${
                        currentStageIndex > idx ? 'bg-blue-500' : 'bg-slate-700'
                      }`}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* State Details */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
              <div className="text-xs font-semibold text-slate-400 mb-1">Current Stage</div>
              <div className="text-sm text-emerald-400 font-medium capitalize">
                {stage.replace('_', ' ')}
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
              <div className="text-xs font-semibold text-slate-400 mb-1">UI Mode</div>
              <div className="text-sm text-blue-400 font-medium capitalize">
                {uiMode.replace('_', ' ')}
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
              <div className="text-xs font-semibold text-slate-400 mb-1">Selected Item</div>
              <div className="text-sm text-purple-400 font-medium truncate">
                {flowState?.selected_item?.title || 'None'}
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
              <div className="text-xs font-semibold text-slate-400 mb-1">Issue</div>
              <div className="text-sm text-amber-400 font-medium truncate">
                {flowState?.selected_reason || 'N/A'}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Architecture Info */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-slate-900/70 rounded-2xl border border-slate-700/50 p-6 backdrop-blur-lg"
      >
        <h2 className="text-lg font-semibold mb-4 text-slate-100">
          Architecture Components
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <div className="font-semibold text-slate-300 mb-3">Backend Services</div>
            <ul className="space-y-2 text-slate-400">
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                ai_support_orchestrator.py
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                session_state_manager.py
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                stream_bot.py
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                card_builder.py
              </li>
            </ul>
          </div>
          <div>
            <div className="font-semibold text-slate-300 mb-3">Frontend Components</div>
            <ul className="space-y-2 text-slate-400">
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                AIChatAssistantLauncher
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                AIDynamicPanel
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                useAISupportFlow hook
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                StreamChatPane
              </li>
            </ul>
          </div>
          <div>
            <div className="font-semibold text-slate-300 mb-3">Event Protocol</div>
            <ul className="space-y-2 text-slate-400">
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-purple-500 rounded-full" />
                ai_intent (Frontend → Backend)
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-purple-500 rounded-full" />
                ai_state (Backend → Frontend)
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-purple-500 rounded-full" />
                Session state persistence
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-purple-500 rounded-full" />
                Stream Chat webhooks
              </li>
            </ul>
          </div>
        </div>
      </motion.div>

      {/* Features Grid */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
      >
        <div className="bg-slate-900/70 rounded-xl border border-slate-700/50 p-5 backdrop-blur-lg">
          <div className="text-3xl mb-3">🔧</div>
          <h3 className="font-semibold text-slate-100 mb-2">Report Issues</h3>
          <p className="text-sm text-slate-400">
            Guided flow for reporting maintenance problems with smart diagnosis
          </p>
        </div>
        <div className="bg-slate-900/70 rounded-xl border border-slate-700/50 p-5 backdrop-blur-lg">
          <div className="text-3xl mb-3">💬</div>
          <h3 className="font-semibold text-slate-100 mb-2">AI Troubleshooting</h3>
          <p className="text-sm text-slate-400">
            Real-time chat with AI for instant help and step-by-step guidance
          </p>
        </div>
        <div className="bg-slate-900/70 rounded-xl border border-slate-700/50 p-5 backdrop-blur-lg">
          <div className="text-3xl mb-3">🚀</div>
          <h3 className="font-semibold text-slate-100 mb-2">Smart Escalation</h3>
          <p className="text-sm text-slate-400">
            Seamless handoff to human agents when needed, with full context
          </p>
        </div>
      </motion.div>
    </div>
  );
}
