import { NextRequest, NextResponse } from "next/server";

// Use internal backend URL for server-side proxying
const backendBase = (process.env.BACKEND_INTERNAL_URL || process.env.BACKEND_URL || "http://localhost:8080").replace(/\/$/, "");

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const contractorEmail = searchParams.get("email");
  const contractorId = searchParams.get("contractor_id");

  if (!contractorEmail) {
    return NextResponse.json({ error: "Contractor email required" }, { status: 400 });
  }

  if (!backendBase) {
    return NextResponse.json({ error: "Backend URL not configured" }, { status: 500 });
  }

  // Contractors use the contractor_onboarding persona
  const persona = "contractor_onboarding";
  const user_id = contractorEmail;

  const url = `${backendBase}/chat/stream/token?user_id=${encodeURIComponent(user_id)}&persona=${encodeURIComponent(persona)}`;
  console.log("[contractor-token] Fetching token for contractor:", contractorEmail, "from:", url);

  try {
    const res = await fetch(url);
    if (!res.ok) {
      const errorText = await res.text();
      console.error("[contractor-token] Backend error:", errorText);
      return NextResponse.json({ error: errorText }, { status: res.status });
    }

    const data = await res.json();

    return NextResponse.json({
      ...data,
      display_user_id: contractorEmail,
      email: contractorEmail,
      persona: "contractor_onboarding",
      // Pass contractor_id in metadata so agent tools can access it
      metadata: {
        contractor_id: contractorId,
      },
    });
  } catch (error) {
    console.error("[contractor-token] Error fetching token:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to fetch token" },
      { status: 500 }
    );
  }
}
