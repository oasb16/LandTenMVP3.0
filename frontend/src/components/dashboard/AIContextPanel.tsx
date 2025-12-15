import React, { memo, useMemo, useState } from "react";
import { Activity, Clock4, Sparkles, Workflow, AlertTriangle, FileText, Shield, DollarSign, ChevronDown, TrendingUp, Target, Zap, CheckCircle2, AlertCircle, Clock, User, Calendar } from "lucide-react";
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

// Calculate risk score (0-100)
function calculateRiskScore(severity?: string, urgency?: string): number {
  const severityScores: Record<string, number> = {
    low: 20,
    medium: 40,
    high: 70,
    urgent: 90,
    emergency: 100,
  };

  const urgencyScores: Record<string, number> = {
    low: 10,
    routine: 20,
    normal: 30,
    urgent: 70,
    critical: 90,
    emergency: 100,
  };

  const sevScore = severity ? severityScores[severity.toLowerCase()] || 40 : 40;
  const urgScore = urgency ? urgencyScores[urgency.toLowerCase()] || 30 : 30;

  return Math.round((sevScore * 0.6) + (urgScore * 0.4));
}

// Extract action items from parsed data
function extractActionItems(conversationInsights: any, stageKey: string) {
  const actions = [];

  // Stage-specific actions
  if (stageKey === "discovery") {
    actions.push({
      id: 1,
      priority: "high",
      title: "Upload diagnostic photos",
      status: conversationInsights.photoCount > 0 ? "completed" : "pending",
      assignee: "Tenant",
      eta: "ASAP",
    });
    actions.push({
      id: 2,
      priority: "high",
      title: "Confirm incident location & access",
      status: "pending",
      assignee: "Tenant",
      eta: "24h",
    });
  } else if (stageKey === "job") {
    actions.push({
      id: 3,
      priority: "critical",
      title: "Review contractor bids",
      status: "pending",
      assignee: "Property Manager",
      eta: "48h",
    });
    actions.push({
      id: 4,
      priority: "medium",
      title: "Schedule site inspection",
      status: "pending",
      assignee: "Contractor",
      eta: "72h",
    });
  } else if (stageKey === "approval") {
    actions.push({
      id: 5,
      priority: "critical",
      title: "Obtain landlord approval",
      status: "pending",
      assignee: "Property Manager",
      eta: "48h",
    });
  }

  // Safety-driven actions
  if (conversationInsights.safetyIssues > 0) {
    actions.unshift({
      id: 0,
      priority: "critical",
      title: "Address safety hazards immediately",
      status: "in_progress",
      assignee: "All Parties",
      eta: "IMMEDIATE",
    });
  }

  // Add parsed next steps
  conversationInsights.nextSteps.forEach((step: string, idx: number) => {
    actions.push({
      id: 100 + idx,
      priority: "medium",
      title: step,
      status: "pending",
      assignee: "AI Agent",
      eta: "TBD",
    });
  });

  return actions.slice(0, 6); // Top 6 actions
}

