'use client';

import { useState, useEffect } from 'react';
import { addBankAccount, getPaymentInfo, type BankAccountDetails, type PaymentInfo } from '@/lib/api';

interface ContractorBankAccountFormProps {
  contractorId: string;
  onSuccess?: () => void;
}

export default function ContractorBankAccountForm({ contractorId, onSuccess }: ContractorBankAccountFormProps) {
  const [formData, setFormData] = useState({
    account_number: '',
    routing_number: '',
    account_holder_name: '',
    account_holder_type: 'individual' as 'individual' | 'company',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [paymentInfo, setPaymentInfo] = useState<PaymentInfo | null>(null);

  useEffect(() => {
    // Fetch existing payment info
    const fetchPaymentInfo = async () => {
      try {
        const info = await getPaymentInfo(contractorId);
        setPaymentInfo(info);
      } catch (err) {
        console.error('Failed to fetch payment info:', err);
      }
    };

    fetchPaymentInfo();
  }, [contractorId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const bankDetails: BankAccountDetails = {
        contractor_id: contractorId,
        ...formData,
      };

      await addBankAccount(bankDetails);
      setSuccess(true);
      setFormData({
        account_number: '',
        routing_number: '',
        account_holder_name: '',
        account_holder_type: 'individual',
      });

      // Refresh payment info
      const updatedInfo = await getPaymentInfo(contractorId);
      setPaymentInfo(updatedInfo);

      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add bank account');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6">Bank Account Information</h2>

      {paymentInfo?.payment_enabled && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-md">
          <p className="text-green-800 font-medium">✓ Payment Setup Complete</p>
          <p className="text-sm text-green-600 mt-1">
            Bank account ending in {paymentInfo.bank_account_last4} is connected
          </p>
        </div>
      )}

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {success && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-md">
          <p className="text-green-800">Bank account added successfully!</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="account_holder_name" className="block text-sm font-medium text-gray-700 mb-1">
            Account Holder Name
          </label>
          <input
            type="text"
            id="account_holder_name"
            name="account_holder_name"
            value={formData.account_holder_name}
            onChange={handleChange}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="John Doe"
          />
        </div>

        <div>
          <label htmlFor="routing_number" className="block text-sm font-medium text-gray-700 mb-1">
            Routing Number
          </label>
          <input
            type="text"
            id="routing_number"
            name="routing_number"
            value={formData.routing_number}
            onChange={handleChange}
            required
            pattern="[0-9]{9}"
            maxLength={9}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="110000000"
          />
          <p className="text-xs text-gray-500 mt-1">9-digit routing number</p>
        </div>

        <div>
          <label htmlFor="account_number" className="block text-sm font-medium text-gray-700 mb-1">
            Account Number
          </label>
          <input
            type="text"
            id="account_number"
            name="account_number"
            value={formData.account_number}
            onChange={handleChange}
            required
            pattern="[0-9]{4,17}"
            maxLength={17}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="000123456789"
          />
          <p className="text-xs text-gray-500 mt-1">4-17 digit account number</p>
        </div>

        <div>
          <label htmlFor="account_holder_type" className="block text-sm font-medium text-gray-700 mb-1">
            Account Type
          </label>
          <select
            id="account_holder_type"
            name="account_holder_type"
            value={formData.account_holder_type}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="individual">Individual</option>
            <option value="company">Company</option>
          </select>
        </div>

        <div className="pt-4">
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Processing...' : paymentInfo?.payment_enabled ? 'Update Bank Account' : 'Add Bank Account'}
          </button>
        </div>
      </form>

      <div className="mt-6 p-4 bg-gray-50 rounded-md">
        <p className="text-xs text-gray-600">
          <strong>Note:</strong> Your bank account information is securely stored with Stripe.
          We never store your full account number on our servers.
        </p>
      </div>
    </div>
  );
}
