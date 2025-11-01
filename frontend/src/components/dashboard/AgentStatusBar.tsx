import React, { memo } from "react";
import { Brain, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";

type Props = {
  persona?: string;
  flowStage?: string | null;
  reasoningActive?: boolean;
  className?: string;
};

const personaLabel = (persona?: string) => {
  switch (persona) {
    case "tenant":
      return "Tenant Guide";
    case "contractor":
      return "Contractor Coordinator";
    case "landlord":
    default:
      return "PropertyManager";
  }
};

function AgentStatusBarComponent({ persona, flowStage, reasoningActive, className }: Props) {
  const label = personaLabel(persona);
  const stageChip = flowStage ? flowStage.replace(/\./g, " → ") : "Idle";

  return (
    <div
      className={`flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-300 backdrop-blur-sm ${className ?? ""}`.trim()}
    >
      <div className="flex items-center gap-2">
        <Brain className="h-4 w-4 text-emerald-400" />
        <span className="font-medium text-slate-100">AI Persona: {label}</span>
        <Badge variant="secondary" className="bg-slate-800/80 text-slate-200">
          Stage · {stageChip || "Idle"}
        </Badge>
      </div>
      <div className="flex items-center gap-2">
        <Zap className={`h-4 w-4 ${reasoningActive ? "text-amber-400 animate-pulse" : "text-slate-500"}`} />
        <span>{reasoningActive ? "Reasoning active" : "Monitoring conversation"}</span>
      </div>
    </div>
  );
}

export const AgentStatusBar = memo(AgentStatusBarComponent);
