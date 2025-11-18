"use client";

import { useEffect } from "react";
import { useSession } from "next-auth/react";
import { usePathname, useRouter } from "next/navigation";

export default function AuthWatcher({
  children,
}: {
  children: React.ReactNode;
}) {
  const { status } = useSession();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (typeof window === "undefined") return;

    if (status === "loading") return;

    if (pathname.startsWith("/auth")) return;

    if (status === "unauthenticated") {
      router.replace("/auth/signin");
    }
  }, [status, pathname, router]);

  return <>{children}</>;
}
