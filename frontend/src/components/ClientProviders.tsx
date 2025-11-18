"use client";

import AuthProvider from "@/components/AuthProvider";
import { StreamChatProvider } from "@/hooks/chat/StreamChatContext";

export default function ClientProviders({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthProvider>
      <StreamChatProvider>{children}</StreamChatProvider>
    </AuthProvider>
  );
}
