'use client';

import React, { useState } from 'react';
import { Send, Home, MessageSquare, Users, Settings, Bot, Camera, Paperclip, X, Play, Image, CheckCircle, Video, Wrench, Calendar, DollarSign, MapPin, Clock, FileText, Upload, Star, AlertCircle, Plus, ChevronRight, Building2, Bell, Briefcase } from 'lucide-react';

export default function PropertyAIApp() {
  const [userRole, setUserRole] = useState<string | null>(null);

  if (!userRole) {
    return (
      <div className="flex flex-col h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 max-w-md mx-auto">
        <div className="flex-1 flex flex-col items-center justify-center p-6">
          <div className="w-20 h-20 bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl flex items-center justify-center mb-6">
            <Bot className="w-12 h-12 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">PropertyAI</h1>
          <p className="text-gray-600 mb-12 text-center">Intelligent Property Management Platform</p>

          <div className="w-full space-y-4">
            <button
              onClick={() => setUserRole('landlord')}
              className="w-full bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all border-2 border-transparent hover:border-blue-500"
            >
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-blue-100 rounded-xl flex items-center justify-center">
                  <Building2 className="w-8 h-8 text-blue-600" />
                </div>
                <div className="flex-1 text-left">
                  <div className="font-bold text-gray-900 text-lg">Landlord</div>
                  <div className="text-sm text-gray-600">Manage properties & tenants</div>
                </div>
                <ChevronRight className="w-6 h-6 text-gray-400" />
              </div>
            </button>

            <button
              onClick={() => setUserRole('tenant')}
              className="w-full bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all border-2 border-transparent hover:border-green-500"
            >
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-green-100 rounded-xl flex items-center justify-center">
                  <Home className="w-8 h-8 text-green-600" />
                </div>
                <div className="flex-1 text-left">
                  <div className="font-bold text-gray-900 text-lg">Tenant</div>
                  <div className="text-sm text-gray-600">Report issues & communicate</div>
                </div>
                <ChevronRight className="w-6 h-6 text-gray-400" />
              </div>
            </button>

            <button
              onClick={() => setUserRole('contractor')}
              className="w-full bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all border-2 border-transparent hover:border-purple-500"
            >
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-purple-100 rounded-xl flex items-center justify-center">
                  <Wrench className="w-8 h-8 text-purple-600" />
                </div>
                <div className="flex-1 text-left">
                  <div className="font-bold text-gray-900 text-lg">Contractor</div>
                  <div className="text-sm text-gray-600">Find jobs & manage schedule</div>
                </div>
                <ChevronRight className="w-6 h-6 text-gray-400" />
              </div>
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (userRole === 'landlord') return <LandlordDashboard onBack={() => setUserRole(null)} />;
  if (userRole === 'tenant') return <TenantDashboard onBack={() => setUserRole(null)} />;
  if (userRole === 'contractor') return <ContractorDashboard onBack={() => setUserRole(null)} />;
}

// ==================== LANDLORD DASHBOARD ====================
function LandlordDashboard({ onBack }: { onBack: () => void }) {
  const [currentView, setCurrentView] = useState('properties');

  const properties = [
    { id: 1, name: '123 Oakwood Ave', tenants: 1, incidents: 2, status: 'Active' },
    { id: 2, name: '456 Maple St', tenants: 1, incidents: 0, status: 'Active' }
  ];

  const incidents = [
    {
      id: 1,
      property: '123 Oakwood Ave',
      title: 'Kitchen Sink Leak',
      status: 'Pending Approval',
      tenant: 'Sarah Chen',
      created: '2 hours ago',
      severity: 'High'
    }
  ];

  if (currentView === 'properties') {
    return (
      <div className="flex flex-col h-screen bg-gray-50 max-w-md mx-auto">
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold">My Properties</h1>
            <div className="flex items-center gap-2 bg-white/20 px-3 py-1 rounded-full">
              <Bot className="w-4 h-4" />
              <span className="text-sm font-medium">AI Active</span>
            </div>
          </div>
          <div className="flex gap-2">
            <button className="flex-1 bg-white text-blue-600 px-4 py-2 rounded-lg font-medium">
              Properties
            </button>
            <button
              onClick={() => setCurrentView('incidents')}
              className="flex-1 bg-white/20 text-white px-4 py-2 rounded-lg font-medium"
            >
              Incidents
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <button className="w-full bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-xl p-4 font-medium hover:shadow-lg transition-all flex items-center justify-center gap-2">
            <Plus className="w-5 h-5" />
            Add New Property
          </button>

          {properties.map(property => (
            <div key={property.id} className="bg-white rounded-xl p-4 border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-bold text-gray-900">{property.name}</h3>
                  <div className="text-sm text-gray-600">{property.tenants} tenant(s)</div>
                </div>
                <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                  {property.status}
                </span>
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                <div className="flex items-center gap-2 text-sm">
                  <AlertCircle className={`w-4 h-4 ${property.incidents > 0 ? 'text-orange-500' : 'text-gray-400'}`} />
                  <span className="text-gray-600">{property.incidents} active incident(s)</span>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400" />
              </div>
            </div>
          ))}
        </div>

        <BottomNav active="properties" role="landlord" onNavigate={(view) => setCurrentView(view)} />
      </div>
    );
  }

  if (currentView === 'incidents') {
    return (
      <div className="flex flex-col h-screen bg-gray-50 max-w-md mx-auto">
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold">Incidents</h1>
            <button className="bg-white/20 p-2 rounded-lg">
              <Bell className="w-5 h-5" />
            </button>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentView('properties')}
              className="flex-1 bg-white/20 text-white px-4 py-2 rounded-lg font-medium"
            >
              Properties
            </button>
            <button className="flex-1 bg-white text-blue-600 px-4 py-2 rounded-lg font-medium">
              Incidents
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <button className="w-full bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-xl p-4 font-medium hover:shadow-lg transition-all flex items-center justify-center gap-2">
            <Plus className="w-5 h-5" />
            Create Manual Incident
          </button>

          {incidents.map(incident => (
            <div key={incident.id} className="bg-white rounded-xl p-4 border border-gray-200">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`w-2 h-2 rounded-full ${incident.severity === 'High' ? 'bg-red-500' : 'bg-yellow-500'}`}></span>
                    <h3 className="font-bold text-gray-900">{incident.title}</h3>
                  </div>
                  <div className="text-sm text-gray-600">{incident.property}</div>
                </div>
                <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs font-medium rounded-full">
                  {incident.status}
                </span>
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                <div className="text-sm text-gray-600">Tenant: {incident.tenant}</div>
                <div className="text-xs text-gray-400">{incident.created}</div>
              </div>
              <div className="mt-3 flex gap-2">
                <button className="flex-1 bg-green-500 text-white px-3 py-2 rounded-lg text-sm font-medium">
                  Approve & Create Job
                </button>
                <button className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700">
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>

        <BottomNav active="incidents" role="landlord" onNavigate={(view) => setCurrentView(view)} />
      </div>
    );
  }

  return null;
}

// ==================== TENANT DASHBOARD ====================
function TenantDashboard({ onBack }: { onBack: () => void }) {
  const [currentView, setCurrentView] = useState('dashboard');

  const myIncidents = [
    { id: 1, title: 'Kitchen Sink Leak', status: 'In Progress', created: '2 hours ago', priority: 'High' },
    { id: 2, title: 'Broken Door Lock', status: 'Scheduled', created: '1 day ago', priority: 'Medium' }
  ];

  if (currentView === 'dashboard') {
    return (
      <div className="flex flex-col h-screen bg-gray-50 max-w-md mx-auto">
        <div className="bg-gradient-to-r from-green-600 to-teal-600 text-white px-6 py-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h1 className="text-2xl font-bold">My Home</h1>
              <div className="text-sm opacity-90">123 Oakwood Ave</div>
            </div>
            <div className="flex items-center gap-2 bg-white/20 px-3 py-1 rounded-full">
              <Bot className="w-4 h-4" />
              <span className="text-sm font-medium">AI Assistant</span>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <button
            onClick={() => setCurrentView('report-issue')}
            className="w-full bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-xl p-4 font-medium hover:shadow-lg transition-all flex items-center justify-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Report New Issue
          </button>

          <div className="bg-white rounded-xl p-4 border border-gray-200">
            <h3 className="font-bold text-gray-900 mb-3">Quick Actions</h3>
            <div className="grid grid-cols-2 gap-3">
              <button className="bg-blue-50 p-3 rounded-lg text-center hover:bg-blue-100 transition-colors">
                <MessageSquare className="w-6 h-6 text-blue-600 mx-auto mb-1" />
                <div className="text-sm font-medium text-gray-900">Chat</div>
              </button>
              <button className="bg-purple-50 p-3 rounded-lg text-center hover:bg-purple-100 transition-colors">
                <FileText className="w-6 h-6 text-purple-600 mx-auto mb-1" />
                <div className="text-sm font-medium text-gray-900">Documents</div>
              </button>
            </div>
          </div>

          <div>
            <h3 className="font-bold text-gray-900 mb-3">My Incidents</h3>
            <div className="space-y-3">
              {myIncidents.map(incident => (
                <div key={incident.id} className="bg-white rounded-xl p-4 border border-gray-200">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`w-2 h-2 rounded-full ${incident.priority === 'High' ? 'bg-red-500' : 'bg-yellow-500'}`}></span>
                        <h4 className="font-semibold text-gray-900">{incident.title}</h4>
                      </div>
                      <div className="text-sm text-gray-600">{incident.created}</div>
                    </div>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                      incident.status === 'In Progress' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'
                    }`}>
                      {incident.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <BottomNav active="home" role="tenant" onNavigate={(view) => setCurrentView(view)} />
      </div>
    );
  }

  if (currentView === 'report-issue') {
    return (
      <div className="flex flex-col h-screen bg-gray-50 max-w-md mx-auto">
        <div className="bg-gradient-to-r from-green-600 to-teal-600 text-white px-6 py-4">
          <div className="flex items-center gap-3">
            <button onClick={() => setCurrentView('dashboard')} className="p-1">
              <X className="w-6 h-6" />
            </button>
            <div className="flex-1">
              <h1 className="text-xl font-bold">Report Issue</h1>
              <div className="text-sm opacity-90">AI will help analyze</div>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div className="flex justify-start">
            <div className="max-w-[85%] bg-gradient-to-br from-purple-50 to-blue-50 border border-purple-200 rounded-2xl px-4 py-3">
              <div className="flex items-center gap-2 mb-2">
                <Bot className="w-5 h-5 text-purple-600" />
                <span className="font-semibold text-gray-900">PropertyAI</span>
              </div>
              <p className="text-gray-800">Hi! I&apos;m here to help you report an issue. Can you describe what&apos;s happening?</p>
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-center">
            <Camera className="w-8 h-8 text-blue-600 mx-auto mb-2" />
            <p className="text-sm text-gray-700 mb-3">Add photos or videos to help me understand</p>
            <button className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg font-medium">
              Upload Media
            </button>
          </div>
        </div>

        <div className="bg-white border-t border-gray-200 px-4 py-3">
          <div className="flex items-center gap-2 bg-gray-100 rounded-full px-4 py-2">
            <input
              type="text"
              placeholder="Describe the issue..."
              className="flex-1 bg-transparent border-none outline-none text-gray-800"
            />
            <button className="w-9 h-9 bg-green-600 rounded-full flex items-center justify-center">
              <Send className="w-4 h-4 text-white" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}

// ==================== CONTRACTOR DASHBOARD ====================
function ContractorDashboard({ onBack }: { onBack: () => void }) {
  const availableBids = [
    {
      id: 1,
      title: 'Kitchen Sink Leak Repair',
      property: '123 Oakwood Ave',
      budget: '$250-350',
      distance: '2.3 miles',
      urgency: 'High',
      matchScore: 95
    },
    {
      id: 2,
      title: 'Bathroom Faucet Replacement',
      property: '456 Pine Street',
      budget: '$180-250',
      distance: '4.1 miles',
      urgency: 'Medium',
      matchScore: 88
    }
  ];

  return (
    <div className="flex flex-col h-screen bg-gray-50 max-w-md mx-auto">
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold">Available Jobs</h1>
            <div className="text-sm opacity-90">John Martinez - ABC Plumbing</div>
          </div>
          <div className="flex items-center gap-2 bg-white/20 px-3 py-1 rounded-full">
            <Bot className="w-4 h-4" />
            <span className="text-sm font-medium">AI Active</span>
          </div>
        </div>
        <div className="bg-white/20 rounded-lg p-3 flex items-center justify-between">
          <div className="text-center">
            <div className="text-2xl font-bold">3</div>
            <div className="text-xs opacity-90">Today</div>
          </div>
          <div className="w-px h-10 bg-white/30"></div>
          <div className="text-center">
            <div className="text-2xl font-bold">4.8★</div>
            <div className="text-xs opacity-90">Rating</div>
          </div>
          <div className="w-px h-10 bg-white/30"></div>
          <div className="text-center">
            <div className="text-2xl font-bold">247</div>
            <div className="text-xs opacity-90">Jobs</div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {availableBids.map(bid => (
          <div key={bid.id} className="bg-white rounded-xl p-4 border border-gray-200 hover:border-purple-300 hover:shadow-md transition-all">
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                    bid.urgency === 'High' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {bid.urgency}
                  </span>
                  <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-medium rounded-full">
                    {bid.matchScore}% Match
                  </span>
                </div>
                <h3 className="font-bold text-gray-900 text-lg">{bid.title}</h3>
                <div className="text-sm text-gray-600 mt-1">{bid.property}</div>
              </div>
            </div>

            <div className="flex items-center gap-4 mb-3 text-sm text-gray-600">
              <div className="flex items-center gap-1">
                <DollarSign className="w-4 h-4" />
                <span>{bid.budget}</span>
              </div>
              <div className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                <span>{bid.distance}</span>
              </div>
            </div>

            <button className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-4 py-2 rounded-lg font-medium hover:shadow-lg transition-all">
              View Details & Accept
            </button>
          </div>
        ))}
      </div>

      <BottomNav active="bids" role="contractor" />
    </div>
  );
}

// ==================== BOTTOM NAVIGATION ====================
interface BottomNavProps {
  active: string;
  role?: string;
  onNavigate?: (view: string) => void;
}

function BottomNav({ active, role = 'landlord', onNavigate }: BottomNavProps) {
  const landlordNav = [
    { id: 'properties', icon: Building2, label: 'Properties' },
    { id: 'incidents', icon: AlertCircle, label: 'Incidents' },
    { id: 'chat', icon: MessageSquare, label: 'Chat' },
    { id: 'profile', icon: Settings, label: 'Profile' }
  ];

  const tenantNav = [
    { id: 'home', icon: Home, label: 'Home' },
    { id: 'incidents', icon: AlertCircle, label: 'Issues' },
    { id: 'chat', icon: MessageSquare, label: 'Chat' },
    { id: 'profile', icon: Settings, label: 'Profile' }
  ];

  const contractorNav = [
    { id: 'bids', icon: Briefcase, label: 'Jobs' },
    { id: 'schedule', icon: Calendar, label: 'Schedule' },
    { id: 'chat', icon: MessageSquare, label: 'Chat' },
    { id: 'profile', icon: Settings, label: 'Profile' }
  ];

  const navItems = role === 'landlord' ? landlordNav : role === 'tenant' ? tenantNav : contractorNav;

  return (
    <div className="bg-white border-t border-gray-200 px-6 py-3">
      <div className="flex justify-around">
        {navItems.map(item => {
          const Icon = item.icon;
          const isActive = active === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate && onNavigate(item.id)}
              className={`flex flex-col items-center gap-1 ${
                isActive ? 'text-blue-600' : 'text-gray-400'
              }`}
            >
              <Icon className="w-6 h-6" />
              <span className="text-xs font-medium">{item.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
