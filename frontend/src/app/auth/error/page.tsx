"use client";

import { useSearchParams } from "next/navigation";

export default function AuthErrorPage() {
  const params = useSearchParams();
  const error = params.get("error");

  return (
    <div style={{ padding: 40, color: "white" }}>
      <h1>Authentication Error</h1>
      <p>{error ?? "Unknown error occurred."}</p>
    </div>
  );
}
