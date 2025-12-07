'use client'

import { useRouter } from 'next/navigation'

type UserRole = 'tenant' | 'landlord' | 'contractor'

export default function WorkflowHub() {
  const router = useRouter()

  const roleCards = [
    {
      role: 'tenant' as UserRole,
      title: '🏠 Tenant Portal',
      description: 'Report incidents, upload photos, track repairs',
      route: '/workflow/tenant',
      color: 'from-blue-600 to-blue-700',
    },
    {
      role: 'landlord' as UserRole,
      title: '👔 Landlord Portal',
      description: 'Review incidents, create jobs, manage contractors',
      route: '/workflow/landlord',
      color: 'from-purple-600 to-purple-700',
    },
    {
      role: 'contractor' as UserRole,
      title: '🔧 Contractor Portal',
      description: 'Browse jobs, submit bids, complete work',
      route: '/workflow/contractor',
      color: 'from-green-600 to-green-700',
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-950 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-4">Complete Workflow Experience</h1>
          <p className="text-xl text-slate-300">
            From incident report to payment - fully automated workflow
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          {roleCards.map((card) => (
            <div
              key={card.role}
              onClick={() => router.push(card.route)}
              className={`bg-gradient-to-br ${card.color} p-8 rounded-xl cursor-pointer transform hover:scale-105 transition-all shadow-xl hover:shadow-2xl`}
            >
              <h2 className="text-2xl font-bold text-white mb-3">{card.title}</h2>
              <p className="text-white text-opacity-90">{card.description}</p>
              <div className="mt-6 text-white text-opacity-75">Click to enter →</div>
            </div>
          ))}
        </div>

        <div className="bg-slate-900 rounded-xl p-8 border border-slate-800">
          <h2 className="text-2xl font-bold text-white mb-6 text-center">How It Works</h2>
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <WorkflowStep number={1} title="Report Incident" description="Tenant creates incident with photos" />
            <Arrow />
            <WorkflowStep number={2} title="Create Job" description="Landlord reviews and posts job" />
            <Arrow />
            <WorkflowStep number={3} title="Submit Bid" description="Contractors compete with bids" />
            <Arrow />
            <WorkflowStep number={4} title="Complete Work" description="Contractor finishes and uploads proof" />
            <Arrow />
            <WorkflowStep number={5} title="Process Payment" description="Landlord pays, contractor receives funds" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-8">
          <StatCard title="Response Time" value="&lt; 2 hours" />
          <StatCard title="Platform Fee" value="15%" />
          <StatCard title="Avg. Job Time" value="3 days" />
          <StatCard title="Success Rate" value="98%" />
        </div>
      </div>
    </div>
  )
}

function WorkflowStep({ number, title, description }: { number: number; title: string; description: string }) {
  return (
    <div className="bg-slate-800 rounded-lg p-4 flex-1 min-w-[150px]">
      <div className="text-3xl font-bold text-blue-400 mb-2">{number}</div>
      <div className="text-white font-semibold mb-1">{title}</div>
      <div className="text-slate-400 text-sm">{description}</div>
    </div>
  )
}

function Arrow() {
  return <div className="text-slate-600 text-2xl hidden md:block">→</div>
}

function StatCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="bg-slate-800 rounded-lg p-4 text-center">
      <div className="text-2xl font-bold text-white mb-1">{value}</div>
      <div className="text-slate-400 text-sm">{title}</div>
    </div>
  )
}
