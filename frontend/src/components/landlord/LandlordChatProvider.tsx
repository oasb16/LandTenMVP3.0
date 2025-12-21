"use client";

import { ReactNode, useEffect, useState, useCallback, useMemo, createContext, useContext } from "react";
import { Channel, StreamChat, type MessageResponse } from "stream-chat";

type ContractorChatContextValue = {
  client: StreamChat | null;
  activeChannel: Channel | null;
  messages: MessageResponse[];
  loading: boolean;
  error: string | null;
  sendMessage: (text: string, messageData?: any) => Promise<any>;
  contractorId: string;
  contractorEmail: string;
};

const LandlordChatContext = createContext<ContractorChatContextValue | undefined>(undefined);

type Props = {
  children: ReactNode;
  contractorId: string;
  contractorEmail: string;
};

const INITIAL_MESSAGE_LOAD = 20;

export function LandlordChatProvider({ children, contractorId, contractorEmail }: Props) {
  const [client, setClient] = useState<StreamChat | null>(null);
  const [activeChannel, setActiveChannel] = useState<Channel | null>(null);
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize Stream client and channel
  useEffect(() => {
    let isMounted = true;
    let streamClient: StreamChat | null = null;

    const initialize = async () => {
      setLoading(true);
      setError(null);

      try {
        console.log("[ContractorChat] Initializing for:", contractorEmail);

        // Fetch token from contractor-specific endpoint
        const tokenRes = await fetch(
          `/api/chat/contractor-token?email=${encodeURIComponent(contractorEmail)}&contractor_id=${encodeURIComponent(contractorId)}`
        );

        if (!tokenRes.ok) {
          throw new Error("Failed to fetch Stream token");
        }

        const tokenData = await tokenRes.json();
        const { api_key, token, user_id, channel_id } = tokenData;

        if (!api_key || !token || !user_id) {
          throw new Error("Stream credentials incomplete");
        }

        // Create Stream client (use unique instance, not singleton)
        // This avoids conflicts with other Stream sessions in the app
        streamClient = new StreamChat(api_key, { timeout: 6000 });

        console.log("[ContractorChat] Connecting user:", user_id);

        // Connect user
        await streamClient.connectUser(
          {
            id: user_id,
            name: contractorEmail,
          },
          token
        );

        console.log("[ContractorChat] Connected to Stream as:", user_id);

        if (!isMounted) {
          await streamClient.disconnectUser();
          return;
        }

        setClient(streamClient);

        // Query channels
        const filters = {
          type: "messaging",
          members: { $in: [user_id] },
        };
        const sort = { last_message_at: -1 as const };
        const channels = await streamClient.queryChannels(filters, sort, {
          watch: true,
          state: true,
        });

        console.log("[ContractorChat] Found", channels.length, "channels");

        // Get default channel (use channel_id if provided, otherwise first channel)
        const defaultChannel =
          channels.find((ch) => ch.id === channel_id || ch.cid === channel_id || ch.cid === `messaging:${channel_id}`) ||
          channels[0] ||
          null;

        if (defaultChannel) {
          console.log("[ContractorChat] Loading channel:", defaultChannel.cid);

          // Load initial messages
          const channelState = await defaultChannel.query({
            messages: { limit: INITIAL_MESSAGE_LOAD },
          });

          if (!isMounted) {
            await streamClient.disconnectUser();
            return;
          }

          setActiveChannel(defaultChannel);
          setMessages(channelState.messages || []);

          // Subscribe to new messages
          defaultChannel.on("message.new", (event) => {
            console.log("[ContractorChat] New message:", event.message?.id);
            if (event.message) {
              setMessages((prev) => {
                // Avoid duplicates
                if (prev.some((msg) => msg.id === event.message!.id)) {
                  return prev.map((msg) => (msg.id === event.message!.id ? event.message! : msg));
                }
                return [...prev, event.message!];
              });
            }
          });

          defaultChannel.on("message.updated", (event) => {
            if (event.message) {
              setMessages((prev) =>
                prev.map((msg) => (msg.id === event.message!.id ? event.message! : msg))
              );
            }
          });
        }

        setLoading(false);
      } catch (err) {
        console.error("[ContractorChat] Initialization error:", err);
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to connect to chat");
          setLoading(false);
        }
        // Clean up on error
        if (streamClient) {
          try {
            await streamClient.disconnectUser();
          } catch (disconnectErr) {
            console.warn("[ContractorChat] Failed to disconnect on error:", disconnectErr);
          }
        }
      }
    };

    initialize();

    return () => {
      isMounted = false;
      // Clean up: disconnect when component unmounts
      if (streamClient) {
        streamClient.disconnectUser().catch((err) => {
          console.warn("[ContractorChat] Cleanup disconnect error:", err);
        });
      }
    };
  }, [contractorId, contractorEmail]);

  const sendMessage = useCallback(
    async (text: string, messageData?: any) => {
      if (!activeChannel) {
        throw new Error("No active channel");
      }

      if (!text.trim() && (!messageData?.attachments || messageData.attachments.length === 0)) {
        return;
      }

      const messagePayload = {
        text: text || "",
        ...(messageData?.attachments && { attachments: messageData.attachments }),
        ...(messageData?.mentioned_users && { mentioned_users: messageData.mentioned_users }),
        metadata: {
          ...(messageData?.metadata || {}),
          contractor_id: contractorId, // Include contractor_id in metadata
          persona: "contractor_onboarding",
        },
      };

      const result = await activeChannel.sendMessage(messagePayload);

      // Forward to AI webhook if agent is enabled
      if (messageData?.metadata?.agentEnabled !== false) {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/api$/, "") || window.location.origin;

        await fetch(`${backendUrl}/ai/stream-webhook`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            type: "message.new",
            message: {
              text: text || "",
              attachments: messageData?.attachments || [],
              user: {
                id: contractorEmail,
                name: contractorEmail,
                is_bot: false,
              },
              metadata: messagePayload.metadata,
            },
            user: {
              id: contractorEmail,
              name: contractorEmail,
              is_bot: false,
            },
            channel_id: activeChannel.cid,
            channel_type: "messaging",
          }),
        });
      }

      return result;
    },
    [activeChannel, contractorId, contractorEmail]
  );

  const value = useMemo<ContractorChatContextValue>(
    () => ({
      client,
      activeChannel,
      messages,
      loading,
      error,
      sendMessage,
      contractorId,
      contractorEmail,
    }),
    [client, activeChannel, messages, loading, error, sendMessage, contractorId, contractorEmail]
  );

  return <LandlordChatContext.Provider value={value}>{children}</LandlordChatContext.Provider>;
}

export function useLandlordChat() {
  const ctx = useContext(LandlordChatContext);
  if (!ctx) {
    throw new Error("useLandlordChat must be used within LandlordChatProvider");
  }
  return ctx;
}
