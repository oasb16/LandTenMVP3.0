"use client";
import { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";

export default function AuthWatcher({ children }: { children: React.ReactNode }) {
  const { status } = useSession();
  const [bannerShown, setBannerShown] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated" && !bannerShown) {
      setBannerShown(true);
      const banner = document.createElement("div");
      banner.style.cssText = `
        position:fixed;top:0;left:0;right:0;background:#121212;color:#fff;
        text-align:center;padding:12px;font-size:14px;z-index:9999;
      `;
      banner.innerHTML = `
        <span style="color:#ff7070;font-weight:600;">Session expired.</span>
        <span> Please sign back in.</span>
        <button id="relogin-btn" style="margin-left:10px;background:#0070f3;color:white;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;">Sign in</button>
      `;
      document.body.appendChild(banner);

      const btn = document.getElementById("relogin-btn");
      btn?.addEventListener("click", async () => {
        banner.textContent = "Signing out…";
        try {
          await fetch("/api/auth/csrf"); // refresh CSRF
          await fetch("/api/auth/signout", { method: "POST" });
        } catch {}
        signOut({ callbackUrl: "/auth/signin" });
      });
    }
  }, [status, bannerShown]);

  return <>{children}</>;
}
          await fetch("/api/auth/signout", { method: "POST" });
