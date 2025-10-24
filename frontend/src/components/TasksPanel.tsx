"use client";

import { useState } from "react";

export type Task = {
  task_id: string;
  title: string;
  description: string;
  status: string;
  persona?: string;
  assigned_to?: string;
};

const statusStyles: Record<string, string> = {
  pending: "bg-slate-800 text-slate-200",
  "in-progress": "bg-amber-500/20 text-amber-200",
  completed: "bg-emerald-500/20 text-emerald-200",
};

export default function TasksPanel({ persona, initialTasks }: { persona: string; initialTasks: Task[] }) {
  const [tasks, setTasks] = useState(initialTasks);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const backendBase = process.env.NEXT_PUBLIC_BACKEND_URL || "";

  const createTask = async () => {
    if (!title.trim()) return;
    if (!backendBase) {
      setError("Backend URL not configured");
      return;
    }
    const task = {
      task_id: `task-${Date.now()}`,
      title,
      description,
      persona,
      created_by: persona,
      assigned_to: persona,
      status: "pending",
    };
    try {
      await fetch(`${backendBase}/task/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "dev" },
        body: JSON.stringify(task),
      });
      setTasks((prev) => [...prev, task]);
      setTitle("");
      setDescription("");
    } catch (error) {
      console.error(error);
      setError("Failed to create task");
    }
  };

  const cycleStatus = async (task: Task) => {
    const order = ["pending", "in-progress", "completed"];
    const idx = order.indexOf(task.status);
    const nextStatus = order[(idx + 1) % order.length];
    if (!backendBase) {
      setError("Backend URL not configured");
      return;
    }
    try {
      await fetch(`${backendBase}/task/update_status`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "dev" },
        body: JSON.stringify({ task_id: task.task_id, status: nextStatus }),
      });
      setTasks((prev) =>
        prev.map((t) => (t.task_id === task.task_id ? { ...t, status: nextStatus } : t))
      );
    } catch (error) {
      console.error(error);
      setError("Failed to update task status");
    }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Task title"
          className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2"
        />
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Task description"
          rows={3}
          className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2"
        />
        <button
          onClick={createTask}
          className="w-full rounded-md bg-emerald-500 px-4 py-2 font-semibold text-slate-900 hover:bg-emerald-400 transition"
        >
          Create Task
        </button>
      </div>

      {error && <div className="text-sm text-rose-400">{error}</div>}

      <div className="space-y-2 max-h-80 overflow-y-auto">
        {tasks.length === 0 && <div className="text-sm text-slate-400">No tasks yet.</div>}
        {tasks.map((task) => (
          <button
            key={task.task_id}
            onClick={() => cycleStatus(task)}
            className={`w-full rounded-md border border-slate-700 px-3 py-2 text-left transition ${
              statusStyles[task.status] || "bg-slate-800 text-slate-200"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-semibold">{task.title}</span>
              <span className="text-xs uppercase">{task.status}</span>
            </div>
            <p className="text-sm text-slate-300 mt-1">{task.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
