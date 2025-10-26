'use client';

import React, { useState, useEffect } from 'react';
import { Send, Home, MessageSquare, Settings, Bot, Camera, X, AlertCircle, Plus, ChevronRight, Building2, Bell, Briefcase, Wrench, Calendar, DollarSign, MapPin, FileText, Loader2 } from 'lucide-react';
import { useSession, signIn, signOut } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useIncidents, useTasks, useJobs, useProperties, useMediaUpload } from '@/hooks/usePropertyData';
import * as api from '@/lib/api';
import StreamChatPane from './StreamChatPane';

export default function PropertyAIApp() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [userRole, setUserRole] = useState<string | null>(null);

  // Redirect to sign in if not authenticated
  useEffect(() => {
    if (status === 'unauthenticated') {
      signIn('google');
    }
  }, [status]);

  // Load user persona from session
  useEffect(() => {
    if (session?.user?.persona) {
      setUserRole(session.user.persona);
    }
  }, [session]);

  // Handle persona selection
  const handleRoleSelect = async (role: string) => {
    if (!session?.user?.email) return;

    try {
      // Save persona to backend via Next.js API route
      const response = await fetch('/api/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ persona: role }),
      });

      if (response.ok) {
        setUserRole(role);
        // Reload session to get updated persona
        window.location.reload();
      }
    } catch (error) {
      console.error('Failed to save persona:', error);
    }
  };

  if (status === 'loading') {
    return (
      <div className="flex flex-col h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 max-w-md mx-auto items-center justify-center">
        <Loader2 className="w-12 h-12 text-blue-600 animate-spin" />
        <p className="mt-4 text-gray-600">Loading...</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="flex flex-col h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 max-w-md mx-auto items-center justify-center">
        <div className="w-20 h-20 bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl flex items-center justify-center mb-6">
          <Bot className="w-12 h-12 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">PropertyAI</h1>
        <p className="text-gray-600 mb-6">Please sign in to continue</p>
        <button
          onClick={() => signIn('google')}
          className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700"
        >
          Sign in with Google
        </button>
      </div>
    );
  }

  if (!userRole) {
    return (
      <div className="flex flex-col h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 max-w-md mx-auto">
        <div className="flex-1 flex flex-col items-center justify-center p-6">
          <div className="w-20 h-20 bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl flex items-center justify-center mb-6">
            <Bot className="w-12 h-12 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">PropertyAI</h1>
          <p className="text-gray-600 mb-4 text-center">Intelligent Property Management Platform</p>
          <p className="text-sm text-gray-500 mb-8">Signed in as {session.user?.email}</p>

          <div className="w-full space-y-4">
            <button
              onClick={() => handleRoleSelect('landlord')}
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
              onClick={() => handleRoleSelect('tenant')}
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
              onClick={() => handleRoleSelect('contractor')}
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

          <button
            onClick={() => signOut({ callbackUrl: '/' })}
            className="mt-6 text-sm text-gray-600 hover:text-gray-900"
          >
            Sign out
          </button>
        </div>
      </div>
    );
  }

  if (userRole === 'landlord') return <LandlordDashboard session={session} />;
  if (userRole === 'tenant') return <TenantDashboard session={session} />;
  if (userRole === 'contractor') return <ContractorDashboard session={session} />;

  return null;
}

