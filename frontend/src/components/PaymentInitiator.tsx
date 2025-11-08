'use client';

import { useState } from 'react';
import { initiatePayment, type PaymentRequest, type PaymentResponse } from '@/lib/api';

interface PaymentInitiatorProps {
  contractorId: string;
  contractorName?: string;
  jobId?: string;
  incidentId?: string;
  defaultAmount?: number;
  defaultDescription?: string;
  onSuccess?: (payment: PaymentResponse) => void;
}

export default function PaymentInitiator({
  contractorId,
  contractorName,
  jobId,
  incidentId,
  defaultAmount = 0,
  defaultDescription = '',
  onSuccess,
}: PaymentInitiatorProps) {
  const [formData, setFormData] = useState({
    amount: defaultAmount || '',
    description: defaultDescription || '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paymentResult, setPaymentResult] = useState<PaymentResponse | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setPaymentResult(null);

    try {
      const amount = typeof formData.amount === 'string' ? parseFloat(formData.amount) : formData.amount;

      if (isNaN(amount) || amount <= 0) {
        throw new Error('Please enter a valid amount greater than 0');
      }

      const paymentRequest: PaymentRequest = {
        contractor_id: contractorId,
        amount,
        description: formData.description,
        job_id: jobId,
        incident_id: incidentId,
      };

      const result = await initiatePayment(paymentRequest);
      setPaymentResult(result);

      if (onSuccess) {
        onSuccess(result);
      }

      // Reset form
      setFormData({
        amount: '',
        description: '',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process payment');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6">Send Payment to Contractor</h2>

      {contractorName && (
        <div className="mb-4 p-3 bg-blue-50 rounded-md">
          <p className="text-sm text-gray-700">
            <strong>Contractor:</strong> {contractorName}
          </p>
        </div>
      )}

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {paymentResult && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-md">
          <p className="text-green-800 font-medium">✓ Payment Initiated Successfully</p>
          <div className="mt-2 text-sm text-green-700 space-y-1">
            <p><strong>Transfer ID:</strong> {paymentResult.transfer_id}</p>
            <p><strong>Amount:</strong> ${paymentResult.amount.toFixed(2)}</p>
            <p><strong>Status:</strong> {paymentResult.transfer_status}</p>
            {paymentResult.contractor_name && (
              <p><strong>To:</strong> {paymentResult.contractor_name}</p>
            )}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="amount" className="block text-sm font-medium text-gray-700 mb-1">
            Amount (USD)
          </label>
          <div className="relative">
            <span className="absolute left-3 top-2 text-gray-500">$</span>
            <input
              type="number"
              id="amount"
              name="amount"
              value={formData.amount}
              onChange={handleChange}
              required
              min="0.01"
              step="0.01"
              className="w-full pl-8 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="0.00"
            />
          </div>
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            required
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Payment for completed work on incident #123"
          />
        </div>

        {jobId && (
          <div className="text-sm text-gray-600">
            <strong>Job ID:</strong> {jobId}
          </div>
        )}

        {incidentId && (
          <div className="text-sm text-gray-600">
            <strong>Incident ID:</strong> {incidentId}
          </div>
        )}

        <div className="pt-4">
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {loading ? 'Processing Payment...' : 'Send Payment'}
          </button>
        </div>
      </form>

      <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
        <p className="text-xs text-yellow-800">
          <strong>Important:</strong> Payments are processed through Stripe and will be transferred to the contractor&apos;s
          bank account. Please ensure the amount and description are correct before submitting.
        </p>
      </div>
    </div>
  );
}
