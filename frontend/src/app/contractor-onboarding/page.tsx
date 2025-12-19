"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  CheckCircle2,
  AlertCircle,
  Loader2,
  Briefcase,
  DollarSign,
  ClipboardCheck,
  User,
  Mail,
  Phone,
  MapPin,
  Building,
} from "lucide-react";

interface MagicLinkVerifyResponse {
  valid: boolean;
  email: string;
  job_id: string;
  landlord_id: string;
  property_id: string;
  tenant_id: string;
  contractor_id?: string;
  message: string;
}

interface ContractorFormData {
  business_name: string;
  email: string;
  phone: string;
  categories: string[];
  service_zip_codes: string[];
  license_number: string;
}

interface Job {
  job_id: string;
  title: string;
  description: string;
  category: string;
  urgency: string;
  budget_min?: number;
  budget_max?: number;
  status: string;
  created_at: string;
}

interface Payment {
  total_earnings: number;
  pending: number;
  completed: number;
}

interface DashboardData {
  contractor: any;
  jobs: {
    available: Job[];
    active: Job[];
    completed: Job[];
    total_available: number;
    total_active: number;
    total_completed: number;
  };
  bids: {
    submitted: any[];
    total: number;
  };
  payments: Payment;
}

export default function ContractorOnboardingPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [magicLinkData, setMagicLinkData] = useState<MagicLinkVerifyResponse | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [isExistingContractor, setIsExistingContractor] = useState(false);

  const [formData, setFormData] = useState<ContractorFormData>({
    business_name: "",
    email: "",
    phone: "",
    categories: [],
    service_zip_codes: [],
    license_number: "",
  });

  // Verify magic link token on mount
  useEffect(() => {
    const verifyToken = async () => {
      if (!token) {
        setError("No magic link token provided");
        setVerifying(false);
        setLoading(false);
        return;
      }

      try {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
        const response = await fetch(`${backendUrl}/magic-links/verify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });

        if (!response.ok) {
          throw new Error("Failed to verify magic link");
        }

        const data: MagicLinkVerifyResponse = await response.json();

        if (!data.valid) {
          setError(data.message || "Invalid or expired magic link");
          setVerifying(false);
          setLoading(false);
          return;
        }

        setMagicLinkData(data);
        setFormData((prev) => ({ ...prev, email: data.email }));

        // If contractor exists, load dashboard
        if (data.contractor_id) {
          setIsExistingContractor(true);
          await loadDashboard(data.contractor_id);
        }

        setVerifying(false);
        setLoading(false);
      } catch (err) {
        console.error("Error verifying token:", err);
        setError("Failed to verify magic link. Please try again.");
        setVerifying(false);
        setLoading(false);
      }
    };

    verifyToken();
  }, [token]);

  const loadDashboard = async (contractorId: string) => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
      const response = await fetch(`${backendUrl}/magic-links/onboarding-dashboard/${contractorId}`);

      if (!response.ok) {
        throw new Error("Failed to load dashboard data");
      }

      const data: DashboardData = await response.json();
      setDashboardData(data);
    } catch (err) {
      console.error("Error loading dashboard:", err);
      setError("Failed to load dashboard data");
    }
  };

  const handleSubmitRegistration = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;

      // Submit registration
      const response = await fetch(`${backendUrl}/contractors/register`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          business_name: formData.business_name,
          email: formData.email,
          phone: formData.phone,
          categories: JSON.stringify(formData.categories),
          service_zip_codes: JSON.stringify(formData.service_zip_codes),
          license_number: formData.license_number || "",
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to register contractor");
      }

      const result = await response.json();
      const contractorId = result.contractor?.contractor_id;

      if (!contractorId) {
        throw new Error("Registration succeeded but no contractor ID returned");
      }

      // Mark magic link as used
      await fetch(`${backendUrl}/magic-links/mark-used/${token}?contractor_id=${contractorId}`, {
        method: "POST",
      });

      // Load dashboard for new contractor
      await loadDashboard(contractorId);
      setIsExistingContractor(true);
      setSubmitting(false);
    } catch (err: any) {
      console.error("Error submitting registration:", err);
      setError(err.message || "Failed to register. Please try again.");
      setSubmitting(false);
    }
  };

  const handleInputChange = (field: keyof ContractorFormData, value: string | string[]) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  if (loading || verifying) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 pb-6 flex flex-col items-center">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
            <p className="text-lg font-medium text-gray-700">Verifying magic link...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error && !magicLinkData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-50 to-pink-100">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 pb-6 flex flex-col items-center">
            <AlertCircle className="h-12 w-12 text-red-600 mb-4" />
            <p className="text-lg font-semibold text-gray-900 mb-2">Invalid Link</p>
            <p className="text-sm text-gray-600 text-center">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Show registration form for new contractors
  if (!isExistingContractor && magicLinkData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
        <div className="max-w-2xl mx-auto">
          <Card>
            <CardHeader>
              <CardTitle className="text-2xl">Welcome to LandTen</CardTitle>
              <CardDescription>
                Complete your contractor registration to get started
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmitRegistration} className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="business_name">Business Name *</Label>
                  <Input
                    id="business_name"
                    required
                    value={formData.business_name}
                    onChange={(e) => handleInputChange("business_name", e.target.value)}
                    placeholder="ABC Plumbing Services"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email *</Label>
                  <Input
                    id="email"
                    type="email"
                    required
                    value={formData.email}
                    disabled
                    className="bg-gray-100"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="phone">Phone Number *</Label>
                  <Input
                    id="phone"
                    type="tel"
                    required
                    value={formData.phone}
                    onChange={(e) => handleInputChange("phone", e.target.value)}
                    placeholder="(555) 123-4567"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="categories">Service Categories * (comma-separated)</Label>
                  <Input
                    id="categories"
                    required
                    value={formData.categories.join(", ")}
                    onChange={(e) =>
                      handleInputChange(
                        "categories",
                        e.target.value.split(",").map((c) => c.trim())
                      )
                    }
                    placeholder="plumbing, hvac, electrical"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="zip_codes">Service ZIP Codes * (comma-separated)</Label>
                  <Input
                    id="zip_codes"
                    required
                    value={formData.service_zip_codes.join(", ")}
                    onChange={(e) =>
                      handleInputChange(
                        "service_zip_codes",
                        e.target.value.split(",").map((z) => z.trim())
                      )
                    }
                    placeholder="10001, 10002, 10003"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="license_number">License Number (optional)</Label>
                  <Input
                    id="license_number"
                    value={formData.license_number}
                    onChange={(e) => handleInputChange("license_number", e.target.value)}
                    placeholder="LIC-12345"
                  />
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-md p-4 flex items-start">
                    <AlertCircle className="h-5 w-5 text-red-600 mr-2 mt-0.5" />
                    <p className="text-sm text-red-800">{error}</p>
                  </div>
                )}

                <Button type="submit" className="w-full" disabled={submitting}>
                  {submitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating Account...
                    </>
                  ) : (
                    "Create Contractor Account"
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // Show dashboard for existing contractors
  if (isExistingContractor && dashboardData) {
    const { contractor, jobs, bids, payments } = dashboardData;

    return (
      <div className="min-h-screen bg-gray-50 py-8 px-4">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Header */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  Welcome back, {contractor?.business_name}!
                </h1>
                <p className="text-gray-600 mt-1">
                  {magicLinkData?.message || "Your contractor dashboard"}
                </p>
              </div>
              <CheckCircle2 className="h-12 w-12 text-green-600" />
            </div>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Earnings</CardTitle>
                <DollarSign className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">${payments.total_earnings.toFixed(2)}</div>
                <p className="text-xs text-muted-foreground">
                  ${payments.pending.toFixed(2)} pending
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Active Jobs</CardTitle>
                <Briefcase className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{jobs.total_active}</div>
                <p className="text-xs text-muted-foreground">In progress or scheduled</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Completed Jobs</CardTitle>
                <ClipboardCheck className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{jobs.total_completed}</div>
                <p className="text-xs text-muted-foreground">
                  {contractor?.rating ? `${contractor.rating} avg rating` : "No ratings yet"}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Available Jobs</CardTitle>
                <Briefcase className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{jobs.total_available}</div>
                <p className="text-xs text-muted-foreground">Ready to bid</p>
              </CardContent>
            </Card>
          </div>

          {/* Profile Section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <User className="mr-2 h-5 w-5" />
                Contractor Profile
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="flex items-start">
                  <Building className="h-5 w-5 text-gray-400 mr-3 mt-1" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Business Name</p>
                    <p className="text-base text-gray-900">{contractor?.business_name}</p>
                  </div>
                </div>

                <div className="flex items-start">
                  <Mail className="h-5 w-5 text-gray-400 mr-3 mt-1" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Email</p>
                    <p className="text-base text-gray-900">{contractor?.email}</p>
                  </div>
                </div>

                <div className="flex items-start">
                  <Phone className="h-5 w-5 text-gray-400 mr-3 mt-1" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Phone</p>
                    <p className="text-base text-gray-900">{contractor?.phone}</p>
                  </div>
                </div>

                <div className="flex items-start">
                  <MapPin className="h-5 w-5 text-gray-400 mr-3 mt-1" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Service Areas</p>
                    <p className="text-base text-gray-900">
                      {contractor?.service_zip_codes?.join(", ") || "N/A"}
                    </p>
                  </div>
                </div>

                <div className="flex items-start">
                  <Briefcase className="h-5 w-5 text-gray-400 mr-3 mt-1" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Categories</p>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {contractor?.categories?.map((cat: string, idx: number) => (
                        <Badge key={idx} variant="secondary">
                          {cat}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flex items-start">
                  <CheckCircle2 className="h-5 w-5 text-gray-400 mr-3 mt-1" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Status</p>
                    <Badge
                      variant={contractor?.status === "active" ? "default" : "secondary"}
                      className="mt-1"
                    >
                      {contractor?.status || "pending"}
                    </Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Jobs Section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Briefcase className="mr-2 h-5 w-5" />
                Jobs Overview
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Active Jobs */}
              <div>
                <h3 className="text-lg font-semibold mb-4">Active Jobs ({jobs.total_active})</h3>
                {jobs.active.length === 0 ? (
                  <p className="text-gray-500 text-sm">No active jobs</p>
                ) : (
                  <div className="space-y-3">
                    {jobs.active.map((job) => (
                      <div
                        key={job.job_id}
                        className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h4 className="font-medium text-gray-900">{job.title}</h4>
                            <p className="text-sm text-gray-600 mt-1">{job.description}</p>
                            <div className="flex items-center gap-2 mt-2">
                              <Badge variant="outline">{job.category}</Badge>
                              <Badge
                                variant={
                                  job.status === "in_progress"
                                    ? "default"
                                    : "secondary"
                                }
                              >
                                {job.status}
                              </Badge>
                            </div>
                          </div>
                          {job.budget_max && (
                            <div className="text-right ml-4">
                              <p className="text-sm font-medium text-gray-900">
                                ${job.budget_min} - ${job.budget_max}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <Separator />

              {/* Completed Jobs */}
              <div>
                <h3 className="text-lg font-semibold mb-4">
                  Completed Jobs ({jobs.total_completed})
                </h3>
                {jobs.completed.length === 0 ? (
                  <p className="text-gray-500 text-sm">No completed jobs yet</p>
                ) : (
                  <div className="space-y-3">
                    {jobs.completed.slice(0, 5).map((job) => (
                      <div
                        key={job.job_id}
                        className="border rounded-lg p-4 bg-green-50 border-green-200"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h4 className="font-medium text-gray-900">{job.title}</h4>
                            <p className="text-sm text-gray-600 mt-1">{job.description}</p>
                            <div className="flex items-center gap-2 mt-2">
                              <Badge variant="outline">{job.category}</Badge>
                              <Badge variant="default" className="bg-green-600">
                                Completed
                              </Badge>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <Separator />

              {/* Available Jobs */}
              <div>
                <h3 className="text-lg font-semibold mb-4">
                  Available Jobs ({jobs.total_available})
                </h3>
                {jobs.available.length === 0 ? (
                  <p className="text-gray-500 text-sm">No available jobs at the moment</p>
                ) : (
                  <div className="space-y-3">
                    {jobs.available.slice(0, 5).map((job) => (
                      <div
                        key={job.job_id}
                        className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h4 className="font-medium text-gray-900">{job.title}</h4>
                            <p className="text-sm text-gray-600 mt-1">{job.description}</p>
                            <div className="flex items-center gap-2 mt-2">
                              <Badge variant="outline">{job.category}</Badge>
                              <Badge variant="secondary">{job.urgency}</Badge>
                            </div>
                          </div>
                          <div className="ml-4">
                            <Button size="sm">View & Bid</Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Payment Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <DollarSign className="mr-2 h-5 w-5" />
                Payment Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <p className="text-sm font-medium text-gray-600">Total Earnings</p>
                  <p className="text-2xl font-bold text-green-700 mt-2">
                    ${payments.total_earnings.toFixed(2)}
                  </p>
                </div>

                <div className="text-center p-4 bg-yellow-50 rounded-lg">
                  <p className="text-sm font-medium text-gray-600">Pending Payments</p>
                  <p className="text-2xl font-bold text-yellow-700 mt-2">
                    ${payments.pending.toFixed(2)}
                  </p>
                </div>

                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm font-medium text-gray-600">Completed Payments</p>
                  <p className="text-2xl font-bold text-blue-700 mt-2">
                    ${payments.completed.toFixed(2)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <div className="flex gap-4">
            <Button
              size="lg"
              onClick={() => router.push("/contractor/contractor/jobs/available")}
            >
              Browse Available Jobs
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={() => router.push("/contractor/contractor/jobs/active")}
            >
              View My Active Jobs
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
