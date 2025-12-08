"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { Briefcase, Clock, DollarSign, AlertCircle, Filter } from "lucide-react";
import { StatusBadge } from "@/components/ui/StatusBadge";

type Job = {
  job_id: string;
  title: string;
  description: string;
  category: string;
  budget_min: number;
  budget_max: number;
  status: string;
  created_at: string;
  bid_count?: number;
  incident_id?: string;
};

type FilterType = "all" | "open" | "in_progress" | "completed";

export default function LandlordJobsPage() {
  const router = useRouter();
  const { data: session } = useSession();

  const [jobs, setJobs] = useState<Job[]>([]);
  const [filteredJobs, setFilteredJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<FilterType>("all");

  const getToken = () => {
    return session?.user?.accessToken || localStorage.getItem("token") || "";
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  useEffect(() => {
    applyFilter();
  }, [jobs, activeFilter]);

  const fetchJobs = async () => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/v1/jobs/landlord/my-jobs", {
        method: "GET",
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
      });

      if (!res.ok) {
        throw new Error("Failed to fetch jobs");
      }

      const data = await res.json();
      setJobs(data);
    } catch (err: any) {
      console.error("Error fetching jobs:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const applyFilter = () => {
    let filtered = [...jobs];

    switch (activeFilter) {
      case "open":
        filtered = jobs.filter((job) => job.status === "open");
        break;
      case "in_progress":
        filtered = jobs.filter((job) => job.status === "in_progress");
        break;
      case "completed":
        filtered = jobs.filter((job) => job.status === "completed");
        break;
      case "all":
      default:
        filtered = jobs;
        break;
    }

    setFilteredJobs(filtered);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const formatBudget = (min: number, max: number) => {
    return `$${min.toLocaleString()} - $${max.toLocaleString()}`;
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "open":
        return "border-l-blue-500";
      case "in_progress":
        return "border-l-yellow-500";
      case "completed":
        return "border-l-green-500";
      case "cancelled":
        return "border-l-red-500";
      default:
        return "border-l-slate-500";
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">My Jobs</h1>
            <p className="text-slate-400">Manage maintenance jobs and contractor bids</p>
          </div>
        </div>

        {/* Filters */}
        <div className="mb-6 flex items-center gap-3 overflow-x-auto pb-2">
          <Filter className="w-5 h-5 text-slate-400 flex-shrink-0" />
          <button
            onClick={() => setActiveFilter("all")}
            className={`px-4 py-2 rounded-lg font-medium transition whitespace-nowrap ${
              activeFilter === "all"
                ? "bg-purple-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            All ({jobs.length})
          </button>
          <button
            onClick={() => setActiveFilter("open")}
            className={`px-4 py-2 rounded-lg font-medium transition whitespace-nowrap ${
              activeFilter === "open"
                ? "bg-purple-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            Open ({jobs.filter((j) => j.status === "open").length})
          </button>
          <button
            onClick={() => setActiveFilter("in_progress")}
            className={`px-4 py-2 rounded-lg font-medium transition whitespace-nowrap ${
              activeFilter === "in_progress"
                ? "bg-purple-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            In Progress ({jobs.filter((j) => j.status === "in_progress").length})
          </button>
          <button
            onClick={() => setActiveFilter("completed")}
            className={`px-4 py-2 rounded-lg font-medium transition whitespace-nowrap ${
              activeFilter === "completed"
                ? "bg-purple-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            Completed ({jobs.filter((j) => j.status === "completed").length})
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
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
          </div>
        )}

        {/* Empty State */}
        {!loading && filteredJobs.length === 0 && (
          <div className="text-center py-12">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-800 mb-4">
              <Briefcase className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-xl font-semibold mb-2">No jobs found</h3>
            <p className="text-slate-400 mb-6">
              {activeFilter === "all"
                ? "No jobs have been created yet"
                : "No jobs match the selected filter"}
            </p>
            <button
              onClick={() => router.push("/landlord/incidents")}
              className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-500 rounded-lg font-semibold transition"
            >
              View Pending Incidents
            </button>
          </div>
        )}

        {/* Jobs Grid */}
        {!loading && filteredJobs.length > 0 && (
          <div className="grid gap-4">
            {filteredJobs.map((job) => (
              <div
                key={job.job_id}
                className={`bg-slate-900 border border-slate-800 border-l-4 ${getStatusColor(
                  job.status,
                )} rounded-lg p-6 hover:border-purple-500 hover:shadow-lg transition cursor-pointer`}
                onClick={() => router.push(`/landlord/jobs/${job.job_id}`)}
              >
                <div className="flex items-start justify-between gap-6">
                  {/* Main Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-4 mb-3">
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg mb-2 line-clamp-1">
                          {job.title}
                        </h3>
                        <p className="text-slate-400 text-sm line-clamp-2 mb-3">
                          {job.description}
                        </p>
                        <div className="flex items-center gap-4 flex-wrap">
                          <span className="px-2 py-1 bg-slate-800 rounded text-xs text-slate-300 capitalize">
                            {job.category}
                          </span>
                          <span className="flex items-center gap-1 text-xs text-emerald-400">
                            <DollarSign className="w-4 h-4" />
                            {formatBudget(job.budget_min, job.budget_max)}
                          </span>
                          {job.bid_count !== undefined && job.bid_count > 0 && (
                            <span className="text-xs text-blue-400">
                              📋 {job.bid_count} {job.bid_count === 1 ? "bid" : "bids"}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Sidebar */}
                  <div className="flex flex-col items-end gap-3">
                    <StatusBadge status={job.status} type="job" />
                    <div className="flex items-center gap-1 text-sm text-slate-500">
                      <Clock className="w-4 h-4" />
                      <span>{formatDate(job.created_at)}</span>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/landlord/jobs/${job.job_id}`);
                      }}
                      className="text-purple-400 hover:text-purple-300 font-medium text-sm"
                    >
                      View Details →
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
