"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

function ErrorContent() {
  const params = useSearchParams();
  const error = params.get("error");

  const messages: Record<string, string> = {
    OAuthCallback: "The external provider returned an invalid callback.",
    OAuthAccountNotLinked: "This email is linked to a different login provider.",
    AccessDenied: "You do not have access.",
    Configuration: "There is a server configuration issue.",
    Default: "Something went wrong. Please try again.",
  };

  const message = messages[error ?? "Default"] ?? messages.Default;

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-black px-4">
      <div className="bg-neutral-900 p-8 rounded-2xl shadow-xl w-full max-w-sm border border-neutral-800">
        <h1 className="text-xl font-semibold text-red-400 mb-4 text-center">
          Authentication Error
        </h1>

        <p className="text-neutral-300 text-center mb-6">{message}</p>

        <a
          href="/auth/signin"
          className="w-full block text-center py-3 bg-white text-black rounded-lg font-medium hover:bg-neutral-200 transition"
        >
          Try Again
        </a>
      </div>
    </div>
  );
}

export default function ErrorPage() {
  return (
    <Suspense fallback={<div className="text-white p-10">Loading…</div>}>
      <ErrorContent />
    </Suspense>
  );
}
