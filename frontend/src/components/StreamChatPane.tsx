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
} from "stream-chat-react";
import "stream-chat-react/dist/css/v2/index.css";

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
    return { members: { $in: [activeUserId] } };
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
            include_agent: true,
            persona,
          }),
        });
        const payload = await res.json();
        if (!res.ok) {
          const message = payload?.error || payload?.detail || "Failed to create conversation";
          throw new Error(message);
        }

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
    [client, participantInput, persona, userInfo?.email],
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
      const response = await channel.sendMessage(message);
      const text: string = message?.text ?? "";
      if (text.toLowerCase().includes("@agent")) {
        try {
          const history = channel.state.messages
            .slice(-10)
            .map((msg) => `${msg.user?.name || msg.user?.id}: ${msg.text || ""}`)
            .join("\n");
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
        } catch (err) {
          console.error("Agent trigger failed", err);
        }
      }
      return response;
    },
    [channel, persona, userInfo?.email],
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

  if (error) {
    return <div className="text-sm text-emerald-300">{error}</div>;
  }

  if (!client || !channel || !activeUserId) {
    return <div>Connecting to Stream chat…</div>;
  }

  return (
    <div className="stream-chat-container">
      <Chat client={client} theme="str-chat__theme-dark">
        <div className="flex" style={{ minHeight: 420 }}>
          <div style={{ width: 260, borderRight: "1px solid #1f2937" }} className="flex flex-col">
            <div className="p-3 border-b border-slate-800">
              <div className="flex flex-col gap-2">
                <button
                  className="w-full rounded bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
                  onClick={() => setShowComposer((prev) => !prev)}
                >
                  {showComposer ? "Cancel" : "New Conversation"}
                </button>
                <button
                  className="w-full rounded border border-emerald-700 px-3 py-2 text-xs font-semibold text-emerald-200 hover:bg-emerald-800"
                  onClick={triggerDiscovery}
                  disabled={!channel}
                >
                  Start Incident Discovery
                </button>
              </div>
              {showComposer && (
                <form onSubmit={handleCreateConversation} className="mt-3 flex flex-col gap-2 text-xs text-slate-200">
                  <textarea
                    className="rounded border border-slate-700 bg-slate-900 p-2 text-xs text-slate-100"
                    rows={3}
                    placeholder="Invite participants by email (comma or space separated)"
                    value={participantInput}
                    onChange={(event) => setParticipantInput(event.target.value)}
                  />
                  <p className="text-[11px] text-slate-400">All participants plus the LandTen agent will join this conversation.</p>
                  <button
                    type="submit"
                    disabled={isCreating}
                    className="rounded bg-slate-700 px-3 py-1 text-xs font-semibold text-white hover:bg-slate-600 disabled:opacity-60"
                  >
                    {isCreating ? "Creating…" : "Create"}
                  </button>
                </form>
              )}
            </div>

            {notifications.length > 0 && (
              <div className="space-y-1 border-b border-slate-800 bg-emerald-950 px-3 py-2 text-xs text-emerald-100">
                {notifications.map((note) => (
                  <div key={`${note.channelId}-${note.at}`} className="flex items-center justify-between gap-2">
                    <span className="line-clamp-2">{note.text}</span>
                    <button
                      className="rounded bg-emerald-700 px-2 py-0.5 text-[11px] text-white hover:bg-emerald-600"
                      onClick={() => openNotification(note)}
                    >
                      Open
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex-1 overflow-hidden">
              <ChannelList
                filters={filters}
                sort={{ last_message_at: -1 }}
                options={{ state: true, watch: true, presence: true }}
                onSelect={handleSelectChannel}
              />
            </div>
          </div>
          <Channel channel={channel} doSendMessageRequest={handleSendMessage}>
            <Window>
              <ChannelHeader live />
              <MessageList disableDateSeparator />
              <MessageInput focus />
            </Window>
            <Thread />
          </Channel>
        </div>
      </Chat>
    </div>
  );
}
