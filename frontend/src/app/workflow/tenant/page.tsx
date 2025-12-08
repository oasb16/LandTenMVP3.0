'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

export default function TenantWorkflowPage() {
  const router = useRouter()

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 to-slate-950 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-4">🏠 Tenant Portal</h1>
          <p className="text-xl text-slate-300">
            Report incidents, track repairs, and communicate with your landlord
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ActionCard
            title="Report New Incident"
            description="Submit a maintenance request with photos and details"
            icon="📝"
            href="/tenant/incidents/new"
            color="from-orange-600 to-red-600"
          />

          <ActionCard
            title="My Incidents"
            description="View and track all your reported incidents"
            icon="📋"
            href="/tenant/incidents"
            color="from-blue-600 to-indigo-600"
          />

          <ActionCard
            title="AI Support Experience"
            description="Get intelligent help with incident reporting and tracking"
            icon="🤖"
            href="/ai-support"
            color="from-blue-600 to-purple-600"
          />

          <ActionCard
            title="PropertyAI Chat"
            description="Chat with AI about your property maintenance needs"
            icon="💬"
            href="/property-ai"
            color="from-purple-600 to-pink-600"
          />

          <ActionCard
            title="Dashboard"
            description="View all your incidents, repairs, and chat history"
            icon="📊"
            href="/dashboard/tenant"
            color="from-emerald-600 to-teal-600"
          />

          <ActionCard
            title="Classic Chat"
            description="Legacy chat interface with AI assistance"
            icon="💭"
            href="/legacy-chat"
            color="from-slate-600 to-slate-700"
          />
        </div>

        <div className="mt-12 bg-slate-900 rounded-xl p-6 border border-slate-800">
          <h2 className="text-2xl font-bold text-white mb-4">Tenant Workflow</h2>
          <div className="space-y-3 text-slate-300">
            <WorkflowStep number={1} text="Report an incident with photos and details" />
            <WorkflowStep number={2} text="Track your incident status in real-time" />
            <WorkflowStep number={3} text="Landlord reviews and creates a maintenance job" />
            <WorkflowStep number={4} text="Contractor is assigned and completes the work" />
            <WorkflowStep number={5} text="Receive notification when work is complete" />
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
      <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold">
        {number}
      </div>
      <div>{text}</div>
    </div>
  )
}
