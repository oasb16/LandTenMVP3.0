"use client";
import { useEffect } from "react";
import { useSession, signOut } from "next-auth/react";

export default function AuthWatcher({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();

  useEffect(() => {
    if (status === "unauthenticated" || !session?.user) {
      console.warn("[auth] Session expired — signing out");
      signOut({ callbackUrl: "/auth/signin" });
    }
  }, [status, session]);

  return <>{children}</>;
}
          await fetch("/api/auth/signout", { method: "POST" });
