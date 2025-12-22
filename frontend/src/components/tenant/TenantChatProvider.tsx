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
  hasMoreMessages: boolean;
  loadingMore: boolean;
  selectChannel: (channel: Channel) => void;
  sendMessage: (text: string, messageData?: any) => Promise<void>;
  triggerAction: (actionValue: string) => Promise<void>;
  loadMoreMessages: () => Promise<void>;
};

const TenantChatContext = createContext<StreamChatContextValue | undefined>(undefined);

type TokenResponse = {
  api_key: string;
  token: string;
  channel_id?: string;
  user_id: string;
  display_user_id?: string;
  persona?: string;
  email?: string;
};

type CachedToken = {
  tokenData: TokenResponse;
  expiresAt: number;
};

const INITIAL_MESSAGE_LOAD = 20; // Load only 20 messages initially
const LOAD_MORE_BATCH_SIZE = 20; // Load 20 more messages when "Load More" is clicked
const MAX_RENDERED_MESSAGES = 100; // Maximum messages to keep in memory
const REASONING_TIMEOUT_MS = 3000;
const TOKEN_CACHE_TTL = 4 * 60 * 1000; // 4 minutes (tokens expire at 5 min)
const RECONNECT_BASE_DELAY = 2000; // 2 seconds
const RECONNECT_MAX_DELAY = 30000; // 30 seconds

const initialReasoningState: ReasoningState = { active: false, stage: null };

// Module-level singleton client instance
let singletonClient: StreamChat | null = null;
let singletonUserId: string | null = null;
let reconnectAttempts = 0;
let lastReconnectTime = 0;

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

// Token caching utilities
const getTokenCacheKey = (userId: string, persona: string): string => {
  return `stream_token_${userId}_${persona}`;
};

const getCachedToken = (userId: string, persona: string): TokenResponse | null => {
  if (typeof window === "undefined") return null;

  try {
    const cacheKey = getTokenCacheKey(userId, persona);
    const cached = sessionStorage.getItem(cacheKey);
    if (!cached) return null;

    const parsed: CachedToken = JSON.parse(cached);
    if (Date.now() > parsed.expiresAt) {
      sessionStorage.removeItem(cacheKey);
      return null;
    }

    console.log("[StreamChat] Using cached token");
    return parsed.tokenData;
  } catch (err) {
    console.warn("[StreamChat] Token cache read failed:", err);
    return null;
  }
};

const setCachedToken = (userId: string, persona: string, tokenData: TokenResponse): void => {
  if (typeof window === "undefined") return;

  try {
    const cacheKey = getTokenCacheKey(userId, persona);
    const cached: CachedToken = {
      tokenData,
      expiresAt: Date.now() + TOKEN_CACHE_TTL,
    };
    sessionStorage.setItem(cacheKey, JSON.stringify(cached));
    console.log("[StreamChat] Token cached for", TOKEN_CACHE_TTL / 1000, "seconds");
  } catch (err) {
    console.warn("[StreamChat] Token cache write failed:", err);
  }
};

const clearTokenCache = (userId: string, persona: string): void => {
  if (typeof window === "undefined") return;

  try {
    const cacheKey = getTokenCacheKey(userId, persona);
    sessionStorage.removeItem(cacheKey);
  } catch (err) {
    console.warn("[StreamChat] Token cache clear failed:", err);
  }
};

