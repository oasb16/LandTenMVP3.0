import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";

const backendBase = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "";

function backendNotConfigured() {
  return NextResponse.json({ error: "Backend URL not configured" }, { status: 500 });
}

export async function GET() {
  const session = await auth();
  if (!session?.user?.email) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (!backendBase) {
    return backendNotConfigured();
  }

  const res = await fetch(
    `${backendBase}/chat/stream/threads/${encodeURIComponent(session.user.email)}`,
    {
      headers: { "Content-Type": "application/json" },
    },
  );

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

export async function POST(request: Request) {
  const session = await auth();
  if (!session?.user?.email) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (!backendBase) {
    return backendNotConfigured();
  }

  const body = await request.json();
  const payload = {
    include_agent: true,
    persona: session.user.persona,
    ...body,
    creator: session.user.email,
  };

  const res = await fetch(`${backendBase}/chat/stream/thread`, {
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
