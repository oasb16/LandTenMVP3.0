/**
 * AI Support Init API Route
 *
 * Initializes a new AI support session
 */

import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";

const backendBase = (
  process.env.BACKEND_INTERNAL_URL ||
  process.env.BACKEND_URL ||
  "http://localhost:8080"
).replace(/\/$/, "");

export async function POST(req: NextRequest) {
  try {
    // Authenticate user
    const session = await auth();
    if (!session?.user?.email) {
      return NextResponse.json(
        { success: false, error: "Unauthorized" },
        { status: 401 }
      );
    }

    // Parse request body
    const body = await req.json();
    const { persona, mode } = body;

    if (!persona || !mode) {
      return NextResponse.json(
        { success: false, error: "Missing required fields: persona, mode" },
        { status: 400 }
      );
    }

    const userId = session.user.email;

    // Forward to backend orchestrator
    const backendUrl = `${backendBase}/ai-support/init`;
    console.log("[AI Support Init] Calling backend:", backendUrl);

    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: userId,
        persona,
        mode,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("[AI Support Init] Backend error:", errorText);
      return NextResponse.json(
        { success: false, error: errorText || "Backend request failed" },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json({
      success: true,
      session_id: data.session_id,
      channel_id: data.channel_id,
      initial_state: data.initial_state,
    });
  } catch (error) {
    console.error("[AI Support Init] Error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Internal server error",
      },
      { status: 500 }
    );
  }
}
