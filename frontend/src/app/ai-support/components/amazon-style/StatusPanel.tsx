/**
 * StatusPanel - Check Status Quick Action
 *
 * Shows user's active tasks, maintenance requests, and incidents
 * Reuses existing TasksPanel and IncidentCardEnhanced components
 */

"use client";

import { motion } from "framer-motion";
import { ArrowLeft, Package, Wrench, FileText } from "lucide-react";
import TasksPanel, { Task } from "@/components/TasksPanel";
import { IncidentCardEnhanced } from "@/components/ai/IncidentCardEnhanced";

interface StatusPanelProps {
  persona: string;
  onBack: () => void;
}

export default function StatusPanel({ persona, onBack }: StatusPanelProps) {
  // Mock data - in production, fetch from backend
  const tasks: Task[] = [
    {
      task_id: "task-1",
      title: "Review maintenance request",
      description: "Kitchen sink leak reported by tenant",
      status: "in-progress",
      persona: persona,
      assigned_to: persona,
    },
    {
      task_id: "task-2",
      title: "Approve contractor bid",
      description: "HVAC repair quote received",
      status: "pending",
      persona: persona,
      assigned_to: persona,
    },
  ];

  const incidents = [
    {
      incident_id: "INC-001",
      title: "Kitchen Sink Leaking",
      category: "Plumbing",
      severity: "medium",
      urgency: "urgent",
      summary: "Water leaking from kitchen sink pipes. Needs immediate attention.",
      created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
      incident_id: "INC-002",
      title: "HVAC Not Cooling",
      category: "HVAC",
      severity: "high",
      urgency: "immediate",
      summary: "Air conditioning system not producing cold air. Temperature rising.",
      created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    },
  ];

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 overflow-y-auto">
      {/* Header */}
      <div className="p-6 border-b border-slate-700/60 sticky top-0 bg-slate-900/95 backdrop-blur-sm z-10">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-slate-400 hover:text-slate-200 transition-colors mb-3"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm">Back</span>
        </button>
        <h2 className="text-xl font-bold text-slate-100">Your Status</h2>
        <p className="text-sm text-slate-400 mt-1">
          Active tasks, requests, and incidents
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 p-6 space-y-6">
        {/* Active Tasks */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <Package className="w-5 h-5 text-emerald-400" />
            <h3 className="text-lg font-semibold text-slate-100">Active Tasks</h3>
          </div>
          <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
            <TasksPanel persona={persona} initialTasks={tasks} />
          </div>
        </section>

        {/* Maintenance Requests */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <Wrench className="w-5 h-5 text-emerald-400" />
            <h3 className="text-lg font-semibold text-slate-100">Maintenance Requests</h3>
          </div>
          <div className="space-y-3">
            {incidents.map((incident, index) => (
              <motion.div
                key={incident.incident_id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <IncidentCardEnhanced
                  metadata={incident}
                  text={incident.summary}
                />
              </motion.div>
            ))}
          </div>
        </section>

        {/* Info Card */}
        <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl">
          <div className="flex items-start gap-3">
            <FileText className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-semibold text-blue-400 mb-1">Need Help?</h4>
              <p className="text-sm text-slate-300">
                Start a chat with our AI assistant for immediate support, or browse help articles
                for common solutions.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
