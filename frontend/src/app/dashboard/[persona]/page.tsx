"use client";

import { use, useState } from "react";
import { StreamChatProvider, useStreamChat } from "@/contexts/StreamChatContext";
import { ConversationList } from "@/components/dashboard/ConversationList";
import { ChatPane } from "@/components/dashboard/ChatPane";
import { AIContextPanel } from "@/components/dashboard/AIContextPanel";
import { FlowBanner } from "@/components/dashboard/FlowBanner";
import { AgentToggleButton } from "@/components/ai/AgentToggleButton";

// ============================================================================
// DASHBOARD CONTENT (Inside Provider)
// ============================================================================

function DashboardContent() {
  const {
    isLoading,
    error,
    flowState,
    reasoningState,
    agentEnabled,
    setAgentEnabled,
  } = useStreamChat();

  const [activeTab, setActiveTab] = useState<"conversations" | "chat" | "insights">("chat");

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-950">
        <div className="text-slate-400 text-lg">Initializing Command Center...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-950">
        <div className="max-w-md p-6 bg-red-950 border border-red-800 rounded-lg">
          <h3 className="text-red-400 font-semibold mb-2">Connection Error</h3>
          <p className="text-red-300 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-full overflow-hidden bg-slate-950 flex flex-col">
      {/* Top Bar */}
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm">
        <div className="px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-white">
              PropertyAI Command Center
            </h1>
            <AgentToggleButton
              initialState={agentEnabled}
              onChange={setAgentEnabled}
            />
          </div>

          {/* Tab Switcher (Mobile) */}
          <div className="flex lg:hidden gap-2">
            {(["conversations", "chat", "insights"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1 text-sm font-medium rounded transition-colors ${
                  activeTab === tab
                    ? "bg-emerald-600 text-white"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Flow Banner */}
        {flowState.type && <FlowBanner flowState={flowState} />}
      </div>

      {/* Main Content - 3 Column Layout */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full grid grid-cols-1 lg:grid-cols-12 gap-0">
          {/* Left Panel: Conversations List */}
          <div
            className={`lg:col-span-3 bg-slate-900/30 border-r border-slate-800 overflow-hidden ${
              activeTab !== "conversations" ? "hidden lg:block" : ""
            }`}
          >
            <ConversationList />
          </div>

          {/* Middle Panel: Chat */}
          <div
            className={`lg:col-span-6 bg-slate-950 overflow-hidden ${
              activeTab !== "chat" ? "hidden lg:block" : ""
            }`}
          >
            <ChatPane />
          </div>

          {/* Right Panel: AI Context & Insights */}
          <div
            className={`lg:col-span-3 bg-slate-900/30 border-l border-slate-800 overflow-hidden ${
              activeTab !== "insights" ? "hidden lg:block" : ""
            }`}
          >
            <AIContextPanel
              flowState={flowState}
              reasoningState={reasoningState}
            />
          </div>
        </div>
      </div>

      {/* Bottom Status Bar */}
      <div className="border-t border-slate-800 bg-slate-900/50 px-4 py-2 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-4">
          <span>Agent: {agentEnabled ? "🟢 Active" : "⭕ Disabled"}</span>
          {flowState.type && (
            <span>Flow: {flowState.type} → {flowState.stage}</span>
          )}
        </div>
        <div>
          {reasoningState.intent && (
            <span>Last Intent: {reasoningState.intent} ({(reasoningState.confidence! * 100).toFixed(0)}%)</span>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// PAGE COMPONENT (With Provider)
// ============================================================================

interface PageProps {
  params: Promise<{
    persona: string;
  }>;
}

export default function DashboardPage({ params }: PageProps) {
  const { persona } = use(params);

  // Validate persona
  const validPersonas = ["tenant", "landlord", "contractor"];
  if (!validPersonas.includes(persona)) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-950">
        <div className="max-w-md p-6 bg-red-950 border border-red-800 rounded-lg">
          <h3 className="text-red-400 font-semibold mb-2">Invalid Persona</h3>
          <p className="text-red-300 text-sm">
            Persona must be one of: {validPersonas.join(", ")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <StreamChatProvider persona={persona}>
      <DashboardContent />
    </StreamChatProvider>
  );
}
