import React, { memo, useMemo } from "react";
import { Activity, Clock4, Sparkles, Workflow, AlertTriangle, FileText, Shield, DollarSign } from "lucide-react";
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

  const stageKey = formatStageKey(flowState?.stage);
  const copy = STAGE_COPY[stageKey] ?? fallbackStageCopy;
  const channelData = (activeChannel?.data ?? {}) as Record<string, unknown>;
  const incidentId = flowState?.incidentId ?? (activeChannel?.id || activeChannel?.cid);
  const persona =
    flowState?.persona ??
    (typeof channelData.persona === "string" ? channelData.persona : undefined) ??
    "assistant";

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
    low: "text-emerald-400 border-emerald-500/30",
    medium: "text-amber-400 border-amber-500/30",
    high: "text-orange-400 border-orange-500/30",
    urgent: "text-red-400 border-red-500/30",
  };
  const severityColor = severityLevel ? severityColors[severityLevel] : "text-slate-400 border-slate-700";

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto">
      {/* Incident Timeline - Show if there's an incident */}
      {incidentId && flowState?.stage && (
        <IncidentTimeline
          currentStage={stageKey}
          incidentId={incidentId as string}
          compact={true}
        />
      )}

      {/* Flow Snapshot with Diagnostic Insights */}
      <Card className={`border ${conversationInsights.hasDiagnostic ? severityColor : 'border-emerald-500/20'} bg-slate-900/70 backdrop-blur`}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-semibold text-emerald-200">
            <Sparkles className="h-4 w-4" /> Flow Snapshot
          </CardTitle>
          <CardDescription className="text-slate-300 space-y-1">
            <div>{copy.summary}</div>
            {conversationInsights.hasDiagnostic && (
              <div className="mt-2 space-y-1 text-xs">
                {conversationInsights.severity && (
                  <div className="flex items-center gap-2">
                    <AlertTriangle className={`h-3 w-3 ${severityLevel ? severityColors[severityLevel].split(' ')[0] : ''}`} />
                    <span>Severity: <strong>{conversationInsights.severity}</strong></span>
                  </div>
                )}
                {conversationInsights.urgency && (
                  <div className="flex items-center gap-2">
                    <Clock4 className="h-3 w-3" />
                    <span>Urgency: <strong>{conversationInsights.urgency}</strong></span>
                  </div>
                )}
                {conversationInsights.estimatedCost && (
                  <div className="flex items-center gap-2">
                    <DollarSign className="h-3 w-3" />
                    <span>Est. Cost: <strong>{conversationInsights.estimatedCost}</strong></span>
                  </div>
                )}
              </div>
            )}
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Incident Context */}
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
            Persona focus: <strong>{persona?.toUpperCase()}</strong>
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Safety Alerts */}
      {conversationInsights.safetyIssues > 0 && (
        <Card className="border border-red-500/30 bg-red-900/20 backdrop-blur">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-red-300">
              <Shield className="h-4 w-4 animate-pulse" /> Safety Alerts
            </CardTitle>
            <CardDescription className="text-red-200">
              {conversationInsights.safetyIssues} safety consideration{conversationInsights.safetyIssues > 1 ? 's' : ''} identified
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {/* Agent Status */}
      <Card className="border border-slate-800/70 bg-slate-900/60 backdrop-blur">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-semibold text-slate-100">
            <Activity className={`h-4 w-4 ${reasoningState.active ? "text-amber-300 animate-pulse" : "text-slate-400"}`} />
            {reasoningState.active ? "Agent reasoning" : "Agent standing by"}
          </CardTitle>
          <CardDescription className="text-slate-400">
            {reasoningState.active
              ? "Analyzing the latest messages to determine the next best action."
              : "Ready to assist with your request."}
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Flow Stage */}
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

      {/* Next Steps from Conversation */}
      <Card className="mt-auto border border-slate-800/70 bg-slate-900/60 backdrop-blur">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-semibold text-slate-100">
            <FileText className="h-4 w-4 text-slate-300" /> Next Steps
          </CardTitle>
          <CardDescription className="text-slate-400">
            {conversationInsights.nextSteps.length > 0 ? (
              <ul className="mt-2 space-y-1 text-xs">
                {conversationInsights.nextSteps.map((step, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-emerald-400">•</span>
                    <span className="flex-1">{step}</span>
                  </li>
                ))}
              </ul>
            ) : (
              copy.next
            )}
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}

export const AIContextPanel = memo(AIContextPanelComponent);
