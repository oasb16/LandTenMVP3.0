"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  ArrowLeft,
  AlertCircle,
  Clock,
  MapPin,
  User,
  CheckCircle,
  Camera,
  FileText
} from "lucide-react";

type Incident = {
  incident_id: string;
  title: string;
  description: string;
  category: string;
  urgency: string;
  status: string;
  property_id: string;
  unit_id?: string;
  tenant_id: string;
  landlord_id: string;
  photos?: string[] | any[];
  discovery_data?: any;
  job_id?: string;
  created_at: string;
  updated_at: string;
};

export default function TenantIncidentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const { data: session } = useSession();
  const incidentId = params?.id as string;

  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const getToken = () => {
    return session?.user?.accessToken || localStorage.getItem("token") || "";
  };

  useEffect(() => {
    if (!incidentId) return;

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
        console.log("Incident data:", data); // Debug log
        setIncident(data);
      } catch (err: any) {
        console.error("Error fetching incident:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchIncident();
  }, [incidentId]);

  const formatDate = (dateString?: string) => {
    if (!dateString) return "N/A";
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return "Invalid date";
      return date.toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (err) {
      return "Invalid date";
    }
  };
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
        return "bg-green-900/30 text-green-400 border-green-500";
      case "medium":
        return "bg-yellow-900/30 text-yellow-400 border-yellow-500";
      case "high":
        return "bg-orange-900/30 text-orange-400 border-orange-500";
      case "emergency":
        return "bg-red-900/30 text-red-400 border-red-500";
      default:
        return "bg-slate-800 text-slate-400 border-slate-500";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "created":
        return "bg-blue-900/30 text-blue-400 border-blue-500";
      case "discovery":
        return "bg-purple-900/30 text-purple-400 border-purple-500";
      case "landlord_review":
        return "bg-yellow-900/30 text-yellow-400 border-yellow-500";
      case "job_created":
        return "bg-emerald-900/30 text-emerald-400 border-emerald-500";
      case "completed":
        return "bg-green-900/30 text-green-400 border-green-500";
      case "cancelled":
        return "bg-red-900/30 text-red-400 border-red-500";
      default:
        return "bg-slate-800 text-slate-400 border-slate-500";
    }
  };

  const getStatusLabel = (status: string) => {
    return status
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="mb-6">
            <button
              onClick={() => router.push("/tenant/incidents")}
              className="flex items-center gap-2 text-slate-400 hover:text-slate-200 transition"
            >
              <ArrowLeft className="w-5 h-5" />
              Back to Incidents
            </button>
          </div>

          <div className="bg-red-900/50 border border-red-500 rounded-lg p-6 flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-200 mb-1">Error Loading Incident</h3>
              <p className="text-red-300">{error || "Incident not found"}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Back Button */}
        <div className="mb-6">
          <button
            onClick={() => router.push("/tenant/incidents")}
            className="flex items-center gap-2 text-slate-400 hover:text-slate-200 transition"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Incidents
          </button>
        </div>

        {/* Header */}
        <div className="mb-8">
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1">
              <h1 className="text-3xl font-bold mb-2">{incident.title}</h1>
              <p className="text-slate-400 text-sm">
                Incident ID: {incident.incident_id}
              </p>
            </div>
            <div className="flex flex-col gap-2 items-end">
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(
                  incident.status
                )}`}
              >
                {getStatusLabel(incident.status)}
              </span>
              <span
                className={`px-3 py-1 rounded-full text-xs font-medium border ${getUrgencyColor(
                  incident.urgency
                )}`}
              >
                {incident.urgency.toUpperCase()}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap gap-4 text-sm text-slate-400">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              <span>Created {formatDate(incident.created_at)}</span>
            </div>
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              <span>Property: {incident.property_id}</span>
            </div>
            {incident.unit_id && (
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4" />
                <span>Unit: {incident.unit_id}</span>
              </div>
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="space-y-6">
          {/* Description */}
          <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
            <h2 className="text-xl font-semibold mb-3 flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Description
            </h2>
            <p className="text-slate-300 whitespace-pre-wrap">{incident.description}</p>
            <div className="mt-4 flex items-center gap-3">
              <span className="px-3 py-1 bg-slate-800 rounded text-sm capitalize">
                {incident.category}
              </span>
            </div>
          </div>

          {/* Photos */}
          {incident.photos && Array.isArray(incident.photos) && incident.photos.length > 0 && (
            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Camera className="w-5 h-5" />
                Photos ({incident.photos.length})
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {incident.photos.map((photo: any, index: number) => (
                  <div
                    key={index}
                    className="aspect-square rounded-lg overflow-hidden bg-slate-800"
                  >
                    <img
                      src={typeof photo === 'string' ? photo : photo.s3_url || photo.url}
                      alt={`Incident photo ${index + 1}`}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg"/>';
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Discovery Data */}
          {incident.discovery_data && (
            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <h2 className="text-xl font-semibold mb-4">Additional Details</h2>
              <div className="space-y-3">
                {Object.entries(incident.discovery_data).map(([key, value]) => (
                  <div key={key} className="border-b border-slate-800 pb-3 last:border-b-0">
                    <p className="text-sm text-slate-400 mb-1">{key}</p>
                    <p className="text-slate-200">{String(value)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Job Link */}
          {incident.job_id && (
            <div className="bg-emerald-900/20 border border-emerald-800 rounded-lg p-6">
              <div className="flex items-start gap-3">
                <CheckCircle className="w-6 h-6 text-emerald-400 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="font-semibold text-emerald-200 mb-1">
                    Maintenance Job Created
                  </h3>
                  <p className="text-emerald-300 text-sm mb-3">
                    A job has been created for this incident and is being processed.
                  </p>
                  <button
                    onClick={() => router.push(`/tenant/jobs/${incident.job_id}`)}
                    className="text-emerald-400 hover:text-emerald-300 font-medium text-sm"
                  >
                    View Job Details →
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Status Timeline (Optional Enhancement) */}
          <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
            <h2 className="text-xl font-semibold mb-4">Status</h2>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                  <CheckCircle className="w-5 h-5" />
                </div>
                <div>
                  <p className="font-medium">Incident Reported</p>
                  <p className="text-sm text-slate-400">
                    {formatDate(incident.created_at)}
                  </p>
                </div>
              </div>

              {incident.status !== "created" && (
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center">
                    <CheckCircle className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="font-medium">Under Review</p>
                    <p className="text-sm text-slate-400">In progress</p>
                  </div>
                </div>
              )}

              {incident.status === "completed" && (
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center">
                    <CheckCircle className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="font-medium">Resolved</p>
                    <p className="text-sm text-slate-400">Incident completed</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
