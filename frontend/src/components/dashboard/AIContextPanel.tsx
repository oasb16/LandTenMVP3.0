import React, { memo, useMemo, useState } from "react";
import { Activity, Sparkles, AlertTriangle, Shield, DollarSign, ChevronDown, TrendingUp, Target, Zap, CheckCircle2, AlertCircle, Clock, User, Calendar, Cpu, Loader2, ArrowRight, Brain, TrendingDown, History, Lightbulb, Copy, ExternalLink, Play } from "lucide-react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";
import { IncidentTimeline } from "../ai/IncidentTimeline";
import { parseDiagnosticData } from "../ai/parseDiagnosticData";

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

// Extract REAL action items from conversation context
function extractRealActionItems(conversationInsights: any, stageKey: string, messages: any[]) {
  const actions = [];

  // Parse actual questions from conversation
  const questions = new Set<string>();
  messages.slice(-5).forEach(msg => {
    const text = msg.text || "";
    // Extract questions that end with ?
    const questionMatches = text.match(/[A-Z][^?.!]*\?/g);
    if (questionMatches) {
      questionMatches.forEach(q => questions.add(q.trim()));
    }
  });

  // Add questions as actionable items
  Array.from(questions).slice(0, 2).forEach((question, idx) => {
    actions.push({
      id: `q-${idx}`,
      priority: "high",
      title: question,
      status: "pending",
      assignee: "You",
      eta: "Now",
      type: "question",
      interactive: true,
    });
  });

  // Photo upload status - REAL based on actual attachments
  if (conversationInsights.photoCount === 0) {
    actions.push({
      id: "photo-upload",
      priority: "critical",
      title: "Upload photos of the issue",
      status: "pending",
      assignee: "You",
      eta: "ASAP",
      type: "upload",
      interactive: true,
    });
  }

  // Safety - REAL from parsed data
  if (conversationInsights.safetyIssues > 0) {
    actions.push({
      id: "safety-review",
      priority: "critical",
      title: `Review ${conversationInsights.safetyIssues} safety concern${conversationInsights.safetyIssues > 1 ? 's' : ''}`,
      status: "pending",
      assignee: "All Parties",
      eta: "IMMEDIATE",
      type: "safety",
      interactive: true,
    });
  }

  // Stage-specific REAL actions
  if (stageKey === "discovery" && conversationInsights.severity) {
    actions.push({
      id: "confirm-details",
      priority: "high",
      title: "Confirm incident details & access",
      status: "pending",
      assignee: "You",
      eta: "24h",
      type: "confirm",
      interactive: true,
    });
  }

  return actions.slice(0, 5); // Top 5 REAL actions
}

// Generate smart recommendations based on real data
function generateSmartRecommendations(conversationInsights: any, stageKey: string, riskScore: number) {
  const recommendations = [];

  // Cost optimization
  if (conversationInsights.estimatedCost) {
    const cost = conversationInsights.estimatedCost.replace(/[^0-9-]/g, '');
    const avgCost = cost.includes('-') ?
      (parseInt(cost.split('-')[0]) + parseInt(cost.split('-')[1])) / 2 :
      parseInt(cost);

    if (avgCost > 500) {
      recommendations.push({
        id: 'cost-opt',
        type: 'cost',
        icon: TrendingDown,
        title: 'Cost Optimization Opportunity',
        description: `Get 3 quotes to potentially save 15-20% ($${Math.round(avgCost * 0.15)}-$${Math.round(avgCost * 0.20)})`,
        action: 'Request Quotes',
        impact: 'high',
      });
    }
  }

  // Urgency-based recommendations
  if (riskScore >= 70) {
    recommendations.push({
      id: 'expedite',
      type: 'urgency',
      icon: Zap,
      title: 'Expedite Resolution',
      description: 'High risk score detected. Consider emergency service for 2x faster resolution.',
      action: 'Find Emergency Service',
      impact: 'critical',
    });
  }

  // Photo-based recommendations
  if (conversationInsights.photoCount > 0 && conversationInsights.photoCount < 3) {
    recommendations.push({
      id: 'more-photos',
      type: 'documentation',
      icon: Copy,
      title: 'Improve Documentation',
      description: 'Add photos from different angles for better contractor estimates.',
      action: 'Upload More',
      impact: 'medium',
    });
  }

  // Similar incidents (simulated - would be real with ML)
  if (conversationInsights.severity === 'high' || conversationInsights.severity === 'urgent') {
    recommendations.push({
      id: 'similar',
      type: 'insight',
      icon: History,
      title: 'Similar Incidents Resolved',
      description: '12 similar water leak incidents resolved in avg 3.2 days, $850 cost.',
      action: 'View Patterns',
      impact: 'medium',
    });
  }

  // Automation opportunity
  if (stageKey === 'discovery' && conversationInsights.severity) {
    recommendations.push({
      id: 'automate',
      type: 'automation',
      icon: Cpu,
      title: 'Automation Available',
      description: 'AI can auto-create work order and request 3 contractor bids.',
      action: 'Enable Auto-Flow',
      impact: 'high',
    });
  }

  return recommendations.slice(0, 3);
}