export function TenantChatProvider({ children }: { children: ReactNode }) {
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
  const [hasMoreMessages, setHasMoreMessages] = useState<boolean>(false);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);

  const reasoningTimeout = useRef<NodeJS.Timeout | null>(null);
  const channelSubscriptions = useRef<Array<() => void>>([]);
  const isInitializing = useRef(false);
  const initializationAttempts = useRef(0);
  const loadedMessageCount = useRef<number>(0);

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
    console.log("[StreamChat] Disconnect requested");
    if (reasoningTimeout.current) {
      clearTimeout(reasoningTimeout.current);
      reasoningTimeout.current = null;
    }
    resetState();

    // Only disconnect if we own this client instance
    if (singletonClient && client === singletonClient) {
      try {
        await singletonClient.disconnectUser();
        console.log("[StreamChat] Client disconnected");
      } catch (disconnectError) {
        console.warn("[StreamChat] Failed to disconnect user", disconnectError);
      }
      singletonClient = null;
      singletonUserId = null;
    }

    setClient(null);
    setUser(null);
  }, [client, resetState]);

  // Calculate exponential backoff delay
  const getReconnectDelay = (): number => {
    const delay = Math.min(
      RECONNECT_BASE_DELAY * Math.pow(2, reconnectAttempts),
      RECONNECT_MAX_DELAY
    );
    return delay;
  };

  useEffect(() => {
    if (status === "loading") return;

    if (!session?.user) {
      disconnectClient();
      return;
    }

    const userEmail = session.user.email || "";
    const userPersona = session.user.persona || "tenant";

    // Guard: Prevent concurrent initializations
    if (isInitializing.current) {
      console.log("[StreamChat] Initialization already in progress, skipping");
      return;
    }

    // Guard: Check if already connected to same user
    if (singletonClient && singletonUserId === userEmail && singletonClient.userID) {
      console.log("[StreamChat] Already connected to Stream as", userEmail);
      if (!client) {
        setClient(singletonClient);
        setUser({
          id: singletonClient.userID,
          name: session.user.email ?? singletonClient.userID,
          email: userEmail,
          persona: userPersona,
        });
      }
      return;
    }

    // Throttle reconnection attempts
    const now = Date.now();
    const timeSinceLastReconnect = now - lastReconnectTime;
    const minDelay = getReconnectDelay();

    if (timeSinceLastReconnect < minDelay) {
      const waitTime = minDelay - timeSinceLastReconnect;
      console.log(`[StreamChat] Throttling reconnect, waiting ${waitTime}ms`);
      const timeout = setTimeout(() => {
        // Trigger re-initialization after throttle period
        setLoading(false);
      }, waitTime);
      return () => clearTimeout(timeout);
    }

    let isMounted = true;
    isInitializing.current = true;

    const initialise = async () => {
      setLoading(true);
      setError(null);

      try {
        lastReconnectTime = Date.now();

        // Try to get cached token first
        let tokenData = getCachedToken(userEmail, userPersona);

        // Block token fetch when unauthenticated or missing email (race during reauth)
        if ((status as string) === "unauthenticated" || !session?.user?.email) {
          console.warn("[chat] Blocked token fetch — user not authenticated");
          disconnectClient();
          return;
        }

        if (!tokenData) {
          const tokenUrl = "/api/chat/token";
          console.log("[StreamChat] Fetching new token from local API", tokenUrl);
          const tokenRes = await fetch(tokenUrl);
          if (!tokenRes.ok) {
            const problem = await tokenRes.json().catch(() => ({}));
            throw new Error(problem.error || "Unable to fetch Stream token");
          }
          tokenData = (await tokenRes.json()) as TokenResponse;

          // Cache the token
          setCachedToken(userEmail, userPersona, tokenData);
        }

        const { api_key, token, user_id, display_user_id, persona, channel_id } = tokenData;

        if (!api_key || !token || !user_id) {
          throw new Error("Stream credentials incomplete");
        }

        // Use singleton client or create new one
        let streamClient = singletonClient;

        if (!streamClient) {
          console.log("[StreamChat] Creating new singleton client");
          streamClient = StreamChat.getInstance(api_key, { timeout: 6000 });
          singletonClient = streamClient;
        }

        // Guard: ensure session still has user email before connecting
        if (!session?.user?.email) {
          console.warn("[chat] Blocked connection — missing session user email");
          disconnectClient();
          return;
        }

        // Guard: Only connect if not already connected to this user
        if (!streamClient.userID) {
          console.log("[StreamChat] Connecting user:", user_id);
          await streamClient.connectUser(
            {
              id: user_id,
              name: display_user_id ?? session.user.email ?? user_id,
            },
            token,
          );
          singletonUserId = userEmail;
          console.log("[StreamChat] ✅ WS connected");
        } else if (streamClient.userID !== user_id) {
          console.log("[StreamChat] User changed, reconnecting:", user_id);
          await streamClient.disconnectUser();
          await streamClient.connectUser(
            {
              id: user_id,
              name: display_user_id ?? session.user.email ?? user_id,
            },
            token,
          );
          singletonUserId = userEmail;
          console.log("[StreamChat] ✅ WS reconnected");
        } else {
          console.log("[StreamChat] Already connected as", user_id);
        }

        if (!isMounted) {
          console.log("[StreamChat] Component unmounted during init, aborting");
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
          console.log("[StreamChat] Component unmounted after query, aborting");
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

          // 🔥 FIX: Use Stream Chat query API to load only 20 messages from server
          console.log("[StreamChat] Fetching initial", INITIAL_MESSAGE_LOAD, "messages from server...");
          const channelState = await defaultChannel.query({
            messages: { limit: INITIAL_MESSAGE_LOAD },
          });

          if (!isMounted) {
            console.log("[StreamChat] Component unmounted after channel query, aborting");
            return;
          }

          setActiveChannel(defaultChannel);

          const initialMessages = (channelState.messages || []).map((msg) => normaliseMessageDates(msg));
          loadedMessageCount.current = initialMessages.length;

          // Check if there are more messages by comparing to channel message count
          const hasMore = initialMessages.length >= INITIAL_MESSAGE_LOAD;
          setHasMoreMessages(hasMore);

          console.log("[StreamChat] Loaded", initialMessages.length, "messages from server, hasMore:", hasMore);
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

        // Reset reconnection counter on successful connection
        reconnectAttempts = 0;
        setLoading(false);

      } catch (err) {
        console.error("[StreamChat] Failed to initialise connection", err);
        reconnectAttempts++;

        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to connect to Stream");
          setLoading(false);

          // Clear cached token on error
          clearTokenCache(userEmail, userPersona);
        }
      } finally {
        isInitializing.current = false;
      }
    };

    initialise();

    return () => {
      isMounted = false;
    };
  }, [session?.user?.email, session?.user?.persona, status]); // Only depend on stable values

  const updateMessagesFromChannel = useCallback(
    (channel: Channel, newMessage?: MessageResponse) => {
      // 🔥 FIX: Only update flow state and append new messages
      // Don't read from channel.state.messages to avoid buffering all messages

      if (newMessage) {
        // Append new message to our controlled state
        setMessages((prev) => {
          // Check if message already exists
          if (prev.some(msg => msg.id === newMessage.id)) {
            // Update existing message
            return prev.map(msg => msg.id === newMessage.id ? normaliseMessageDates(newMessage) : msg);
          }
          // Add new message and limit to MAX_RENDERED_MESSAGES
          const updated = [...prev, normaliseMessageDates(newMessage)];
          return updated.slice(-MAX_RENDERED_MESSAGES);
        });
      }

      // Update flow state from latest message or channel metadata
      const newest = newMessage ?? channel.state.messages.at(-1);
      const flowFromMessage = deriveFlowStateFromMessage(newest ? normaliseMessageDates(newest) : undefined);
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
          updateMessagesFromChannel(channel, event.message);
        }
      });

      subscribe("message.updated", (event: Event) => {
        console.log("[StreamChat] message.updated event received:", event.message?.id);
        if (event.message) {
          updateMessagesFromChannel(channel, event.message);
        }
      });

      subscribe("message.deleted", (event: Event) => {
        console.log("[StreamChat] message.deleted event received:", event.message?.id);
        // Remove deleted message from state
        if (event.message?.id) {
          setMessages((prev) => prev.filter((msg) => msg.id !== event.message!.id));
        }
      });

      subscribe("channel.updated", (event: Event) => {
        console.log("[StreamChat] channel.updated event received");
        updateMessagesFromChannel(channel);
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
    // Don't call updateMessagesFromChannel here - messages are already loaded via channel.query()
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
  }, [activeChannel, attachChannelListeners]);

  useEffect(() => {
    return () => {
      if (reasoningTimeout.current) {
        clearTimeout(reasoningTimeout.current);
      }
    };
  }, []);

  const selectChannel = useCallback((channel: Channel) => {
    console.log("[StreamChat] Selecting channel:", channel.cid);
    setActiveChannel((prev) => {
      if (prev?.cid === channel.cid) {
        console.log("[StreamChat] Channel already active");
        return prev;
      }
      console.log("[StreamChat] Switching to new channel");
      setReasoningState(initialReasoningState);
      // Reset pagination when switching channels
      loadedMessageCount.current = 0;
      setHasMoreMessages(false);
      return channel;
    });
  }, []);

  const loadMoreMessages = useCallback(async () => {
    if (!activeChannel || loadingMore || !hasMoreMessages) {
      console.log("[StreamChat] Skipping load more:", { hasChannel: !!activeChannel, loadingMore, hasMoreMessages });
      return;
    }

    console.log("[StreamChat] Loading more messages from server...");
    setLoadingMore(true);

    try {
      // Get the oldest message ID from currently loaded messages
      const currentMessages = activeChannel.state.messages || [];
      const oldestMessage = currentMessages[0];

      if (!oldestMessage) {
        console.log("[StreamChat] No messages to paginate from");
        setLoadingMore(false);
        setHasMoreMessages(false);
        return;
      }

      console.log("[StreamChat] Fetching", LOAD_MORE_BATCH_SIZE, "messages older than", oldestMessage.id);

      // 🔥 FIX: Use Stream Chat API to fetch older messages from server
      const response = await activeChannel.query({
        messages: {
          limit: LOAD_MORE_BATCH_SIZE,
          id_lt: oldestMessage.id, // Get messages older than this ID
        },
      });

      const olderMessages = (response.messages || []).map((msg) => normaliseMessageDates(msg));

      console.log("[StreamChat] Fetched", olderMessages.length, "older messages from server");

      // If we got fewer messages than requested, we've reached the end
      const hasMore = olderMessages.length >= LOAD_MORE_BATCH_SIZE;
      setHasMoreMessages(hasMore);

      // Prepend older messages to current state
      setMessages((prev) => {
        const combined = [...olderMessages, ...prev];
        // Limit total messages in memory
        const limited = combined.slice(-MAX_RENDERED_MESSAGES);
        loadedMessageCount.current = limited.length;
        return limited;
      });

      console.log("[StreamChat] Successfully loaded more messages, hasMore:", hasMore);
    } catch (err) {
      console.error("[StreamChat] Failed to load more messages:", err);
      setHasMoreMessages(false);
    } finally {
      setLoadingMore(false);
    }
  }, [activeChannel, loadingMore, hasMoreMessages]);

  const sendMessage = useCallback(
    async (text: string, messageData?: any) => {
      if (!activeChannel) return;
      // Allow empty text if we have attachments
      if (!text.trim() && (!messageData?.attachments || messageData.attachments.length === 0)) {
        return;
      }
      try {
        console.log("[StreamChat] Sending message:", text.substring(0, 50));
        console.log("[StreamChat] Attachments:", messageData?.attachments?.length || 0);

        const messagePayload = {
          text: text || '',  // Allow empty text with attachments
          ...(messageData?.attachments && { attachments: messageData.attachments }),
          ...(messageData?.mentioned_users && { mentioned_users: messageData.mentioned_users }),
          ...(messageData?.metadata && { metadata: messageData.metadata }),
        };

        const result = await activeChannel.sendMessage(messagePayload);
        console.log("[StreamChat] Message sent successfully, result:", result?.message?.id);
        console.log("[StreamChat] Message attachments in result:", result?.message?.attachments?.length || 0);

        // ✅ No need to update messages - message.new event will handle it

        return result;  // 🔥 CRITICAL: Return the result!
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

      console.log("[StreamChat] 🎯 Triggering action:", actionValue);

      try {
        // Send action as a Stream message with format: "action:action_name:incident_id"
        // This will trigger the webhook which handles action: prefix messages
        const actionMessage = actionValue.startsWith("action:") ? actionValue : `action:${actionValue}`;

        console.log("[StreamChat] Sending action message:", actionMessage);

        const result = await activeChannel.sendMessage({
          text: actionMessage,
          type: "regular",
        });

        console.log("[StreamChat] ✅ Action sent successfully:", result?.message?.id);

        // ✅ No need to update messages - message.new event will handle it
      } catch (err) {
        console.error("[StreamChat] ❌ Failed to trigger action:", err);
        throw err;
      }
    },
    [activeChannel, updateMessagesFromChannel],
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
      hasMoreMessages,
      loadingMore,
      selectChannel,
      sendMessage,
      triggerAction,
      loadMoreMessages,
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
      hasMoreMessages,
      loadingMore,
      selectChannel,
      sendMessage,
      triggerAction,
      loadMoreMessages,
    ],
  );

  return <TenantChatContext.Provider value={value}>{children}</TenantChatContext.Provider>;
}

export function useTenantChat() {
  const ctx = useContext(TenantChatContext);
  if (!ctx) {
    throw new Error("useTenantChat must be used within a TenantChatProvider");
  }
  return ctx;
}
