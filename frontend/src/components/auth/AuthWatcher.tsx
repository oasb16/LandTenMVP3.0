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

    // 1. Don’t run during SSR hydration
    if (status === "loading") return;

    // 2. Allow all auth pages without interference
    if (pathname.startsWith("/auth")) return;

    // 3. Allow Google callback (VERY IMPORTANT!) 
    if (pathname.startsWith("/api/auth")) return;

    // 4. Not logged in → redirect
    if (status === "unauthenticated") {
      router.replace("/auth/signin");
      return;
    }

    // 5. Logged in — do nothing
  }, [status, pathname, router]);

  return <>{children}</>;
}
