"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  AlertCircle,
  DollarSign,
  Clock,
  Star,
  CheckCircle,
  Briefcase,
  Calendar,
} from "lucide-react";
import { StatusBadge } from "@/components/ui/StatusBadge";

type Job = {
  job_id: string;
  incident_id: string;
  landlord_id: string;
  budget_min: number;
  budget_max: number;
  status: string;
  created_at: string;
  incident?: {
    title: string;
    category: string;
    description: string;
  };
};

type Bid = {
  bid_id: string;
  job_id: string;
  contractor_id: string;
  bid_amount: number;
  estimated_hours: number;
  materials_cost: number;
  labor_cost: number;
  description: string;
  status: string;
  created_at: string;
  contractor?: {
    contractor_id: string;
    name: string;
    email: string;
    rating?: number;
    jobs_completed?: number;
  };
};

export default function LandlordJobBidsPage() {
  const router = useRouter();
  const params = useParams();
  const { data: session } = useSession();
  const jobId = params.id as string;

  const [job, setJob] = useState<Job | null>(null);
  const [bids, setBids] = useState<Bid[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedBidId, setSelectedBidId] = useState<string | null>(null);
  const [awardingBid, setAwardingBid] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  const getToken = () => {
    return session?.user?.accessToken || localStorage.getItem("token") || "";
  };

  useEffect(() => {
    if (jobId) {
      fetchJobAndBids();
    }
  }, [jobId]);

  const fetchJobAndBids = async () => {
    setLoading(true);
    setError(null);

    try {
      // Fetch job details
      const jobRes = await fetch(`/api/v1/jobs/${jobId}`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
      });

      if (!jobRes.ok) {
        throw new Error("Failed to fetch job details");
      }

      const jobData = await jobRes.json();
      setJob(jobData);

      // Fetch bids
      const bidsRes = await fetch(`/api/v1/jobs/${jobId}/bids`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
      });

      if (!bidsRes.ok) {
        throw new Error("Failed to fetch bids");
      }

      const bidsData = await bidsRes.json();
      // Sort bids by amount (lowest first)
      const sortedBids = bidsData.sort((a: Bid, b: Bid) => a.bid_amount - b.bid_amount);
      setBids(sortedBids);
    } catch (err: any) {
      console.error("Error fetching job and bids:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAwardBid = async () => {
    if (!selectedBidId) return;

    setAwardingBid(true);
    setError(null);

    try {
      const res = await fetch(`/api/v1/jobs/${jobId}/award/${selectedBidId}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to award job");
      }

      // Success! Refresh the page
      setShowConfirmDialog(false);
      await fetchJobAndBids();

      // Show success message
      alert("Job successfully awarded to contractor!");
    } catch (err: any) {
      console.error("Error awarding bid:", err);
      setError(err.message);
    } finally {
      setAwardingBid(false);
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

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount);
  };

  const renderStars = (rating: number) => {
    return (
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={`w-4 h-4 ${
              star <= rating ? "fill-yellow-400 text-yellow-400" : "text-slate-600"
            }`}
          />
        ))}
        <span className="ml-1 text-sm text-slate-400">({rating.toFixed(1)})</span>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="p-6 bg-red-900/50 border border-red-500 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-200 text-lg">Error</h3>
              <p className="text-red-300">{error || "Job not found"}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.back()}
            className="text-blue-400 hover:text-blue-300 mb-4 inline-flex items-center gap-2"
          >
            ← Back
          </button>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold mb-2">
                {job.incident?.title || "Job Listing"}
              </h1>
              <p className="text-slate-400">{job.incident?.description}</p>
            </div>
            <StatusBadge status={job.status} type="job" />
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

        {/* Job Info Card */}
        <div className="mb-8 bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Job Details</h2>
          <div className="grid md:grid-cols-3 gap-6">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Category</label>
              <div className="flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-slate-400" />
                <span className="capitalize">{job.incident?.category || "N/A"}</span>
              </div>
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Budget Range</label>
              <div className="flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-slate-400" />
                <span className="font-semibold">
                  {formatCurrency(job.budget_min)} - {formatCurrency(job.budget_max)}
                </span>
              </div>
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Posted</label>
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-slate-400" />
                <span>{formatDate(job.created_at)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Bids Section */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4">
            Received Bids ({bids.length})
          </h2>

          {bids.length === 0 ? (
            <div className="text-center py-12 bg-slate-900 border border-slate-800 rounded-lg">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-800 mb-4">
                <AlertCircle className="w-8 h-8 text-slate-400" />
              </div>
              <h3 className="text-xl font-semibold mb-2">No bids yet</h3>
              <p className="text-slate-400">
                Contractors will submit bids for this job soon
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {bids.map((bid, index) => (
                <div
                  key={bid.bid_id}
                  className={`bg-slate-900 border rounded-lg p-6 transition ${
                    selectedBidId === bid.bid_id
                      ? "border-blue-500 shadow-lg shadow-blue-500/20"
                      : "border-slate-800 hover:border-slate-700"
                  } ${index === 0 ? "border-l-4 border-l-emerald-500" : ""}`}
                >
                  <div className="flex items-start justify-between gap-6">
                    {/* Left: Contractor Info */}
                    <div className="flex-1">
                      <div className="flex items-start gap-4 mb-4">
                        <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-xl font-bold">
                          {bid.contractor?.name?.charAt(0) || "C"}
                        </div>
                        <div className="flex-1">
                          <h3 className="font-semibold text-lg mb-1">
                            {bid.contractor?.name || "Contractor"}
                          </h3>
                          {bid.contractor?.rating && renderStars(bid.contractor.rating)}
                          <div className="flex items-center gap-4 mt-2 text-sm text-slate-400">
                            <span className="flex items-center gap-1">
                              <CheckCircle className="w-4 h-4" />
                              {bid.contractor?.jobs_completed || 0} jobs completed
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Bid Details */}
                      <div className="grid md:grid-cols-3 gap-4 mb-4">
                        <div className="bg-slate-800/50 rounded-lg p-3">
                          <label className="block text-xs text-slate-400 mb-1">
                            Estimated Hours
                          </label>
                          <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4 text-slate-400" />
                            <span className="font-semibold">{bid.estimated_hours}h</span>
                          </div>
                        </div>
                        <div className="bg-slate-800/50 rounded-lg p-3">
                          <label className="block text-xs text-slate-400 mb-1">
                            Materials Cost
                          </label>
                          <span className="font-semibold">
                            {formatCurrency(bid.materials_cost)}
                          </span>
                        </div>
                        <div className="bg-slate-800/50 rounded-lg p-3">
                          <label className="block text-xs text-slate-400 mb-1">
                            Labor Cost
                          </label>
                          <span className="font-semibold">
                            {formatCurrency(bid.labor_cost)}
                          </span>
                        </div>
                      </div>

                      {/* Description */}
                      <div>
                        <label className="block text-sm text-slate-400 mb-2">
                          Bid Description
                        </label>
                        <p className="text-slate-200 leading-relaxed">{bid.description}</p>
                      </div>
                    </div>

                    {/* Right: Bid Amount & Actions */}
                    <div className="flex flex-col items-end gap-4">
                      {index === 0 && (
                        <span className="px-3 py-1 bg-emerald-900/30 text-emerald-400 text-xs font-medium rounded-full">
                          LOWEST BID
                        </span>
                      )}
                      <div className="text-right">
                        <label className="block text-sm text-slate-400 mb-1">
                          Bid Amount
                        </label>
                        <div className="text-3xl font-bold text-emerald-400">
                          {formatCurrency(bid.bid_amount)}
                        </div>
                      </div>

                      {bid.status === "pending" && job.status === "open" && (
                        <div className="flex flex-col gap-2 w-full">
                          <button
                            onClick={() => setSelectedBidId(bid.bid_id)}
                            className={`px-4 py-2 rounded-lg font-medium transition ${
                              selectedBidId === bid.bid_id
                                ? "bg-blue-600 text-white"
                                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                            }`}
                          >
                            {selectedBidId === bid.bid_id ? "Selected" : "Select for Review"}
                          </button>

                          {selectedBidId === bid.bid_id && (
                            <button
                              onClick={() => setShowConfirmDialog(true)}
                              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium transition flex items-center justify-center gap-2"
                            >
                              <CheckCircle className="w-4 h-4" />
                              Award Job
                            </button>
                          )}
                        </div>
                      )}

                      {bid.status === "awarded" && (
                        <div className="px-4 py-2 bg-emerald-900/30 text-emerald-400 rounded-lg font-medium">
                          ✓ Awarded
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Confirmation Dialog */}
        {showConfirmDialog && selectedBidId && (
          <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 max-w-md w-full">
              <h3 className="text-xl font-bold mb-4">Confirm Job Award</h3>
              <p className="text-slate-300 mb-6">
                Are you sure you want to award this job to this contractor? This action cannot
                be undone.
              </p>

              <div className="flex gap-3">
                <button
                  onClick={() => setShowConfirmDialog(false)}
                  disabled={awardingBid}
                  className="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg font-medium transition disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAwardBid}
                  disabled={awardingBid}
                  className="flex-1 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {awardingBid ? (
                    "Awarding..."
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      Confirm Award
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
