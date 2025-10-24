import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";

const backendBase = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "";

export async function POST(request: Request) {
  if (!backendBase) {
    return NextResponse.json({ error: "Backend URL not configured" }, { status: 500 });
  }

  const session = await auth();
  const body = await request.json();
  const payload = {
    ...body,
    requesting_user: body.requesting_user || session?.user?.email,
    persona: body.persona || session?.user?.persona,
  };

  const res = await fetch(`${backendBase}/chat/stream/agent_reply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const text = await res.text();
  let data: unknown;
  try {
    data = text ? JSON.parse(text) : {};
  } catch (err) {
    data = { error: text || "Failed to parse response" };
  }

  if (!res.ok) {
    return NextResponse.json(typeof data === "object" ? data : { error: text }, { status: res.status });
  }

  return NextResponse.json(data);
}
