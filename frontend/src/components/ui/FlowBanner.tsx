import { AnimatePresence, motion } from "framer-motion";
import React from "react";

type Props = {
  stage?: string;
  persona?: string;
  reasoningLabel?: string | null;
  reasoningStage?: string | null;
};

const STAGE_STYLES: Record<string, string> = {
  incident: "from-rose-900/90 via-rose-800/70 to-rose-950/95 text-rose-100",
  discovery: "from-amber-900/90 via-amber-800/70 to-amber-950/95 text-amber-100",
  job: "from-indigo-900/90 via-indigo-800/70 to-slate-950/95 text-indigo-100",
  approval: "from-emerald-900/90 via-emerald-800/70 to-emerald-950/95 text-emerald-100",
  completion: "from-emerald-800/90 via-teal-700/70 to-slate-950/95 text-emerald-50",
  policy_violation: "from-red-950 via-rose-900 to-rose-950 text-rose-100",
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
  const gradient = normalizedStage ? STAGE_STYLES[normalizedStage] : "from-slate-900 via-slate-900 to-slate-950 text-slate-100";
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
