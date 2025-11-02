"use client";

import { AuthProvider } from "@/components/AuthProvider";
import { StreamChatProvider } from "@/hooks/chat/StreamChatContext";

/**
 * Client-side providers wrapper.
 * This must be a separate "use client" component to avoid hydration issues
 * when used in a server component layout that exports metadata.
 */
export function ClientProviders({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <StreamChatProvider>{children}</StreamChatProvider>
    </AuthProvider>
  );
}
