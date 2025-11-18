"use client";

import { useEffect } from "react";
import { useSession } from "next-auth/react";
import { usePathname, useRouter } from "next/navigation";

export default function AuthWatcher({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (typeof window === "undefined") return;

    // 1. Allow SSR to hydrate without redirect
    if (status === "loading") return;

    // 2. Allow all auth pages without redirect
    if (pathname?.startsWith("/auth")) return;

    // 3. If user is NOT logged in → redirect to signin
    if (status === "unauthenticated") {
      router.replace("/auth/signin");
    }
  }, [status, pathname, router]);

  return <>{children}</>;
}
