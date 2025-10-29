"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { StreamChat, Channel as StreamChannel } from "stream-chat";
import {
  Chat,
  Channel,
  ChannelHeader,
  MessageInput,
  MessageList,
  Thread,
  Window,
  ChannelList,
  MessageSimple,
} from "stream-chat-react";
import "stream-chat-react/dist/css/v2/index.css";
import { CustomMessageUI } from "./ai/CustomMessageUI";
import { CustomAttachment } from "./ai/CustomAttachment";
import { CustomChannelHeader } from "./ai/CustomChannelHeader";
import { AgentToggleButton } from "./ai/AgentToggleButton";

type Props = {
  persona: string;
};

type NotificationItem = {
  channelId: string;
  channelType: string;
  text: string;
  at: number;
};

export default function StreamChatPane({ persona }: Props) {
  const [client, setClient] = useState<StreamChat | null>(null);
  const [channel, setChannel] = useState<StreamChannel | null>(null);
  const [userInfo, setUserInfo] = useState<{ id: string; email: string; display: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showComposer, setShowComposer] = useState(false);
  const [participantInput, setParticipantInput] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [agentEnabled, setAgentEnabled] = useState(true);
  const [channelListKey, setChannelListKey] = useState(0); // Force re-render

  useEffect(() => {
    let chatClient: StreamChat | null = null;
    const init = async () => {
      try {
        const res = await fetch("/api/chat/token");
        if (!res.ok) {
          const contentType = res.headers.get("content-type") || "";
          let msg = "token fetch failed";
          if (contentType.includes("application/json")) {
            const json = await res.json().catch(() => null);
            msg = json?.detail || JSON.stringify(json);
          } else {
            msg = await res.text();
          }
          throw new Error(msg || "token fetch failed");
        }
        const data = await res.json();
        chatClient = StreamChat.getInstance(data.api_key);
        const userId = data.user_id as string;
        const displayId = (data.display_user_id as string | undefined) ?? userId;
        const email = (data.email as string | undefined) ?? displayId;
        await chatClient.connectUser(
          {
            id: userId,
            name: displayId,
            email: email,
          },
          data.token,
        );

        const initialChannel = chatClient.channel("messaging", data.channel_id || "landten-default");
        await initialChannel.watch();
        setClient(chatClient);
        setChannel(initialChannel);
        setUserInfo({ id: userId, email, display: displayId });
      } catch (err) {
        console.error(err);
        setError(err instanceof Error ? err.message : "Stream Chat configuration error.");
      }
    };
    init();
    return () => {
      if (chatClient) {
        chatClient.disconnectUser();
      }
    };
  }, [persona]);

  useEffect(() => {
    if (!client) return;

    const handler = (event: any) => {
      if (event.type !== "notification.message_new") return;
      const incomingChannelId: string | undefined = event.channel?.id || event.channel_id;
      const incomingType: string = event.channel?.type || event.channel_type || "messaging";
      if (!incomingChannelId || event.user?.id === client.userID) {
        return;
      }
      if (incomingChannelId === channel?.id) {
        return;
      }
      const preview = event.message?.text || "New message";
      const from = event.user?.name || event.user?.id || "Someone";
      const text = `${from}: ${preview}`;
      setNotifications((prev) => {
        const filtered = prev.filter((n) => n.channelId !== incomingChannelId);
        return [{ channelId: incomingChannelId, channelType: incomingType, text, at: Date.now() }, ...filtered].slice(0, 5);
      });
    };

    client.on(handler);
    return () => {
      client.off(handler);
    };
  }, [client, channel?.id]);

  useEffect(() => {
    if (!channel) return;
    channel
      .markRead()
      .catch((err) => console.error("Failed to mark channel as read", err));
  }, [channel?.cid]);

  const activeUserId = userInfo?.id ?? client?.userID ?? undefined;

  const filters = useMemo(() => {
    if (!activeUserId) return {};
    return { members: { $in: [activeUserId] }, type: "messaging" };
  }, [activeUserId]);

  const handleSelectChannel = useCallback(
    async (nextChannel: StreamChannel) => {
      try {
        await nextChannel.watch();
        await nextChannel.markRead();
        setChannel(nextChannel);
        const selectableId = nextChannel.id || nextChannel.cid?.split(":")[1];
        if (selectableId) {
          setNotifications((prev) => prev.filter((n) => n.channelId !== selectableId));
        }
      } catch (err) {
        console.error(err);
        setError(err instanceof Error ? err.message : "Failed to open conversation");
      }
    },
    [],
  );

  const handleCreateConversation = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!client || !userInfo?.email) {
        setError("Chat client not ready");
        return;
      }

      const participants = participantInput
        .split(/[\s,]+/)
        .map((entry) => entry.trim())
        .filter((entry) => entry.length > 0 && entry !== userInfo.email);

      if (participants.length === 0) {
        setError("Add at least one participant email");
        return;
      }

      setIsCreating(true);
      try {
        const res = await fetch("/api/chat/thread", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            creator: userInfo.email,
            participants,
            include_agent: agentEnabled,
            persona,
          }),
        });
        const payload = await res.json();
        if (!res.ok) {
          const message = payload?.error || payload?.detail || "Failed to create conversation";
          throw new Error(message);
        }

        // Force ChannelList refresh
        setChannelListKey(prev => prev + 1);

        // Switch to new channel
        const newChannel = client.channel("messaging", payload.channel_id);
        await newChannel.watch();
        await newChannel.markRead();
        setChannel(newChannel);
        setNotifications((prev) => prev.filter((n) => n.channelId !== payload.channel_id));
        setParticipantInput("");
        setShowComposer(false);
      } catch (err) {
        console.error(err);
        setError(err instanceof Error ? err.message : "Failed to create conversation");
      } finally {
        setIsCreating(false);
      }
    },
    [client, participantInput, persona, userInfo?.email, agentEnabled],
  );

  const openNotification = useCallback(
    async (item: NotificationItem) => {
      if (!client) return;
      try {
        const target = client.channel(item.channelType, item.channelId);
        await target.watch();
        await target.markRead();
        setChannel(target);
        setNotifications((prev) => prev.filter((n) => n.channelId !== item.channelId));
      } catch (err) {
        console.error(err);
        setError(err instanceof Error ? err.message : "Failed to open conversation");
      }
    },
    [client],
  );

  const handleSendMessage = useCallback(
    async (_cid: string, message: any) => {
      if (!channel) return;

      console.log('[StreamChatPane] Sending message, agent enabled:', agentEnabled);

      const response = await channel.sendMessage(message);
      const text: string = message?.text ?? "";

      // Check if we should trigger agent processing
      const hasAgentTrigger = text.toLowerCase().includes("@agent") ||
                              text.toLowerCase().includes("@landten-agent") ||
                              text.toLowerCase().includes("landten agent");
      const shouldProcessAgent = agentEnabled || hasAgentTrigger;

      if (shouldProcessAgent) {
        console.log('[StreamChatPane] Triggering agent processing for:', text.substring(0, 50));

        try {
          const history = channel.state.messages
            .slice(-10)
            .map((msg) => `${msg.user?.name || msg.user?.id}: ${msg.text || ""}`)
            .join("\n");

          // Call backend agent endpoint which will:
          // 1. Generate AI response via get_ai_response()
          // 2. Trigger PropertyAIBot.handle_message_event() for incident detection
          await fetch("/api/chat/agent", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              channel_id: channel.id,
              prompt: text,
              persona,
              context: history,
              requesting_user: userInfo?.email,
            }),
          });

          console.log('[StreamChatPane] Agent processing initiated');
        } catch (err) {
          console.error("[StreamChatPane] Agent trigger failed:", err);
        }
      } else {
        console.log('[StreamChatPane] Agent OFF - message sent without AI processing');
      }

      return response;
    },
    [channel, persona, userInfo?.email, agentEnabled],
  );

  const triggerDiscovery = useCallback(async () => {
    if (!channel) return;
    try {
      await channel.sendMessage({ text: "@agent start discovery" });
    } catch (err) {
      console.error("Failed to trigger discovery", err);
      setError(err instanceof Error ? err.message : "Failed to trigger discovery");
    }
  }, [channel]);

  const handleActionClick = useCallback(
    async (actionValue: string) => {
      console.log("[StreamChatPane] Action clicked:", actionValue);

      if (!client || !channel) return;

      const user = client.user || {};

      try {
        const payload = {
          type: "message.new",
          message: {
            text: actionValue,
            user: {
              id: user.id || "unknown",
              name: user.name || "Anonymous User",
              is_bot: false,
            },
          },
          user: {
            id: user.id || "unknown",
            name: user.name || "Anonymous User",
            is_bot: false,
          },
          channel_id: channel.id,
        };

        const res = await fetch("http://localhost:8080/ai/stream-webhook", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        const text = await res.text();
        console.log("[StreamChatPane] Action sent. Response:", text);
      } catch (err) {
        console.error("[StreamChatPane] Action error:", err);
      }
    },
    [client, channel]
  );


  const handleAgentToggle = useCallback((enabled: boolean) => {
    setAgentEnabled(enabled);
    console.log('[StreamChatPane] Agent toggled:', enabled ? 'ON' : 'OFF');
  }, []);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-sm text-red-400 bg-red-950 border border-red-800 rounded px-4 py-2">
          {error}
        </div>
      </div>
    );
  }

  if (!client || !channel || !activeUserId) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-slate-400">Connecting to Stream chat…</div>
      </div>
    );
  }

  return (
    <div className="stream-chat-wrapper">
      <Chat client={client} theme="str-chat__theme-dark">
        <div className="stream-chat-layout">
          {/* Sidebar */}
          <div className="stream-chat-sidebar">
            <div className="p-3 border-b border-slate-800 space-y-2">
              {/* Agent Toggle */}
              <AgentToggleButton
                initialState={agentEnabled}
                onChange={handleAgentToggle}
              />

              {/* New Conversation Button */}
              <button
                className="w-full rounded bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors"
                onClick={() => setShowComposer((prev) => !prev)}
              >
                {showComposer ? "Cancel" : "New Conversation"}
              </button>

              {/* Discovery Button */}
              <button
                className="w-full rounded border border-emerald-700 px-3 py-2 text-xs font-semibold text-emerald-200 hover:bg-emerald-800 transition-colors disabled:opacity-50"
                onClick={triggerDiscovery}
                disabled={!channel}
              >
                Start Incident Discovery
              </button>

              {/* New Conversation Form */}
              {showComposer && (
                <form
                  onSubmit={handleCreateConversation}
                  className="mt-3 flex flex-col gap-2 text-xs text-slate-200"
                >
                  <textarea
                    className="rounded border border-slate-700 bg-slate-900 p-2 text-xs text-slate-100 focus:border-emerald-600 focus:outline-none"
                    rows={3}
                    placeholder="Invite participants by email (comma or space separated)"
                    value={participantInput}
                    onChange={(event) => setParticipantInput(event.target.value)}
                  />
                  <p className="text-[11px] text-slate-400">
                    {agentEnabled
                      ? "All participants plus the LandTen agent will join this conversation."
                      : "Participants will join this conversation. Agent is OFF."}
                  </p>
                  <button
                    type="submit"
                    disabled={isCreating}
                    className="rounded bg-slate-700 px-3 py-1 text-xs font-semibold text-white hover:bg-slate-600 disabled:opacity-60 transition-colors"
                  >
                    {isCreating ? "Creating…" : "Create"}
                  </button>
                </form>
              )}
            </div>

            {/* Notifications */}
            {notifications.length > 0 && (
              <div className="space-y-1 border-b border-slate-800 bg-emerald-950 px-3 py-2 text-xs text-emerald-100 max-h-32 overflow-y-auto">
                {notifications.map((note) => (
                  <div
                    key={`${note.channelId}-${note.at}`}
                    className="flex items-center justify-between gap-2"
                  >
                    <span className="line-clamp-2 flex-1">{note.text}</span>
                    <button
                      className="rounded bg-emerald-700 px-2 py-0.5 text-[11px] text-white hover:bg-emerald-600 transition-colors shrink-0"
                      onClick={() => openNotification(note)}
                    >
                      Open
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Channel List */}
            <div className="flex-1 overflow-y-auto">
              <ChannelList
                key={channelListKey}
                filters={filters}
                sort={{ last_message_at: -1 }}
                options={{ state: true, watch: true, presence: true, limit: 30 }}
                onSelect={handleSelectChannel}
              />
            </div>
          </div>

          {/* Chat Window */}
          <div className="stream-chat-main">
            <Channel
              channel={channel}
              doSendMessageRequest={handleSendMessage}
              Attachment={(attachmentProps) => (
                <CustomAttachment {...attachmentProps} onActionClick={handleActionClick} />
              )}
            >
              <Window>
                <CustomChannelHeader
                  agentEnabled={agentEnabled}
                  onAgentToggle={handleAgentToggle}
                />
                <MessageList
                  disableDateSeparator
                  Message={(props) => (
                    <MessageSimple
                      {...props}
                      MessageText={(textProps) => (
                        <CustomMessageUI {...textProps} onActionClick={handleActionClick} />
                      )}
                    />
                  )}
                  // Prevent Stream from executing actions
                  actionsEnabled={false}
                />
                <MessageInput focus />
              </Window>
              <Thread />
            </Channel>
          </div>
        </div>
      </Chat>

      <style jsx>{`
        .stream-chat-wrapper {
          display: flex;
          flex-direction: column;
          height: 100%;
          width: 100%;
          overflow: hidden;
          background: #0f172a;
        }

        .stream-chat-layout {
          display: flex;
          flex: 1;
          height: 100%;
          width: 100%;
          overflow: hidden;
        }

        .stream-chat-sidebar {
          display: flex;
          flex-direction: column;
          width: 280px;
          max-width: 40%;
          background: #0f172a;
          border-right: 1px solid #1e293b;
          overflow: hidden;
        }

        .stream-chat-main {
          flex: 1;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          height: 100%;
          min-width: 0; /* Allow flex shrinking */
        }

        /* Fix Stream Chat container */
        .stream-chat-main :global(.str-chat__container) {
          height: 100%;
          display: flex;
          flex-direction: column;
          background: #0b0f1a;
        }

        .stream-chat-main :global(.str-chat__main-panel) {
          height: 100%;
          display: flex;
          flex-direction: column;
          overflow-y: auto;
          padding-bottom: 1rem;
        }

        /* Fix message list scrolling */
        .stream-chat-main :global(.str-chat__list) {
          flex: 1;
          overflow-y: auto;
          overflow-x: hidden;
        }

        /* Ensure proper dark theme */
        :global(.str-chat__theme-dark) {
          --str-chat__primary-color: #10b981;
          --str-chat__background-color: #0f172a;
          --str-chat__secondary-background-color: #1e293b;
          --str-chat__border-color: #334155;
        }

        /* Responsive */
        @media (max-width: 768px) {
          .stream-chat-layout {
            flex-direction: column;
          }

          .stream-chat-sidebar {
            width: 100%;
            max-width: 100%;
            max-height: 250px;
            border-right: none;
            border-bottom: 1px solid #1e293b;
          }
        }
      `}</style>
    </div>
  );
}
