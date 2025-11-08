import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";

// Public-facing base used by client-side code
const FRONTEND_API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "";
// Internal backend base for server-side calls (defaults to localhost for local dev)
const BACKEND_API_BASE = process.env.BACKEND_INTERNAL_URL || process.env.BACKEND_URL || "http://localhost:8080";

async function createProfileOnBackend(email: string, name: string | undefined, persona = "tenant") {
  const payload = { user_id: email, name: name || "", persona };
  const url = `${BACKEND_API_BASE.replace(/\/$/, "")}/profile`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    console.error(`[profile-route] createProfile failed for user_id=${email}: ${res.status} ${text} url=${url}`);
    throw new Error(`Backend profile create failed: ${res.status} ${text}`);
  }
  const created = await res.json();
  console.log(`[profile-route] Created profile successfully for user_id=${email}`);
  return created;
}

export async function GET() {
  const session = await auth();
  if (!session?.user?.email) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (!BACKEND_API_BASE) {
    return NextResponse.json({ error: "Backend URL not configured" }, { status: 500 });
  }

  const email = session.user.email as string;
  const name = (session.user.name as string) || undefined;

  try {
  const url = `${BACKEND_API_BASE.replace(/\/$/, "")}/profile/${encodeURIComponent(email)}`;
    const res = await fetch(url);
    if (res.status === 404) {
      // Auto-provision profile to avoid 404 loops after OAuth sign-in
      const created = await createProfileOnBackend(email, name, "tenant");
      // Normalize shape to use user_id
      return NextResponse.json({ user_id: created.user_id || email, name: created.name || name || "", persona: created.persona || "tenant" });
    }
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      console.error(`[profile-route] GET backend error: ${res.status} ${txt} url=${url}`);
      return NextResponse.json({ error: `Backend error: ${res.status} ${txt}` }, { status: 502 });
    }
    const data = await res.json();
    return NextResponse.json({ user_id: data.user_id || email, name: data.name, persona: data.persona });
  } catch (e: any) {
    console.error(`[profile-route] GET fetch exception: ${String(e)}`);
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}

export async function POST(request: Request) {
  const session = await auth();
  if (!session?.user?.email) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (!BACKEND_API_BASE) {
    return NextResponse.json({ error: "Backend URL not configured" }, { status: 500 });
  }

  const email = session.user.email as string;
  const name = (session.user.name as string) || undefined;

  let body: any = {};
  try {
    body = await request.json();
  } catch {
    // ignore — allow empty body to upsert with defaults
  }

  const persona = body?.persona || body?.profile?.persona || "tenant";

  try {
    // Upsert profile on backend (backend expects user_id)
    const payload = { user_id: email, name: name || body?.name || "", persona };
    const url = `${BACKEND_API_BASE.replace(/\/$/, "")}/profile`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      console.error(`[profile-route] POST backend error for user_id=${email}: ${res.status} ${txt} url=${url}`);
      return NextResponse.json({ error: `Backend error: ${res.status} ${txt}` }, { status: 502 });
    }
    const data = await res.json();
    return NextResponse.json({ user_id: data.user_id || email, name: data.name || name || "", persona: data.persona || persona });
  } catch (e: any) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
