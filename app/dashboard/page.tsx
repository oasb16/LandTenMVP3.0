"use client";

import { useEffect, useState, useRef } from "react";
import { useSession, signIn } from "next-auth/react";
import { useRouter } from "next/navigation";

const personas = [
  { id: "tenant", label: "Tenant" },
  { id: "landlord", label: "Landlord" },
  { id: "contractor", label: "Contractor" },
];

export default function PersonaSelectorPage() {
  const { data: session, status, update } = useSession();
  const router = useRouter();
  const [persona, setPersona] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasChecked = useRef(false);

  // Auto-redirect if persona already exists - run only once
  useEffect(() => {
    if (status !== "authenticated" || hasChecked.current) return;

    hasChecked.current = true;

    const checkPersona = async () => {
      // First check session
      if (session?.user?.persona) {
        router.replace(`/dashboard/${session.user.persona}`);
        return;
      }

      // Then check database
      setLoading(true);
      try {
        const res = await fetch("/api/profile");
        if (res.ok) {
          const data = await res.json();
          if (data?.persona) {
            // Sync to session and redirect
            await fetch("/api/auth/session?update");
            await update({ persona: data.persona });
            router.replace(`/dashboard/${data.persona}`);
            return;
          }
        }
      } catch (err) {
        console.error("Failed to check persona:", err);
      }
      setLoading(false);
    };

    checkPersona();
  }, [status, session, update, router]);

  const handleSave = async () => {
    if (!persona) {
      setError("Please select a persona.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Step 1: Save persona to database
      const res = await fetch("/api/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ persona }),
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || "Failed to store persona");
      }

      // Step 2: Force session refresh from backend
      await fetch("/api/auth/session?update");

      // Step 3: Update client-side session
      await update({ persona });

      // Step 4: Navigate to dashboard
      router.replace(`/dashboard/${persona}`);
    } catch (err: any) {
      setError(err.message || "Failed to store persona");
      setLoading(false);
    }
  };

  if (status === "loading" || loading) {
    return (
      <div style={{ padding: "20px", textAlign: "center" }}>
        <p>Loading…</p>
      </div>
    );
  }

  if (status !== "authenticated") {
    return (
      <div style={{ padding: "20px", textAlign: "center" }}>
        <button onClick={() => signIn("google")}>Sign in with Google</button>
      </div>
    );
  }

  return (
    <div style={{ padding: "20px", maxWidth: "600px", margin: "0 auto" }}>
      <h1>Select Your Persona</h1>
      <p>Choose how you want to use the platform:</p>
      <div style={{ margin: "20px 0" }}>
        {personas.map((p) => (
          <button
            key={p.id}
            onClick={() => setPersona(p.id)}
            disabled={loading}
            style={{
              display: "block",
              width: "100%",
              padding: "15px",
              margin: "10px 0",
              border: persona === p.id ? "2px solid #0070f3" : "1px solid #ccc",
              backgroundColor: persona === p.id ? "#f0f8ff" : "#fff",
              cursor: loading ? "not-allowed" : "pointer",
              fontSize: "16px",
              borderRadius: "4px",
            }}
          >
            {p.label}
          </button>
        ))}
      </div>
      <button
        onClick={handleSave}
        disabled={loading || !persona}
        style={{
          padding: "12px 24px",
          backgroundColor: !persona || loading ? "#ccc" : "#0070f3",
          color: "#fff",
          border: "none",
          borderRadius: "4px",
          cursor: !persona || loading ? "not-allowed" : "pointer",
          fontSize: "16px",
        }}
      >
        {loading ? "Saving..." : "Continue"}
      </button>
      {error && (
        <div style={{ marginTop: "20px", padding: "10px", backgroundColor: "#fee", color: "#c00", borderRadius: "4px" }}>
          {error}
        </div>
      )}
    </div>
  );
}
