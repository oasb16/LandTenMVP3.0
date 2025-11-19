import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";

/** 
 * Public-facing base used by client code
 */
const FRONTEND_API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "";

/** 
 * Internal backend base for server-side calls 
 * (resolves correctly on Vercel + local)
 */
const BACKEND_API_BASE =
  process.env.BACKEND_INTERNAL_URL ||
  process.env.BACKEND_URL ||
  "http://localhost:8080";

/**
 * Helper for backend POST (create or update profile)
 */
async function createOrUpdateProfile(email: string, name: string, persona: string) {
  const payload = { user_id: email, name: name || "", persona };
  const url = `${BACKEND_API_BASE.replace(/\/$/, "")}/profile`;

  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      // Ensure Vercel edge routing never strips host
      cache: "no-store",
    });
  } catch (err) {
    console.error(`[profile-route] Backend POST failed: ${String(err)} url=${url}`);
    throw new Error(`Backend POST failed: ${String(err)}`);
  }

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    console.error(
      `[profile-route] Backend responded with error ${res.status}: ${text} url=${url}`
    );
    throw new Error(`Backend error ${res.status}: ${text}`);
  }

  return res.json();
}

/**
 * GET — Fetch profile from backend.
 * If missing → auto-provision.
 */
export async function GET() {
  const session = await auth();
  if (!session?.user?.email) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!BACKEND_API_BASE) {
    return NextResponse.json(
      { error: "Backend URL not configured" },
      { status: 500 }
    );
  }

  const email = session.user.email as string;
  const name = (session.user.name as string) || "";

  const url = `${BACKEND_API_BASE.replace(/\/$/, "")}/profile/${encodeURIComponent(email)}`;

  try {
    const res = await fetch(url, { cache: "no-store" });

    if (res.status === 404) {
      // Auto-create profile without causing infinite loops
      const created = await createOrUpdateProfile(email, name, "tenant");
      return NextResponse.json({
        user_id: created.user_id || email,
        name: created.name || name,
        persona: created.persona || "tenant",
      });
    }

    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      console.error(`[profile-route] GET backend error ${res.status}: ${txt}`);
      return NextResponse.json(
        { error: `Backend error: ${res.status} ${txt}` },
        { status: 502 }
      );
    }

    const data = await res.json();
    return NextResponse.json({
      user_id: data.user_id || email,
      name: data.name || name,
      persona: data.persona || "tenant",
    });
  } catch (err: any) {
    console.error(`[profile-route] GET fetch exception: ${String(err)}`);
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}

/**
 * POST — Update persona
 */
export async function POST(request: Request) {
  const session = await auth();
  if (!session?.user?.email) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!BACKEND_API_BASE) {
    return NextResponse.json(
      { error: "Backend URL not configured" },
      { status: 500 }
    );
  }

  const email = session.user.email as string;
  const name = (session.user.name as string) || "";

  let body = {};
  try {
    body = await request.json();
  } catch (_) {}

  const persona =
    (body as any)?.persona ||
    (body as any)?.profile?.persona ||
    "tenant";

  try {
    const updated = await createOrUpdateProfile(email, name, persona);
    return NextResponse.json({
      user_id: updated.user_id || email,
      name: updated.name || name,
      persona: updated.persona || persona,
    });
  } catch (err: any) {
    console.error(`[profile-route] POST exception: ${String(err)}`);
    return NextResponse.json(
      { error: `Failed to store persona: ${String(err)}` },
      { status: 500 }
    );
  }
}
