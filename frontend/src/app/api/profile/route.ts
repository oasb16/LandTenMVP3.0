import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";

const backendBase = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "";

export async function GET() {
  const session = await auth();
  if (!session?.user?.email) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (!backendBase) {
    return NextResponse.json({ persona: null });
  }
  const res = await fetch(`${backendBase}/profile/${encodeURIComponent(session.user.email)}`);
  if (!res.ok) {
    return NextResponse.json({ persona: null });
  }
  const data = await res.json();
  return NextResponse.json(data);
}

export async function POST(request: Request) {
  const session = await auth();
  if (!session?.user?.email) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const body = await request.json();
  const persona = body?.persona;
  if (!persona) {
    return NextResponse.json({ error: "persona required" }, { status: 400 });
  }
  if (!backendBase) {
    return NextResponse.json({ error: "Backend URL not configured" }, { status: 500 });
  }
  const res = await fetch(`${backendBase}/profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: session.user.email, persona }),
  });
  if (!res.ok) {
    return NextResponse.json({ error: "Failed to store persona" }, { status: 500 });
  }
  return NextResponse.json({ status: "stored", persona });
}
