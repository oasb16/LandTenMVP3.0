"use client";

import { SessionProvider } from "next-auth/react";
import AuthWatcher from "@/components/auth/AuthWatcher";

export default function AuthProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SessionProvider refetchOnWindowFocus={false} refetchInterval={0}>
      <AuthWatcher>{children}</AuthWatcher>
    </SessionProvider>
  );
}
