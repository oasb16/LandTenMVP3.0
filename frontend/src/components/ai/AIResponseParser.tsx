import React, { memo, useMemo } from "react";
import { motion } from "framer-motion";
import {
  CheckCircle,
  Compass,
  FileCheck,
  Hammer,
  Megaphone,
  NotebookPen,
  ShieldCheck,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { ActionCard } from "./ActionCard";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type NextAction = {
  action: string;
  details?: string;
};

type AnalysisPayload = {
  summary?: string;
  next_actions?: NextAction[];
};

type RawAIResponse = {
  analysis?: AnalysisPayload;
};

const iconPicker = (label: string = ""): LucideIcon => {
  const normalized = label.toLowerCase();
  if (/(create|report|confirm|check|verify)/.test(normalized)) {
    return FileCheck;
  }
  if (/(notify|advise|inform|escalate|alert)/.test(normalized)) {
    return Megaphone;
  }
  if (/(prepare|document|summarize|note|record)/.test(normalized)) {
    return NotebookPen;
  }
  return Sparkles;
};

type Props = {
  data: RawAIResponse;
  stage?: string | null;
  incidentId?: string | null;
  persona?: string;
  onActionClick?: (actionText: string) => void | Promise<void>;
};

const normaliseStage = (stage?: string | null) => stage?.toLowerCase() ?? null;

const AIResponseParserComponent = ({ data, stage, incidentId, persona, onActionClick }: Props) => {
  const analysis: AnalysisPayload | null = data?.analysis ?? null;

  const actions = useMemo(() => analysis?.next_actions ?? [], [analysis?.next_actions]);
  const normalizedStage = normaliseStage(stage);

  // Handler for action button clicks
  const handleActionClick = async (title: string, desc?: string) => {
    if (!onActionClick) return;

    // Construct a contextual message from the action
    const actionMessage = desc
      ? `${title}: ${desc}`
      : title;

    await onActionClick(actionMessage);
  };

  const stageContext = useMemo(() => {
    if (!analysis) return null;
    if (!normalizedStage) return null;
    if (normalizedStage.includes("discovery")) {
      return <QuestionsCard incidentId={incidentId} persona={persona} />;
    }
    if (normalizedStage.includes("job")) {
      return <JobCard incidentId={incidentId} />;
    }
    if (normalizedStage.includes("approval")) {
      return <ApprovalCard incidentId={incidentId} persona={persona} />;
    }
    if (normalizedStage.includes("completion")) {
      return <CompletionCard incidentId={incidentId} />;
    }
    return null;
  }, [analysis, normalizedStage, incidentId, persona]);

  if (!analysis || (!analysis.summary && actions.length === 0)) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97, y: 4 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="flex w-full flex-col gap-4 rounded-3xl border border-emerald-500/20 bg-gradient-to-br from-slate-900/80 via-slate-900 to-slate-950 p-4 shadow-xl backdrop-blur-xl"
    >
      {analysis.summary && (
        <div className="flex items-start gap-3 text-sm text-slate-200">
          <Sparkles className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-300" />
          <p className="leading-relaxed">{analysis.summary}</p>
        </div>
      )}

      {stageContext}

      {actions.length > 0 && (
        <motion.div
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: {
              transition: {
                staggerChildren: 0.08,
              },
            },
          }}
          className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3"
        >
          {actions.map((item, index) => {
            const Icon = iconPicker(item.action);
            return (
              <motion.div
                key={`${item.action}-${index}`}
                variants={{
                  hidden: { opacity: 0, y: 8 },
                  visible: { opacity: 1, y: 0 },
                }}
              >
                <ActionCard
                  icon={Icon}
                  title={item.action}
                  desc={item.details}
                  index={index}
                  onClick={onActionClick ? handleActionClick : undefined}
                />
              </motion.div>
            );
          })}
        </motion.div>
      )}
    </motion.div>
  );
};

export const AIResponseParser = memo(AIResponseParserComponent);

const StageCardShell: React.FC<{
  icon: LucideIcon;
  title: string;
  description: string;
  tone?: "info" | "action" | "success";
}> = ({ icon: Icon, title, description, tone = "info" }) => {
  const toneStyles =
    tone === "success"
      ? "border-emerald-500/20 text-emerald-100"
      : tone === "action"
        ? "border-indigo-500/20 text-indigo-100"
        : "border-amber-500/20 text-amber-100";

  return (
    <Card className={`border ${toneStyles} bg-slate-900/70 shadow-inner`}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Icon className="h-4 w-4 flex-shrink-0" />
          {title}
        </CardTitle>
        <CardDescription className="text-xs text-slate-300">{description}</CardDescription>
      </CardHeader>
    </Card>
  );
};

const QuestionsCard: React.FC<{ incidentId?: string | null; persona?: string }> = ({ incidentId, persona }) => (
  <StageCardShell
    icon={Compass}
    title="Discovery In Progress"
    description={
      incidentId
        ? `Guiding ${persona === "tenant" ? "tenant" : "participant"} through discovery for incident ${incidentId}.`
        : "The assistant is gathering more details to scope this incident."
    }
  />
);

const JobCard: React.FC<{ incidentId?: string | null }> = ({ incidentId }) => (
  <StageCardShell
    icon={Hammer}
    tone="action"
    title="Work Order Preparation"
    description={
      incidentId
        ? `Drafting work order for incident ${incidentId}. Review estimates and assign a contractor.`
        : "Creating job ticket based on the latest discovery answers."
    }
  />
);

const ApprovalCard: React.FC<{ incidentId?: string | null; persona?: string }> = ({ incidentId, persona }) => (
  <StageCardShell
    icon={ShieldCheck}
    tone="action"
    title="Awaiting Approval"
    description={
      incidentId
        ? `${persona === "landlord" ? "You" : "Landlord"} can approve the proposed fix for ${incidentId}.`
        : "The assistant needs confirmation before scheduling the repair."
    }
  />
);

const CompletionCard: React.FC<{ incidentId?: string | null }> = ({ incidentId }) => (
  <StageCardShell
    icon={CheckCircle}
    tone="success"
    title="Resolution Logged"
    description={
      incidentId
        ? `Incident ${incidentId} is marked as resolved. Archiving conversation and updating metrics.`
        : "Incident marked complete. Closing the active flow."
    }
  />
);
