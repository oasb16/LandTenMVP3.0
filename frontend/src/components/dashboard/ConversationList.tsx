import React, { memo, useMemo, useState } from "react";
import { MessageCircle, TriangleAlert, Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useStreamChat } from "@/hooks/chat/StreamChatContext";
// import { auth } from "@/utils/firebase";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";

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

const severityIcon = (severity: string | undefined) => {
  if (severity === "high") return <TriangleAlert className="h-3.5 w-3.5 text-rose-300" />;
  if (severity === "medium") return <TriangleAlert className="h-3.5 w-3.5 text-amber-300" />;
  return <TriangleAlert className="h-3.5 w-3.5 text-slate-400" />;
};

const formatSnippet = (text: string | undefined) => {
  if (!text) return "";
  return text.length > 64 ? `${text.slice(0, 61)}…` : text;
};

function ConversationListComponent() {
  const { client, channels, activeChannel, selectChannel, flowState } = useStreamChat();
  const { data: session } = useSession();
  const router = useRouter();
  const [creating, setCreating] = useState(false);
  const [localChannels, setLocalChannels] = useState<any[]>([]);
  // simple inline toast state as a fallback to a global toast provider
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
        const severity = (channelData.severity as string | undefined) ?? "medium";
        return {
          channel,
          id: channel.id || channel.cid,
          title: (channelData.name as string | undefined) ?? incidentId ?? channel.cid,
          lastMessage: formatSnippet(lastMessage?.text),
          stage: stageFromChannel,
          severity,
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
    <div className="flex h-full flex-col gap-4">
      <div className="sticky top-0 z-10 flex items-center justify-between rounded-xl border border-slate-800/60 bg-slate-900/70 px-3 py-2 backdrop-blur">
        <div>
          <h2 className="text-base font-semibold text-slate-100">Active Conversations</h2>
          <p className="text-xs text-slate-400">Monitor AI-guided flows across your portfolio.</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge className="bg-slate-800/80 text-slate-200">
            <MessageCircle className="mr-1 h-3.5 w-3.5" />
            {items.length}
          </Badge>

          <button
            type="button"
            onClick={handleNewChat}
            disabled={creating}
            className={`inline-flex items-center gap-2 rounded-md px-3 py-1 text-sm font-medium transition disabled:opacity-60 disabled:pointer-events-none bg-emerald-600/90 hover:bg-emerald-600/100 text-white`}
          >
            <Plus className="h-4 w-4" />
            {creating ? "Creating…" : "New Chat"}
          </button>
        </div>
      </div>

      <ScrollArea className="flex-1 rounded-2xl border border-slate-800/60 bg-slate-900/40 p-2">
        <div className="space-y-2">
          {items.map(({ channel, id, title, lastMessage, stage, severity }) => {
            const isActive = activeChannel?.cid === channel.cid;
            return (
              <button
                type="button"
                key={id}
                onClick={() => selectChannel(channel)}
                className={`w-full rounded-xl border px-3 py-3 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/60 ${
                  isActive
                    ? "border-emerald-500/40 bg-emerald-500/10"
                    : "border-slate-800/60 bg-slate-900/60 hover:bg-slate-800/60"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <p className="font-medium text-slate-100">{title}</p>
                    {lastMessage ? (
                      <p className="text-xs text-slate-400">{lastMessage}</p>
                    ) : (
                      <p className="text-xs text-slate-500">No messages yet</p>
                    )}
                  </div>
                  <div className="flex min-w-[110px] flex-col items-end gap-1">
                    <Badge variant="secondary" className={`capitalize ${stageTone(stage)}`}>
                      {stage ?? "general"}
                    </Badge>
                    <div className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-slate-400">
                      {severityIcon(severity)}
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

