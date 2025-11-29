/**
 * AIChatContainer
 *
 * Main container that provides Stream Chat context and orchestrates the AI Support flow
 *
 * FALLBACK MODE:
 * This component gracefully degrades when Stream Chat is unavailable.
 * Missing env vars or connection failures show a friendly message instead of crashing.
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
  const [fatalError, setFatalError] = useState<boolean>(false);

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
        // Check for required environment variables BEFORE attempting anything
        const apiKey = process.env.NEXT_PUBLIC_STREAM_KEY;

        if (!apiKey) {
          console.warn("[AI Support Container] NEXT_PUBLIC_STREAM_KEY not configured - entering fallback mode");
          console.warn("[AI Support Container] The rest of the app will continue to work normally");
          if (mounted) {
            setFatalError(true);
            setClientError("Stream Chat is not configured. Please contact support or try again later.");
          }
          return;
        }

        const { StreamChat } = await import("stream-chat");

        // Fetch token from API
        const tokenRes = await fetch("/api/chat/token");
        if (!tokenRes.ok) {
          const errorData = await tokenRes.json().catch(() => ({}));
          throw new Error(errorData.error || "Failed to fetch Stream token");
        }

        const tokenData = await tokenRes.json();
        const { token, user_id } = tokenData;

        if (!token || !user_id) {
          throw new Error("Invalid token response from server");
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
          console.log("[AI Support Container] Stream client connected successfully");
        }

        if (mounted) {
          setClient(streamClient);
          setFatalError(false); // Clear any previous fatal error
        }
      } catch (err) {
        console.error("[AI Support Container] Failed to initialize Stream client:", err);
        if (mounted) {
          setClientError(err instanceof Error ? err.message : "Failed to initialize chat");
          setFatalError(true);
        }
      }
    };

    initClient();

    return () => {
      mounted = false;
    };
  }, [session, status]);

  // Use AI Support Flow hook - disabled if fatal error
  const {
    channel,
    uiMode,
    payload,
    sendIntent,
    initializing,
    error: flowError,
  } = useAISupportFlow({
    mode,
    autoInit: !fatalError, // Don't auto-init if we have a fatal error
    disabled: fatalError,   // Pass disabled flag to hook
  });

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

  // FALLBACK MODE: Stream Chat unavailable
  if (fatalError) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center max-w-lg p-8">
          <div className="w-20 h-20 bg-yellow-100 dark:bg-yellow-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg
              className="w-10 h-10 text-yellow-600 dark:text-yellow-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>

          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">
            AI Support Assistant
          </h2>

          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
            <p className="text-sm text-blue-900 dark:text-blue-100 font-medium mb-2">
              Chat system is temporarily unavailable
            </p>
            <p className="text-xs text-blue-700 dark:text-blue-300">
              {error || "The chat service could not be initialized. This may be due to missing configuration or network issues."}
            </p>
          </div>

          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 mb-6">
            <p className="text-sm text-green-900 dark:text-green-100 font-medium mb-2">
              ✓ The rest of the app is working normally
            </p>
            <p className="text-xs text-green-700 dark:text-green-300">
              You can continue using other features of LandTen. Only the AI Support chat is affected.
            </p>
          </div>

          <div className="space-y-3">
            <a
              href="/"
              className="block w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
            >
              Return to Home
            </a>

            <a
              href="/dashboard"
              className="block w-full px-6 py-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg transition-colors font-medium"
            >
              Go to Dashboard
            </a>
          </div>

          <p className="text-xs text-gray-500 dark:text-gray-400 mt-6">
            If this problem persists, please contact support with error code: STREAM_INIT_FAILED
          </p>
        </div>
      </div>
    );
  }

  // Show client loading state (only if not fatal error)
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
