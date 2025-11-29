/**
 * AIChatContainer
 *
 * Main container that provides Stream Chat context and orchestrates the AI Support flow
 *
 * AUTHENTICATION:
 * Uses the same Stream Chat authentication as Classic Dashboard:
 * - Fetches per-user tokens from /api/chat/token backend endpoint
 * - Uses actual user identity from session.user.email
 * - Tokens are generated server-side with STREAM_CHAT_API_KEY/SECRET
 * - No client-side env vars required
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

  // Initialize Stream Chat client using same pattern as Classic Dashboard
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
        // Fetch token from backend (same as Classic Dashboard)
        console.log("[AI Support Container] Fetching token from /api/chat/token");
        const tokenRes = await fetch("/api/chat/token");

        if (!tokenRes.ok) {
          const error = await tokenRes.json().catch(() => ({}));
          throw new Error(error.error || "Unable to fetch Stream token");
        }

        const tokenData = await tokenRes.json();
        const { api_key, token, user_id, display_user_id } = tokenData;

        if (!api_key || !token || !user_id) {
          throw new Error("Stream credentials incomplete");
        }

        const { StreamChat } = await import("stream-chat");

        // Create singleton client (same pattern as Classic Dashboard)
        const streamClient = StreamChat.getInstance(api_key, { timeout: 8000 });

        // Connect with actual user identity (not fixed "prod-user")
        if (!streamClient.userID) {
          console.log("[AI Support Container] Connecting as", user_id);
          await streamClient.connectUser(
            {
              id: user_id,
              name: display_user_id ?? session.user.email ?? user_id,
            },
            token
          );
          console.log("[AI Support Container] ✅ Stream client connected successfully");
        } else if (streamClient.userID !== user_id) {
          console.log("[AI Support Container] User changed, reconnecting:", user_id);
          await streamClient.disconnectUser();
          await streamClient.connectUser(
            {
              id: user_id,
              name: display_user_id ?? session.user.email ?? user_id,
            },
            token
          );
          console.log("[AI Support Container] ✅ Stream client reconnected");
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

  // Use AI Support Flow hook (pass client to avoid duplicate token requests)
  const {
    channel,
    uiMode,
    payload,
    sendIntent,
    initializing,
    error: flowError,
  } = useAISupportFlow({ mode, autoInit: true, client });

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

  // Show initialization error (only if truly failed)
  if (error && !client) {
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
          <div className="space-y-3">
            <button
              onClick={() => window.location.reload()}
              className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              Retry
            </button>
            <a
              href="/"
              className="block w-full px-6 py-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg transition-colors"
            >
              Return to Home
            </a>
          </div>
        </div>
      </div>
    );
  }

  // Show client loading state
  if (!client) {
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

  // Normal operation - Stream Chat is available
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
