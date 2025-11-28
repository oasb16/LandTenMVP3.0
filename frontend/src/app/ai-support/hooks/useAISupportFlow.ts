/**
 * useAISupportFlow Hook
 *
 * Manages the AI Support Experience state machine and Stream Chat integration
 *
 * FALLBACK MODE:
 * This hook gracefully degrades when disabled or when Stream Chat fails.
 * Returns safe no-op functions instead of crashing.
 */

"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useSession } from "next-auth/react";
import type { Channel, Event, StreamChat } from "stream-chat";
import {
  type UIMode,
  type IntentType,
  type FlowState,
  type AISupportFlowHook,
  type Persona,
  isValidUIMode,
} from "@/types/ai-support";

interface UseAISupportFlowOptions {
  mode: "guided";
  autoInit?: boolean;
  disabled?: boolean; // NEW: Allows parent to disable this hook entirely
}

const DEFAULT_UI_MODE: UIMode = "idle";
const DEFAULT_PAYLOAD: Record<string, unknown> = {};

// Safe no-op function for when hook is disabled
const noopAsync = async () => {
  console.warn("[AI Support Flow] Hook is disabled - action ignored");
};

/**
 * Main hook for AI Support Experience
 */
export default function useAISupportFlow({
  mode,
  autoInit = true,
  disabled = false,
}: UseAISupportFlowOptions): AISupportFlowHook {
  const { data: session, status } = useSession();

  // Stream Chat client (will be passed from parent)
  const [client, setClient] = useState<StreamChat | null>(null);
  const [channel, setChannel] = useState<Channel | null>(null);

  // UI State
  const [uiMode, setUiMode] = useState<UIMode>(DEFAULT_UI_MODE);
  const [payload, setPayload] = useState<Record<string, unknown>>(DEFAULT_PAYLOAD);

  // Flow State
  const [flowState, setFlowState] = useState<FlowState | null>(null);

  // Loading & Error States
  const [loading, setLoading] = useState<boolean>(false);
  const [initializing, setInitializing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Refs for cleanup
  const eventListenersRef = useRef<Array<() => void>>([]);
  const isInitializedRef = useRef<boolean>(false);
  const channelIdRef = useRef<string | null>(null);

  /**
   * Initialize Stream Chat client
   * SKIP if disabled
   */
  useEffect(() => {
    if (disabled) {
      console.log("[AI Support Flow] Hook is disabled, skipping client init");
      return;
    }

    if (typeof window === "undefined") return;
    if (status === "loading") return;
    if (!session?.user?.email) {
      console.log("[AI Support] No session, skipping client init");
      return;
    }

    const initClient = async () => {
      try {
        // Dynamically import StreamChat to avoid SSR issues
        const { StreamChat } = await import("stream-chat");

        // Get API key from env
        const apiKey = process.env.NEXT_PUBLIC_STREAM_KEY;
        if (!apiKey) {
          console.warn("[AI Support Flow] Stream API key not configured - gracefully degrading");
          setError("Stream Chat is not configured");
          return;
        }

        // Fetch token from our API
        const tokenRes = await fetch("/api/chat/token");
        if (!tokenRes.ok) {
          throw new Error("Failed to fetch Stream token");
        }

        const tokenData = await tokenRes.json();
        const { token, user_id } = tokenData;

        if (!token || !user_id) {
          throw new Error("Invalid token response");
        }

        // Create or get singleton client
        const streamClient = StreamChat.getInstance(apiKey);

        // Connect user if not already connected
        if (!streamClient.userID) {
          await streamClient.connectUser(
            {
              id: user_id,
              name: session.user.email,
            },
            token
          );
          console.log("[AI Support] Stream client connected");
        }

        setClient(streamClient);
      } catch (err) {
        console.error("[AI Support] Failed to initialize Stream client:", err);
        setError(err instanceof Error ? err.message : "Failed to initialize chat");
      }
    };

    initClient();
  }, [session, status, disabled]);

  /**
   * Initialize AI Support channel
   * SKIP if disabled or no client
   */
  useEffect(() => {
    if (disabled) return;
    if (!client || !session?.user?.email) return;
    if (isInitializedRef.current) return;
    if (!autoInit) return;

    const initChannel = async () => {
      setInitializing(true);
      setError(null);

      try {
        const persona = (session.user.persona as Persona) || "tenant";
        const userId = session.user.email;

        // Create unique channel for this AI support session
        const channelId = `ai-support-${userId}-${Date.now()}`;
        channelIdRef.current = channelId;

        console.log("[AI Support] Creating channel:", channelId);

        const ch = client.channel("messaging", channelId, {
          name: "AI Support Session",
          ai_mode: mode,
          persona,
          created_by: userId,
        });

        await ch.watch();
        setChannel(ch);

        // Initialize flow state
        setFlowState({
          session_id: channelId,
          incident_id: null,
          persona,
          current_mode: "idle",
          selected_item: null,
          selected_reason: null,
          resolution_data: null,
          chat_channel_id: channelId,
        });

        // Send init event to backend
        await ch.sendEvent({
          type: "ai_intent",
          intent: "session_init",
          payload: {
            persona,
            mode: "guided",
          },
        });

        console.log("[AI Support] Session initialized");
        isInitializedRef.current = true;
        setInitializing(false);
      } catch (err) {
        console.error("[AI Support] Failed to initialize channel:", err);
        setError(err instanceof Error ? err.message : "Failed to initialize session");
        setInitializing(false);
      }
    };

    initChannel();
  }, [client, session, autoInit, mode, disabled]);

  /**
   * Attach event listeners to channel
   * SKIP if disabled
   */
  useEffect(() => {
    if (disabled) return;
    if (!channel) return;

    console.log("[AI Support] Attaching event listeners");

    // Cleanup previous listeners
    eventListenersRef.current.forEach((cleanup) => cleanup());
    eventListenersRef.current = [];

    // Listen for AI state updates
    const aiStateListener = channel.on("ai_state", (event: Event) => {
      console.log("[AI Support] Received ai_state event:", event);

      const uiModeValue = (event as any).ui_mode;
      const payloadValue = (event as any).payload || {};

      if (isValidUIMode(uiModeValue)) {
        setUiMode(uiModeValue);
        setPayload(payloadValue);

        // Update flow state
        setFlowState((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            current_mode: uiModeValue,
          };
        });
      }
    });

    // Listen for custom flow updates
    const flowUpdateListener = channel.on("custom.flow_update", (event: Event) => {
      console.log("[AI Support] Received flow_update event:", event);

      const flowData = (event as any).payload || {};

      setFlowState((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          ...flowData,
        };
      });
    });

    // Listen for errors
    const errorListener = channel.on("custom.error", (event: Event) => {
      console.error("[AI Support] Received error event:", event);

      const errorMessage = (event as any).message || "An error occurred";
      setError(errorMessage);
    });

    // Store cleanup functions
    eventListenersRef.current = [
      () => aiStateListener.unsubscribe(),
      () => flowUpdateListener.unsubscribe(),
      () => errorListener.unsubscribe(),
    ];

    // Cleanup on unmount
    return () => {
      eventListenersRef.current.forEach((cleanup) => cleanup());
      eventListenersRef.current = [];
    };
  }, [channel, disabled]);

  /**
   * Send an intent to the backend
   * SAFE NO-OP if disabled or no channel
   */
  const sendIntent = useCallback(
    async (intent: IntentType, intentPayload: Record<string, unknown> = {}) => {
      if (disabled) {
        console.warn("[AI Support] Hook is disabled - cannot send intent");
        return;
      }

      if (!channel) {
        console.error("[AI Support] Cannot send intent: no channel available");
        return;
      }

      setLoading(true);
      setError(null);

      try {
        console.log("[AI Support] Sending intent:", intent, intentPayload);

        await channel.sendEvent({
          type: "ai_intent",
          intent,
          payload: intentPayload,
        });

        console.log("[AI Support] Intent sent successfully");
      } catch (err) {
        console.error("[AI Support] Failed to send intent:", err);
        setError(err instanceof Error ? err.message : "Failed to send message");
      } finally {
        setLoading(false);
      }
    },
    [channel, disabled]
  );

  /**
   * Reset the session
   * SAFE NO-OP if disabled
   */
  const resetSession = useCallback(async () => {
    if (disabled) {
      console.warn("[AI Support] Hook is disabled - cannot reset session");
      return;
    }

    console.log("[AI Support] Resetting session");

    // Clear state
    setUiMode(DEFAULT_UI_MODE);
    setPayload(DEFAULT_PAYLOAD);
    setFlowState(null);
    setError(null);

    // Cleanup event listeners
    eventListenersRef.current.forEach((cleanup) => cleanup());
    eventListenersRef.current = [];

    // Stop watching channel
    if (channel) {
      try {
        await channel.stopWatching();
      } catch (err) {
        console.warn("[AI Support] Error stopping channel watch:", err);
      }
    }

    setChannel(null);
    isInitializedRef.current = false;
    channelIdRef.current = null;
  }, [channel, disabled]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      eventListenersRef.current.forEach((cleanup) => cleanup());
      eventListenersRef.current = [];
    };
  }, []);

  // FALLBACK MODE: Return safe no-op values if disabled
  if (disabled) {
    return {
      channel: null,
      uiMode: DEFAULT_UI_MODE,
      payload: DEFAULT_PAYLOAD,
      flowState: null,
      loading: false,
      initializing: false,
      error: "AI Support is currently unavailable",
      sendIntent: noopAsync,
      resetSession: noopAsync,
    };
  }

  // Normal operation
  return {
    channel,
    uiMode,
    payload,
    flowState,
    loading,
    initializing,
    error,
    sendIntent,
    resetSession,
  };
}
