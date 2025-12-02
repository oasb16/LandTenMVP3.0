/**
 * AI Support Experience Page
 *
 * Landing page with drawer-based assistant (inspired by proposed1.jsx)
 * Integrates real backend flow with Amazon-style UX
 *
 * ARCHITECTURE:
 * - Landing page shows hero, state visualization, and architecture info
 * - Drawer contains StreamChatPane + AIDynamicPanel (real backend integration)
 * - Uses AIChatAssistantLauncher for drawer UX
 * - All data flows through real orchestrator (no mocks)
 */

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";
import StreamChatPane from "@/components/StreamChatPane";
import AIDynamicPanel from "./components/AIDynamicPanel";
import AIChatAssistantLauncher from "./components/AIChatAssistantLauncher";
import HelpHub from "./components/amazon-style/HelpHub";
import ItemReasonPanel from "./components/amazon-style/ItemReasonPanel";
import RufusWelcome from "./components/amazon-style/RufusWelcome";
import StatusPanel from "./components/amazon-style/StatusPanel";
import HelpArticles from "./components/amazon-style/HelpArticles";
import { AIContextPanel } from "@/components/dashboard/AIContextPanel";
import { AgentStatusBar } from "@/components/dashboard/AgentStatusBar";
import { DebugPanel } from "@/components/dashboard/DebugPanel";
import { ConversationList } from "@/components/dashboard/ConversationList";
import PaymentInitiator from "@/components/PaymentInitiator";
import useAISupportFlow from "./hooks/useAISupportFlow";
import { AISupportFlowProvider } from "./context/AISupportFlowContext";
import { Settings, MessageSquare, Bug } from "lucide-react";
import "./ai-support.css";

