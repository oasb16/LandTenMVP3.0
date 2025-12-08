'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

export default function LandlordWorkflowPage() {
  const router = useRouter()

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 to-slate-950 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-4">👔 Landlord Portal</h1>
          <p className="text-xl text-slate-300">
            Review incidents, create jobs, and manage contractors
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ActionCard
            title="Manage Incidents"
            description="Review and triage tenant-reported incidents"
            icon="🔍"
            href="/landlord/incidents"
            color="from-purple-600 to-indigo-600"
          />

          <ActionCard
            title="Manage Jobs"
            description="Create jobs, review bids, and approve contractors"
            icon="📋"
            href="/landlord/jobs"
            color="from-indigo-600 to-blue-600"
          />

          <ActionCard
            title="Dashboard"
            description="Overview of all properties, incidents, and jobs"
            icon="📊"
            href="/dashboard/landlord"
            color="from-emerald-600 to-teal-600"
          />

          <ActionCard
            title="AI Support"
            description="Get AI assistance with property management"
            icon="🤖"
            href="/ai-support"
            color="from-blue-600 to-purple-600"
          />
        </div>

        <div className="mt-12 bg-slate-900 rounded-xl p-6 border border-slate-800">
          <h2 className="text-2xl font-bold text-white mb-4">Landlord Workflow</h2>
          <div className="space-y-3 text-slate-300">
            <WorkflowStep number={1} text="Receive incident notification from tenant" />
            <WorkflowStep number={2} text="Review incident details and photos" />
            <WorkflowStep number={3} text="Create maintenance job posting" />
            <WorkflowStep number={4} text="Review contractor bids" />
            <WorkflowStep number={5} text="Award job to best contractor" />
            <WorkflowStep number={6} text="Monitor work completion" />
            <WorkflowStep number={7} text="Process payment upon completion" />
          </div>
        </div>

        <div className="mt-8 text-center">
          <Link
            href="/workflow"
            className="text-slate-400 hover:text-slate-200 transition"
          >
            ← Back to Workflow Hub
          </Link>
        </div>
      </div>
    </div>
  )
}

function ActionCard({
  title,
  description,
  icon,
  href,
  color
}: {
  title: string
  description: string
  icon: string
  href: string
  color: string
}) {
  return (
    <Link
      href={href}
      className={`bg-gradient-to-br ${color} p-6 rounded-xl hover:scale-105 transition-all shadow-xl hover:shadow-2xl block`}
    >
      <div className="text-4xl mb-3">{icon}</div>
      <h2 className="text-2xl font-bold text-white mb-2">{title}</h2>
      <p className="text-white text-opacity-90">{description}</p>
    </Link>
  )
}

function WorkflowStep({ number, text }: { number: number; text: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex-shrink-0 w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center text-white font-bold">
        {number}
      </div>
      <div>{text}</div>
    </div>
  )
}
