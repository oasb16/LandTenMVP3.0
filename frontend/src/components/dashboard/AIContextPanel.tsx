import React, { memo } from "react";
import { Activity, Clock4, Sparkles, Workflow } from "lucide-react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";

const STAGE_COPY: Record<string, { label: string; summary: string; next: string }> = {
  discovery: {
    label: "Discovery",
    summary: "Collecting structured details to scope the issue.",
    next: "Gather location, severity, and supporting media to triage effectively.",
  },
  job: {
    label: "Work Order",
    summary: "Drafting the work order and matching contractors.",
    next: "Review bids and confirm scheduling details with stakeholders.",
  },
  approval: {
    label: "Approval",
    summary: "Waiting for authorization to proceed with repairs.",
    next: "Landlord approval unlocks scheduling and materials ordering.",
  },
  completion: {
    label: "Completion",
    summary: "Documenting outcomes and closing the incident loop.",
    next: "Log invoices, archive media, and notify participants of closure.",
  },
  incident: {
    label: "Incident",
    summary: "Initial incident context being organized.",
    next: "Route the incident into the appropriate discovery path.",
  },
};

const fallbackStageCopy = STAGE_COPY.incident;

const formatStageKey = (stage?: string | null) => {
  if (!stage) return "incident";
  const lowered = stage.toLowerCase();
  if (lowered.includes("discovery")) return "discovery";
  if (lowered.includes("job")) return "job";
  if (lowered.includes("approval")) return "approval";
  if (lowered.includes("completion")) return "completion";
  return "incident";
};

function AIContextPanelComponent() {
  const { activeChannel, flowState, reasoningState } = useStreamChat();

  const stageKey = formatStageKey(flowState?.stage);
  const copy = STAGE_COPY[stageKey] ?? fallbackStageCopy;
  const channelData = (activeChannel?.data ?? {}) as Record<string, unknown>;
  const incidentId = flowState?.incidentId ?? (activeChannel?.id || activeChannel?.cid);
  const persona =
    flowState?.persona ??
    (typeof channelData.persona === "string" ? channelData.persona : undefined) ??
    "assistant";

  return (
    <div className="flex h-full flex-col gap-4">
      <Card className="border border-emerald-500/20 bg-slate-900/70 backdrop-blur">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-semibold text-emerald-200">
            <Sparkles className="h-4 w-4" /> Flow Snapshot
          </CardTitle>
          <CardDescription className="text-slate-300">{copy.summary}</CardDescription>
        </CardHeader>
      </Card>

      <Card className="border border-slate-800/70 bg-slate-900/60 backdrop-blur">
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-sm font-semibold text-slate-100">
            <span>Incident Context</span>
            {incidentId ? (
              <span className="text-xs text-emerald-300">{incidentId}</span>
            ) : (
              <span className="text-xs text-slate-500">No incident pinned</span>
            )}
          </CardTitle>
          <CardDescription className="text-slate-400">
            Persona focus: {persona?.toUpperCase()}
          </CardDescription>
        </CardHeader>
      </Card>

      <Card className="border border-slate-800/70 bg-slate-900/60 backdrop-blur">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-semibold text-slate-100">
            <Activity className={`h-4 w-4 ${reasoningState.active ? "text-amber-300 animate-pulse" : "text-slate-400"}`} />
            {reasoningState.active ? "Agent reasoning in progress" : "Agent standing by"}
          </CardTitle>
          <CardDescription className="text-slate-400">
            {reasoningState.active
              ? "Analyzing the latest messages to determine the next best action."
              : copy.next}
          </CardDescription>
        </CardHeader>
      </Card>

      <Card className="border border-slate-800/70 bg-slate-900/60 backdrop-blur">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-semibold text-slate-100">
            <Workflow className="h-4 w-4 text-indigo-300" /> Flow Stage
          </CardTitle>
          <CardDescription className="text-slate-300">
            {copy.label} · {(flowState?.stage ?? "general").toString().replace(/\./g, " → ")}
          </CardDescription>
        </CardHeader>
      </Card>

      <Card className="mt-auto border border-slate-800/70 bg-slate-900/60 backdrop-blur">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-semibold text-slate-100">
            <Clock4 className="h-4 w-4 text-slate-300" /> Next best action
          </CardTitle>
          <CardDescription className="text-slate-400">{copy.next}</CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}

export const AIContextPanel = memo(AIContextPanelComponent);
