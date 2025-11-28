/**
 * AI Support Send Intent API Route
 *
 * Sends user intents to the backend orchestrator
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
    const { channel_id, session_id, intent } = body;

    if (!channel_id || !session_id || !intent) {
      return NextResponse.json(
        {
          success: false,
          error: "Missing required fields: channel_id, session_id, intent",
        },
        { status: 400 }
      );
    }

    const userId = session.user.email;

    // Forward to backend orchestrator
    const backendUrl = `${backendBase}/ai-support/intent`;
    console.log("[AI Support Intent] Calling backend:", backendUrl);

    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: userId,
        channel_id,
        session_id,
        intent: intent.intent,
        payload: intent.payload,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("[AI Support Intent] Backend error:", errorText);
      return NextResponse.json(
        { success: false, error: errorText || "Backend request failed" },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json({
      success: true,
      acknowledged: data.acknowledged || true,
    });
  } catch (error) {
    console.error("[AI Support Intent] Error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Internal server error",
      },
      { status: 500 }
    );
  }
}
