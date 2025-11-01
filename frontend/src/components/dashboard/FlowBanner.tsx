"use client";

interface FlowState {
  type: "incident" | "discovery" | "job" | "approval" | "completion" | "general" | null;
  stage: string | null;
  incident_id?: string;
  job_id?: string;
  metadata?: Record<string, any>;
}

interface FlowBannerProps {
  flowState: FlowState;
}

export function FlowBanner({ flowState }: FlowBannerProps) {
  if (!flowState.type || flowState.type === "general") {
    return null;
  }

  // Get flow type emoji and color
  const getFlowStyle = () => {
    switch (flowState.type) {
      case "incident":
        return {
          emoji: "🔧",
          label: "Incident Report",
          color: "border-red-500 bg-red-950/30 text-red-400",
        };
      case "discovery":
        return {
          emoji: "📋",
          label: "Discovery Mode",
          color: "border-blue-500 bg-blue-950/30 text-blue-400",
        };
      case "job":
        return {
          emoji: "🔨",
          label: "Job Processing",
          color: "border-yellow-500 bg-yellow-950/30 text-yellow-400",
        };
      case "approval":
        return {
          emoji: "✅",
          label: "Approval Required",
          color: "border-purple-500 bg-purple-950/30 text-purple-400",
        };
      case "completion":
        return {
          emoji: "🎉",
          label: "Completed",
          color: "border-green-500 bg-green-950/30 text-green-400",
        };
      default:
        return {
          emoji: "💬",
          label: "Active Flow",
          color: "border-slate-500 bg-slate-950/30 text-slate-400",
        };
    }
  };

  const style = getFlowStyle();

  return (
    <div className={`border-t ${style.color} px-4 py-2 animate-pulse-subtle`}>
      <div className="flex items-center gap-3">
        <span className="text-2xl">{style.emoji}</span>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold">{style.label}</span>
            {flowState.stage && (
              <>
                <span className="opacity-50">→</span>
                <span className="text-sm opacity-75">{flowState.stage}</span>
              </>
            )}
          </div>
          {(flowState.incident_id || flowState.job_id) && (
            <div className="text-xs opacity-60 mt-0.5">
              {flowState.incident_id && `Incident: ${flowState.incident_id}`}
              {flowState.incident_id && flowState.job_id && " • "}
              {flowState.job_id && `Job: ${flowState.job_id}`}
            </div>
          )}
        </div>
        <div className="h-2 w-2 rounded-full bg-current animate-pulse" />
      </div>
    </div>
  );
}
