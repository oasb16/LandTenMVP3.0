'use client';

/**
 * Pay Contractor Button Component
 *
 * Example component showing how landlords can pay contractors for completed jobs.
 * Creates a Stripe checkout session and redirects to payment.
 */

import React, { useState } from 'react';
import { JobPaymentRequest, CheckoutSessionResponse } from '@/types/checkout-payment';

interface PayContractorButtonProps {
  jobId: string;
  bidId: string;
  contractorName: string;
  contractorEmail: string;
  landlordEmail: string;
  amount: number;
  description?: string;
  onSuccess?: () => void;
  onError?: (error: string) => void;
}

export function PayContractorButton({
  jobId,
  bidId,
  contractorName,
  contractorEmail,
  landlordEmail,
  amount,
  description,
  onSuccess,
  onError,
}: PayContractorButtonProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handlePayment = async () => {
    setIsLoading(true);

    try {
      const requestBody: JobPaymentRequest = {
        job_id: jobId,
        bid_id: bidId,
        contractor_name: contractorName,
        contractor_email: contractorEmail,
        landlord_email: landlordEmail,
        amount,
        description,
      };

      const response = await fetch('/api/checkout/job-payment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      const data: CheckoutSessionResponse = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to create payment session');
      }

      // Redirect to Stripe checkout
      if (data.checkoutUrl) {
        window.location.href = data.checkoutUrl;
      }

      onSuccess?.();
    } catch (error) {
      console.error('Payment error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Payment failed';
      onError?.(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      onClick={handlePayment}
      disabled={isLoading}
      className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
    >
      {isLoading ? (
        <>
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          Processing...
        </>
      ) : (
        <>💳 Pay ${amount.toFixed(2)}</>
      )}
    </button>
  );
}
