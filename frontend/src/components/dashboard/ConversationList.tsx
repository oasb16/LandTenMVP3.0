import React, { memo, useMemo, useState } from "react";
import { MessageCircle, TriangleAlert, Plus, AlertCircle, DollarSign, Shield, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { parseDiagnosticData } from "../ai/parseDiagnosticData";

const stageTone = (stage: string | null | undefined) => {
  if (!stage) return "bg-slate-800/60 text-slate-200 border border-slate-700/40";
  const lowered = stage.toLowerCase();
  if (lowered.includes("job")) return "bg-indigo-800/60 text-indigo-100 border border-indigo-500/30";
  if (lowered.includes("approval")) return "bg-emerald-800/60 text-emerald-100 border border-emerald-500/30";
  if (lowered.includes("discovery")) return "bg-amber-800/60 text-amber-100 border border-amber-500/30";
  if (lowered.includes("incident")) return "bg-rose-800/60 text-rose-100 border border-rose-500/30";
  if (lowered.includes("completion")) return "bg-slate-700/80 text-slate-100 border border-slate-500/40";
  return "bg-slate-800/60 text-slate-200 border border-slate-700/40";
};

const severityConfig = {
  low: {
    icon: <AlertCircle className="h-3.5 w-3.5 text-emerald-400" />,
    color: "text-emerald-400",
    bgColor: "bg-emerald-900/30",
    borderColor: "border-emerald-500/30",
  },
  medium: {
    icon: <TriangleAlert className="h-3.5 w-3.5 text-amber-400" />,
    color: "text-amber-400",
    bgColor: "bg-amber-900/30",
    borderColor: "border-amber-500/30",
  },
  high: {
    icon: <TriangleAlert className="h-3.5 w-3.5 text-orange-400" />,
    color: "text-orange-400",
    bgColor: "bg-orange-900/30",
    borderColor: "border-orange-500/30",
  },
  urgent: {
    icon: <TriangleAlert className="h-3.5 w-3.5 text-red-400 animate-pulse" />,
    color: "text-red-400",
    bgColor: "bg-red-900/30",
    borderColor: "border-red-500/30",
  },
  emergency: {
    icon: <TriangleAlert className="h-3.5 w-3.5 text-red-500 animate-pulse" />,
    color: "text-red-500",
    bgColor: "bg-red-900/40",
    borderColor: "border-red-500/40",
  },
};

const formatSnippet = (text: string | undefined) => {
  if (!text) return "";
  return text.length > 64 ? `${text.slice(0, 61)}…` : text;
};

// Parse diagnostic data from channel messages
function parseChannelInsights(channel: any) {
  const messages = channel?.state?.messages || [];
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
}

function ConversationListComponent() {
  const { client, channels, activeChannel, selectChannel, flowState } = useStreamChat();
  const { data: session } = useSession();
  const router = useRouter();
  const [creating, setCreating] = useState(false);
  const [localChannels, setLocalChannels] = useState<any[]>([]);
  const [toast, setToast] = useState<{ id: number; message: string } | null>(null);

  const items = useMemo(
    () => {
      // Merge locally-created channels (optimistic) with the canonical channels
      const merged = [...localChannels, ...channels.filter((c) => !localChannels.find((lc) => lc.cid === c.cid))];

      return merged.map((channel) => {
        const lastMessage = channel.state.messages.at(-1);
        const channelData = (channel.data ?? {}) as Record<string, unknown>;
        const flowMeta = (channelData.flow_state as Record<string, unknown> | undefined) ?? {};
        const stageFromChannel = (flowMeta.stage as string | undefined) ?? flowState?.stage ?? null;
        const incidentId = (flowMeta.incidentId as string | undefined) ?? flowState?.incidentId ?? null;

        // Parse diagnostic insights from messages
        const insights = parseChannelInsights(channel);
        const severity = insights.severity || (channelData.severity as string | undefined) || "medium";

        return {
          channel,
          id: channel.id || channel.cid,
          title: (channelData.name as string | undefined) ?? incidentId ?? channel.cid,
          lastMessage: formatSnippet(lastMessage?.text),
          stage: stageFromChannel,
          severity: severity.toLowerCase(),
          urgency: insights.urgency,
          estimatedCost: insights.estimatedCost,
          hasSafety: insights.hasSafety,
        };
      });
    },
    [channels, flowState?.incidentId, flowState?.stage, localChannels],
  );

  const handleNewChat = async () => {
    if (!client) {
      setToast({ id: Date.now(), message: "Chat client not ready — please try again in a moment." });
      return;
    }
    setCreating(true);
    try {
      const payload = {
        creator: session?.user?.email,
        participants: [session?.user?.email],
        persona: session?.user?.persona ?? "tenant",
        include_agent: true,
        extra_data: { initiated_by: session?.user?.email },
      };

      const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/api$/, "")}/chat/stream/thread`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error(`Backend error: ${res.status}`);
      const data = await res.json();

      const channelId = data.channel_id || data.channel?.id;
      const streamChannel = client.channel("messaging", channelId);
      await streamChannel.watch();

      setLocalChannels((prev) => [streamChannel, ...prev]);
      selectChannel(streamChannel);
      router.push(`/dashboard/${session?.user?.persona ?? "tenant"}?cid=${channelId}`);
    } catch (err) {
      console.error("Failed to create thread", err);
      setToast({ id: Date.now(), message: "Failed to create new chat — please try again." });
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col gap-2 sm:gap-4 p-2 sm:p-0">
      <div className="flex-shrink-0 flex items-center justify-between rounded-xl border border-slate-800/60 bg-slate-900/70 px-2 sm:px-3 py-1.5 sm:py-2 backdrop-blur">
        <div className="min-w-0 flex-1">
          <h2 className="text-sm sm:text-base font-semibold text-slate-100 truncate">Active Conversations</h2>
          <p className="text-[10px] sm:text-xs text-slate-400 hidden sm:block">Monitor AI-guided flows across your portfolio.</p>
        </div>
        <div className="flex items-center gap-1.5 sm:gap-3 flex-shrink-0">
          <Badge className="bg-slate-800/80 text-slate-200 text-[10px] sm:text-xs px-1.5 sm:px-2">
            <MessageCircle className="mr-0.5 sm:mr-1 h-3 w-3 sm:h-3.5 sm:w-3.5" />
            {items.length}
          </Badge>

          <button
            type="button"
            onClick={handleNewChat}
            disabled={creating}
            className={`inline-flex items-center gap-1 sm:gap-2 rounded-md px-2 sm:px-3 py-1 text-xs sm:text-sm font-medium transition disabled:opacity-60 disabled:pointer-events-none bg-emerald-600/90 hover:bg-emerald-600/100 text-white`}
          >
            <Plus className="h-3 w-3 sm:h-4 sm:w-4" />
            <span className="hidden sm:inline">{creating ? "Creating…" : "New Chat"}</span>
            <span className="sm:hidden">+</span>
          </button>
        </div>
      </div>

      <ScrollArea className="flex-1 min-h-0 rounded-xl sm:rounded-2xl border border-slate-800/60 bg-slate-900/40 p-1.5 sm:p-2">
        <div className="space-y-2">
          {items.map(({ channel, id, title, lastMessage, stage, severity, urgency, estimatedCost, hasSafety }) => {
            const isActive = activeChannel?.cid === channel.cid;
            const severityKey = (severity || "medium") as keyof typeof severityConfig;
            const config = severityConfig[severityKey] || severityConfig.medium;

            return (
              <button
                type="button"
                key={id}
                onClick={() => selectChannel(channel)}
                className={`w-full rounded-lg sm:rounded-xl border px-2 sm:px-3 py-2 sm:py-3 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/60 ${
                  isActive
                    ? `border-emerald-500/40 bg-emerald-500/10`
                    : `${config.borderColor} ${config.bgColor} hover:bg-slate-800/60`
                }`}
              >
                <div className="flex items-start justify-between gap-2 sm:gap-3">
                  <div className="flex-1 space-y-1 sm:space-y-1.5 min-w-0">
                    <div className="flex items-center gap-1.5 sm:gap-2">
                      <p className="font-medium text-slate-100 text-xs sm:text-sm truncate">{title}</p>
                      {hasSafety && (
                        <Shield className="h-3 w-3 sm:h-3.5 sm:w-3.5 text-red-400 animate-pulse flex-shrink-0" title="Safety alerts present" />
                      )}
                    </div>
                    {lastMessage ? (
                      <p className="text-[10px] sm:text-xs text-slate-400 truncate">{lastMessage}</p>
                    ) : (
                      <p className="text-[10px] sm:text-xs text-slate-500">No messages yet</p>
                    )}

                    {/* Diagnostic Info Row */}
                    {(urgency || estimatedCost) && (
                      <div className="flex items-center gap-2 sm:gap-3 text-[9px] sm:text-[10px] text-slate-400">
                        {urgency && (
                          <span className="flex items-center gap-0.5 sm:gap-1">
                            <Clock className="h-2.5 w-2.5 sm:h-3 sm:w-3" />
                            {urgency}
                          </span>
                        )}
                        {estimatedCost && (
                          <span className="flex items-center gap-0.5 sm:gap-1">
                            <DollarSign className="h-2.5 w-2.5 sm:h-3 sm:w-3" />
                            {estimatedCost}
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex min-w-[80px] sm:min-w-[110px] flex-col items-end gap-1 sm:gap-1.5 flex-shrink-0">
                    <Badge variant="secondary" className={`capitalize text-[9px] sm:text-[10px] px-1.5 sm:px-2 py-0.5 ${stageTone(stage)}`}>
                      {stage ?? "general"}
                    </Badge>
                    <div className={`flex items-center gap-0.5 sm:gap-1 text-[10px] sm:text-[11px] uppercase tracking-wide ${config.color}`}>
                      {config.icon}
                      <span>{severity}</span>
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}

export const ConversationList = memo(ConversationListComponent);
