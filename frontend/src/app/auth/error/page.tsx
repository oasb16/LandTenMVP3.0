"use client";

import { useEffect } from "react";
import { signOut } from "next-auth/react";

export default function AuthErrorPage() {
  useEffect(() => {
    console.warn("[auth] Redirected to error page — forcing sign-out");
    // Force logout and clear stale cookies
    signOut({ callbackUrl: "/auth/signin?error=relogin_required" });
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen text-center">
      <h1 className="text-2xl font-semibold mb-4">Session Reset Required</h1>
      <p className="text-gray-600">
        Something went wrong while connecting to Google.
        You’ll be signed out and asked to log in again.
      </p>
    </div>
  );
}
