"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  ReactNode,
} from "react";
import { StreamChat, Channel as StreamChannel, Event, MessageResponse } from "stream-chat";

// ============================================================================
// TYPES
// ============================================================================

interface FlowState {
  type: "incident" | "discovery" | "job" | "approval" | "completion" | "general" | null;
  stage: string | null;
  incident_id?: string;
  job_id?: string;
  metadata?: Record<string, any>;
}

interface ReasoningState {
  intent: string | null;
  confidence: number | null;
  entities: Record<string, any>;
  last_updated: string | null;
}

interface StreamChatContextValue {
  // Stream Client
  client: StreamChat | null;
  isConnected: boolean;

  // Current Channel
  activeChannel: StreamChannel | null;
  selectChannel: (channel: StreamChannel) => Promise<void>;

  // Channels List
  channels: StreamChannel[];
  refreshChannels: () => Promise<void>;

  // Messages
  messages: MessageResponse[];
  sendMessage: (text: string, metadata?: Record<string, any>) => Promise<void>;

  // Actions
  triggerAction: (actionValue: string) => Promise<void>;

  // Flow State (from backend)
  flowState: FlowState;
  reasoningState: ReasoningState;

  // Agent Control
  agentEnabled: boolean;
  setAgentEnabled: (enabled: boolean) => void;

  // User Info
  userInfo: {
    id: string;
    email: string;
    display: string;
    persona: string;
  } | null;

  // Error Handling
  error: string | null;
  clearError: () => void;

  // Loading States
  isLoading: boolean;
  isSending: boolean;
}

// ============================================================================
// CONTEXT
// ============================================================================

const StreamChatContext = createContext<StreamChatContextValue | null>(null);

export const useStreamChat = () => {
  const context = useContext(StreamChatContext);
  if (!context) {
    throw new Error("useStreamChat must be used within StreamChatProvider");
  }
  return context;
};

// ============================================================================
// PROVIDER
// ============================================================================

interface StreamChatProviderProps {
  children: ReactNode;
  persona: string;
}

