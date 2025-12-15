import { AnimatePresence, motion } from "framer-motion";
import React, { useMemo } from "react";
import { AlertTriangle, Shield, DollarSign, Clock } from "lucide-react";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";
import { parseDiagnosticData } from "../ai/parseDiagnosticData";

type Props = {
  stage?: string;
  persona?: string;
  reasoningLabel?: string | null;
  reasoningStage?: string | null;
};

const STAGE_STYLES: Record<string, string> = {
  incident: "from-slate-700/90 via-slate-600/70 to-slate-800/95 text-slate-100",
  discovery: "from-blue-900/90 via-blue-800/70 to-slate-900/95 text-blue-100",
  job: "from-blue-800/90 via-blue-700/70 to-slate-800/95 text-blue-100",
  approval: "from-blue-700/90 via-blue-600/70 to-slate-700/95 text-blue-50",
  completion: "from-blue-600/90 via-cyan-600/70 to-slate-700/95 text-blue-50",
  policy_violation: "from-slate-800 via-slate-700 to-slate-900 text-slate-100",
  // Severity-based gradients
  low: "from-emerald-700/90 via-emerald-600/70 to-slate-800/95 text-emerald-100",
  medium: "from-amber-700/90 via-amber-600/70 to-slate-800/95 text-amber-100",
  high: "from-orange-700/90 via-orange-600/70 to-slate-800/95 text-orange-100",
  urgent: "from-red-700/90 via-red-600/70 to-slate-800/95 text-red-100",
};

const getTone = (persona?: string) => {
  switch (persona) {
    case "tenant":
      return "Empathetic assistance";
    case "landlord":
      return "Actionable insight";
    case "contractor":
      return "Operational update";
    default:
      return "Coordinated intelligence";
  }
};

const normaliseStage = (stage?: string) => stage?.split(".")[0] ?? undefined;

export default function FlowBanner({ stage, persona, reasoningLabel, reasoningStage }: Props) {
  const { activeChannel } = useStreamChat();
  const normalizedStage = normaliseStage(stage);
  const tone = getTone(persona);

  // Parse conversation insights
  const insights = useMemo(() => {
    if (!activeChannel?.state?.messages) {
      return { severity: null, urgency: null, estimatedCost: null, hasSafety: false };
    }

    const messages = activeChannel.state.messages;
    let severity = null;
    let urgency = null;
    let estimatedCost = null;
    let hasSafety = false;

    // Parse recent messages (last 10)
    for (let i = messages.length - 1; i >= Math.max(0, messages.length - 10); i--) {
      const msg = messages[i];
      const text = msg.text || "";
      const metadata = (msg as any).metadata || {};

      const diagnosticData = parseDiagnosticData(text);

      if (diagnosticData.hasDiagnostic) {
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

        if (!hasSafety && diagnosticData.safetyConsiderations && diagnosticData.safetyConsiderations.length > 0) {
          hasSafety = true;
        }
      }
    }

    return { severity, urgency, estimatedCost, hasSafety };
  }, [activeChannel?.state?.messages]);

  // Choose gradient based on severity if available, otherwise use stage
  const severityKey = insights.severity?.toLowerCase();
  const gradient = severityKey && STAGE_STYLES[severityKey]
    ? STAGE_STYLES[severityKey]
    : normalizedStage
      ? STAGE_STYLES[normalizedStage]
      : "from-slate-700 via-slate-600 to-slate-800 text-slate-100";

  const displayText =
    reasoningLabel && (reasoningStage || stage)
      ? `🧠 Agent is reasoning (flow: ${reasoningStage || stage})`
      : normalizedStage
        ? `🧠 ${tone} • Flow Stage: ${stage}`
        : null;

  const hasInsights = insights.severity || insights.urgency || insights.estimatedCost || insights.hasSafety;

  return (
    <AnimatePresence mode="wait">
      {displayText ? (
        <motion.div
          key={`${displayText}-${gradient}`}
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          className={`w-full border-b border-white/5 bg-gradient-to-r transition-[background] duration-500 ${gradient}`}
        >
          {/* Main banner text */}
          <div className="px-3 py-2 text-sm font-medium tracking-tight">
            {displayText}
          </div>

          {/* Diagnostic insights row */}
          {hasInsights && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              transition={{ duration: 0.3 }}
              className="border-t border-white/10 px-3 py-1.5 flex items-center gap-4 text-xs"
            >
              {insights.severity && (
                <div className="flex items-center gap-1">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  <span className="font-medium">Severity:</span>
                  <span className="capitalize">{insights.severity}</span>
                </div>
              )}

              {insights.urgency && (
                <div className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  <span className="font-medium">Urgency:</span>
                  <span className="capitalize">{insights.urgency}</span>
                </div>
              )}

              {insights.estimatedCost && (
                <div className="flex items-center gap-1">
                  <DollarSign className="h-3.5 w-3.5" />
                  <span className="font-medium">Est. Cost:</span>
                  <span>{insights.estimatedCost}</span>
                </div>
              )}

              {insights.hasSafety && (
                <div className="flex items-center gap-1 text-red-300">
                  <Shield className="h-3.5 w-3.5 animate-pulse" />
                  <span className="font-medium">Safety Alert</span>
                </div>
              )}
            </motion.div>
          )}
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
