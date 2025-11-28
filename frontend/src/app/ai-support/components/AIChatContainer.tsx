/**
 * AIChatContainer
 *
 * Main container that provides Stream Chat context and orchestrates the AI Support flow
 */

"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Chat } from "stream-chat-react";
import type { StreamChat } from "stream-chat";

import AIChatAssistantLauncher from "./AIChatAssistantLauncher";
import AIChatPanel from "./AIChatPanel";
import useAISupportFlow from "../hooks/useAISupportFlow";

// Import Stream Chat React styles
import "stream-chat-react/dist/css/v2/index.css";

interface AIChatContainerProps {
  mode: "guided";
}

export default function AIChatContainer({ mode }: AIChatContainerProps) {
  const { data: session, status } = useSession();
  const [client, setClient] = useState<StreamChat | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);

  // Initialize Stream Chat client
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (status === "loading") return;

    if (!session?.user?.email) {
      console.log("[AI Support Container] No session, skipping client init");
      return;
    }

    let mounted = true;

    const initClient = async () => {
      try {
        const { StreamChat } = await import("stream-chat");

        const apiKey = process.env.NEXT_PUBLIC_STREAM_KEY;
        if (!apiKey) {
          throw new Error("NEXT_PUBLIC_STREAM_KEY not configured");
        }

        // Fetch token from API
        const tokenRes = await fetch("/api/chat/token");
        if (!tokenRes.ok) {
          const errorData = await tokenRes.json().catch(() => ({}));
          throw new Error(errorData.error || "Failed to fetch Stream token");
        }

        const tokenData = await tokenRes.json();
        const { token, user_id } = tokenData;

        if (!token || !user_id) {
          throw new Error("Invalid token response");
        }

        // Create singleton client
        const streamClient = StreamChat.getInstance(apiKey, { timeout: 8000 });

        // Connect user if not already connected
        if (!streamClient.userID) {
          await streamClient.connectUser(
            {
              id: user_id,
              name: session.user.email,
            },
            token
          );
          console.log("[AI Support Container] Stream client connected");
        }

        if (mounted) {
          setClient(streamClient);
        }
      } catch (err) {
        console.error("[AI Support Container] Failed to initialize Stream client:", err);
        if (mounted) {
          setClientError(err instanceof Error ? err.message : "Failed to initialize chat");
        }
      }
    };

    initClient();

    return () => {
      mounted = false;
    };
  }, [session, status]);

  // Use AI Support Flow hook
  const {
    channel,
    uiMode,
    payload,
    sendIntent,
    initializing,
    error: flowError,
  } = useAISupportFlow({ mode, autoInit: true });

  const error = clientError || flowError;

  // Show loading while auth is loading
  if (status === "loading") {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Show auth required state
  if (status === "unauthenticated" || !session?.user) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center max-w-md p-8">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
            Authentication Required
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            Please sign in to access AI Support
          </p>
          <a
            href="/auth/signin"
            className="inline-block px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            Sign In
          </a>
        </div>
      </div>
    );
  }

  // Show client loading/error state
  if (!client) {
    if (error) {
      return (
        <div className="w-full h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
          <div className="text-center max-w-md p-8">
            <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-red-600 dark:text-red-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Connection Error
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-4">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className="w-full h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">
            Connecting to AI Support...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-screen relative bg-gray-50 dark:bg-gray-900">
      <Chat client={client} theme="str-chat__theme-light">
        <AIChatAssistantLauncher autoOpen={true}>
          <AIChatPanel
            channel={channel}
            uiMode={uiMode}
            payload={payload}
            sendIntent={sendIntent}
            initializing={initializing}
            error={error}
          />
        </AIChatAssistantLauncher>
      </Chat>
    </div>
  );
}
