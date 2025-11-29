/**
 * useAISupportFlow Hook
 *
 * Manages the AI Support Experience state machine and Stream Chat integration
 *
 * AUTHENTICATION:
 * Uses the same Stream Chat authentication as Classic Dashboard:
 * - Receives pre-initialized client from AIChatContainer (avoids duplicate token requests)
 * - AIChatContainer fetches tokens from /api/chat/token backend endpoint
 * - Uses actual user identity from session.user.email
 * - Tokens are generated server-side with STREAM_CHAT_API_KEY/SECRET
 * - No client-side env vars required
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
  client?: StreamChat | null; // Accept client from parent to avoid duplicate token requests
}

const DEFAULT_UI_MODE: UIMode = "idle";
const DEFAULT_PAYLOAD: Record<string, unknown> = {};

/**
 * Main hook for AI Support Experience
 */
export default function useAISupportFlow({
  mode,
  autoInit = true,
  client: externalClient,
}: UseAISupportFlowOptions): AISupportFlowHook {
  const { data: session, status } = useSession();

  // Use client from parent (AIChatContainer) to avoid duplicate token requests
  const [client, setClient] = useState<StreamChat | null>(externalClient ?? null);
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

  console.log("[AI Support Flow] 🔵 Hook called - externalClient:", !!externalClient, "client:", !!client, "channel:", !!channel);

  /**
   * Sync client from parent (AIChatContainer owns client initialization)
   */
  useEffect(() => {
    console.log("[AI Support Flow] 🟡 Client sync effect fired - externalClient:", !!externalClient);
    if (externalClient) {
      console.log("[AI Support Flow] ✅ Using client from parent container");
      setClient(externalClient);
    } else {
      console.log("[AI Support Flow] ⚠️ No external client yet");
    }
  }, [externalClient]);

  /**
   * Initialize AI Support channel
   */
  useEffect(() => {
    console.log("[AI Support Flow] 🟡 Channel init effect fired - checking conditions");

    if (!client) {
      console.log("[AI Support Flow] ⚠️ Skipping: no client");
      return;
    }

    if (!session?.user?.email) {
      console.log("[AI Support Flow] ⚠️ Skipping: no session/email");
      return;
    }

    if (isInitializedRef.current) {
      console.log("[AI Support Flow] ⚠️ Skipping: already initialized");
      return;
    }

    if (!autoInit) {
      console.log("[AI Support Flow] ⚠️ Skipping: autoInit disabled");
      return;
    }

    console.log("[AI Support Flow] ✅ All conditions met, starting channel init");

    const initChannel = async () => {
      setInitializing(true);
      setError(null);

      try {
        const persona = (session.user.persona as Persona) || "tenant";
        const userId = session.user.email;

        console.log("[AI Support Flow] 📡 Step 1: Sanitizing email for channel ID");
        // Sanitize email for channel ID (Stream only allows letters, numbers, and !-_)
        const sanitizedEmail = userId.toLowerCase().replace(/[^a-z0-9-_]/g, "-");
        console.log("[AI Support Flow] ✅ Step 1 COMPLETE: Email sanitized:", sanitizedEmail);

        // Create unique channel for this AI support session
        const channelId = `ai-support-${sanitizedEmail}-${Date.now()}`;
        channelIdRef.current = channelId;

        console.log("[AI Support Flow] 📡 Step 2: Creating channel:", channelId);

        const ch = client.channel("messaging", channelId, {
          name: "AI Support Session",
          ai_mode: mode,
          persona,
        });
        console.log("[AI Support Flow] ✅ Step 2 COMPLETE: Channel object created");

        console.log("[AI Support Flow] 📡 Step 3: Watching channel (creates if doesn't exist)");
        await ch.watch();
        console.log("[AI Support Flow] ✅ Step 3 COMPLETE: Channel watch successful");

        console.log("[AI Support Flow] 📡 Step 4: Setting channel state");
        setChannel(ch);
        console.log("[AI Support Flow] ✅ Step 4 COMPLETE: Channel state updated");

        console.log("[AI Support Flow] 📡 Step 5: Initializing flow state");
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
        console.log("[AI Support Flow] ✅ Step 5 COMPLETE: Flow state initialized");

        console.log("[AI Support Flow] 📡 Step 6: Sending session_init event to backend");
        // Send init event to backend
        await ch.sendEvent({
          type: "ai_intent",
          intent: "session_init",
          payload: {
            persona,
            mode: "guided",
          },
        });
        console.log("[AI Support Flow] ✅ Step 6 COMPLETE: Session init event sent");

        console.log("[AI Support Flow] 🎉 ALL STEPS COMPLETE - AI Support session initialized");
        isInitializedRef.current = true;
        setInitializing(false);
      } catch (err) {
        console.error("[AI Support Flow] ❌ CHANNEL INITIALIZATION FAILED:", err);
        setError(err instanceof Error ? err.message : "Failed to initialize session");
        setInitializing(false);
      }
    };

    initChannel();
  }, [client, session, autoInit, mode]);

  /**
   * Attach event listeners to channel
   */
  useEffect(() => {
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
  }, [channel]);

  /**
   * Send an intent to the backend
   */
  const sendIntent = useCallback(
    async (intent: IntentType, intentPayload: Record<string, unknown> = {}) => {
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
    [channel]
  );

  /**
   * Reset the session
   */
  const resetSession = useCallback(async () => {
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
  }, [channel]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      eventListenersRef.current.forEach((cleanup) => cleanup());
      eventListenersRef.current = [];
    };
  }, []);

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
