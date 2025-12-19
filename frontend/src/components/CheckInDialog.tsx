'use client';

/**
 * Check-In Dialog Component
 *
 * Handles guest check-in with payment pre-authorization.
 * Supports both live Elavon terminal payments and simulated mode.
 */

import React, { useState } from 'react';
import { usePayment } from '@/contexts/PaymentContext';

interface CheckInDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  guestName: string;
  roomPrice: number;
  nights: number;
  onSuccess: (transactionId: string, amount: number) => void;
}

export function CheckInDialog({
  open,
  onOpenChange,
  guestName,
  roomPrice,
  nights,
  onSuccess,
}: CheckInDialogProps) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [preAuthAmount, setPreAuthAmount] = useState('');
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null);

  const { elavonConfig } = usePayment();

  const estimatedTotal = nights * roomPrice;
  const suggestedPreAuth = Math.ceil(estimatedTotal * 1.2); // 20% buffer

  const handleCheckIn = async () => {
    const authAmount = parseFloat(preAuthAmount) || suggestedPreAuth;
    setIsProcessing(true);
    setMessage(null);

    try {
      let transactionId = `PREAUTH-${Date.now()}`;
      let preAuthStatus: 'pre_authorized' | 'pending' = 'pending';

      // If Elavon is configured with token, perform live pre-auth
      if (elavonConfig?.token) {
        console.log('Processing live Elavon pre-authorization...');

        const response = await fetch('/api/payment/elavon/preauth', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            token: elavonConfig.token,
            amount: authAmount,
            terminalId: elavonConfig.terminalId,
            merchantId: elavonConfig.merchantId,
          }),
        });

        const data = await response.json();

        if (!response.ok || data.status === 'DECLINED' || data.status === 'ERROR') {
          throw new Error(data.error || data.detail || 'Pre-authorization declined');
        }

        transactionId = data.transactionId;
        preAuthStatus = 'pre_authorized';
        console.log('Pre-authorization successful:', data);
      } else {
        // Simulated mode for testing
        console.log('No token available, simulating pre-authorization...');
        setMessage({ type: 'warning', text: 'Using simulated pre-authorization (demo mode)' });
        await new Promise((resolve) => setTimeout(resolve, 1000));
        preAuthStatus = 'pre_authorized';
      }

      setMessage({ type: 'success', text: `Check-in complete! Pre-authorized $${authAmount.toLocaleString()}` });
      setTimeout(() => {
        onSuccess(transactionId, authAmount);
        onOpenChange(false);
      }, 1500);
    } catch (error) {
      console.error('Pre-authorization error:', error);
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to process pre-authorization',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-lg w-full p-6 space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Check-In Guest</h2>
        </div>

        {/* Guest Info */}
        <div className="bg-gray-50 p-4 rounded-lg">
          <p className="font-semibold text-gray-900">{guestName}</p>
          <p className="text-sm text-gray-600">
            {nights} night{nights > 1 ? 's' : ''} • Estimated total: ${estimatedTotal.toLocaleString()}
          </p>
        </div>

        {/* Pre-Auth Amount */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-900">Pre-Authorization Amount ($)</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">💳</span>
            <input
              type="number"
              value={preAuthAmount}
              onChange={(e) => setPreAuthAmount(e.target.value)}
              placeholder={suggestedPreAuth.toString()}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <p className="text-xs text-gray-500">
            Suggested: ${suggestedPreAuth.toLocaleString()} (room + 20% for incidentals)
          </p>
        </div>

        {/* Status Indicators */}
        {!elavonConfig ? (
          <div className="flex items-start gap-3 rounded-lg border border-yellow-500/50 bg-yellow-50 p-4">
            <span className="text-yellow-600 text-xl">⚠️</span>
            <div className="text-sm">
              <p className="font-medium text-yellow-800">Payment gateway not configured</p>
              <p className="text-yellow-700">Configure Elavon in Settings for live transactions.</p>
            </div>
          </div>
        ) : !elavonConfig.token ? (
          <div className="flex items-start gap-3 rounded-lg border border-yellow-500/50 bg-yellow-50 p-4">
            <span className="text-yellow-600 text-xl">⚠️</span>
            <div className="text-sm">
              <p className="font-medium text-yellow-800">No active token</p>
              <p className="text-yellow-700">Get a token in Settings to enable live transactions.</p>
            </div>
          </div>
        ) : (
          <div className="flex items-start gap-3 rounded-lg border border-green-500/50 bg-green-50 p-4">
            <span className="text-green-600 text-xl">💳</span>
            <div className="text-sm">
              <p className="font-medium text-green-800">Live payment ready</p>
              <p className="text-green-700">Pre-authorization will be processed via Elavon.</p>
            </div>
          </div>
        )}

        {/* Message Display */}
        {message && (
          <div
            className={`p-4 rounded-lg ${
              message.type === 'success'
                ? 'bg-green-50 text-green-800 border border-green-200'
                : message.type === 'error'
                ? 'bg-red-50 text-red-800 border border-red-200'
                : 'bg-yellow-50 text-yellow-800 border border-yellow-200'
            }`}
          >
            {message.text}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={() => onOpenChange(false)}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
            disabled={isProcessing}
          >
            Cancel
          </button>
          <button
            onClick={handleCheckIn}
            disabled={isProcessing}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isProcessing ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
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
              <>
                💳 Check-In & Pre-Authorize
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
