"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

export default function TenantDashboard() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const hasRedirected = useRef(false);

  useEffect(() => {
    // Wait for session to load
    if (status === "loading") return;

    // Prevent multiple redirects
    if (hasRedirected.current) return;

    // Redirect unauthenticated users to sign in
    if (status === "unauthenticated") {
      hasRedirected.current = true;
      router.replace("/auth/signin");
      return;
    }

    // If authenticated, check persona
    if (status === "authenticated") {
      if (!session?.user?.persona) {
        // No persona selected, go to selector
        hasRedirected.current = true;
        router.replace("/dashboard");
        return;
      }

      if (session.user.persona !== "tenant") {
        // Wrong persona, redirect to correct dashboard
        hasRedirected.current = true;
        router.replace(`/dashboard/${session.user.persona}`);
        return;
      }
    }
  }, [status, session, router]);

  // Show loading while session is loading or redirecting
  if (status === "loading") {
    return (
      <div style={{ padding: "20px", textAlign: "center" }}>
        <p>Loading workspace…</p>
      </div>
    );
  }

  if (status === "unauthenticated" || !session?.user?.persona || session.user.persona !== "tenant") {
    return (
      <div style={{ padding: "20px", textAlign: "center" }}>
        <p>Redirecting…</p>
      </div>
    );
  }

  // Main dashboard content
  return (
    <div style={{ padding: "20px" }}>
      <h1>Tenant Dashboard</h1>
      <p>Welcome, {session.user.email}</p>
      <div style={{ marginTop: "20px" }}>
        {/* Your tenant dashboard content here */}
        <h2>Your Properties</h2>
        <p>View and manage your rental properties.</p>

        <h2>Maintenance Requests</h2>
        <p>Submit and track maintenance requests.</p>

        <h2>Payments</h2>
        <p>View payment history and manage rent payments.</p>
      </div>
    </div>
  );
}
