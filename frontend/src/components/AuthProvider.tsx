"use client";

import { SessionProvider } from "next-auth/react";
import AuthWatcher from "@/components/auth/AuthWatcher";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider refetchInterval={300} refetchOnWindowFocus={false}>
      <AuthWatcher>{children}</AuthWatcher>
    </SessionProvider>
  );
}
