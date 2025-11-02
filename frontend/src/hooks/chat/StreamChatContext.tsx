"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useSession } from "next-auth/react";
import { Channel, Event, type MessageResponse, StreamChat, type EventHandler, type EventTypes } from "stream-chat";

type FlowState = {
  stage?: string | null;
  incidentId?: string | null;
  persona?: string | null;
};

type ReasoningState = {
  active: boolean;
  stage?: string | null;
};

type StreamUser = {
  id: string;
  name?: string | null;
  email?: string | null;
  persona?: string | null;
};

type StreamChatContextValue = {
  client: StreamChat | null;
  user: StreamUser | null;
  channels: Channel[];
  activeChannel: Channel | null;
  messages: MessageResponse[];
  flowState: FlowState | null;
  reasoningState: ReasoningState;
  loading: boolean;
  error: string | null;
  selectChannel: (channel: Channel) => void;
  sendMessage: (text: string) => Promise<void>;
  triggerAction: (actionValue: string) => Promise<void>;
};

const StreamChatContext = createContext<StreamChatContextValue | undefined>(undefined);

type TokenResponse = {
  api_key: string;
  token: string;
  channel_id?: string;
  user_id: string;
  display_user_id?: string;
  persona?: string;
  email?: string;
};

const MAX_RENDERED_MESSAGES = 50;
const REASONING_TIMEOUT_MS = 3000;

const initialReasoningState: ReasoningState = { active: false, stage: null };

const normaliseStage = (value?: string | null) => value?.toLowerCase() ?? null;

const deriveFlowState = (input?: Record<string, unknown> | null): FlowState | null => {
  if (!input) return null;
  const stage = typeof input.stage === "string" ? input.stage : undefined;
  const incidentId =
    typeof input.incidentId === "string"
      ? input.incidentId
      : typeof input.incident_id === "string"
        ? input.incident_id
        : undefined;
  const persona = typeof input.persona === "string" ? input.persona : undefined;
  if (!stage && !incidentId && !persona) {
    return null;
  }
  return {
    stage: stage ?? null,
    incidentId: incidentId ?? null,
    persona: persona ?? null,
  };
};

const deriveFlowStateFromMessage = (message?: MessageResponse): FlowState | null => {
  if (!message) return null;
  const metadata = (message as { metadata?: Record<string, unknown> }).metadata ?? {};
  const flowStateMeta = (metadata.flow_state as Record<string, unknown> | undefined) ?? undefined;
  const contextType = typeof metadata.context_type === "string" ? metadata.context_type : undefined;
  const base =
    deriveFlowState(flowStateMeta) ??
    deriveFlowState({
      stage: contextType,
      incidentId: metadata.incident_id,
      persona: metadata.persona,
    });
  return base;
};

const isAIMessage = (message?: MessageResponse) => {
  if (!message?.user) return false;
  const identifier = message.user.id ?? "";
  const displayName = message.user.name ?? "";
  const messageType = (message.type as string | undefined) ?? "";
  return (
    identifier.startsWith("ai-") ||
    displayName.toLowerCase().includes("landten") ||
    displayName.toLowerCase().includes("assistant") ||
    messageType === "ai-message"
  );
};

const extractReasoningStage = (message?: MessageResponse): string | null => {
  const metadata = (message as { metadata?: Record<string, unknown> }).metadata ?? {};
  const stage = typeof metadata.context_type === "string" ? metadata.context_type : undefined;
  const flowStage =
    typeof metadata.flow_stage === "string"
      ? metadata.flow_stage
      : typeof metadata.flow_state === "object" && metadata.flow_state
        ? (metadata.flow_state as Record<string, unknown>).stage
        : undefined;
  return (flowStage as string | undefined) ?? stage ?? null;
};

const shouldTreatAsAnalysis = (message?: MessageResponse) => {
  if (!message?.text) return false;
  const trimmed = message.text.trim();
  return trimmed.startsWith("{") && trimmed.includes('"analysis"');
};

const normaliseMessageDates = (raw: unknown): MessageResponse => {
  if (!raw || typeof raw !== "object") {
    return raw as MessageResponse;
  }
  const message = { ...(raw as Record<string, unknown>) };
  const dateKeys = ["created_at", "updated_at", "deleted_at", "pinned_at", "sync_status_changed_at"];
  for (const key of dateKeys) {
    const value = message[key];
    if (value instanceof Date) {
      message[key] = value.toISOString();
    }
  }
  return message as unknown as MessageResponse;
};

