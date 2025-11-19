"use client";

import { useEffect } from "react";
import { useSession } from "next-auth/react";
import { usePathname, useRouter } from "next/navigation";

export default function AuthWatcher({ children }: { children: React.ReactNode }) {
  const { status } = useSession();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    // 1. Avoid running on SSR hydration
    if (typeof window === "undefined") return;

    // 2. Wait for session to load
    if (status === "loading") return;

    // 3. Avoid redirecting on auth system routes
    if (pathname.startsWith("/auth")) return;

    // 4. Avoid redirecting on internal API or static resources
    if (
      pathname.startsWith("/api") ||
      pathname === "/favicon.ico" ||
      pathname === "/robots.txt"
    ) {
      return;
    }

    // 5. User is not logged in → redirect to signin
    if (status === "unauthenticated") {
      router.replace("/auth/signin");
    }
  }, [status, pathname, router]);

  return <>{children}</>;
}
