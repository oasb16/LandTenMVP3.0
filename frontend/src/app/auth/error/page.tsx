'use client';

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import Link from "next/link";

function ErrorContent() {
  const params = useSearchParams();
  const error = params.get("error");

  // Map common error codes to user-friendly messages
  const errorMessages: Record<string, string> = {
    Configuration: "There is a problem with the server configuration.",
    AccessDenied: "Access denied. You do not have permission to sign in.",
    Verification: "The verification token has expired or has already been used.",
    Default: "An error occurred during authentication.",
  };

  const errorMessage = error ? errorMessages[error] || errorMessages.Default : errorMessages.Default;

  return (
    <div className="h-screen flex items-center justify-center bg-slate-950">
      <div className="text-center p-8 max-w-md">
        <h1 className="text-3xl font-bold text-red-500 mb-4">Authentication Error</h1>
        <p className="text-slate-300 mb-6">{errorMessage}</p>
        {error && (
          <p className="text-slate-500 text-sm mb-6">
            Error code: <span className="font-mono">{error}</span>
          </p>
        )}
        <Link
          href="/auth/signin"
          className="inline-block px-6 py-3 bg-emerald-500 text-slate-900 font-semibold rounded-lg hover:bg-emerald-400 transition"
        >
          Try Again
        </Link>
      </div>
    </div>
  );
}

export default function ErrorPage() {
  return (
    <Suspense fallback={
      <div className="h-screen flex items-center justify-center bg-slate-950">
        <p className="text-slate-300">Loading...</p>
      </div>
    }>
      <ErrorContent />
    </Suspense>
  );
}