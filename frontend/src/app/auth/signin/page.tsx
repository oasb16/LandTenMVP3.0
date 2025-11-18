'use client';

import { signIn } from "next-auth/react";

export default function SignInPage() {
  return (
    <div className="h-screen flex items-center justify-center">
      <button
        className="px-4 py-2 bg-white text-black rounded"
        onClick={() => signIn("google")}
      >
        Sign in with Google
      </button>
    </div>
  );
}
