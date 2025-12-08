'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

export default function ContractorWorkflowPage() {
  const router = useRouter()

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-900 to-slate-950 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-4">🔧 Contractor Portal</h1>
          <p className="text-xl text-slate-300">
            Browse jobs, submit bids, and complete maintenance work
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ActionCard
            title="Available Jobs"
            description="Browse and bid on open maintenance jobs"
            icon="🔍"
            href="/contractor/contractor/jobs/available"
            color="from-green-600 to-emerald-600"
          />

          <ActionCard
            title="My Bids"
            description="Track your submitted bids and their status"
            icon="📊"
            href="/contractor/contractor/jobs/my-bids"
            color="from-emerald-600 to-teal-600"
          />

          <ActionCard
            title="Active Jobs"
            description="View and manage jobs you've been awarded"
            icon="⚡"
            href="/contractor/contractor/jobs/active"
            color="from-teal-600 to-cyan-600"
          />

          <ActionCard
            title="Dashboard"
            description="Overview of all your jobs and earnings"
            icon="💼"
            href="/dashboard/contractor"
            color="from-blue-600 to-indigo-600"
          />
        </div>

        <div className="mt-12 bg-slate-900 rounded-xl p-6 border border-slate-800">
          <h2 className="text-2xl font-bold text-white mb-4">Contractor Workflow</h2>
          <div className="space-y-3 text-slate-300">
            <WorkflowStep number={1} text="Browse available maintenance jobs" />
            <WorkflowStep number={2} text="Review job details and requirements" />
            <WorkflowStep number={3} text="Submit competitive bid with timeline" />
            <WorkflowStep number={4} text="Get notified if awarded the job" />
            <WorkflowStep number={5} text="Complete work and upload proof" />
            <WorkflowStep number={6} text="Get paid via Stripe Connect" />
          </div>
        </div>

        <div className="mt-8 bg-emerald-900/30 border border-emerald-800 rounded-xl p-6">
          <h3 className="text-xl font-bold text-white mb-3">💰 Earnings</h3>
          <p className="text-slate-300">
            Platform fee: <span className="font-bold text-emerald-400">15%</span> of each job
          </p>
          <p className="text-slate-400 text-sm mt-2">
            Fast payments via Stripe Connect - receive funds within 2-3 business days
          </p>
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
      <div className="flex-shrink-0 w-8 h-8 bg-green-600 rounded-full flex items-center justify-center text-white font-bold">
        {number}
      </div>
      <div>{text}</div>
    </div>
  )
}
