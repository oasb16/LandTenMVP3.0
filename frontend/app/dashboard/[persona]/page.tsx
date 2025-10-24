"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import StreamChatPane from "@/components/StreamChatPane";
import TasksPanel, { type Task } from "@/components/TasksPanel";

export default function PersonaDashboardPage() {
  const params = useParams<{ persona: string }>();
  const { data: session, status } = useSession();
  const router = useRouter();
  const personaParam = (params?.persona ?? "").toLowerCase();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "loading") return;
    if (!session) {
      router.replace("/dashboard");
      return;
    }
    if (!session.user?.persona) {
      router.replace("/dashboard");
      return;
    }
    if (session.user.persona !== personaParam) {
      router.replace(`/dashboard/${session.user.persona}`);
    }
  }, [status, session, personaParam, router]);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const base = process.env.NEXT_PUBLIC_BACKEND_URL || "";
        const res = await fetch(`${base}/task/list/${personaParam}`, {
          headers: { Authorization: "dev" },
        });
        if (res.ok) {
          const data = await res.json();
          setTasks((data.tasks || []) as Task[]);
        }
      } catch (error) {
        console.error(error);
        setError("Failed to load tasks");
      }
    };
    if (personaParam) fetchTasks();
  }, [personaParam]);

  if (status === "loading" || !session?.user?.persona || session.user.persona !== personaParam) {
    return <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100">Loading workspace…</div>;
  }

  const personaLabel = personaParam.charAt(0).toUpperCase() + personaParam.slice(1);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold">{personaLabel} Dashboard</h1>
          <p className="text-sm text-slate-400">Signed in as {session.user?.email}</p>
        </div>
        <button
          onClick={() => signOut({ callbackUrl: "/" })}
          className="rounded-md border border-slate-600 px-4 py-2 text-sm hover:bg-slate-800"
        >
          Sign out
        </button>
      </header>

      <main className="grid gap-6 px-6 py-6 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-6">
          <section className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <h2 className="text-lg font-semibold mb-4">Conversations</h2>
            <StreamChatPane persona={personaParam} />
          </section>
        </div>
        <aside className="space-y-6">
          <section className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <h2 className="text-lg font-semibold mb-4">Tasks</h2>
            <TasksPanel persona={personaParam} initialTasks={tasks} />
            {error && <div className="text-sm text-rose-400 mt-4">{error}</div>}
          </section>
        </aside>
      </main>
    </div>
  );
}