export default function AISupportPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [view, setView] = useState<"hub" | "item_reason">("hub");
  const [drawerMode, setDrawerMode] = useState<"welcome" | "chat" | "status" | "conversations" | "billing">("welcome");
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const [showContextPanel, setShowContextPanel] = useState(false);
  const [selectedItem, setSelectedItem] = useState<{
    id: string;
    type: string;
    title: string;
    subtitle?: string;
  } | null>(null);

  // Use Classic Dashboard's StreamChat context (already initialized app-wide)
  const { client, activeChannel, loading: streamLoading, error: streamError } = useStreamChat();

  // AI Support flow state machine (for guided flow panels)
  const {
    uiMode,
    stage,
    payload,
    flowState,
    loading: flowLoading,
    initializing,
    error: flowError,
    sendIntent,
  } = useAISupportFlow({
    mode: "guided",
    autoInit: isDrawerOpen, // Only init when drawer opens
    client, // Pass Classic Dashboard's client
  });

  console.log("[AI Support Page] Render - status:", status, "client:", !!client, "drawer:", isDrawerOpen);

  // Redirect unauthenticated users
  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/auth/signin");
    }
  }, [status, router]);

  // Show loading during auth
  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500 mx-auto mb-4" />
          <p className="text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Show auth required
  if (!session?.user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-4">Authentication Required</h2>
          <p className="text-slate-400 mb-6">Please sign in to access AI Support</p>
          <a
            href="/auth/signin"
            className="inline-block px-6 py-3 bg-emerald-500 hover:bg-emerald-400 text-emerald-950 rounded-lg font-semibold transition"
          >
            Sign In
          </a>
        </div>
      </div>
    );
  }

  const error = streamError || flowError;
  const persona = (session.user as any).persona || "tenant";

  const handleSelectItem = (itemId: string, itemType: string, itemTitle: string) => {
    setSelectedItem({ id: itemId, type: itemType, title: itemTitle });

    // Special handling for specific item types that should open drawer directly
    if (itemType === "lease" || itemType === "notification") {
      // For lease and notifications, go straight to chat with context
      sendIntent("item_selected", {
        item_id: itemId,
        item_title: itemTitle,
        item_type: itemType,
      }).then(() => {
        setDrawerMode("chat");
        setIsDrawerOpen(true);
      });
    } else if (itemType === "incident" || itemType === "job") {
      // For incidents and jobs, send to backend for proper routing
      sendIntent("item_selected", {
        item_id: itemId,
        item_title: itemTitle,
        item_type: itemType,
      }).then(() => {
        setDrawerMode("chat");
        setIsDrawerOpen(true);
      });
    } else {
      // For other types (property, billing), show reason picker
      setView("item_reason");
    }
  };

  const handleSelectReason = async (reasonId: string, reasonLabel: string) => {
    // Store selection in flow state metadata
    if (selectedItem) {
      await sendIntent("item_selected", {
        item_id: selectedItem.id,
        item_title: selectedItem.title,
        item_type: selectedItem.type,
      });
      await sendIntent("reason_selected", {
        reason: reasonLabel,
        reason_id: reasonId,
      });

      // Special routing for specific reason types
      if (reasonId === "pay") {
        // Payment reason → open billing drawer
        setDrawerMode("billing");
        setIsDrawerOpen(true);
      } else if (reasonId === "status" || reasonId === "check") {
        // Status check reason → open status panel
        setDrawerMode("status");
        setIsDrawerOpen(true);
      } else {
        // Default: open chat mode
        setDrawerMode("chat");
        setIsDrawerOpen(true);
      }
    }
  };

  const handleLaunchChat = async () => {
    // Init AI session and open drawer
    await sendIntent("ai_init", {});
    setDrawerMode("chat");
    setIsDrawerOpen(true);
  };

  const handleBackToHub = () => {
    setView("hub");
    setSelectedItem(null);
  };

  const handleQuickAction = async (action: string) => {
    if (action === "maintenance") {
      // Start maintenance flow - skip intro, go to item select
      await sendIntent("select_cta", { cta_id: "maintenance" });
      setDrawerMode("chat");
      setIsDrawerOpen(true);
    } else if (action === "billing") {
      // Start billing flow - show payment initiator
      setDrawerMode("billing");
      setIsDrawerOpen(true);
    } else if (action === "chat") {
      // Free-form chat mode
      await sendIntent("ai_init", {});
      setDrawerMode("chat");
      setIsDrawerOpen(true);
    } else if (action === "conversations") {
      // Show conversation list
      setDrawerMode("conversations");
      setIsDrawerOpen(true);
    }
  };

  const handleShowStatus = () => {
    setDrawerMode("status");
    setIsDrawerOpen(true);
  };

  const handleBackToWelcome = () => {
    setDrawerMode("welcome");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-screen flex-col px-4 pb-6 pt-6 sm:px-6 lg:px-10 max-w-7xl">

        {/* Header */}
        <header className="mb-6 flex flex-col gap-4 rounded-3xl border border-slate-800/60 bg-slate-950/80 p-6 backdrop-blur-xl lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-emerald-300">AI Support</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-50 lg:text-3xl">
              Property Assistant
            </h1>
            <p className="mt-2 text-sm text-slate-400">
              Signed in as {session.user.email}
            </p>
          </div>
          <div className="flex gap-3">
            <a
              href="/dashboard"
              className="self-start rounded-full bg-slate-700 px-5 py-2 text-sm font-semibold text-slate-100 shadow-lg transition hover:bg-slate-600 lg:self-auto"
            >
              Dashboard
            </a>
            <a
              href="/"
              className="self-start rounded-full bg-emerald-500 px-5 py-2 text-sm font-semibold text-emerald-950 shadow-lg shadow-emerald-500/20 transition hover:bg-emerald-400 lg:self-auto"
            >
              Home
            </a>
          </div>
        </header>

        {/* Error Banner */}
        {error && (
          <div className="mb-4 rounded-2xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-100">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Main Content */}
        <main className="flex-1 flex flex-col gap-4">
          {/* Amazon-style Help Hub or Item Reason Panel */}
          <div className="flex-1 rounded-3xl border border-slate-800/60 bg-slate-950/80 backdrop-blur-xl overflow-hidden">
            {view === "hub" ? (
              <HelpHub
                userName={session.user.name || "User"}
                persona={persona}
                onSelectItem={handleSelectItem}
                onLaunchChat={handleLaunchChat}
              />
            ) : (
              <ItemReasonPanel
                itemId={selectedItem?.id || ""}
                itemType={selectedItem?.type || ""}
                itemTitle={selectedItem?.title || ""}
                itemSubtitle={selectedItem?.subtitle}
                persona={persona}
                onBack={handleBackToHub}
                onSelectReason={handleSelectReason}
              />
            )}
          </div>

          {/* Help Articles Section */}
          {view === "hub" && (
            <div className="rounded-3xl border border-slate-800/60 bg-slate-950/80 backdrop-blur-xl">
              <HelpArticles persona={persona} onArticleClick={(articleId, articleTitle) => {
                console.log("Article clicked:", articleId, articleTitle);
                // Open drawer with article context
                handleLaunchChat();
              }} />
            </div>
          )}
        </main>

        {/* Footer */}
        <footer className="mt-6 rounded-2xl border border-slate-800/60 bg-slate-900/70 backdrop-blur-lg p-4 flex items-center justify-between text-sm">
          <div className="flex items-center gap-3">
            <div className={`h-2 w-2 rounded-full ${client && activeChannel ? 'bg-emerald-500' : 'bg-slate-500'}`} />
            <span className="text-slate-400">
              {client && activeChannel ? 'Connected' : 'Ready'}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setDrawerMode("conversations");
                setIsDrawerOpen(true);
              }}
              className="text-slate-500 hover:text-emerald-400 transition-colors"
              title="View conversations"
            >
              <MessageSquare className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShowDebugPanel(!showDebugPanel)}
              className="text-slate-500 hover:text-purple-400 transition-colors"
              title="Toggle debug panel"
            >
              <Bug className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShowContextPanel(!showContextPanel)}
              className="text-slate-500 hover:text-emerald-400 transition-colors"
              title="Toggle context panel"
            >
              <Settings className="w-4 h-4" />
            </button>
            <div className="text-slate-500 text-xs">
              Powered by LandTen AI • Amazon-style UX
            </div>
          </div>
        </footer>

        {/* Debug Panel (overlay) */}
        {showDebugPanel && (
          <div className="fixed bottom-20 right-4 z-50 w-96">
            <DebugPanel />
          </div>
        )}

      </div>

      {/* AI Support Drawer (Amazon-style guided flow) */}
      {isDrawerOpen && (
        <AIChatAssistantLauncher
          autoOpen={true}
          onClose={() => setIsDrawerOpen(false)}
        >
          <AISupportFlowProvider sendIntent={sendIntent}>
            <div className="flex h-full flex-col">
            {/* Conditional View: Welcome / Status / Conversations / Billing / Chat+Flow */}
            {drawerMode === "welcome" ? (
              /* Show Rufus Welcome */
              <RufusWelcome
                onQuickAction={handleQuickAction}
                onShowStatus={handleShowStatus}
              />
            ) : drawerMode === "status" ? (
              /* Show Status Panel */
              <StatusPanel
                persona={persona}
                onBack={handleBackToWelcome}
              />
            ) : drawerMode === "conversations" ? (
              /* Show Conversation List */
              <div className="flex-1 flex flex-col p-4 overflow-hidden">
                <button
                  onClick={handleBackToWelcome}
                  className="mb-4 text-sm text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-2"
                >
                  ← Back
                </button>
                <ConversationList />
              </div>
            ) : drawerMode === "billing" ? (
              /* Show Payment Initiator */
              <div className="flex-1 overflow-y-auto p-4">
                <button
                  onClick={handleBackToWelcome}
                  className="mb-4 text-sm text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-2"
                >
                  ← Back
                </button>
                <PaymentInitiator
                  contractorId="default-contractor"
                  contractorName="Contractor Services"
                  defaultAmount={0}
                  defaultDescription="Payment for services"
                  onSuccess={(payment) => {
                    console.log("Payment successful:", payment);
                    // Return to welcome after payment
                    setTimeout(() => {
                      handleBackToWelcome();
                    }, 2000);
                  }}
                />
              </div>
            ) : (
              /* Show Chat + Guided Flow */
              <>
                {/* Split View: Chat + Guided Flow Panel */}
                <div className="flex flex-1 flex-col lg:flex-row gap-2 p-2 overflow-hidden">
                  {/* Chat Panel (60% width on desktop) */}
                  <div className="flex-1 lg:w-[60%] rounded-xl border border-slate-700/50 bg-slate-900/50 overflow-hidden">
                    <StreamChatPane
                      className="h-full"
                      showEscalation={stage === "diagnosis"}
                      onEscalate={async () => {
                        await sendIntent("ai_escalate", {
                          reason: "user_requested",
                          current_stage: stage,
                        });
                      }}
                    />
                  </div>

                  {/* Guided Flow Panel (40% width on desktop) */}
                  <aside className="lg:w-[40%] rounded-xl border border-slate-700/50 bg-slate-950/70 p-4 flex flex-col gap-3 overflow-y-auto">
                    <div className="flex items-center justify-between">
                      <h2 className="text-sm font-semibold text-slate-100">Guided Flow</h2>
                      <div className="flex items-center gap-2">
                        {initializing && (
                          <span className="text-xs text-slate-400">Initializing...</span>
                        )}
                        <button
                          onClick={() => setShowContextPanel(!showContextPanel)}
                          className={`text-xs px-2 py-1 rounded transition-colors ${showContextPanel ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700/50 text-slate-400 hover:text-slate-200'}`}
                          title="Toggle context panel"
                        >
                          Context
                        </button>
                      </div>
                    </div>

                    {showContextPanel ? (
                      <AIContextPanel />
                    ) : (
                      <AIDynamicPanel
                        uiMode={uiMode}
                        payload={payload}
                        sendIntent={sendIntent}
                        flowState={flowState}
                      />
                    )}
                  </aside>
                </div>

                {/* Drawer Footer - Agent Status Bar */}
                <AgentStatusBar
                  persona={persona}
                  flowStage={stage}
                  reasoningActive={initializing || flowLoading}
                />
              </>
            )}
            </div>
          </AISupportFlowProvider>
        </AIChatAssistantLauncher>
      )}
    </div>
  );
}