export function StreamChatProvider({ children, persona }: StreamChatProviderProps) {
  // Core State
  const [client, setClient] = useState<StreamChat | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [activeChannel, setActiveChannel] = useState<StreamChannel | null>(null);
  const [channels, setChannels] = useState<StreamChannel[]>([]);
  const [messages, setMessages] = useState<MessageResponse[]>([]);

  // Agent State
  const [agentEnabled, setAgentEnabled] = useState(true);

  // Flow State (synced from backend custom events)
  const [flowState, setFlowState] = useState<FlowState>({
    type: null,
    stage: null,
    metadata: {},
  });

  const [reasoningState, setReasoningState] = useState<ReasoningState>({
    intent: null,
    confidence: null,
    entities: {},
    last_updated: null,
  });

  // User Info
  const [userInfo, setUserInfo] = useState<StreamChatContextValue["userInfo"]>(null);

  // UI State
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);

  // ============================================================================
  // INITIALIZE STREAM CHAT CLIENT
  // ============================================================================

  useEffect(() => {
    let chatClient: StreamChat | null = null;

    const initializeClient = async () => {
      try {
        setIsLoading(true);
        console.log("[StreamChatContext] Initializing client for persona:", persona);

        // Fetch token from backend
        const res = await fetch("/api/chat/token");
        if (!res.ok) {
          const contentType = res.headers.get("content-type") || "";
          let msg = "Token fetch failed";
          if (contentType.includes("application/json")) {
            const json = await res.json().catch(() => null);
            msg = json?.detail || JSON.stringify(json);
          } else {
            msg = await res.text();
          }
          throw new Error(msg);
        }

        const data = await res.json();
        console.log("[StreamChatContext] Token received for user:", data.user_id);

        // Initialize Stream Chat client
        chatClient = StreamChat.getInstance(data.api_key);

        const userId = data.user_id as string;
        const displayId = (data.display_user_id as string | undefined) ?? userId;
        const email = (data.email as string | undefined) ?? displayId;

        // Connect user
        await chatClient.connectUser(
          {
            id: userId,
            name: displayId,
            email: email,
          },
          data.token
        );

        console.log("[StreamChatContext] User connected successfully");

        setClient(chatClient);
        setIsConnected(true);
        setUserInfo({
          id: userId,
          email,
          display: displayId,
          persona,
        });

        // Watch initial channel
        const initialChannelId = data.channel_id || `${persona}-general`;
        const initialChannel = chatClient.channel("messaging", initialChannelId);
        await initialChannel.watch();
        setActiveChannel(initialChannel);

        console.log("[StreamChatContext] Initial channel loaded:", initialChannelId);

        setIsLoading(false);
      } catch (err) {
        console.error("[StreamChatContext] Initialization error:", err);
        setError(err instanceof Error ? err.message : "Stream Chat initialization failed");
        setIsLoading(false);
      }
    };

    initializeClient();

    return () => {
      if (chatClient) {
        console.log("[StreamChatContext] Disconnecting client");
        chatClient.disconnectUser().catch(console.error);
      }
    };
  }, [persona]);

  // ============================================================================
  // SUBSCRIBE TO CHANNEL MESSAGES
  // ============================================================================

  useEffect(() => {
    if (!activeChannel) {
      setMessages([]);
      return;
    }

    console.log("[StreamChatContext] Subscribing to channel:", activeChannel.id);

    // Load existing messages
    const loadMessages = async () => {
      try {
        const state = activeChannel.state;
        const msgs = Array.from(state.messages.values())
          .filter((msg): msg is MessageResponse => msg !== undefined)
          .sort((a, b) => {
            const aTime = new Date(a.created_at || 0).getTime();
            const bTime = new Date(b.created_at || 0).getTime();
            return aTime - bTime;
          });

        setMessages(msgs);
        console.log("[StreamChatContext] Loaded", msgs.length, "existing messages");
      } catch (err) {
        console.error("[StreamChatContext] Error loading messages:", err);
      }
    };

    loadMessages();

    // Subscribe to new messages
    const handleNewMessage = (event: Event) => {
      console.log("[StreamChatContext] New message event:", event.type);

      if (event.message) {
        setMessages((prev) => {
          // Check if message already exists
          const exists = prev.some((msg) => msg.id === event.message!.id);
          if (exists) {
            console.log("[StreamChatContext] Message already exists, skipping");
            return prev;
          }
          console.log("[StreamChatContext] Adding new message to state");
          return [...prev, event.message as MessageResponse];
        });
      }
    };

    const handleMessageUpdated = (event: Event) => {
      console.log("[StreamChatContext] Message updated event");
      if (event.message) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === event.message!.id ? (event.message as MessageResponse) : msg
          )
        );
      }
    };

    const handleMessageDeleted = (event: Event) => {
      console.log("[StreamChatContext] Message deleted event");
      if (event.message) {
        setMessages((prev) => prev.filter((msg) => msg.id !== event.message!.id));
      }
    };

    // Custom flow update events from backend
    const handleCustomEvent = (event: Event) => {
      console.log("[StreamChatContext] Custom event:", event.type, event);

      if (event.type === "custom.flow_update") {
        console.log("[StreamChatContext] Flow state updated:", event);
        setFlowState({
          type: event.flow_type || null,
          stage: event.stage || null,
          incident_id: event.incident_id,
          job_id: event.job_id,
          metadata: event.metadata || {},
        });
      }

      if (event.type === "custom.reasoning_update") {
        console.log("[StreamChatContext] Reasoning state updated:", event);
        setReasoningState({
          intent: event.intent || null,
          confidence: event.confidence || null,
          entities: event.entities || {},
          last_updated: new Date().toISOString(),
        });
      }
    };

    // Attach listeners
    activeChannel.on("message.new", handleNewMessage);
    activeChannel.on("message.updated", handleMessageUpdated);
    activeChannel.on("message.deleted", handleMessageDeleted);
    activeChannel.on(handleCustomEvent);

    return () => {
      console.log("[StreamChatContext] Unsubscribing from channel:", activeChannel.id);
      activeChannel.off("message.new", handleNewMessage);
      activeChannel.off("message.updated", handleMessageUpdated);
      activeChannel.off("message.deleted", handleMessageDeleted);
      activeChannel.off(handleCustomEvent);
    };
  }, [activeChannel]);

  // ============================================================================
  // LOAD CHANNELS LIST
  // ============================================================================

  const refreshChannels = useCallback(async () => {
    if (!client || !userInfo) return;

    try {
      console.log("[StreamChatContext] Refreshing channels for user:", userInfo.id);

      const filters = {
        members: { $in: [userInfo.id] },
        type: "messaging",
      };

      const sort = [{ last_message_at: -1 as const }];

      const channelsResponse = await client.queryChannels(filters, sort, {
        state: true,
        watch: true,
        presence: true,
        limit: 30,
      });

      setChannels(channelsResponse);
      console.log("[StreamChatContext] Loaded", channelsResponse.length, "channels");
    } catch (err) {
      console.error("[StreamChatContext] Error loading channels:", err);
    }
  }, [client, userInfo]);

  useEffect(() => {
    if (isConnected && userInfo) {
      refreshChannels();
    }
  }, [isConnected, userInfo, refreshChannels]);

  // ============================================================================
  // SELECT CHANNEL
  // ============================================================================

  const selectChannel = useCallback(
    async (channel: StreamChannel) => {
      try {
        console.log("[StreamChatContext] Selecting channel:", channel.id);
        await channel.watch();
        await channel.markRead();
        setActiveChannel(channel);
      } catch (err) {
        console.error("[StreamChatContext] Error selecting channel:", err);
        setError(err instanceof Error ? err.message : "Failed to select channel");
      }
    },
    []
  );

  // ============================================================================
  // SEND MESSAGE
  // ============================================================================

  const sendMessage = useCallback(
    async (text: string, metadata?: Record<string, any>) => {
      if (!activeChannel || !userInfo) {
        console.error("[StreamChatContext] Cannot send: no active channel or user");
        return;
      }

      try {
        setIsSending(true);
        console.log("[StreamChatContext] Sending message:", text.substring(0, 50));

        // Send message to Stream
        const messageData = {
          text,
          metadata: {
            ...metadata,
            agentEnabled,
            persona,
          },
        };

        await activeChannel.sendMessage(messageData);

        console.log("[StreamChatContext] Message sent successfully");

        // If agent is enabled, trigger backend processing
        if (agentEnabled) {
          console.log("[StreamChatContext] Triggering agent processing");

          const history = messages
            .slice(-10)
            .map((msg) => `${msg.user?.name || msg.user?.id}: ${msg.text || ""}`)
            .join("\n");

          // Call backend agent endpoint (fire and forget)
          fetch("/api/chat/agent", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              channel_id: activeChannel.id,
              prompt: text,
              persona,
              context: history,
              requesting_user: userInfo.email,
            }),
          }).catch((err) => {
            console.error("[StreamChatContext] Agent processing error:", err);
          });
        }
      } catch (err) {
        console.error("[StreamChatContext] Error sending message:", err);
        setError(err instanceof Error ? err.message : "Failed to send message");
      } finally {
        setIsSending(false);
      }
    },
    [activeChannel, userInfo, agentEnabled, persona, messages]
  );

  // ============================================================================
  // TRIGGER ACTION (Button Click)
  // ============================================================================

  const triggerAction = useCallback(
    async (actionValue: string) => {
      if (!activeChannel || !client) {
        console.error("[StreamChatContext] Cannot trigger action: no channel/client");
        return;
      }

      try {
        console.log("[StreamChatContext] Triggering action:", actionValue);

        const user = client.user || {};

        // Send action to backend webhook
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
          channel_id: activeChannel.id,
        };

        const res = await fetch("http://localhost:8000/ai/stream-webhook", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          throw new Error(`Action failed: ${res.status}`);
        }

        console.log("[StreamChatContext] Action triggered successfully");
      } catch (err) {
        console.error("[StreamChatContext] Error triggering action:", err);
        setError(err instanceof Error ? err.message : "Action failed");
      }
    },
    [activeChannel, client]
  );

  // ============================================================================
  // CONTEXT VALUE
  // ============================================================================

  const value: StreamChatContextValue = useMemo(
    () => ({
      client,
      isConnected,
      activeChannel,
      selectChannel,
      channels,
      refreshChannels,
      messages,
      sendMessage,
      triggerAction,
      flowState,
      reasoningState,
      agentEnabled,
      setAgentEnabled,
      userInfo,
      error,
      clearError: () => setError(null),
      isLoading,
      isSending,
    }),
    [
      client,
      isConnected,
      activeChannel,
      selectChannel,
      channels,
      refreshChannels,
      messages,
      sendMessage,
      triggerAction,
      flowState,
      reasoningState,
      agentEnabled,
      userInfo,
      error,
      isLoading,
      isSending,
    ]
  );

  return <StreamChatContext.Provider value={value}>{children}</StreamChatContext.Provider>;
}
