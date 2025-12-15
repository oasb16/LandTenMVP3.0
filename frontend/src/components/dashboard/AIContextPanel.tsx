import React, { memo, useMemo, useState } from "react";
import { Activity, Clock4, Sparkles, Workflow, AlertTriangle, FileText, Shield, DollarSign, ChevronDown } from "lucide-react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";
import { IncidentTimeline } from "../ai/IncidentTimeline";
import { parseDiagnosticData, determineSeverity } from "../ai/parseDiagnosticData";

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
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(["snapshot", "context"]));

  const stageKey = formatStageKey(flowState?.stage);
  const copy = STAGE_COPY[stageKey] ?? fallbackStageCopy;
  const channelData = (activeChannel?.data ?? {}) as Record<string, unknown>;
  const incidentId = flowState?.incidentId ?? (activeChannel?.id || activeChannel?.cid);
  const persona =
    flowState?.persona ??
    (typeof channelData.persona === "string" ? channelData.persona : undefined) ??
    "assistant";

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(section)) {
        newSet.delete(section);
      } else {
        newSet.add(section);
      }
      return newSet;
    });
  };

  // Parse conversation messages to extract diagnostic data
  const conversationInsights = useMemo(() => {
    if (!activeChannel?.state?.messages) {
      return {
        hasDiagnostic: false,
        latestDiagnostic: null,
        severity: null,
        urgency: null,
        estimatedCost: null,
        safetyIssues: 0,
        nextSteps: [],
      };
    }

    const messages = activeChannel.state.messages;
    let latestDiagnostic = null;
    let severity = null;
    let urgency = null;
    let estimatedCost = null;
    let safetyIssues = 0;
    const allNextSteps: string[] = [];

    // Parse messages in reverse (newest first)
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      const text = msg.text || "";
      const metadata = (msg as any).metadata || {};

      // Parse diagnostic data from message
      const diagnosticData = parseDiagnosticData(text);

      if (diagnosticData.hasDiagnostic) {
        if (!latestDiagnostic) {
          latestDiagnostic = diagnosticData;
        }

        // Extract severity from diagnostic or metadata
        if (!severity && diagnosticData.diagnosticResult?.severity) {
          severity = diagnosticData.diagnosticResult.severity;
        }
        if (!severity && metadata.severity) {
          severity = metadata.severity;
        }

        // Extract urgency
        if (!urgency && diagnosticData.diagnosticResult?.urgency) {
          urgency = diagnosticData.diagnosticResult.urgency;
        }
        if (!urgency && metadata.urgency) {
          urgency = metadata.urgency;
        }

        // Extract cost estimate
        if (!estimatedCost && diagnosticData.diagnosticResult?.estimatedCost) {
          estimatedCost = diagnosticData.diagnosticResult.estimatedCost;
        }

        // Count safety issues
        if (diagnosticData.safetyConsiderations) {
          safetyIssues += diagnosticData.safetyConsiderations.length;
        }

        // Collect next steps
        if (diagnosticData.nextSteps) {
          allNextSteps.push(...diagnosticData.nextSteps);
        }
      }
    }

    return {
      hasDiagnostic: !!latestDiagnostic,
      latestDiagnostic,
      severity,
      urgency,
      estimatedCost,
      safetyIssues,
      nextSteps: allNextSteps.slice(0, 3), // Keep top 3 next steps
    };
  }, [activeChannel?.state?.messages]);

  // Determine severity level for color coding
  const severityLevel = conversationInsights.severity?.toLowerCase() as 'low' | 'medium' | 'high' | 'urgent' | undefined;
  const severityColors = {
    low: "text-emerald-400 border-emerald-500/30 bg-emerald-900/20",
    medium: "text-amber-400 border-amber-500/30 bg-amber-900/20",
    high: "text-orange-400 border-orange-500/30 bg-orange-900/20",
    urgent: "text-red-400 border-red-500/30 bg-red-900/20",
  };
  const severityConfig = severityLevel ? severityColors[severityLevel] : "text-slate-400 border-slate-700 bg-slate-900/70";

  return (
    <div className="h-full w-full overflow-y-auto px-3 py-4 pb-safe space-y-3">
      {/* Incident Timeline - Horizontal on mobile */}
      {incidentId && flowState?.stage && (
        <div className="w-full">
          <IncidentTimeline
            currentStage={stageKey}
            incidentId={incidentId as string}
            compact={true}
          />
        </div>
      )}

      {/* Diagnostic Summary Card - Prominent on mobile */}
      {conversationInsights.hasDiagnostic && (
        <Card className={`border ${severityConfig} backdrop-blur-sm`}>
          <CardHeader className="p-4">
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <AlertTriangle className={`h-5 w-5 ${severityLevel ? severityColors[severityLevel].split(' ')[0] : ''}`} />
              Incident Summary
            </CardTitle>
            <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
              {conversationInsights.severity && (
                <div className="flex flex-col gap-1">
                  <span className="text-xs text-slate-400">Severity</span>
                  <span className={`font-semibold capitalize ${severityLevel ? severityColors[severityLevel].split(' ')[0] : ''}`}>
                    {conversationInsights.severity}
                  </span>
                </div>
              )}
              {conversationInsights.urgency && (
                <div className="flex flex-col gap-1">
                  <span className="text-xs text-slate-400">Urgency</span>
                  <span className="font-semibold capitalize text-slate-200">
                    {conversationInsights.urgency}
                  </span>
                </div>
              )}
              {conversationInsights.estimatedCost && (
                <div className="flex flex-col gap-1 col-span-2">
                  <span className="text-xs text-slate-400">Estimated Cost</span>
                  <span className="font-semibold text-emerald-300">
                    ${conversationInsights.estimatedCost}
                  </span>
                </div>
              )}
            </div>
          </CardHeader>
        </Card>
      )}

      {/* Safety Alerts - Prominent if present */}
      {conversationInsights.safetyIssues > 0 && (
        <Card className="border border-red-500/40 bg-red-900/30 backdrop-blur-sm">
          <CardHeader className="p-4">
            <CardTitle className="flex items-center gap-2 text-base font-semibold text-red-200">
              <Shield className="h-5 w-5 animate-pulse" />
              Safety Alert
            </CardTitle>
            <CardDescription className="text-red-100 mt-2 text-sm">
              {conversationInsights.safetyIssues} safety consideration{conversationInsights.safetyIssues > 1 ? 's' : ''} identified
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {/* Flow Snapshot - Collapsible */}
      <Card className="border border-emerald-500/20 bg-slate-900/70 backdrop-blur-sm">
        <button
          onClick={() => toggleSection("snapshot")}
          className="w-full text-left"
        >
          <CardHeader className="p-4">
            <CardTitle className="flex items-center justify-between text-sm font-semibold text-emerald-200">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4" />
                Flow Snapshot
              </div>
              <ChevronDown
                className={`h-4 w-4 transition-transform ${expandedSections.has("snapshot") ? "rotate-180" : ""}`}
              />
            </CardTitle>
          </CardHeader>
        </button>
        {expandedSections.has("snapshot") && (
          <CardDescription className="px-4 pb-4 text-slate-300 text-sm">
            {copy.summary}
          </CardDescription>
        )}
      </Card>

      {/* Incident Context - Compact */}
      <Card className="border border-slate-800/70 bg-slate-900/60 backdrop-blur-sm">
        <CardHeader className="p-4">
          <CardTitle className="flex items-center justify-between text-sm font-semibold text-slate-100">
            <span>Incident</span>
            {incidentId ? (
              <span className="text-xs text-emerald-300 font-mono">{String(incidentId).slice(-8)}</span>
            ) : (
              <span className="text-xs text-slate-500">None</span>
            )}
          </CardTitle>
          <CardDescription className="text-slate-400 text-xs mt-1">
            Focus: <strong className="text-slate-200">{persona?.toUpperCase()}</strong>
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Agent Status - Compact */}
      <Card className="border border-slate-800/70 bg-slate-900/60 backdrop-blur-sm">
        <CardHeader className="p-4">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold text-slate-100">
            <Activity className={`h-4 w-4 ${reasoningState.active ? "text-amber-300 animate-pulse" : "text-slate-400"}`} />
            {reasoningState.active ? "Agent Analyzing..." : "Agent Ready"}
          </CardTitle>
        </CardHeader>
      </Card>

      {/* Flow Stage - Compact */}
      <Card className="border border-slate-800/70 bg-slate-900/60 backdrop-blur-sm">
        <CardHeader className="p-4">
          <CardTitle className="flex items-center justify-between text-sm font-semibold text-slate-100">
            <div className="flex items-center gap-2">
              <Workflow className="h-4 w-4 text-indigo-300" />
              Stage
            </div>
            <span className="text-xs text-indigo-300 capitalize">{copy.label}</span>
          </CardTitle>
        </CardHeader>
      </Card>

      {/* Next Steps - Collapsible */}
      {conversationInsights.nextSteps.length > 0 && (
        <Card className="border border-slate-800/70 bg-slate-900/60 backdrop-blur-sm">
          <button
            onClick={() => toggleSection("nextsteps")}
            className="w-full text-left"
          >
            <CardHeader className="p-4">
              <CardTitle className="flex items-center justify-between text-sm font-semibold text-slate-100">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-slate-300" />
                  Next Steps
                </div>
                <ChevronDown
                  className={`h-4 w-4 transition-transform ${expandedSections.has("nextsteps") ? "rotate-180" : ""}`}
                />
              </CardTitle>
            </CardHeader>
          </button>
          {expandedSections.has("nextsteps") && (
            <CardDescription className="px-4 pb-4 text-slate-400">
              <ul className="space-y-2 text-xs">
                {conversationInsights.nextSteps.map((step, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-emerald-400 mt-0.5">•</span>
                    <span className="flex-1 leading-relaxed">{step}</span>
                  </li>
                ))}
              </ul>
            </CardDescription>
          )}
        </Card>
      )}
    </div>
  );
}

export const AIContextPanel = memo(AIContextPanelComponent);
