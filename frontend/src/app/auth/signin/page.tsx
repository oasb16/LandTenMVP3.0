"use client";

import { signIn } from "@/lib/auth";

export default function SignInPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-black px-4">
      <div className="bg-neutral-900 p-8 rounded-2xl shadow-xl w-full max-w-sm border border-neutral-800">
        <h1 className="text-2xl font-semibold text-white mb-6 text-center">
          Sign in to LandTen MVP 3.0
        </h1>

        <button
          onClick={() => signIn("google")}
          className="w-full py-3 bg-white text-black rounded-lg font-medium hover:bg-neutral-200 transition"
        >
          Sign in with Google
        </button>
      </div>
    </div>
  );
}