function AIContextPanelComponent() {
  const { activeChannel, flowState, reasoningState } = useStreamChat();
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["actions", "metrics"])
  );

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  const incidentId = useMemo(() => {
    const data = activeChannel?.data as Record<string, unknown> | undefined;
    const flowMeta = (data?.flow_state as Record<string, unknown> | undefined) ?? {};
    return (flowMeta.incidentId as string | undefined) ?? flowState?.incidentId ?? null;
  }, [activeChannel?.data, flowState?.incidentId]);

  const persona = useMemo(() => {
    const data = activeChannel?.data as Record<string, unknown> | undefined;
    return (data?.persona as string | undefined) ?? flowState?.persona ?? "tenant";
  }, [activeChannel?.data, flowState?.persona]);

  const stageKey = formatStageKey(flowState?.stage);
  const copy = STAGE_COPY[stageKey] ?? fallbackStageCopy;

  // Parse conversation insights
  const conversationInsights = useMemo(() => {
    if (!activeChannel?.state?.messages) {
      return {
        hasDiagnostic: false,
        severity: null,
        urgency: null,
        estimatedCost: null,
        safetyIssues: 0,
        nextSteps: [],
        photoCount: 0,
        description: null,
      };
    }

    const messages = activeChannel.state.messages;
    let severity = null;
    let urgency = null;
    let estimatedCost = null;
    let safetyIssues = 0;
    const nextStepsSet = new Set<string>();
    let photoCount = 0;
    let description = null;
    let hasDiagnostic = false;

    // Parse messages from most recent backwards
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      const text = msg.text || "";
      const metadata = (msg as any).metadata || {};

      const diagnosticData = parseDiagnosticData(text);

      if (diagnosticData.hasDiagnostic) {
        hasDiagnostic = true;

        if (!severity && diagnosticData.diagnosticResult?.severity) {
          severity = diagnosticData.diagnosticResult.severity;
        }
        if (!severity && metadata.severity) {
          severity = metadata.severity;
        }

        if (!urgency && diagnosticData.diagnosticResult?.urgency) {
          urgency = diagnosticData.diagnosticResult.urgency;
        }
        if (!urgency && metadata.urgency) {
          urgency = metadata.urgency;
        }

        if (!estimatedCost && diagnosticData.diagnosticResult?.estimatedCost) {
          estimatedCost = diagnosticData.diagnosticResult.estimatedCost;
        }

        if (!description && diagnosticData.diagnosticResult?.description) {
          description = diagnosticData.diagnosticResult.description;
        }

        if (diagnosticData.safetyConsiderations && diagnosticData.safetyConsiderations.length > 0) {
          safetyIssues = Math.max(safetyIssues, diagnosticData.safetyConsiderations.length);
        }

        if (diagnosticData.nextSteps && diagnosticData.nextSteps.length > 0) {
          diagnosticData.nextSteps.forEach((step) => nextStepsSet.add(step));
        }
      }

      // Count photos
      if (msg.attachments && msg.attachments.length > 0) {
        photoCount += msg.attachments.length;
      }
    }

    return {
      hasDiagnostic,
      severity,
      urgency,
      estimatedCost,
      safetyIssues,
      nextSteps: Array.from(nextStepsSet),
      photoCount,
      description,
    };
  }, [activeChannel?.state?.messages]);

  const severityLevel = determineSeverity(conversationInsights.severity, conversationInsights.urgency);

  const riskScore = calculateRiskScore(conversationInsights.severity, conversationInsights.urgency);

  const actionItems = extractActionItems(conversationInsights, stageKey);

  const severityColors: Record<string, string> = {
    low: "text-emerald-400 border-emerald-500/30 bg-emerald-900/20",
    medium: "text-amber-400 border-amber-500/30 bg-amber-900/20",
    high: "text-orange-400 border-orange-500/30 bg-orange-900/20",
    urgent: "text-red-400 border-red-500/30 bg-red-900/20",
  };
  const severityConfig = severityLevel ? severityColors[severityLevel] : "text-slate-400 border-slate-700 bg-slate-900/70";

  const priorityConfig: Record<string, { color: string; icon: any }> = {
    critical: { color: "text-red-400", icon: <AlertTriangle className="h-3 w-3 sm:h-3.5 sm:w-3.5 animate-pulse" /> },
    high: { color: "text-orange-400", icon: <AlertCircle className="h-3 w-3 sm:h-3.5 sm:w-3.5" /> },
    medium: { color: "text-amber-400", icon: <Clock className="h-3 w-3 sm:h-3.5 sm:w-3.5" /> },
    low: { color: "text-emerald-400", icon: <CheckCircle2 className="h-3 w-3 sm:h-3.5 sm:w-3.5" /> },
  };

  const statusConfig: Record<string, { color: string; label: string }> = {
    completed: { color: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30", label: "Done" },
    in_progress: { color: "bg-amber-500/20 text-amber-300 border-amber-500/30", label: "Active" },
    pending: { color: "bg-slate-500/20 text-slate-300 border-slate-500/30", label: "Pending" },
  };

  return (
    <div className="flex-1 min-h-0 w-full overflow-y-auto overflow-x-hidden px-2 sm:px-3 py-3 sm:py-4 space-y-2 sm:space-y-3" style={{ WebkitOverflowScrolling: 'touch' }}>

      {/* Incident Timeline */}
      {incidentId && flowState?.stage && (
        <IncidentTimeline
          currentStage={stageKey}
          incidentId={incidentId as string}
          compact={true}
        />
      )}

      {/* Critical Metrics Overview */}
      {conversationInsights.hasDiagnostic && (
        <Card className={`border ${severityConfig} backdrop-blur-sm`}>
          <CardHeader className="p-2.5 sm:p-4">
            <CardTitle className="flex items-center gap-2 text-sm sm:text-base font-bold text-slate-50">
              <Target className="h-4 w-4 sm:h-5 sm:w-5" />
              Incident Intelligence
            </CardTitle>
            <div className="mt-2 sm:mt-3 space-y-2">
              {/* Risk Score */}
              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/50 border border-slate-700/50">
                <div className="flex items-center gap-2">
                  <TrendingUp className={`h-4 w-4 ${riskScore >= 70 ? 'text-red-400' : riskScore >= 40 ? 'text-amber-400' : 'text-emerald-400'}`} />
                  <span className="text-xs sm:text-sm text-slate-300 font-medium">Risk Score</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-24 sm:w-32 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${riskScore >= 70 ? 'bg-red-500' : riskScore >= 40 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                      style={{ width: `${riskScore}%` }}
                    />
                  </div>
                  <span className={`text-sm sm:text-base font-bold ${riskScore >= 70 ? 'text-red-400' : riskScore >= 40 ? 'text-amber-400' : 'text-emerald-400'}`}>
                    {riskScore}
                  </span>
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 gap-2">
                <div className="flex flex-col gap-0.5 p-2 rounded-lg bg-slate-800/30 border border-slate-700/30">
                  <span className="text-[10px] sm:text-xs text-slate-400">Severity</span>
                  <span className={`text-xs sm:text-sm font-bold capitalize ${severityLevel ? severityColors[severityLevel].split(' ')[0] : 'text-slate-300'}`}>
                    {conversationInsights.severity || "N/A"}
                  </span>
                </div>
                <div className="flex flex-col gap-0.5 p-2 rounded-lg bg-slate-800/30 border border-slate-700/30">
                  <span className="text-[10px] sm:text-xs text-slate-400">Urgency</span>
                  <span className="text-xs sm:text-sm font-bold capitalize text-slate-200">
                    {conversationInsights.urgency || "N/A"}
                  </span>
                </div>
                <div className="flex flex-col gap-0.5 p-2 rounded-lg bg-slate-800/30 border border-slate-700/30">
                  <span className="text-[10px] sm:text-xs text-slate-400">Est. Cost</span>
                  <span className="text-xs sm:text-sm font-bold text-emerald-300">
                    ${conversationInsights.estimatedCost || "TBD"}
                  </span>
                </div>
                <div className="flex flex-col gap-0.5 p-2 rounded-lg bg-slate-800/30 border border-slate-700/30">
                  <span className="text-[10px] sm:text-xs text-slate-400">Photos</span>
                  <span className="text-xs sm:text-sm font-bold text-slate-200">
                    {conversationInsights.photoCount}
                  </span>
                </div>
              </div>
            </div>
          </CardHeader>
        </Card>
      )}

      {/* Safety Intelligence */}
      {conversationInsights.safetyIssues > 0 && (
        <Card className="border border-red-500/40 bg-red-900/30 backdrop-blur-sm">
          <CardHeader className="p-2.5 sm:p-4">
            <CardTitle className="flex items-center gap-2 text-sm sm:text-base font-bold text-red-100">
              <Shield className="h-4 w-4 sm:h-5 sm:w-5 animate-pulse" />
              Safety Intelligence
            </CardTitle>
            <div className="mt-2 space-y-1.5">
              <div className="flex items-center justify-between p-2 rounded-lg bg-red-950/50 border border-red-500/30">
                <span className="text-xs sm:text-sm text-red-100 font-medium">Active Safety Alerts</span>
                <span className="text-lg sm:text-xl font-bold text-red-300">{conversationInsights.safetyIssues}</span>
              </div>
              <p className="text-[10px] sm:text-xs text-red-200 leading-relaxed">
                Critical safety considerations identified. Immediate attention required before proceeding with standard workflow.
              </p>
            </div>
          </CardHeader>
        </Card>
      )}

      {/* Action Center */}
      {actionItems.length > 0 && (
        <Card className="border border-slate-800/70 bg-slate-900/60 backdrop-blur-sm">
          <button
            onClick={() => toggleSection("actions")}
            className="w-full text-left"
          >
            <CardHeader className="p-2.5 sm:p-4">
              <CardTitle className="flex items-center justify-between text-xs sm:text-sm font-bold text-slate-100">
                <div className="flex items-center gap-1.5 sm:gap-2">
                  <Zap className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-amber-400" />
                  Action Center
                  <span className="text-[10px] sm:text-xs text-slate-400 font-normal">({actionItems.length} items)</span>
                </div>
                <ChevronDown
                  className={`h-3.5 w-3.5 sm:h-4 sm:w-4 transition-transform ${expandedSections.has("actions") ? "rotate-180" : ""}`}
                />
              </CardTitle>
            </CardHeader>
          </button>
          {expandedSections.has("actions") && (
            <div className="px-2.5 sm:px-4 pb-2.5 sm:pb-4 space-y-1.5">
              {actionItems.map((action) => (
                <div
                  key={action.id}
                  className="flex items-start gap-2 p-2 rounded-lg bg-slate-800/40 border border-slate-700/40 hover:bg-slate-800/60 transition"
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {priorityConfig[action.priority]?.icon}
                  </div>
                  <div className="flex-1 min-w-0 space-y-1">
                    <p className="text-[10px] sm:text-xs text-slate-200 font-medium">{action.title}</p>
                    <div className="flex items-center gap-2 text-[9px] sm:text-[10px] text-slate-400">
                      <span className="flex items-center gap-1">
                        <User className="h-2.5 w-2.5" />
                        {action.assignee}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="h-2.5 w-2.5" />
                        {action.eta}
                      </span>
                    </div>
                  </div>
                  <div className={`flex-shrink-0 px-1.5 py-0.5 rounded text-[9px] sm:text-[10px] font-semibold border ${statusConfig[action.status]?.color}`}>
                    {statusConfig[action.status]?.label}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Performance Metrics */}
      <Card className="border border-slate-800/70 bg-slate-900/60 backdrop-blur-sm">
        <button
          onClick={() => toggleSection("metrics")}
          className="w-full text-left"
        >
          <CardHeader className="p-2.5 sm:p-4">
            <CardTitle className="flex items-center justify-between text-xs sm:text-sm font-bold text-slate-100">
              <div className="flex items-center gap-1.5 sm:gap-2">
                <Activity className={`h-3.5 w-3.5 sm:h-4 sm:w-4 ${reasoningState.active ? "text-amber-300 animate-pulse" : "text-slate-400"}`} />
                Performance Metrics
              </div>
              <ChevronDown
                className={`h-3.5 w-3.5 sm:h-4 sm:w-4 transition-transform ${expandedSections.has("metrics") ? "rotate-180" : ""}`}
              />
            </CardTitle>
          </CardHeader>
        </button>
        {expandedSections.has("metrics") && (
          <div className="px-2.5 sm:px-4 pb-2.5 sm:pb-4">
            <div className="grid grid-cols-2 gap-2">
              <div className="p-2 rounded-lg bg-slate-800/30 border border-slate-700/30">
                <p className="text-[10px] sm:text-xs text-slate-400">Stage</p>
                <p className="text-xs sm:text-sm font-bold text-indigo-300 capitalize mt-0.5">{copy.label}</p>
              </div>
              <div className="p-2 rounded-lg bg-slate-800/30 border border-slate-700/30">
                <p className="text-[10px] sm:text-xs text-slate-400">AI Status</p>
                <p className={`text-xs sm:text-sm font-bold mt-0.5 ${reasoningState.active ? 'text-amber-300' : 'text-emerald-300'}`}>
                  {reasoningState.active ? "Analyzing" : "Ready"}
                </p>
              </div>
              <div className="p-2 rounded-lg bg-slate-800/30 border border-slate-700/30">
                <p className="text-[10px] sm:text-xs text-slate-400">Incident ID</p>
                <p className="text-xs sm:text-sm font-bold text-emerald-300 font-mono mt-0.5">
                  {incidentId ? String(incidentId).slice(-8) : "N/A"}
                </p>
              </div>
              <div className="p-2 rounded-lg bg-slate-800/30 border border-slate-700/30">
                <p className="text-[10px] sm:text-xs text-slate-400">Persona</p>
                <p className="text-xs sm:text-sm font-bold text-slate-200 uppercase mt-0.5">{persona}</p>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Strategic Guidance */}
      <Card className="border border-emerald-500/20 bg-slate-900/70 backdrop-blur-sm">
        <CardHeader className="p-2.5 sm:p-4">
          <CardTitle className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm font-bold text-emerald-200">
            <Sparkles className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            Strategic Guidance
          </CardTitle>
          <CardDescription className="text-[10px] sm:text-xs text-slate-300 mt-1.5 sm:mt-2 leading-relaxed">
            {copy.next}
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}

export const AIContextPanel = memo(AIContextPanelComponent);
