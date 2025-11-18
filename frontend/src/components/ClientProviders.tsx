"use client";

import { SessionProvider } from "next-auth/react";
import AuthProvider from "@/components/auth/AuthProvider";
import { StreamChatProvider } from "@/hooks/chat/StreamChatContext";

export function ClientProviders({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider refetchInterval={300} refetchOnWindowFocus={false}>
      <AuthProvider>
        <StreamChatProvider>{children}</StreamChatProvider>
      </AuthProvider>
    </SessionProvider>
  );
}
