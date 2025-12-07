"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { Plus, AlertCircle, Clock, CheckCircle } from "lucide-react";
import { StatusBadge } from "@/components/ui/StatusBadge";

type Incident = {
  incident_id: string;
  title: string;
  category: string;
  urgency: string;
  status: string;
  description: string;
  created_at: string;
};

export default function TenantIncidentsPage() {
  const router = useRouter();
  const { data: session } = useSession();

  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const getToken = () => {
    return session?.user?.accessToken || localStorage.getItem("token") || "";
  };

  useEffect(() => {
    fetchIncidents();
  }, []);

  const fetchIncidents = async () => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/v1/incidents/my-incidents", {
        method: "GET",
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
      });

      if (!res.ok) {
        throw new Error("Failed to fetch incidents");
      }

      const data = await res.json();
      setIncidents(data);
    } catch (err: any) {
      console.error("Error fetching incidents:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency.toLowerCase()) {
      case "low":
        return "text-green-400";
      case "medium":
        return "text-yellow-400";
      case "high":
        return "text-orange-400";
      case "emergency":
        return "text-red-400";
      default:
        return "text-slate-400";
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">My Incidents</h1>
            <p className="text-slate-400">Track and manage your reported incidents</p>
          </div>
          <button
            onClick={() => router.push("/tenant/incidents/new")}
            className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-semibold transition"
          >
            <Plus className="w-5 h-5" />
            New Incident
          </button>
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

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        )}

        {/* Empty State */}
        {!loading && incidents.length === 0 && (
          <div className="text-center py-12">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-800 mb-4">
              <AlertCircle className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-xl font-semibold mb-2">No incidents yet</h3>
            <p className="text-slate-400 mb-6">Report an issue to get started</p>
            <button
              onClick={() => router.push("/tenant/incidents/new")}
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-semibold transition"
            >
              <Plus className="w-5 h-5" />
              Report First Incident
            </button>
          </div>
        )}

        {/* Incidents Grid */}
        {!loading && incidents.length > 0 && (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {incidents.map((incident) => (
              <div
                key={incident.incident_id}
                className="bg-slate-900 border border-slate-800 rounded-lg p-6 hover:border-blue-500 transition cursor-pointer"
                onClick={() => router.push(`/tenant/incidents/${incident.incident_id}`)}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-semibold text-lg line-clamp-2">{incident.title}</h3>
                  <StatusBadge status={incident.status} type="incident" />
                </div>

                {/* Category & Urgency */}
                <div className="flex items-center gap-3 mb-3 text-sm">
                  <span className="px-2 py-1 bg-slate-800 rounded text-slate-300">
                    {incident.category}
                  </span>
                  <span className={`font-medium ${getUrgencyColor(incident.urgency)}`}>
                    {incident.urgency.toUpperCase()}
                  </span>
                </div>

                {/* Description */}
                <p className="text-slate-400 text-sm mb-4 line-clamp-2">
                  {incident.description}
                </p>

                {/* Footer */}
                <div className="flex items-center justify-between text-sm text-slate-500">
                  <div className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    <span>{formatDate(incident.created_at)}</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      router.push(`/tenant/incidents/${incident.incident_id}`);
                    }}
                    className="text-blue-400 hover:text-blue-300 font-medium"
                  >
                    View Details →
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Floating Action Button (Mobile) */}
        <button
          onClick={() => router.push("/tenant/incidents/new")}
          className="fixed bottom-6 right-6 md:hidden w-14 h-14 bg-blue-600 hover:bg-blue-500 rounded-full shadow-lg flex items-center justify-center transition"
        >
          <Plus className="w-6 h-6" />
        </button>
      </div>
    </div>
  );
}
