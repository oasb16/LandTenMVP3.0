import { AnimatePresence, motion } from "framer-motion";
import React from "react";

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
  const normalizedStage = normaliseStage(stage);
  const gradient = normalizedStage ? STAGE_STYLES[normalizedStage] : "from-slate-700 via-slate-600 to-slate-800 text-slate-100";
  const tone = getTone(persona);

  const displayText =
    reasoningLabel && (reasoningStage || stage)
      ? `🧠 Agent is reasoning (flow: ${reasoningStage || stage})`
      : normalizedStage
        ? `🧠 ${tone} • Flow Stage: ${stage}`
        : null;

  return (
    <AnimatePresence mode="wait">
      {displayText ? (
        <motion.div
          key={`${displayText}-${gradient}`}
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          className={`w-full border-b border-white/5 bg-gradient-to-r px-3 py-2 text-sm font-medium tracking-tight transition-[background] duration-500 ${gradient}`}
        >
          {displayText}
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
