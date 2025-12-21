"use client";

import { useState } from "react";
import { CheckCircle, FileText, Shield, Building2, Loader2 } from "lucide-react";

type LicenseVerificationCardProps = {
  onSubmit: (licenseNumber: string, businessAddress: string) => void;
};

export function LicenseVerificationCard({ onSubmit }: LicenseVerificationCardProps) {
  const [licenseNumber, setLicenseNumber] = useState("");
  const [businessAddress, setBusinessAddress] = useState("");
  const [businessWebsite, setBusinessWebsite] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!licenseNumber.trim() || !businessAddress.trim()) return;

    setSubmitting(true);
    await onSubmit(licenseNumber, businessAddress);
    setSubmitting(false);
  };

  return (
    <div className="bg-white rounded-xl border-2 border-blue-200 p-6 shadow-lg max-w-md">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
          <FileText className="h-6 w-6 text-blue-600" />
        </div>
        <div>
          <h3 className="font-bold text-lg text-gray-900">Business Verification</h3>
          <p className="text-sm text-gray-600">Verify your contractor license</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Contractor License Number *
          </label>
          <input
            type="text"
            placeholder="e.g., CLB-123456"
            value={licenseNumber}
            onChange={(e) => setLicenseNumber(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Business Address *
          </label>
          <input
            type="text"
            placeholder="123 Main St, City, State ZIP"
            value={businessAddress}
            onChange={(e) => setBusinessAddress(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Business Website (optional)
          </label>
          <input
            type="url"
            placeholder="https://yourcompany.com"
            value={businessWebsite}
            onChange={(e) => setBusinessWebsite(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <button
          type="submit"
          disabled={submitting || !licenseNumber.trim() || !businessAddress.trim()}
          className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold py-3 px-4 rounded-lg hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {submitting ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Verifying...
            </span>
          ) : (
            "Submit License Information"
          )}
        </button>
      </form>

      <p className="text-xs text-gray-500 mt-3 text-center">
        🔒 Your information is encrypted and secure
      </p>
    </div>
  );
}

type IdentityVerificationCardProps = {
  onStart: () => void;
};

export function IdentityVerificationCard({ onStart }: IdentityVerificationCardProps) {
  const [verifying, setVerifying] = useState(false);

  const handleStart = async () => {
    setVerifying(true);
    await onStart();
  };

  return (
    <div className="bg-white rounded-xl border-2 border-purple-200 p-6 shadow-lg max-w-md">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center">
          <Shield className="h-6 w-6 text-purple-600" />
        </div>
        <div>
          <h3 className="font-bold text-lg text-gray-900">Identity Verification</h3>
          <p className="text-sm text-gray-600">Verify your identity securely</p>
        </div>
      </div>

      {verifying ? (
        <div className="text-center py-8">
          <div className="relative w-24 h-24 mx-auto mb-4">
            <div className="absolute inset-0 rounded-full border-4 border-blue-200"></div>
            <div className="absolute inset-0 rounded-full border-4 border-t-blue-600 animate-spin"></div>
            <Shield className="absolute inset-0 m-auto h-10 w-10 text-blue-600" />
          </div>
          <h4 className="font-semibold text-gray-900 mb-2">Verifying your identity...</h4>
          <p className="text-sm text-gray-600 mb-2">Powered by Jumio Identity Verification</p>
          <div className="w-64 mx-auto bg-gray-200 rounded-full h-2 mb-2">
            <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: "60%" }}></div>
          </div>
          <p className="text-xs text-gray-500">This usually takes less than 30 seconds</p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-purple-50 rounded-lg p-4 space-y-2">
            <div className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-purple-600 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-gray-700">Government ID required (Driver's License, Passport, etc.)</p>
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-purple-600 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-gray-700">Selfie verification for security</p>
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-purple-600 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-gray-700">Bank-level encryption and privacy</p>
            </div>
          </div>

          <button
            onClick={handleStart}
            className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold py-3 px-4 rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all"
          >
            Start Identity Verification
          </button>

          <p className="text-xs text-gray-500 text-center">
            Verification typically takes under 1 minute
          </p>
        </div>
      )}
    </div>
  );
}

type BankAccountSetupCardProps = {
  onSubmit: (routingNumber: string, accountNumber: string, accountName: string) => void;
};

export function BankAccountSetupCard({ onSubmit }: BankAccountSetupCardProps) {
  const [accountName, setAccountName] = useState("");
  const [accountType, setAccountType] = useState("checking");
  const [routingNumber, setRoutingNumber] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [confirmAccountNumber, setConfirmAccountNumber] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (accountNumber !== confirmAccountNumber) {
      alert("Account numbers don't match");
      return;
    }
    if (!routingNumber.trim() || !accountNumber.trim() || !accountName.trim()) return;

    setSubmitting(true);
    await onSubmit(routingNumber, accountNumber, accountName);
    setSubmitting(false);
  };

  return (
    <div className="bg-white rounded-xl border-2 border-green-200 p-6 shadow-lg max-w-md">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
          <Building2 className="h-6 w-6 text-green-600" />
        </div>
        <div>
          <h3 className="font-bold text-lg text-gray-900">Payment Account Setup</h3>
          <p className="text-sm text-gray-600">Where you'll receive payments</p>
        </div>
      </div>

      <div className="bg-green-50 rounded-lg p-3 mb-4">
        <p className="text-sm text-gray-700">
          <span className="font-semibold">Hi Contractor!</span> Let's set up where you'll receive payments for completed jobs.
        </p>
        <div className="flex items-center gap-2 mt-2 text-xs text-gray-600">
          <CheckCircle className="h-3 w-3 text-green-600" />
          <span>Payments are deposited within 2-3 business days</span>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Business / Account Holder Name *
          </label>
          <input
            type="text"
            placeholder="Your Business Name"
            value={accountName}
            onChange={(e) => setAccountName(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Account Type
          </label>
          <select
            value={accountType}
            onChange={(e) => setAccountType(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
          >
            <option value="checking">Checking</option>
            <option value="savings">Savings</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Routing Number *
          </label>
          <input
            type="text"
            placeholder="9 digits"
            value={routingNumber}
            onChange={(e) => setRoutingNumber(e.target.value.replace(/\D/g, "").slice(0, 9))}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            maxLength={9}
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Account Number *
          </label>
          <input
            type="text"
            placeholder="Account number"
            value={accountNumber}
            onChange={(e) => setAccountNumber(e.target.value.replace(/\D/g, ""))}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Confirm Account Number *
          </label>
          <input
            type="text"
            placeholder="Re-enter account number"
            value={confirmAccountNumber}
            onChange={(e) => setConfirmAccountNumber(e.target.value.replace(/\D/g, ""))}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            required
          />
        </div>

        <div className="flex items-center gap-2 text-xs text-gray-600 bg-gray-50 p-3 rounded-lg">
          <Shield className="h-4 w-4 text-gray-500" />
          <span>Your bank information is encrypted and secure</span>
        </div>

        <button
          type="submit"
          disabled={submitting || accountNumber !== confirmAccountNumber}
          className="w-full bg-gradient-to-r from-green-600 to-emerald-600 text-white font-semibold py-3 px-4 rounded-lg hover:from-green-700 hover:to-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {submitting ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Verifying...
            </span>
          ) : (
            "Add Bank Account"
          )}
        </button>
      </form>
    </div>
  );
}

type SuccessCardProps = {
  title: string;
  message: string;
  icon?: "license" | "identity" | "payment";
};

export function SuccessCard({ title, message, icon = "license" }: SuccessCardProps) {
  const getIcon = () => {
    switch (icon) {
      case "license":
        return <FileText className="h-8 w-8 text-green-600" />;
      case "identity":
        return <Shield className="h-8 w-8 text-green-600" />;
      case "payment":
        return <Building2 className="h-8 w-8 text-green-600" />;
    }
  };

  return (
    <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl border-2 border-green-200 p-6 shadow-lg max-w-md">
      <div className="flex flex-col items-center text-center space-y-4">
        <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center">
          <div className="w-16 h-16 rounded-full bg-green-200 flex items-center justify-center">
            <CheckCircle className="h-10 w-10 text-green-600" />
          </div>
        </div>

        <div>
          <h3 className="font-bold text-xl text-gray-900 mb-2">{title}</h3>
          <p className="text-sm text-gray-700">{message}</p>
        </div>

        <div className="w-full bg-white rounded-lg p-4 flex items-center gap-3">
          {getIcon()}
          <div className="flex-1 text-left">
            <p className="text-sm font-semibold text-gray-900">Verified Successfully!</p>
            <p className="text-xs text-gray-600">Your information has been confirmed</p>
          </div>
          <CheckCircle className="h-6 w-6 text-green-600" />
        </div>
      </div>
    </div>
  );
}
