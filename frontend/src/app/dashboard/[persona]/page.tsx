"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import { AlertTriangle } from "lucide-react";
import FlowBanner from "@/components/ui/FlowBanner";
import StreamChatPane from "@/components/StreamChatPane";
import { ConversationList } from "@/components/dashboard/ConversationList";
import { AgentStatusBar } from "@/components/dashboard/AgentStatusBar";
import { AIContextPanel } from "@/components/dashboard/AIContextPanel";
import { DebugPanel } from "@/components/dashboard/DebugPanel";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";

const MOBILE_TABS = ["conversations", "chat", "insights"] as const;

type MobileTab = (typeof MOBILE_TABS)[number];

type ActiveChannelType = ReturnType<typeof useStreamChat>["activeChannel"];

const stageFromChannelData = (channel: ActiveChannelType) => {
  if (!channel) return undefined;
  const data = (channel.data ?? {}) as Record<string, unknown>;
  const flowState = data.flow_state as Record<string, unknown> | undefined;
  if (flowState && typeof flowState.stage === "string") {
    return flowState.stage;
  }
  if (typeof data.stage === "string") return data.stage;
  return undefined;
};

export default function PersonaDashboardPage() {
  const params = useParams<{ persona: string }>();
  const { data: session, status } = useSession();
  const router = useRouter();
  const personaParam = (params?.persona ?? "").toLowerCase();
  const { flowState, reasoningState, activeChannel, loading, error } = useStreamChat();

  const [activeTab, setActiveTab] = useState<MobileTab>("chat");
  const [hasRedirected, setHasRedirected] = useState(false);

  // Handle authentication and persona routing
  useEffect(() => {
    // Don't redirect while session is loading
    if (status === "loading") return;

    // Prevent multiple redirects
    if (hasRedirected) return;

    // Redirect unauthenticated users to sign in
    if (status === "unauthenticated") {
      setHasRedirected(true);
      router.replace("/auth/signin");
      return;
    }

    // If authenticated, check persona matches
    if (status === "authenticated") {
      const sessionPersona = session?.user?.persona;

      // No persona selected, go to selector
      if (!sessionPersona) {
        setHasRedirected(true);
        router.replace("/dashboard");
        return;
      }

      // Wrong persona, redirect to correct dashboard
      if (sessionPersona !== personaParam) {
        setHasRedirected(true);
        router.replace(`/dashboard/${sessionPersona}`);
        return;
      }
    }
  }, [status, session?.user?.persona, personaParam, router, hasRedirected]);

  const personaLabel = useMemo(() => {
    if (!personaParam) return "Operations";
    return personaParam.charAt(0).toUpperCase() + personaParam.slice(1);
  }, [personaParam]);

  const activeStage = useMemo(() => {
    const fromFlow = flowState?.stage;
    const fromChannel = stageFromChannelData(activeChannel);
    return fromFlow ?? fromChannel ?? undefined;
  }, [flowState?.stage, activeChannel]);

  const personaForBanner = useMemo(() => {
    return flowState?.persona ?? session?.user?.persona ?? personaParam;
  }, [flowState?.persona, session?.user?.persona, personaParam]);

  // Show loading during session load or redirect
  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
        Loading workspace…
      </div>
    );
  }

  // Show loading while redirecting (persona mismatch or missing)
  if (status === "unauthenticated" || !session?.user?.persona || session.user.persona !== personaParam) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
        Redirecting…
      </div>
    );
  }

  const reasoningLabel = reasoningState.active ? "analysis" : null;
  const reasoningStage = reasoningState.active
    ? reasoningState.stage ?? activeStage ?? null
    : null;

  const conversationPanelClasses = [
    "rounded-2xl border border-slate-800/60 bg-slate-900/50 backdrop-blur-md p-4",
    activeTab === "conversations" ? "flex" : "hidden",
    "lg:flex",
    "flex-col",
    "h-full",
    "gap-4",
    "col-span-12 lg:col-span-4 xl:col-span-3",
  ].join(" ");

  const chatPanelClasses = [
    "rounded-2xl border border-slate-800/60 bg-slate-950/70 backdrop-blur-lg",
    activeTab === "chat" ? "flex" : "hidden",
    "lg:flex",
    "flex-col",
    "h-full",
    "col-span-12 lg:col-span-8 xl:col-span-6",
  ].join(" ");

  const insightsPanelClasses = [
    "rounded-2xl border border-slate-800/60 bg-slate-900/50 backdrop-blur-md p-4",
    activeTab === "insights" ? "flex" : "hidden",
    "xl:flex",
    "flex-col",
    "h-full",
    "gap-4",
    "col-span-12 xl:col-span-3",
  ].join(" ");

  return (
    <div className="h-screen overflow-hidden bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      <div className="mx-auto flex h-full max-w-7xl flex-col px-4 pb-6 pt-6 sm:px-6 lg:px-10">
        <header className="mb-4 flex flex-col gap-4 rounded-3xl border border-slate-800/60 bg-slate-950/80 p-6 backdrop-blur-xl lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-emerald-300">Command Center</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-50 lg:text-3xl">
              {personaLabel} operations
            </h1>
            <p className="mt-2 text-sm text-slate-400">
              Signed in as {session.user.email}. Coordinate incidents, automation, and approvals in real time.
            </p>
          </div>
          <button
            type="button"
            onClick={() => signOut({ callbackUrl: "/" })}
            className="self-start rounded-full bg-emerald-500 px-5 py-2 text-sm font-semibold text-emerald-950 shadow-lg shadow-emerald-500/20 transition hover:bg-emerald-400 lg:self-auto"
          >
            Sign out
          </button>
        </header>

        <div className="mb-4 flex items-center gap-2 lg:hidden">
          {MOBILE_TABS.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`flex-1 rounded-full px-4 py-2 text-sm font-semibold transition ${
                activeTab === tab ? "bg-emerald-500 text-emerald-950" : "bg-slate-800/80 text-slate-300"
              }`}
            >
              {tab === "chat" ? "Chat" : tab === "conversations" ? "Conversations" : "Insights"}
            </button>
          ))}
        </div>

        {error ? (
          <div className="mb-4 flex items-center gap-3 rounded-2xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-100">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}

        <main className="grid flex-1 grid-cols-12 gap-5 min-h-0">
          <aside className={conversationPanelClasses}>
            <ConversationList />
          </aside>

          <section className={chatPanelClasses}>
            <FlowBanner
              stage={activeStage}
              persona={personaForBanner ?? personaParam}
              reasoningLabel={reasoningLabel}
              reasoningStage={reasoningStage}
            />
            <div className="flex flex-1 flex-col min-h-0">
              <StreamChatPane className="h-full" />
            </div>
          </section>

          <aside className={insightsPanelClasses}>
            <AIContextPanel />
            <DebugPanel />
          </aside>
        </main>

        <AgentStatusBar
          persona={personaForBanner ?? personaParam}
          flowStage={activeStage ?? null}
          reasoningActive={reasoningState.active}
          className="mt-4 rounded-2xl border border-slate-800/60 bg-slate-900/70 backdrop-blur-lg"
        />
      </div>
    </div>
  );
}
