"use client";

import React, { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { useSearchParams } from "next/navigation";

/**
 * SessionRecovery
 * - Detects expired/invalid NextAuth sessions (common errors like session_expired or JWTSessionError)
 * - Shows a small dismissible banner/toast to the user
 * - Automatically calls signOut({ callbackUrl: '/auth/signin' }) a few seconds after detection
 *
 * This is a lightweight, drop-in client component safe to mount inside your client
 * providers (for example `ClientProviders`) so every page benefits.
 */
export function SessionRecovery() {
  const { data: session, status } = useSession();
  const searchParams = useSearchParams();
  const [visible, setVisible] = useState(false);
  const [countdown, setCountdown] = useState<number | null>(null);

  useEffect(() => {
    // Run only on client
    if (typeof window === "undefined") return;

    const urlError = searchParams?.get("error") ?? "";
    const normalizedUrlError = urlError.toLowerCase();

    // common NextAuth session-related error substrings
    const knownErrorSubstrings = [
      "jwt", // JWTSessionError
      "jwtsessionerror",
      "session_expired",
      "session-expired",
      "no matching decryption",
      "no_matching_decryption",
      "no matching decryption secret",
      "no_matching_decryption_secret",
      "decryption",
      "invalid_token",
    ];

    const urlHasKnownError = knownErrorSubstrings.some((s) =>
      normalizedUrlError.includes(s)
    );

    // If NextAuth resolves to unauthenticated, or we detect a known error in URL,
    // show the banner and schedule sign out.
    if (status === "unauthenticated" || !session?.user || urlHasKnownError) {
      // show banner to user
      setVisible(true);

      // start a short countdown before redirecting the user to sign-in so
      // they see the toast/banner. Adjust the delay as needed.
      const initial = 4; // seconds
      setCountdown(initial);

      const interval = setInterval(() => {
        setCountdown((c) => {
          if ((c ?? 0) <= 1) {
            clearInterval(interval);
            // perform sign out and redirect to sign-in page
            // callbackUrl keeps user on signin route after signOut
            signOut({ callbackUrl: process.env.NEXTAUTH_URL + "/auth/signin" });
            return null;
          }
          return (c ?? 0) - 1;
        });
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [status, session, searchParams]);

  if (!visible) return null;

  return (
    <div
      aria-live="polite"
      style={{
        position: "fixed",
        top: 16,
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 60,
        maxWidth: "min(920px, 96%)",
      }}
    >
      <div
        style={{
          display: "flex",
          gap: 12,
          alignItems: "center",
          padding: "12px 16px",
          background: "#fff6f6",
          border: "1px solid #f5c6c6",
          color: "#6b0f0f",
          borderRadius: 8,
          boxShadow:
            "0 6px 18px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04)",
        }}
      >
        <div style={{ flex: 1 }}>
          <strong style={{ display: "block", marginBottom: 2 }}>Session expired</strong>
          <div style={{ fontSize: 13 }}>
            Your session is no longer valid. You will be redirected to the sign-in
            page to re-authenticate.
            {countdown ? ` Redirecting in ${countdown}s…` : ""}
          </div>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => signOut({ callbackUrl: process.env.NEXTAUTH_URL + "/auth/signin"})}
            style={{
              background: "#0f172a",
              color: "white",
              border: "none",
              padding: "8px 12px",
              borderRadius: 6,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            Sign in again
          </button>

          <button
            onClick={() => setVisible(false)}
            aria-label="Dismiss session banner"
            style={{
              background: "transparent",
              border: "1px solid rgba(15,23,42,0.06)",
              padding: "8px 10px",
              borderRadius: 6,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}

export default SessionRecovery;
