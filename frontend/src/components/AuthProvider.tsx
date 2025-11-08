"use client";

import { SessionProvider, useSession } from "next-auth/react";
import { useEffect } from "react";

function SessionWatcher() {
  const { status } = useSession();

  useEffect(() => {
    if (status === "unauthenticated") {
      console.log("[auth] Session invalidated — redirecting to sign-in");
      try {
        window.location.href = "/auth/signin?error=session_expired";
      } catch (e) {
        // ignore in non-browser env
      }
    }
  }, [status]);

  return null;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <SessionWatcher />
      {children}
    </SessionProvider>
  );
}
