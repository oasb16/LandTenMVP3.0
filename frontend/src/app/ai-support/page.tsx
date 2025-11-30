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
import LandingPage from "./components/LandingPage";
import useAISupportFlow from "./hooks/useAISupportFlow";
import "./ai-support.css";

export default function AISupportPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

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

        {/* Main Content - Landing Page */}
        <main className="flex-1">
          <LandingPage
            onLaunch={() => setIsDrawerOpen(true)}
            sessionId={flowState?.session_id || null}
            persona={persona}
            stage={stage}
            uiMode={uiMode}
            flowState={flowState}
            isDrawerOpen={isDrawerOpen}
          />
        </main>

        {/* Footer */}
        <footer className="mt-6 rounded-2xl border border-slate-800/60 bg-slate-900/70 backdrop-blur-lg p-4 flex items-center justify-between text-sm">
          <div className="flex items-center gap-3">
            <div className={`h-2 w-2 rounded-full ${client && activeChannel ? 'bg-emerald-500' : 'bg-slate-500'}`} />
            <span className="text-slate-400">
              {client && activeChannel ? 'Connected' : 'Ready'}
            </span>
          </div>
          <div className="text-slate-500 text-xs">
            Powered by LandTen AI • Amazon-style UX
          </div>
        </footer>

      </div>

      {/* AI Support Drawer (Amazon-style guided flow) */}
      {isDrawerOpen && (
        <AIChatAssistantLauncher autoOpen={true}>
          <div className="flex h-full flex-col">
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
                  {initializing && (
                    <span className="text-xs text-slate-400">Initializing...</span>
                  )}
                </div>

                <AIDynamicPanel
                  uiMode={uiMode}
                  payload={payload}
                  sendIntent={sendIntent}
                  flowState={flowState}
                />
              </aside>

            </div>

            {/* Drawer Footer - Status Bar */}
            <div className="border-t border-slate-700/50 bg-slate-950/80 px-4 py-2 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <div className={`h-1.5 w-1.5 rounded-full ${flowState?.session_id ? 'bg-emerald-500 animate-pulse' : 'bg-slate-500'}`} />
                <span className="text-slate-400">
                  Stage: <span className="font-medium text-emerald-400">{stage}</span>
                </span>
              </div>
              <div className="text-slate-500">
                Mode: {uiMode} • {persona}
              </div>
            </div>
          </div>
        </AIChatAssistantLauncher>
      )}
    </div>
  );
}
