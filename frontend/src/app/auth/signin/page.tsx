"use client";
import { signIn } from "next-auth/react";

export default function SignInPage() {
  return (
    <div style={{ display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", height:"100vh", color:"#fff", background:"#0b0b0b" }}>
      <h2>Sign back in</h2>
      <p style={{ marginBottom:16 }}>Your session expired or was closed.</p>
      <button
        onClick={() => signIn("google")}
        style={{ background:"#0070f3", color:"#fff", padding:"10px 20px", border:"none", borderRadius:6, cursor:"pointer" }}
      >
        Sign in with Google
      </button>
    </div>
  );
}