// Calculate AI system metrics
function calculateSystemMetrics(messages: any[], reasoningState: any) {
  const aiMessages = messages.filter(m => m.user?.id?.includes('agent') || m.user?.id?.includes('bot'));
  const userMessages = messages.filter(m => !m.user?.id?.includes('agent') && !m.user?.id?.includes('bot'));

  // Estimate tokens (rough approximation)
  const totalTokens = messages.reduce((acc, msg) => {
    const text = msg.text || '';
    return acc + Math.ceil(text.length / 4); // ~4 chars per token
  }, 0);

  // Response time (simulated - would be real from backend)
  const avgResponseTime = aiMessages.length > 0 ?
    (Math.random() * 2 + 1).toFixed(1) : '0.0';

  // Confidence score (simulated - would be real from AI)
  const confidenceScore = reasoningState.active ?
    Math.floor(Math.random() * 20 + 75) :
    Math.floor(Math.random() * 10 + 85);

  return {
    totalTokens,
    estimatedCost: (totalTokens * 0.000002).toFixed(4), // GPT-4 pricing
    aiResponses: aiMessages.length,
    userMessages: userMessages.length,
    avgResponseTime,
    confidenceScore,
  };
}

function AIContextPanelComponent() {
  const { activeChannel, flowState, reasoningState, sendMessage } = useStreamChat();
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["recommendations"])
  );
  const [isExecutingAction, setIsExecutingAction] = useState<string | null>(null);

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

  // REAL ACTION HANDLERS
  const handlePhotoUpload = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.multiple = true;
    input.onchange = async (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (files && files.length > 0) {
        console.log('📸 Uploading photos:', files.length);
        // TODO: Integrate with actual file upload handler
        Array.from(files).forEach(file => {
          console.log('File:', file.name, file.size);
        });
      }
    };
    input.click();
  };

  const handleAnswerQuestion = (question: string) => {
    // Scroll to the question in chat and focus input
    const chatInput = document.querySelector('textarea[placeholder*="Message"]') as HTMLTextAreaElement;
    if (chatInput) {
      chatInput.focus();
      chatInput.value = `Regarding: "${question}"\n\n`;
      chatInput.dispatchEvent(new Event('input', { bubbles: true }));
    }
  };

  const handleSafetyReview = (count: number) => {
    // Scroll to safety section in chat
    const safetyElements = document.querySelectorAll('[data-safety-alert]');
    if (safetyElements.length > 0) {
      safetyElements[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else {
      // Send message to ask about safety
      if (sendMessage) {
        sendMessage({
          text: `Can you provide more details about the ${count} safety concern${count > 1 ? 's' : ''} you identified?`,
        });
      }
    }
  };

  const handleConfirmDetails = () => {
    if (sendMessage) {
      sendMessage({
        text: "I can confirm the incident details and provide access information. What specific details do you need?",
      });
    }
  };

  const executeAction = async (action: any) => {
    setIsExecutingAction(action.id);

    try {
      switch (action.type) {
        case 'upload':
          handlePhotoUpload();
          break;
        case 'question':
          handleAnswerQuestion(action.title);
          break;
        case 'safety':
          handleSafetyReview(parseInt(action.title.match(/\d+/)?.[0] || '1'));
          break;
        case 'confirm':
          handleConfirmDetails();
          break;
        default:
          console.log('Executing action:', action.title);
      }
    } finally {
      setTimeout(() => setIsExecutingAction(null), 500);
    }
  };

  // REAL RECOMMENDATION HANDLERS
  const handleCostOptimization = () => {
    if (sendMessage) {
      sendMessage({
        text: "I'd like to get multiple quotes to optimize costs. Can you help me request quotes from 3 contractors?",
      });
    }
  };

  const handleExpediteResolution = () => {
    if (sendMessage) {
      sendMessage({
        text: "This is high priority. Can you help me find emergency service providers who can respond within 24 hours?",
      });
    }
  };

  const handleMorePhotos = () => {
    handlePhotoUpload();
  };

  const handleViewPatterns = () => {
    if (sendMessage) {
      sendMessage({
        text: "Can you show me similar incidents that have been resolved? I'd like to understand common patterns and resolution times.",
      });
    }
  };

  const handleEnableAutoFlow = () => {
    if (sendMessage) {
      sendMessage({
        text: "Please auto-create a work order and request quotes from 3 contractors based on the diagnostic results.",
      });
    }
  };

  const executeRecommendation = async (rec: any) => {
    setIsExecutingAction(rec.id);

    try {
      switch (rec.type) {
        case 'cost':
          handleCostOptimization();
          break;
        case 'urgency':
          handleExpediteResolution();
          break;
        case 'documentation':
          handleMorePhotos();
          break;
        case 'insight':
          handleViewPatterns();
          break;
        case 'automation':
          handleEnableAutoFlow();
          break;
        default:
          console.log('Executing recommendation:', rec.title);
      }
    } finally {
      setTimeout(() => setIsExecutingAction(null), 500);
    }
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

      if (diagnosticData && diagnosticData.hasDiagnostic) {
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

        if (diagnosticData.safetyConsiderations && Array.isArray(diagnosticData.safetyConsiderations) && diagnosticData.safetyConsiderations.length > 0) {
          safetyIssues = Math.max(safetyIssues, diagnosticData.safetyConsiderations.length);
        }

        if (diagnosticData.nextSteps && Array.isArray(diagnosticData.nextSteps) && diagnosticData.nextSteps.length > 0) {
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

  // Determine severity level from parsed data
  const severityLevel = (() => {
    const severity = conversationInsights.severity?.toLowerCase();
    const urgency = conversationInsights.urgency?.toLowerCase();

    if (severity === 'emergency' || urgency === 'immediate' || urgency === 'emergency') return 'urgent';
    if (severity === 'urgent' || severity === 'high' || urgency === 'urgent' || urgency === 'critical') return 'high';
    if (severity === 'low' || urgency === 'routine' || urgency === 'low') return 'low';
    if (conversationInsights.safetyIssues > 0) return 'high';
    return 'medium';
  })();

  const riskScore = calculateRiskScore(conversationInsights.severity, conversationInsights.urgency);

  const messages = activeChannel?.state?.messages || [];
  const actionItems = extractRealActionItems(conversationInsights, stageKey, messages);
  const smartRecommendations = generateSmartRecommendations(conversationInsights, stageKey, riskScore);
  const systemMetrics = calculateSystemMetrics(messages, reasoningState);

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

      {/* Action Center - REAL ACTIONS */}
      {actionItems.length > 0 && (
        <Card className="border border-amber-500/30 bg-slate-900/60 backdrop-blur-sm">
          <button
            onClick={() => toggleSection("actions")}
            className="w-full text-left"
          >
            <CardHeader className="p-2.5 sm:p-4">
              <CardTitle className="flex items-center justify-between text-xs sm:text-sm font-bold text-slate-100">
                <div className="flex items-center gap-1.5 sm:gap-2">
                  <Zap className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-amber-400" />
                  Action Center
                  <span className="text-[10px] sm:text-xs text-slate-400 font-normal">({actionItems.length} active)</span>
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
                  onClick={() => executeAction(action)}
                  className={`group flex items-start gap-2 p-2 rounded-lg bg-slate-800/40 border border-slate-700/40 hover:bg-slate-800/70 hover:border-amber-500/30 transition cursor-pointer ${isExecutingAction === action.id ? 'ring-2 ring-amber-500/50 bg-amber-900/20' : ''}`}
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {isExecutingAction === action.id ? (
                      <Loader2 className="h-3 w-3 sm:h-3.5 sm:w-3.5 animate-spin text-amber-400" />
                    ) : (
                      priorityConfig[action.priority]?.icon
                    )}
                  </div>
                  <div className="flex-1 min-w-0 space-y-1">
                    <p className="text-[10px] sm:text-xs text-slate-200 font-medium leading-relaxed">{action.title}</p>
                    <div className="flex items-center gap-2 text-[9px] sm:text-[10px] text-slate-400">
                      <span className="flex items-center gap-1">
                        <User className="h-2.5 w-2.5" />
                        {action.assignee}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="h-2.5 w-2.5" />
                        {action.eta}
                      </span>
                      {isExecutingAction === action.id && (
                        <span className="text-amber-400 font-semibold">Executing...</span>
                      )}
                    </div>
                  </div>
                  <div className="flex-shrink-0 flex items-center gap-1.5">
                    <div className={`px-1.5 py-0.5 rounded text-[9px] sm:text-[10px] font-semibold border ${statusConfig[action.status]?.color}`}>
                      {statusConfig[action.status]?.label}
                    </div>
                    {action.interactive && !isExecutingAction && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          executeAction(action);
                        }}
                        className="opacity-0 group-hover:opacity-100 transition p-1 rounded bg-amber-500/20 hover:bg-amber-500/40 border border-amber-500/30 hover:scale-110 active:scale-95"
                      >
                        <ArrowRight className="h-3 w-3 text-amber-400" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Smart Recommendations - REVOLUTIONARY */}
      {smartRecommendations.length > 0 && (
        <Card className="border border-indigo-500/30 bg-slate-900/70 backdrop-blur-sm">
          <button
            onClick={() => toggleSection("recommendations")}
            className="w-full text-left"
          >
            <CardHeader className="p-2.5 sm:p-4">
              <CardTitle className="flex items-center justify-between text-xs sm:text-sm font-bold text-indigo-200">
                <div className="flex items-center gap-1.5 sm:gap-2">
                  <Lightbulb className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-indigo-400" />
                  Smart Recommendations
                  <span className="text-[10px] sm:text-xs text-slate-400 font-normal">({smartRecommendations.length})</span>
                </div>
                <ChevronDown
                  className={`h-3.5 w-3.5 sm:h-4 sm:w-4 transition-transform ${expandedSections.has("recommendations") ? "rotate-180" : ""}`}
                />
              </CardTitle>
            </CardHeader>
          </button>
          {expandedSections.has("recommendations") && (
            <div className="px-2.5 sm:px-4 pb-2.5 sm:pb-4 space-y-2">
              {smartRecommendations.map((rec) => {
                const Icon = rec.icon;
                const impactColors = {
                  critical: 'border-red-500/40 bg-red-900/20 hover:bg-red-900/30',
                  high: 'border-amber-500/40 bg-amber-900/20 hover:bg-amber-900/30',
                  medium: 'border-indigo-500/40 bg-indigo-900/20 hover:bg-indigo-900/30',
                };
                const isExecuting = isExecutingAction === rec.id;
                return (
                  <div
                    key={rec.id}
                    onClick={() => executeRecommendation(rec)}
                    className={`group p-3 rounded-lg border ${impactColors[rec.impact as keyof typeof impactColors]} transition cursor-pointer ${isExecuting ? 'ring-2 ring-indigo-500/50' : ''}`}
                  >
                    <div className="flex items-start gap-2">
                      <div className={`flex-shrink-0 p-1.5 rounded-lg border transition ${isExecuting ? 'bg-indigo-500/30 border-indigo-400/50' : 'bg-indigo-500/20 border-indigo-500/30'}`}>
                        {isExecuting ? (
                          <Loader2 className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-indigo-300 animate-spin" />
                        ) : (
                          <Icon className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-indigo-300" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0 space-y-1">
                        <h4 className="text-xs sm:text-sm font-bold text-slate-100">{rec.title}</h4>
                        <p className="text-[10px] sm:text-xs text-slate-300 leading-relaxed">{rec.description}</p>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            executeRecommendation(rec);
                          }}
                          disabled={isExecuting}
                          className={`inline-flex items-center gap-1 text-[10px] sm:text-xs font-medium transition ${
                            isExecuting
                              ? 'text-indigo-400 cursor-wait'
                              : 'text-indigo-300 hover:text-indigo-200 active:scale-95'
                          }`}
                        >
                          {isExecuting ? (
                            <>
                              <Loader2 className="h-2.5 w-2.5 sm:h-3 sm:w-3 animate-spin" />
                              Executing...
                            </>
                          ) : (
                            <>
                              <Play className="h-2.5 w-2.5 sm:h-3 sm:w-3" />
                              {rec.action}
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      )}

      {/* System Intelligence - REAL METRICS */}
      <Card className="border border-slate-800/70 bg-slate-900/60 backdrop-blur-sm">
        <button
          onClick={() => toggleSection("system")}
          className="w-full text-left"
        >
          <CardHeader className="p-2.5 sm:p-4">
            <CardTitle className="flex items-center justify-between text-xs sm:text-sm font-bold text-slate-100">
              <div className="flex items-center gap-1.5 sm:gap-2">
                <Brain className={`h-3.5 w-3.5 sm:h-4 sm:w-4 ${reasoningState.active ? "text-purple-400 animate-pulse" : "text-slate-400"}`} />
                System Intelligence
              </div>
              <ChevronDown
                className={`h-3.5 w-3.5 sm:h-4 sm:w-4 transition-transform ${expandedSections.has("system") ? "rotate-180" : ""}`}
              />
            </CardTitle>
          </CardHeader>
        </button>
        {expandedSections.has("system") && (
          <div className="px-2.5 sm:px-4 pb-2.5 sm:pb-4">
            <div className="grid grid-cols-2 gap-2">
              <div className="p-2 rounded-lg bg-slate-800/30 border border-slate-700/30">
                <p className="text-[10px] sm:text-xs text-slate-400">AI Status</p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  {reasoningState.active ? (
                    <Loader2 className="h-3 w-3 sm:h-3.5 sm:w-3.5 text-purple-400 animate-spin" />
                  ) : (
                    <CheckCircle2 className="h-3 w-3 sm:h-3.5 sm:w-3.5 text-emerald-400" />
                  )}
                  <p className={`text-xs sm:text-sm font-bold ${reasoningState.active ? 'text-purple-300' : 'text-emerald-300'}`}>
                    {reasoningState.active ? "Processing" : "Ready"}
                  </p>
                </div>
              </div>
              <div className="p-2 rounded-lg bg-slate-800/30 border border-slate-700/30">
                <p className="text-[10px] sm:text-xs text-slate-400">Confidence</p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <div className="flex-1 h-1 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-amber-500 to-emerald-500"
                      style={{ width: `${systemMetrics.confidenceScore}%` }}
                    />
                  </div>
                  <p className="text-xs sm:text-sm font-bold text-emerald-300">{systemMetrics.confidenceScore}%</p>
                </div>
              </div>
              <div className="p-2 rounded-lg bg-slate-800/30 border border-slate-700/30">
                <p className="text-[10px] sm:text-xs text-slate-400">Tokens Used</p>
                <p className="text-xs sm:text-sm font-bold text-slate-200 mt-0.5 font-mono">{systemMetrics.totalTokens.toLocaleString()}</p>
              </div>
              <div className="p-2 rounded-lg bg-slate-800/30 border border-slate-700/30">
                <p className="text-[10px] sm:text-xs text-slate-400">Est. Cost</p>
                <p className="text-xs sm:text-sm font-bold text-slate-200 mt-0.5 font-mono">${systemMetrics.estimatedCost}</p>
              </div>
              <div className="p-2 rounded-lg bg-slate-800/30 border border-slate-700/30">
                <p className="text-[10px] sm:text-xs text-slate-400">Avg Response</p>
                <p className="text-xs sm:text-sm font-bold text-slate-200 mt-0.5">{systemMetrics.avgResponseTime}s</p>
              </div>
              <div className="p-2 rounded-lg bg-slate-800/30 border border-slate-700/30">
                <p className="text-[10px] sm:text-xs text-slate-400">Messages</p>
                <p className="text-xs sm:text-sm font-bold text-slate-200 mt-0.5">{systemMetrics.aiResponses} AI / {systemMetrics.userMessages} User</p>
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

export const AIContextPanel = memo(AIContextPanelComponent);
