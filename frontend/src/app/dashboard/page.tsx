"use client";

import { useEffect, useState, useRef } from "react";
import { useSession, signIn, signOut } from "next-auth/react";
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

  // Prevent endless profile polling
  const fetchedOnce = useRef(false);

  //
  // 1. If session already has persona → go directly to dashboard
  //
  useEffect(() => {
    if (session?.user?.persona) {
      router.replace(`/dashboard/${session.user.persona}`);
    }
  }, [session?.user?.persona, router]);

  //
  // 2. Fetch persona only ONCE per page load, only if missing
  //
  useEffect(() => {
    if (status !== "authenticated") return;
    if (session?.user?.persona) return;
    if (fetchedOnce.current) return;

    fetchedOnce.current = true;

    async function fetchPersonaOnce() {
      try {
        const res = await fetch("/api/profile", { method: "GET" });

        if (!res.ok) {
          console.warn("[persona] backend returned", res.status);
          return; // Do not retry automatically
        }

        const data = await res.json();
        if (data?.persona) {
          // Update session with persona
          await update({ persona: data.persona });
          router.replace(`/dashboard/${data.persona}`);
        }
      } catch (err) {
        console.warn("[persona] fetch failed:", err);
      }
    }

    fetchPersonaOnce();
  }, [status, session?.user?.persona, update, router]);

  //
  // 3. Save persona to backend
  //
  const handleSave = async () => {
    if (!persona) {
      setError("Please select a persona.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ persona }),
      });

      const txt = await res.text();
      if (!res.ok) {
        throw new Error(txt || `Backend error ${res.status}`);
      }

      // Update session with selected persona
      await update({ persona });

      // Navigate to dashboard
      router.replace(`/dashboard/${persona}`);
    } catch (err: any) {
      console.error("[persona-save] error:", err);
      setError(`Failed to store persona: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  //
  // 4. Loading UI
  //
  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 text-slate-100">
        Loading…
      </div>
    );
  }

  //
  // 5. Not logged in → require login
  //
  if (status !== "authenticated") {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-slate-900 text-slate-100">
        <h1 className="text-3xl font-semibold">Sign in to continue</h1>
        <button
          onClick={() => signIn("google")}
          className="rounded-md bg-emerald-500 px-6 py-3 font-semibold text-slate-900 hover:bg-emerald-400 transition"
        >
          Sign in with Google
        </button>
      </div>
    );
  }

  //
  // 6. UI: Persona selection
  //
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center py-12 px-6">
      <div className="w-full max-w-xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Choose your workspace</h1>
            <p className="text-slate-400">Signed in as {session.user?.email}</p>
          </div>

          <button
            onClick={() => signOut({ callbackUrl: "/" })}
            className="rounded-md border border-slate-600 px-4 py-2 text-sm hover:bg-slate-800"
          >
            Sign out
          </button>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          {personas.map((p) => (
            <button
              key={p.id}
              onClick={() => setPersona(p.id)}
              className={`rounded-lg border px-4 py-6 text-left transition ${
                persona === p.id
                  ? "border-emerald-400 bg-emerald-500/10"
                  : "border-slate-700 bg-slate-900 hover:border-emerald-500"
              }`}
            >
              <h2 className="text-xl font-semibold">{p.label}</h2>
              <p className="mt-2 text-sm text-slate-400">
                Access {p.label.toLowerCase()} tools.
              </p>
            </button>
          ))}
        </div>

        {error && <div className="text-sm text-rose-400">{error}</div>}

        <button
          onClick={handleSave}
          disabled={loading || !persona}
          className="w-full rounded-md bg-emerald-500 px-6 py-3 font-semibold text-slate-900 hover:bg-emerald-400 transition disabled:opacity-50"
        >
          {loading ? "Saving…" : "Continue"}
        </button>
      </div>
    </div>
  );
}
