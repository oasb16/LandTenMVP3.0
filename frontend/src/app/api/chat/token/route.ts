import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";

// Use internal backend URL for server-side proxying (prefer BACKEND_INTERNAL_URL, then BACKEND_URL)
const backendBase = (process.env.BACKEND_INTERNAL_URL || process.env.BACKEND_URL || "http://localhost:8080").replace(/\/$/, "");

export async function GET() {
  const session = await auth();
  if (!session?.user?.email) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (!backendBase) {
    return NextResponse.json({ error: "Backend URL not configured" }, { status: 500 });
  }
  const persona = session.user.persona;
  if (!persona) {
    return NextResponse.json({ error: "Persona not set" }, { status: 400 });
  }
  const user_id = session.user.email as string;
  const url = `${backendBase}/chat/stream/token?user_id=${encodeURIComponent(user_id)}&persona=${encodeURIComponent(persona)}`;
  console.log("[chat-token] Proxying token request to backend:", url);
  const res = await fetch(url);
  if (!res.ok) {
    return NextResponse.json({ error: await res.text() }, { status: res.status });
  }
  const data = await res.json();
  return NextResponse.json({
    ...data,
    display_user_id: data.display_user_id ?? session.user.email,
    email: session.user.email,
  });
}
