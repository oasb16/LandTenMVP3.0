"use client";
import { useEffect } from "react";
import { useSession, signOut } from "next-auth/react";

export default function AuthWatcher({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();

  useEffect(() => {
    if (typeof window === "undefined") return; // skip SSR builds
    if (status === "unauthenticated" || !session?.user) {
      console.warn("[auth] Session expired — forcing signout");
      try {
        signOut({ callbackUrl: "/auth/signin", redirect: true });
      } catch (err) {
        console.error("[auth] signOut failed:", err);
      }
    }
  }, [status, session]);

  return <>{children}</>;
}

