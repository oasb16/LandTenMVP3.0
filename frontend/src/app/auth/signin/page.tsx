"use client";

import { signIn } from "@/lib/auth";

export default function SignInPage() {
  return (
    <div style={{
      height: "100vh",
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      background: "#000"
    }}>
      <button
        onClick={() => signIn("google")}
        style={{
          padding: "12px 24px",
          background: "white",
          borderRadius: 6,
          cursor: "pointer",
        }}
      >
        Sign in with Google
      </button>
    </div>
  );
}