export function StreamChatProvider({ children }: { children: ReactNode }) {
  const { data: session, status } = useSession();
  const [client, setClient] = useState<StreamChat | null>(null);
  const [user, setUser] = useState<StreamUser | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [activeChannel, setActiveChannel] = useState<Channel | null>(null);
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [flowState, setFlowState] = useState<FlowState | null>(null);
  const [reasoningState, setReasoningState] = useState<ReasoningState>(initialReasoningState);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const reasoningTimeout = useRef<NodeJS.Timeout | null>(null);
  const channelSubscriptions = useRef<Array<() => void>>([]);

  const resetState = useCallback(() => {
    channelSubscriptions.current.forEach((unsubscribe) => {
      try {
        unsubscribe();
      } catch {
        // noop
      }
    });
    channelSubscriptions.current = [];
    setChannels([]);
    setActiveChannel(null);
    setMessages([]);
    setFlowState(null);
    setReasoningState(initialReasoningState);
  }, []);

  const disconnectClient = useCallback(async () => {
    if (reasoningTimeout.current) {
      clearTimeout(reasoningTimeout.current);
      reasoningTimeout.current = null;
    }
    resetState();
    if (client) {
      try {
        await client.disconnectUser();
      } catch (disconnectError) {
        console.warn("[StreamChat] Failed to disconnect user", disconnectError);
      }
    }
    setClient(null);
    setUser(null);
  }, [client, resetState]);

  useEffect(() => {
    if (status === "loading") return;
    if (!session?.user) {
      disconnectClient();
      return;
    }

    let isMounted = true;
    const initialise = async () => {
      setLoading(true);
      setError(null);
      try {
        const tokenRes = await fetch("/api/chat/token");
        if (!tokenRes.ok) {
          const problem = await tokenRes.json().catch(() => ({}));
          throw new Error(problem.error || "Unable to fetch Stream token");
        }
        const tokenData = (await tokenRes.json()) as TokenResponse;
        const { api_key, token, user_id, display_user_id, persona, channel_id } = tokenData;

        if (!api_key || !token || !user_id) {
          throw new Error("Stream credentials incomplete");
        }

        const streamClient = StreamChat.getInstance(api_key, { timeout: 6000 });
        if (!streamClient.userID) {
          await streamClient.connectUser(
            {
              id: user_id,
              name: display_user_id ?? session.user.email ?? user_id,
            },
            token,
          );
        } else if (streamClient.userID !== user_id) {
          await streamClient.disconnectUser();
          await streamClient.connectUser(
            {
              id: user_id,
              name: display_user_id ?? session.user.email ?? user_id,
            },
            token,
          );
        }

        if (!isMounted) {
          await streamClient.disconnectUser();
          return;
        }

        setClient(streamClient);
        setUser({
          id: user_id,
          name: display_user_id ?? session.user.email ?? user_id,
          email: session.user.email ?? null,
          persona: persona ?? session.user.persona ?? null,
        });

        const filters = {
          type: "messaging",
          members: { $in: [user_id] },
        };
        const sort = { last_message_at: -1 as const };
        const queriedChannels = await streamClient.queryChannels(filters, sort, {
          watch: true,
          state: true,
        });

        if (!isMounted) {
          await streamClient.disconnectUser();
          return;
        }

        setChannels(queriedChannels);

        const defaultChannel =
          queriedChannels.find(
            (channel) =>
              channel.id === channel_id ||
              channel.cid === channel_id ||
              channel.cid === `messaging:${channel_id}`,
          ) ?? queriedChannels[0] ?? null;

        if (defaultChannel) {
          console.log("[StreamChat] Setting default channel:", defaultChannel.cid);
          setActiveChannel(defaultChannel);
          const initialMessages = defaultChannel.state.messages
            .slice(-MAX_RENDERED_MESSAGES)
            .map((msg) => normaliseMessageDates(msg));
          console.log("[StreamChat] Loaded", initialMessages.length, "initial messages");
          setMessages(initialMessages);
          const defaultChannelData = (defaultChannel.data ?? {}) as Record<string, unknown>;
          const initialFlow =
            deriveFlowState(defaultChannelData.flow_state as Record<string, unknown>) ??
            deriveFlowState({
              stage: defaultChannelData.stage,
              incidentId: defaultChannelData.incidentId,
              persona: defaultChannelData.persona,
            });
          if (initialFlow) {
            console.log("[StreamChat] Initial flow state:", initialFlow);
            setFlowState(initialFlow);
          }
        }

        setLoading(false);
      } catch (err) {
        console.error("[StreamChat] Failed to initialise connection", err);
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to connect to Stream");
          setLoading(false);
        }
      }
    };

    initialise();

    return () => {
      isMounted = false;
    };
  }, [session, status, disconnectClient]);

  const updateMessagesFromChannel = useCallback(
    (channel: Channel, forceUpdate = false) => {
      const latestMessages = channel.state.messages
        .slice(-MAX_RENDERED_MESSAGES)
        .map((msg) => normaliseMessageDates(msg));

      // Always update to ensure reactivity - use functional update for consistency
      setMessages((prev) => {
        // Force update if requested or if the array has changed
        if (forceUpdate || prev.length !== latestMessages.length) {
          return latestMessages;
        }
        // Check if the last message has changed
        const prevLast = prev[prev.length - 1];
        const newLast = latestMessages[latestMessages.length - 1];
        if (prevLast?.id !== newLast?.id) {
          return latestMessages;
        }
        // Return prev to avoid unnecessary re-renders
        return prev;
      });

      const newest = latestMessages.at(-1);
      const flowFromMessage = deriveFlowStateFromMessage(newest);
      const channelData = (channel.data ?? {}) as Record<string, unknown>;
      const flowFromChannel =
        deriveFlowState(channelData.flow_state as Record<string, unknown>) ??
        deriveFlowState({
          stage: channelData.stage,
          incidentId: channelData.incidentId,
          persona: channelData.persona,
        });
      const candidate = flowFromMessage ?? flowFromChannel;
      if (candidate) {
        setFlowState((prev) => {
          const prevStage = normaliseStage(prev?.stage);
          const nextStage = normaliseStage(candidate.stage);
          const sameStage = prevStage === nextStage;
          const sameIncident = (prev?.incidentId ?? null) === (candidate.incidentId ?? null);
          const samePersona = (prev?.persona ?? null) === (candidate.persona ?? null);
          if (sameStage && sameIncident && samePersona) {
            return prev;
          }
          return {
            stage: candidate.stage ?? null,
            incidentId: candidate.incidentId ?? null,
            persona: candidate.persona ?? null,
          };
        });
      }
      setChannels((prev) => {
        let found = false;
        const next = prev.map((existing) => {
          if (existing.cid === channel.cid) {
            found = true;
            return channel;
          }
          return existing;
        });
        return found ? next : prev;
      });
    },
    [],
  );

  const handleReasoningCue = useCallback(
    (message?: MessageResponse) => {
      if (!message || !isAIMessage(message) || !shouldTreatAsAnalysis(message)) {
        return;
      }
      const stage = extractReasoningStage(message);
      setReasoningState((prev) => {
        const normalizedStage = stage ?? prev.stage ?? null;
        if (prev.active && prev.stage === normalizedStage) {
          return prev;
        }
        return { active: true, stage: normalizedStage };
      });
      if (reasoningTimeout.current) {
        clearTimeout(reasoningTimeout.current);
      }
      reasoningTimeout.current = setTimeout(() => {
        setReasoningState((prev) => {
          if (!prev.active) return prev;
          return { active: false, stage: stage ?? prev.stage ?? null };
        });
        reasoningTimeout.current = null;
      }, REASONING_TIMEOUT_MS);
    },
    [],
  );

  const attachChannelListeners = useCallback(
    (channel: Channel) => {
      channelSubscriptions.current.forEach((unsubscribe) => {
        try {
          unsubscribe();
        } catch {
          // noop
        }
      });
      channelSubscriptions.current = [];

      const subscribe = (event: string, handler: EventHandler) => {
        const listener = channel.on(event as EventTypes, handler);
        const unsubscribe = () => {
          try {
            listener.unsubscribe();
          } catch {
            // ignore
          }
        };
        channelSubscriptions.current.push(unsubscribe);
      };

      subscribe("message.new", (event: Event) => {
        console.log("[StreamChat] message.new event received:", event.message?.id);
        if (event.message) {
          handleReasoningCue(event.message);
        }
        updateMessagesFromChannel(channel, true);
      });

      subscribe("message.updated", (event: Event) => {
        console.log("[StreamChat] message.updated event received");
        updateMessagesFromChannel(channel, true);
      });

      subscribe("message.deleted", (event: Event) => {
        console.log("[StreamChat] message.deleted event received");
        updateMessagesFromChannel(channel, true);
      });

      subscribe("channel.updated", (event: Event) => {
        console.log("[StreamChat] channel.updated event received");
        updateMessagesFromChannel(channel, true);
      });

      subscribe("custom.flow_update", (event: Event) => {
        console.log("[StreamChat] custom.flow_update event received");
        const payload = (event as unknown as { payload?: Record<string, unknown> }).payload ?? {};
        const flow = deriveFlowState(payload ?? {});
        if (flow) {
          console.log("[StreamChat] Flow state update:", flow);
          setFlowState((prev) => {
            const prevStage = normaliseStage(prev?.stage);
            const nextStage = normaliseStage(flow.stage);
            const sameStage = prevStage === nextStage;
            const sameIncident = (prev?.incidentId ?? null) === (flow.incidentId ?? null);
            const samePersona = (prev?.persona ?? null) === (flow.persona ?? null);
            if (sameStage && sameIncident && samePersona) {
              return prev;
            }
            return {
              stage: flow.stage ?? null,
              incidentId: flow.incidentId ?? null,
              persona: flow.persona ?? null,
            };
          });
        }
      });

      subscribe("custom.reasoning_state", (event: Event) => {
        console.log("[StreamChat] custom.reasoning_state event received");
        const payload = (event as unknown as { payload?: Record<string, unknown> }).payload;
        const active = Boolean(payload?.active);
        const stage = typeof payload?.stage === "string" ? payload.stage : null;
        setReasoningState((prev) => {
          if (prev.active === active && prev.stage === stage) return prev;
          return { active, stage };
        });
      });
    },
    [handleReasoningCue, updateMessagesFromChannel],
  );

  useEffect(() => {
    if (!activeChannel) return;
    updateMessagesFromChannel(activeChannel);
    attachChannelListeners(activeChannel);
    return () => {
      channelSubscriptions.current.forEach((unsubscribe) => {
        try {
          unsubscribe();
        } catch {
          // noop
        }
      });
      channelSubscriptions.current = [];
    };
  }, [activeChannel, attachChannelListeners, updateMessagesFromChannel]);

  useEffect(() => {
    return () => {
      if (reasoningTimeout.current) {
        clearTimeout(reasoningTimeout.current);
      }
    };
  }, []);

  useEffect(() => {
    return () => {
      disconnectClient();
    };
  }, [disconnectClient]);

  const selectChannel = useCallback((channel: Channel) => {
    console.log("[StreamChat] Selecting channel:", channel.cid);
    setActiveChannel((prev) => {
      if (prev?.cid === channel.cid) {
        console.log("[StreamChat] Channel already active");
        return prev;
      }
      console.log("[StreamChat] Switching to new channel");
      setReasoningState(initialReasoningState);
      return channel;
    });
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!activeChannel || !text.trim()) return;
      try {
        console.log("[StreamChat] Sending message:", text.substring(0, 50));
        const result = await activeChannel.sendMessage({
          text,
          type: "regular",
        });
        console.log("[StreamChat] Message sent successfully, result:", result?.message?.id);

        // Force update messages after sending
        if (result) {
          // Small delay to ensure the message is in the channel state
          setTimeout(() => {
            updateMessagesFromChannel(activeChannel, true);
          }, 100);
        }
      } catch (err) {
        console.error("[StreamChat] Failed to send message", err);
        throw err;
      }
    },
    [activeChannel, updateMessagesFromChannel],
  );

  const triggerAction = useCallback(
    async (actionValue: string) => {
      if (!activeChannel) {
        throw new Error("No active channel selected");
      }
      const body = {
        channel_id: activeChannel.id || activeChannel.cid,
        action: actionValue,
      };
      const res = await fetch("/api/chat/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        throw new Error(payload.error || "Failed to trigger action");
      }
      return res.json().catch(() => ({}));
    },
    [activeChannel],
  );

  const value = useMemo<StreamChatContextValue>(
    () => ({
      client,
      user,
      channels,
      activeChannel,
      messages,
      flowState,
      reasoningState,
      loading,
      error,
      selectChannel,
      sendMessage,
      triggerAction,
    }),
    [
      client,
      user,
      channels,
      activeChannel,
      messages,
      flowState,
      reasoningState,
      loading,
      error,
      selectChannel,
      sendMessage,
      triggerAction,
    ],
  );

  return <StreamChatContext.Provider value={value}>{children}</StreamChatContext.Provider>;
}

export function useStreamChat() {
  const ctx = useContext(StreamChatContext);
  if (!ctx) {
    throw new Error("useStreamChat must be used within a StreamChatProvider");
  }
  return ctx;
}
