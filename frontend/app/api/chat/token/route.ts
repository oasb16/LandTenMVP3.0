import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";

const backendBase = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "";

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
  const query = new URLSearchParams({
    user_id: session.user.email,
    persona,
  });
  const res = await fetch(`${backendBase}/chat/stream/token?${query.toString()}`);
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