// ==================== LANDLORD DASHBOARD ====================
function LandlordDashboard({ session }: { session: any }) {
  const [currentView, setCurrentView] = useState('properties');
  const userId = session?.user?.email || '';
  const { properties } = useProperties(userId);
  const { incidents, loading: incidentsLoading, refetch: refetchIncidents } = useIncidents(userId);

  const handleApproveIncident = async (incidentId: string) => {
    // Create a job from the incident
    try {
      const incident = incidents.find(i => i.id === incidentId);
      if (!incident) return;

      await api.createJob({
        incident_id: incidentId,
        contractor_id: 'pending', // Will be assigned later
        status: 'pending',
      });

      // Update incident status
      alert('Job created successfully! Contractors will be notified.');
      refetchIncidents();
    } catch (error) {
      alert('Failed to create job');
    }
  };

  if (currentView === 'properties') {
    return (
      <div className="flex flex-col h-screen bg-gray-50 max-w-md mx-auto">
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold">My Properties</h1>
              <div className="text-sm opacity-90">{session?.user?.email}</div>
            </div>
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
              className="flex-1 bg-white/20 text-white px-4 py-2 rounded-lg font-medium relative"
            >
              Incidents
              {incidents.length > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                  {incidents.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setCurrentView('chat')}
              className="flex-1 bg-white/20 text-white px-4 py-2 rounded-lg font-medium"
            >
              Chat
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <button className="w-full bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-xl p-4 font-medium hover:shadow-lg transition-all flex items-center justify-center gap-2">
            <Plus className="w-5 h-5" />
            Add New Property
          </button>

          {properties.map(property => {
            const propertyIncidents = incidents.filter(i => i.property === property.name);
            return (
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
                    <AlertCircle className={`w-4 h-4 ${propertyIncidents.length > 0 ? 'text-orange-500' : 'text-gray-400'}`} />
                    <span className="text-gray-600">{propertyIncidents.length} active incident(s)</span>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-400" />
                </div>
              </div>
            );
          })}
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
            <button
              onClick={() => setCurrentView('chat')}
              className="flex-1 bg-white/20 text-white px-4 py-2 rounded-lg font-medium"
            >
              Chat
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {incidentsLoading && (
            <div className="flex justify-center py-8">
              <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
            </div>
          )}

          {!incidentsLoading && incidents.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No incidents yet
            </div>
          )}

          {incidents.map(incident => (
            <div key={incident.id} className="bg-white rounded-xl p-4 border border-gray-200">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`w-2 h-2 rounded-full ${incident.severity === 'High' ? 'bg-red-500' : 'bg-yellow-500'}`}></span>
                    <h3 className="font-bold text-gray-900">{incident.title || incident.description}</h3>
                  </div>
                  <div className="text-sm text-gray-600">{incident.property}</div>
                </div>
                <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs font-medium rounded-full">
                  {incident.status}
                </span>
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                <div className="text-sm text-gray-600">Tenant: {incident.tenant || incident.tenant_id}</div>
                <div className="text-xs text-gray-400">{incident.created || 'Recently'}</div>
              </div>
              {incident.status === 'Pending Approval' && (
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => handleApproveIncident(incident.id)}
                    className="flex-1 bg-green-500 text-white px-3 py-2 rounded-lg text-sm font-medium hover:bg-green-600"
                  >
                    Approve & Create Job
                  </button>
                  <button className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>

        <BottomNav active="incidents" role="landlord" onNavigate={(view) => setCurrentView(view)} />
      </div>
    );
  }

  if (currentView === 'chat') {
    return (
      <div className="flex flex-col h-screen bg-gray-50 max-w-md mx-auto">
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold">Chat</h1>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentView('properties')}
              className="flex-1 bg-white/20 text-white px-4 py-2 rounded-lg font-medium"
            >
              Properties
            </button>
            <button
              onClick={() => setCurrentView('incidents')}
              className="flex-1 bg-white/20 text-white px-4 py-2 rounded-lg font-medium"
            >
              Incidents
            </button>
            <button className="flex-1 bg-white text-blue-600 px-4 py-2 rounded-lg font-medium">
              Chat
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-hidden">
          <StreamChatPane persona="landlord" />
        </div>

        <BottomNav active="chat" role="landlord" onNavigate={(view) => setCurrentView(view)} />
      </div>
    );
  }

  return null;
}

// ==================== TENANT DASHBOARD ====================
function TenantDashboard({ session }: { session: any }) {
  const [currentView, setCurrentView] = useState('dashboard');
  const userId = session?.user?.email || '';
  const { incidents, loading: incidentsLoading, createIncident } = useIncidents(userId);
  const [issueDescription, setIssueDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { upload, uploading } = useMediaUpload();

  const handleReportIssue = async () => {
    if (!issueDescription.trim()) return;

    setIsSubmitting(true);
    try {
      await createIncident({
        id: `incident-${Date.now()}`,
        tenant_id: userId,
        description: issueDescription,
        status: 'Pending Approval',
        title: issueDescription.substring(0, 50),
        severity: 'Medium',
        property: '123 Oakwood Ave',
      });
      setIssueDescription('');
      setCurrentView('dashboard');
      alert('Issue reported successfully!');
    } catch (error) {
      alert('Failed to report issue');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleMediaUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const url = await upload(file);
    if (url) {
      alert('Media uploaded successfully!');
    }
  };

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
              <button
                onClick={() => setCurrentView('chat')}
                className="bg-blue-50 p-3 rounded-lg text-center hover:bg-blue-100 transition-colors"
              >
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
            {incidentsLoading && (
              <div className="flex justify-center py-4">
                <Loader2 className="w-6 h-6 text-green-600 animate-spin" />
              </div>
            )}
            {!incidentsLoading && incidents.length === 0 && (
              <div className="text-center py-4 text-gray-500 text-sm">
                No incidents yet
              </div>
            )}
            <div className="space-y-3">
              {incidents.map(incident => (
                <div key={incident.id} className="bg-white rounded-xl p-4 border border-gray-200">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`w-2 h-2 rounded-full ${incident.severity === 'High' ? 'bg-red-500' : 'bg-yellow-500'}`}></span>
                        <h4 className="font-semibold text-gray-900">{incident.title || incident.description}</h4>
                      </div>
                      <div className="text-sm text-gray-600">{incident.created || 'Recently'}</div>
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
            <label className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg font-medium cursor-pointer inline-block hover:bg-blue-700">
              {uploading ? 'Uploading...' : 'Upload Media'}
              <input
                type="file"
                accept="image/*,video/*"
                className="hidden"
                onChange={handleMediaUpload}
                disabled={uploading}
              />
            </label>
          </div>

          <textarea
            value={issueDescription}
            onChange={(e) => setIssueDescription(e.target.value)}
            placeholder="Describe the issue in detail..."
            className="w-full bg-white border border-gray-300 rounded-xl p-4 min-h-[120px] resize-none outline-none focus:border-green-500"
          />

          <button
            onClick={handleReportIssue}
            disabled={isSubmitting || !issueDescription.trim()}
            className="w-full bg-gradient-to-r from-green-600 to-teal-600 text-white px-4 py-3 rounded-xl font-medium hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Submitting...
              </>
            ) : (
              <>
                <Send className="w-5 h-5" />
                Submit Issue
              </>
            )}
          </button>
        </div>
      </div>
    );
  }

  if (currentView === 'chat') {
    return (
      <div className="flex flex-col h-screen bg-gray-50 max-w-md mx-auto">
        <div className="bg-gradient-to-r from-green-600 to-teal-600 text-white px-6 py-4">
          <div className="flex items-center gap-3">
            <button onClick={() => setCurrentView('dashboard')} className="p-1">
              <X className="w-6 h-6" />
            </button>
            <h1 className="text-xl font-bold">Chat</h1>
          </div>
        </div>

        <div className="flex-1 overflow-hidden">
          <StreamChatPane persona="tenant" />
        </div>

        <BottomNav active="chat" role="tenant" onNavigate={(view) => setCurrentView(view)} />
      </div>
    );
  }

  return null;
}

// ==================== CONTRACTOR DASHBOARD ====================
function ContractorDashboard({ session }: { session: any }) {
  const [currentView, setCurrentView] = useState('bids');
  const userId = session?.user?.email || '';
  const { jobs, loading: jobsLoading } = useJobs(userId);

  return (
    <div className="flex flex-col h-screen bg-gray-50 max-w-md mx-auto">
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold">Available Jobs</h1>
            <div className="text-sm opacity-90">{session?.user?.email}</div>
          </div>
          <div className="flex items-center gap-2 bg-white/20 px-3 py-1 rounded-full">
            <Bot className="w-4 h-4" />
            <span className="text-sm font-medium">AI Active</span>
          </div>
        </div>
        <div className="bg-white/20 rounded-lg p-3 flex items-center justify-between">
          <div className="text-center">
            <div className="text-2xl font-bold">{jobs.length}</div>
            <div className="text-xs opacity-90">Available</div>
          </div>
          <div className="w-px h-10 bg-white/30"></div>
          <div className="text-center">
            <div className="text-2xl font-bold">4.8★</div>
            <div className="text-xs opacity-90">Rating</div>
          </div>
          <div className="w-px h-10 bg-white/30"></div>
          <div className="text-center">
            <div className="text-2xl font-bold">247</div>
            <div className="text-xs opacity-90">Completed</div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {jobsLoading && (
          <div className="flex justify-center py-8">
            <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
          </div>
        )}

        {!jobsLoading && jobs.length === 0 && (
          <div className="text-center py-8">
            <Briefcase className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-500">No jobs available yet</p>
            <p className="text-sm text-gray-400 mt-1">Check back soon for new opportunities</p>
          </div>
        )}

        {jobs.map(job => (
          <div key={job.id} className="bg-white rounded-xl p-4 border border-gray-200 hover:border-purple-300 hover:shadow-md transition-all">
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                    job.urgency === 'High' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {job.urgency || 'Medium'}
                  </span>
                  <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-medium rounded-full">
                    {job.matchScore || 85}% Match
                  </span>
                </div>
                <h3 className="font-bold text-gray-900 text-lg">{job.title || 'Maintenance Job'}</h3>
                <div className="text-sm text-gray-600 mt-1">{job.property || 'Property Address'}</div>
              </div>
            </div>

            <div className="flex items-center gap-4 mb-3 text-sm text-gray-600">
              <div className="flex items-center gap-1">
                <DollarSign className="w-4 h-4" />
                <span>{job.budget || '$200-300'}</span>
              </div>
              <div className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                <span>{job.distance || '3.5 miles'}</span>
              </div>
            </div>

            <button className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-4 py-2 rounded-lg font-medium hover:shadow-lg transition-all">
              View Details & Accept
            </button>
          </div>
        ))}
      </div>

      <BottomNav active="bids" role="contractor" onNavigate={(view) => setCurrentView(view)} />
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
