"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  AlertCircle,
  Clock,
  DollarSign,
  ChevronDown,
  ChevronUp,
  CheckCircle,
} from "lucide-react";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PhotoGallery } from "@/components/ui/PhotoGallery";

type Incident = {
  incident_id: string;
  title: string;
  category: string;
  urgency: string;
  status: string;
  description: string;
  created_at: string;
  tenant_id: string;
  tenant_name?: string;
  photos?: Array<{ url: string; photo_id: string }>;
  discovery_answers?: Record<string, string>;
};

export default function LandlordIncidentReviewPage() {
  const router = useRouter();
  const params = useParams();
  const { data: session } = useSession();
  const incidentId = params.id as string;

  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Job creation state
  const [showJobForm, setShowJobForm] = useState(false);
  const [minBudget, setMinBudget] = useState("");
  const [maxBudget, setMaxBudget] = useState("");
  const [creatingJob, setCreatingJob] = useState(false);

  // Discovery answers expansion
  const [discoveryExpanded, setDiscoveryExpanded] = useState(false);

  const getToken = () => {
    return session?.user?.accessToken || localStorage.getItem("token") || "";
  };

  useEffect(() => {
    if (incidentId) {
      fetchIncident();
    }
  }, [incidentId]);

  const fetchIncident = async () => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/v1/incidents/${incidentId}`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
      });

      if (!res.ok) {
        throw new Error("Failed to fetch incident details");
      }

      const data = await res.json();
      setIncident(data);
    } catch (err: any) {
      console.error("Error fetching incident:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingJob(true);
    setError(null);

    try {
      const res = await fetch("/api/v1/jobs/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          incident_id: incidentId,
          budget_min: parseFloat(minBudget),
          budget_max: parseFloat(maxBudget),
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to create job");
      }

      const data = await res.json();
      // Redirect to the job page
      router.push(`/landlord/jobs/${data.job_id}`);
    } catch (err: any) {
      console.error("Error creating job:", err);
      setError(err.message);
    } finally {
      setCreatingJob(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency.toLowerCase()) {
      case "low":
        return "text-green-400 bg-green-900/30";
      case "medium":
        return "text-yellow-400 bg-yellow-900/30";
      case "high":
        return "text-orange-400 bg-orange-900/30";
      case "emergency":
        return "text-red-400 bg-red-900/30";
      default:
        return "text-slate-400 bg-slate-800";
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="p-6 bg-red-900/50 border border-red-500 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-200 text-lg">Error</h3>
              <p className="text-red-300">{error || "Incident not found"}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.back()}
            className="text-blue-400 hover:text-blue-300 mb-4 inline-flex items-center gap-2"
          >
            ← Back
          </button>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h1 className="text-3xl font-bold mb-2">{incident.title}</h1>
              <div className="flex items-center gap-3 text-sm text-slate-400">
                <Clock className="w-4 h-4" />
                <span>Reported {formatDate(incident.created_at)}</span>
                {incident.tenant_name && (
                  <>
                    <span>•</span>
                    <span>by {incident.tenant_name}</span>
                  </>
                )}
              </div>
            </div>
            <StatusBadge status={incident.status} type="incident" />
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-900/50 border border-red-500 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-200">Error</h3>
              <p className="text-red-300 text-sm">{error}</p>
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Details Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Incident Details</h2>

              <div className="space-y-4">
                {/* Category & Urgency */}
                <div className="flex items-center gap-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Category</label>
                    <span className="inline-block px-3 py-1 bg-slate-800 rounded-lg text-slate-200 capitalize">
                      {incident.category}
                    </span>
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Urgency</label>
                    <span
                      className={`inline-block px-3 py-1 rounded-lg font-medium capitalize ${getUrgencyColor(
                        incident.urgency,
                      )}`}
                    >
                      {incident.urgency}
                    </span>
                  </div>
                </div>

                {/* Description */}
                <div>
                  <label className="block text-sm text-slate-400 mb-2">Description</label>
                  <p className="text-slate-200 leading-relaxed">{incident.description}</p>
                </div>
              </div>
            </div>

            {/* Photos */}
            {incident.photos && incident.photos.length > 0 && (
              <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
                <h2 className="text-xl font-semibold mb-4">Photos</h2>
                <PhotoGallery photos={incident.photos} />
              </div>
            )}

            {/* Discovery Answers */}
            {incident.discovery_answers &&
              Object.keys(incident.discovery_answers).length > 0 && (
                <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
                  <button
                    onClick={() => setDiscoveryExpanded(!discoveryExpanded)}
                    className="w-full flex items-center justify-between text-xl font-semibold mb-4 hover:text-blue-400 transition"
                  >
                    <span>Additional Details</span>
                    {discoveryExpanded ? (
                      <ChevronUp className="w-5 h-5" />
                    ) : (
                      <ChevronDown className="w-5 h-5" />
                    )}
                  </button>

                  {discoveryExpanded && (
                    <div className="space-y-4">
                      {Object.entries(incident.discovery_answers).map(([question, answer]) => (
                        <div key={question}>
                          <label className="block text-sm text-slate-400 mb-1">
                            {question}
                          </label>
                          <p className="text-slate-200">{answer || "No answer provided"}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Create Job Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Actions</h2>

              {!showJobForm ? (
                <button
                  onClick={() => setShowJobForm(true)}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-semibold transition flex items-center justify-center gap-2"
                >
                  <DollarSign className="w-5 h-5" />
                  Create Job Listing
                </button>
              ) : (
                <form onSubmit={handleCreateJob} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Minimum Budget ($)
                    </label>
                    <input
                      type="number"
                      required
                      min="0"
                      step="0.01"
                      value={minBudget}
                      onChange={(e) => setMinBudget(e.target.value)}
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="500.00"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Maximum Budget ($)
                    </label>
                    <input
                      type="number"
                      required
                      min="0"
                      step="0.01"
                      value={maxBudget}
                      onChange={(e) => setMaxBudget(e.target.value)}
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="1500.00"
                    />
                  </div>

                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => setShowJobForm(false)}
                      className="flex-1 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg font-medium transition"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={creatingJob || !minBudget || !maxBudget}
                      className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {creatingJob ? (
                        "Creating..."
                      ) : (
                        <>
                          <CheckCircle className="w-4 h-4" />
                          Create
                        </>
                      )}
                    </button>
                  </div>
                </form>
              )}

              <p className="mt-4 text-xs text-slate-400">
                Creating a job will allow contractors to submit bids for this work.
              </p>
            </div>

            {/* Info Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
              <h3 className="font-semibold mb-3">Need Help?</h3>
              <p className="text-sm text-slate-400">
                Review the incident details and photos before creating a job listing.
                Contractors will be able to submit bids based on the information provided.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
