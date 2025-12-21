import Link from "next/link";
import { cookies } from "next/headers";

export const dynamic = "force-dynamic";

export default async function LandingPage() {
  const cookieStore = await cookies();
  const hasSession = Boolean(
    cookieStore.get("next-auth.session-token") ||
      cookieStore.get("__Secure-next-auth.session-token") ||
      cookieStore.get("next-auth.session-token.0")
  );
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center px-6">
      <div className="max-w-3xl text-center space-y-6">
        <h1 className="text-4xl sm:text-5xl font-bold">LandTenMVP 3.0</h1>
        <p className="text-lg text-slate-300">
          A unified command center for landlords, tenants, and contractors. Coordinate maintenance,
          chat in real time, and automate follow-ups with AI assistance.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 max-w-3xl mx-auto">
          <Link
            href="/ai-support"
            className="inline-flex items-center justify-center rounded-md bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-3 font-semibold text-white hover:from-blue-700 hover:to-purple-700 transition shadow-lg"
          >
            🤖 AI Support Experience
          </Link>
          <Link
            href="/property-ai"
            className="inline-flex items-center justify-center rounded-md bg-gradient-to-r from-purple-600 to-pink-600 px-6 py-3 font-semibold text-white hover:from-purple-700 hover:to-pink-700 transition shadow-lg"
          >
            💬 PropertyAI Chat
          </Link>
          <Link
            href={hasSession ? "/dashboard" : "/dashboard"}
            className="inline-flex items-center justify-center rounded-md bg-emerald-500 px-6 py-3 font-semibold text-slate-900 hover:bg-emerald-400 transition"
          >
            {hasSession ? "📊 Continue to Dashboard" : "📊 Classic Dashboard"}
          </Link>
          <a
            href="https://github.com/oasb16/LandTenMVP2.0"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center rounded-md border border-slate-500 px-6 py-3 font-semibold text-slate-100 hover:bg-slate-800 transition"
          >
            📚 View Legacy MVP2.0
          </a>
          <Link
            href="/workflow"
            className="inline-flex items-center justify-center rounded-md bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-500 transition shadow-lg col-span-1 sm:col-span-2"
          >
            ⚡ Full Workflow Experience
          </Link>
          <Link
            href="/test-contractor-onboarding"
            className="inline-flex items-center justify-center rounded-md bg-gradient-to-r from-orange-600 to-red-600 px-6 py-3 font-semibold text-white hover:from-orange-700 hover:to-red-700 transition shadow-lg col-span-1 sm:col-span-2 md:col-span-3"
          >
            🧪 Test Contractor Onboarding (E2E)
          </Link>
        </div>
        <div className="grid sm:grid-cols-3 gap-6 text-left">
          <div className="rounded-lg border border-slate-700 p-4 bg-slate-900/60">
            <h2 className="font-semibold text-lg">🤖 AI Support</h2>
            <p className="text-sm text-slate-400">Amazon-style guided support with intelligent issue resolution and automated workflows.</p>
          </div>
          <div className="rounded-lg border border-slate-700 p-4 bg-slate-900/60">
            <h2 className="font-semibold text-lg">💬 Real-time Chat</h2>
            <p className="text-sm text-slate-400">Stream-powered messaging keeps every persona in sync across devices.</p>
          </div>
          <div className="rounded-lg border border-slate-700 p-4 bg-slate-900/60">
            <h2 className="font-semibold text-lg">⚡ Task Orchestration</h2>
            <p className="text-sm text-slate-400">Assign, track, and complete maintenance tasks seamlessly with AI assistance.</p>
          </div>
        </div>
      </div>
    </main>
  );
}
