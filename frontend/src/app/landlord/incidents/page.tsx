"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { AlertCircle, Clock, Filter } from "lucide-react";
import { StatusBadge } from "@/components/ui/StatusBadge";

type Incident = {
  incident_id: string;
  title: string;
  category: string;
  urgency: string;
  status: string;
  description: string;
  created_at: string;
  tenant_name?: string;
  photo_count?: number;
};

type FilterType = "all" | "high_priority" | "requires_attention";

export default function LandlordIncidentsPage() {
  const router = useRouter();
  const { data: session } = useSession();

  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [filteredIncidents, setFilteredIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<FilterType>("all");

  const getToken = () => {
    return session?.user?.accessToken || localStorage.getItem("token") || "";
  };

  useEffect(() => {
    fetchIncidents();
  }, []);

  useEffect(() => {
    applyFilter();
  }, [incidents, activeFilter]);

  const fetchIncidents = async () => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/v1/incidents/landlord/pending", {
        method: "GET",
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
      });

      if (!res.ok) {
        throw new Error("Failed to fetch pending incidents");
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

  const applyFilter = () => {
    let filtered = [...incidents];

    switch (activeFilter) {
      case "high_priority":
        filtered = incidents.filter(
          (inc) => inc.urgency === "high" || inc.urgency === "emergency",
        );
        break;
      case "requires_attention":
        filtered = incidents.filter((inc) => inc.status === "pending");
        break;
      case "all":
      default:
        filtered = incidents;
        break;
    }

    setFilteredIncidents(filtered);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) {
      return "Just now";
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    } else {
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
    }
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency.toLowerCase()) {
      case "low":
        return "border-l-green-500";
      case "medium":
        return "border-l-yellow-500";
      case "high":
        return "border-l-orange-500";
      case "emergency":
        return "border-l-red-500";
      default:
        return "border-l-slate-500";
    }
  };

  const getUrgencyBadgeColor = (urgency: string) => {
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

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Pending Incidents</h1>
          <p className="text-slate-400">Review and manage tenant-reported incidents</p>
        </div>

        {/* Filters */}
        <div className="mb-6 flex items-center gap-3 overflow-x-auto pb-2">
          <Filter className="w-5 h-5 text-slate-400 flex-shrink-0" />
          <button
            onClick={() => setActiveFilter("all")}
            className={`px-4 py-2 rounded-lg font-medium transition whitespace-nowrap ${
              activeFilter === "all"
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            All ({incidents.length})
          </button>
          <button
            onClick={() => setActiveFilter("high_priority")}
            className={`px-4 py-2 rounded-lg font-medium transition whitespace-nowrap ${
              activeFilter === "high_priority"
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            High Priority (
            {incidents.filter((i) => i.urgency === "high" || i.urgency === "emergency").length})
          </button>
          <button
            onClick={() => setActiveFilter("requires_attention")}
            className={`px-4 py-2 rounded-lg font-medium transition whitespace-nowrap ${
              activeFilter === "requires_attention"
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            Requires Attention ({incidents.filter((i) => i.status === "pending").length})
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
        {!loading && filteredIncidents.length === 0 && (
          <div className="text-center py-12">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-800 mb-4">
              <AlertCircle className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-xl font-semibold mb-2">No incidents found</h3>
            <p className="text-slate-400">
              {activeFilter === "all"
                ? "No pending incidents at this time"
                : "No incidents match the selected filter"}
            </p>
          </div>
        )}

        {/* Incidents Grid */}
        {!loading && filteredIncidents.length > 0 && (
          <div className="grid gap-4">
            {filteredIncidents.map((incident) => (
              <div
                key={incident.incident_id}
                className={`bg-slate-900 border border-slate-800 border-l-4 ${getUrgencyColor(
                  incident.urgency,
                )} rounded-lg p-6 hover:border-blue-500 hover:shadow-lg transition cursor-pointer`}
                onClick={() => router.push(`/landlord/incidents/${incident.incident_id}`)}
              >
                <div className="flex items-start justify-between gap-6">
                  {/* Main Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-4 mb-3">
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg mb-2 line-clamp-1">
                          {incident.title}
                        </h3>
                        <p className="text-slate-400 text-sm line-clamp-2 mb-3">
                          {incident.description}
                        </p>
                        <div className="flex items-center gap-4 flex-wrap">
                          <span className="px-2 py-1 bg-slate-800 rounded text-xs text-slate-300 capitalize">
                            {incident.category}
                          </span>
                          <span
                            className={`px-2 py-1 rounded text-xs font-medium capitalize ${getUrgencyBadgeColor(
                              incident.urgency,
                            )}`}
                          >
                            {incident.urgency}
                          </span>
                          {incident.tenant_name && (
                            <span className="text-xs text-slate-500">
                              by {incident.tenant_name}
                            </span>
                          )}
                          {incident.photo_count && incident.photo_count > 0 && (
                            <span className="text-xs text-blue-400">
                              📷 {incident.photo_count}{" "}
                              {incident.photo_count === 1 ? "photo" : "photos"}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Sidebar */}
                  <div className="flex flex-col items-end gap-3">
                    <StatusBadge status={incident.status} type="incident" />
                    <div className="flex items-center gap-1 text-sm text-slate-500">
                      <Clock className="w-4 h-4" />
                      <span>{formatDate(incident.created_at)}</span>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/landlord/incidents/${incident.incident_id}`);
                      }}
                      className="text-blue-400 hover:text-blue-300 font-medium text-sm"
                    >
                      Review →
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
