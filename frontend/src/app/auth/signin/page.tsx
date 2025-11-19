'use client';

import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function SignInPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  // If already authenticated, redirect to dashboard
  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/dashboard");
    }
  }, [status, router]);

  // Show loading while checking session
  if (status === "loading") {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-950 text-slate-100">
        <p>Loading...</p>
      </div>
    );
  }

  // Already signed in, about to redirect
  if (status === "authenticated") {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-950 text-slate-100">
        <p>Redirecting to dashboard...</p>
      </div>
    );
  }

  // Show sign in button
  return (
    <div className="h-screen flex items-center justify-center bg-slate-950">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-slate-100 mb-6">Welcome to LandTenMVP3</h1>
        <button
          className="px-6 py-3 bg-emerald-500 text-slate-900 font-semibold rounded-lg hover:bg-emerald-400 transition"
          onClick={() => signIn("google", { callbackUrl: "/dashboard" })}
        >
          Sign in with Google
        </button>
      </div>
    </div>
  );
}
