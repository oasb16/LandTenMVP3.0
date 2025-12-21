"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, AlertCircle, CheckCircle2, Lock } from "lucide-react";

interface OnboardingStatus {
  contractor_id: string;
  onboarding_license_submitted: boolean;
  onboarding_license_verified: boolean;
  onboarding_identity_verified: boolean;
  onboarding_payment_setup: boolean;
  onboarding_complete: boolean;
  onboarding_current_step: string;
}

function ContractorOnboardingContent() {
  const searchParams = useSearchParams();
  const token = searchParams?.get("token");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [contractorId, setContractorId] = useState<string | null>(null);
  const [contractorEmail, setContractorEmail] = useState<string | null>(null);
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus | null>(null);

  // Verify magic link and get contractor info
  useEffect(() => {
    if (!token) {
      setError("No magic link token provided");
      setLoading(false);
      return;
    }

    const verifyToken = async () => {
      try {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
        const response = await fetch(`${backendUrl}/api/v1/magic-links/verify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });

        if (!response.ok) {
          throw new Error("Failed to verify magic link");
        }

        const data = await response.json();

        if (!data.valid) {
          setError(data.message || "Invalid or expired magic link");
          setLoading(false);
          return;
        }

        // Check if contractor exists
        if (data.contractor_id) {
          setContractorId(data.contractor_id);
          setContractorEmail(data.email);
          // Load onboarding status
          await loadOnboardingStatus(data.contractor_id);
        } else {
          // Create minimal contractor record for onboarding
          await createContractorForOnboarding(data.email, data.job_id);
        }

        setLoading(false);
      } catch (err) {
        console.error("Error verifying token:", err);
        setError("Failed to verify magic link");
        setLoading(false);
      }
    };

    verifyToken();
  }, [token]);

  const createContractorForOnboarding = async (email: string, jobId: string) => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;

      // Create minimal contractor record
      const response = await fetch(`${backendUrl}/api/v1/contractors/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          business_name: "Pending",
          email: email,
          phone: "Pending",
          categories: [],
          service_zip_codes: [],
          license_number: "",
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to create contractor record");
      }

      const result = await response.json();
      setContractorId(result.contractor.contractor_id);
      setContractorEmail(email);

      // Load initial onboarding status
      await loadOnboardingStatus(result.contractor.contractor_id);
    } catch (err) {
      console.error("Error creating contractor:", err);
      setError("Failed to initialize onboarding");
    }
  };

  const loadOnboardingStatus = async (cid: string) => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
      const response = await fetch(`${backendUrl}/api/v1/contractors/${cid}/onboarding-status`);

      if (!response.ok) {
        throw new Error("Failed to load onboarding status");
      }

      const status = await response.json();
      setOnboardingStatus(status);
    } catch (err) {
      console.error("Error loading onboarding status:", err);
    }
  };

  // Poll for onboarding status updates every 2 seconds
  useEffect(() => {
    if (!contractorId) return;

    const interval = setInterval(async () => {
      await loadOnboardingStatus(contractorId);
    }, 2000);

    return () => clearInterval(interval);
  }, [contractorId]);

  if (loading) {
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

  if (error || !contractorId) {
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

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Left side: Dashboard Preview (grayed out until complete) */}
      <div
        className={`flex-1 overflow-y-auto p-6 transition-opacity duration-300 ${
          !onboardingStatus?.onboarding_complete ? 'opacity-40 pointer-events-none' : ''
        }`}
      >
        <div className="max-w-6xl mx-auto space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Contractor Dashboard</h1>
              <p className="text-gray-600 mt-1">Welcome to HomeAI</p>
            </div>
            {!onboardingStatus?.onboarding_complete && (
              <div className="flex items-center gap-2 text-amber-600 bg-amber-50 px-4 py-2 rounded-lg">
                <Lock className="h-5 w-5" />
                <span className="font-medium">Complete onboarding to unlock</span>
              </div>
            )}
          </div>

          {/* Profile Section */}
          <Card className={onboardingStatus?.onboarding_license_verified ? 'border-green-200' : ''}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  Profile
                  {onboardingStatus?.onboarding_license_verified && (
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                  )}
                </CardTitle>
              </div>
              <CardDescription>Your business information</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Business Name</p>
                  <p className="font-medium">Your Business Name</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">License Number</p>
                  <p className="font-medium">License #XXXXX</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Email</p>
                  <p className="font-medium">{contractorEmail}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Service Areas</p>
                  <p className="font-medium">ZIP codes</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Jobs Section */}
          <Card className={onboardingStatus?.onboarding_identity_verified ? 'border-green-200' : ''}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  Available Jobs
                  {onboardingStatus?.onboarding_identity_verified && (
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                  )}
                </CardTitle>
              </div>
              <CardDescription>Jobs you can bid on</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                <p>No jobs available yet</p>
                <p className="text-sm mt-2">Complete onboarding to see available jobs</p>
              </div>
            </CardContent>
          </Card>

          {/* Payments Section */}
          <Card className={onboardingStatus?.onboarding_payment_setup ? 'border-green-200' : ''}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  Payments
                  {onboardingStatus?.onboarding_payment_setup && (
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                  )}
                </CardTitle>
              </div>
              <CardDescription>Your earnings and payouts</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600">Total Earnings</p>
                  <p className="text-2xl font-bold text-gray-900">$0</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600">Pending</p>
                  <p className="text-2xl font-bold text-gray-900">$0</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600">Paid Out</p>
                  <p className="text-2xl font-bold text-gray-900">$0</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Right side: Chat Interface */}
      <div className="w-96 border-l border-gray-200 bg-white flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">Contractor Onboarding</h2>
          <p className="text-sm text-gray-600">Complete the steps to get started</p>

          {/* Progress Indicators */}
          <div className="mt-4 space-y-2">
            <div className="flex items-center gap-2 text-sm">
              {onboardingStatus?.onboarding_license_verified ? (
                <CheckCircle2 className="h-4 w-4 text-green-600" />
              ) : (
                <div className="h-4 w-4 rounded-full border-2 border-gray-300" />
              )}
              <span className={onboardingStatus?.onboarding_license_verified ? 'text-green-600' : ''}>
                License Verification
              </span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              {onboardingStatus?.onboarding_identity_verified ? (
                <CheckCircle2 className="h-4 w-4 text-green-600" />
              ) : (
                <div className="h-4 w-4 rounded-full border-2 border-gray-300" />
              )}
              <span className={onboardingStatus?.onboarding_identity_verified ? 'text-green-600' : ''}>
                Identity Verification
              </span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              {onboardingStatus?.onboarding_payment_setup ? (
                <CheckCircle2 className="h-4 w-4 text-green-600" />
              ) : (
                <div className="h-4 w-4 rounded-full border-2 border-gray-300" />
              )}
              <span className={onboardingStatus?.onboarding_payment_setup ? 'text-green-600' : ''}>
                Payment Setup
              </span>
            </div>
          </div>
        </div>

        {/* Chat placeholder - will be replaced with actual StreamChatPane */}
        <div className="flex-1 p-4 overflow-y-auto bg-gray-50">
          <div className="space-y-4">
            <Alert>
              <AlertDescription>
                <strong>Chat onboarding coming soon!</strong>
                <br />
                This will be replaced with StreamChatPane for interactive onboarding.
                <br /><br />
                Contractor ID: <code className="text-xs">{contractorId}</code>
              </AlertDescription>
            </Alert>
          </div>
        </div>

        {/* Chat input placeholder */}
        <div className="p-4 border-t border-gray-200">
          <input
            type="text"
            placeholder="Type your message..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            disabled
          />
          <p className="text-xs text-gray-500 mt-2">Chat interface will be integrated here</p>
        </div>
      </div>
    </div>
  );
}

export default function ContractorOnboardingPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ContractorOnboardingContent />
    </Suspense>
  );
}
