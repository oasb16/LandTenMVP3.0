'use client';

/**
 * Payment Settings Page
 *
 * Configuration interface for Elavon and Stripe payment providers.
 * Allows users to:
 * - Configure Elavon terminal credentials
 * - Get authentication tokens
 * - Set up mobile checkout (Converge)
 * - Switch between payment providers
 */

import React, { useState } from 'react';
import { usePayment } from '@/contexts/PaymentContext';
import { ElavonConfig } from '@/types/payment';

export default function PaymentSettingsPage() {
  const { elavonConfig, paymentConfig, setElavonConfig, setElavonToken, setActivePaymentProvider } = usePayment();

  const [isGettingToken, setIsGettingToken] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [formData, setFormData] = useState<ElavonConfig>({
    merchantId: elavonConfig?.merchantId || '',
    userId: elavonConfig?.userId || '',
    pin: elavonConfig?.pin || '',
    terminalId: elavonConfig?.terminalId || '',
    apiEndpoint: elavonConfig?.apiEndpoint || 'https://uat.pos.hpi.elavonaws.com',
    isTestMode: elavonConfig?.isTestMode ?? true,
    checkoutJsEnabled: elavonConfig?.checkoutJsEnabled ?? false,
    convergeMerchantId: elavonConfig?.convergeMerchantId || '',
    convergeUserId: elavonConfig?.convergeUserId || '',
    convergePin: elavonConfig?.convergePin || '',
  });

  const handleSaveConfig = () => {
    setElavonConfig(formData);
    setMessage({ type: 'success', text: 'Configuration saved successfully' });
    setTimeout(() => setMessage(null), 3000);
  };

  const handleGetToken = async () => {
    setIsGettingToken(true);
    setMessage(null);

    try {
      const response = await fetch('/api/payment/elavon/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          merchantId: formData.merchantId,
          userId: formData.userId,
          pin: formData.pin,
          apiEndpoint: formData.apiEndpoint,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || 'Failed to get token');
      }

      setElavonToken(data.token, new Date(data.expiresAt));
      setMessage({ type: 'success', text: 'Token retrieved successfully' });
      setTimeout(() => setMessage(null), 3000);
    } catch (error) {
      console.error('Token error:', error);
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to get token',
      });
    } finally {
      setIsGettingToken(false);
    }
  };

  return (
    <div className="container max-w-4xl mx-auto py-8 px-4 space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Payment Settings</h1>

      {/* Provider Selection */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <h2 className="text-xl font-semibold text-gray-900">Payment Provider</h2>
        <div className="space-y-2">
          <label className="flex items-center gap-3 p-3 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50">
            <input
              type="radio"
              value="elavon"
              checked={paymentConfig.activeProvider === 'elavon'}
              onChange={(e) => setActivePaymentProvider(e.target.value as 'elavon')}
              className="w-4 h-4"
            />
            <span className="text-gray-900">Elavon (Terminal + Mobile)</span>
          </label>
          <label className="flex items-center gap-3 p-3 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50">
            <input
              type="radio"
              value="stripe"
              checked={paymentConfig.activeProvider === 'stripe'}
              onChange={(e) => setActivePaymentProvider(e.target.value as 'stripe')}
              className="w-4 h-4"
            />
            <span className="text-gray-900">Stripe (Mobile Only)</span>
          </label>
        </div>
      </div>

      {/* Elavon Configuration */}
      {paymentConfig.activeProvider === 'elavon' && (
        <>
          <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
            <h2 className="text-xl font-semibold text-gray-900">Elavon Terminal Configuration</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-900">Merchant ID</label>
                <input
                  type="text"
                  value={formData.merchantId}
                  onChange={(e) => setFormData({ ...formData, merchantId: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-900">User ID</label>
                <input
                  type="text"
                  value={formData.userId}
                  onChange={(e) => setFormData({ ...formData, userId: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-900">PIN</label>
                <input
                  type="password"
                  value={formData.pin}
                  onChange={(e) => setFormData({ ...formData, pin: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-900">Terminal ID</label>
                <input
                  type="text"
                  value={formData.terminalId}
                  onChange={(e) => setFormData({ ...formData, terminalId: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-900">API Endpoint</label>
              <input
                type="text"
                value={formData.apiEndpoint}
                onChange={(e) => setFormData({ ...formData, apiEndpoint: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.isTestMode}
                onChange={(e) => setFormData({ ...formData, isTestMode: e.target.checked })}
                className="w-4 h-4"
              />
              <span className="text-gray-900">Test Mode</span>
            </label>

            <div className="flex gap-2">
              <button
                onClick={handleSaveConfig}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Save Configuration
              </button>
              <button
                onClick={handleGetToken}
                disabled={isGettingToken}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isGettingToken ? (
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
                    Getting Token...
                  </>
                ) : (
                  'Get Token'
                )}
              </button>
            </div>

            {elavonConfig?.token && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-sm font-medium text-green-800">✓ Token Active</p>
                <p className="text-xs text-green-700 mt-1">
                  Expires: {elavonConfig.tokenExpiresAt?.toLocaleString()}
                </p>
              </div>
            )}
          </div>

          {/* Mobile Checkout Configuration */}
          <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
            <h2 className="text-xl font-semibold text-gray-900">Elavon Mobile Checkout (Converge)</h2>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.checkoutJsEnabled}
                onChange={(e) => setFormData({ ...formData, checkoutJsEnabled: e.target.checked })}
                className="w-4 h-4"
              />
              <span className="text-gray-900">Enable Mobile Checkout</span>
            </label>

            {formData.checkoutJsEnabled && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-900">Converge Merchant ID</label>
                  <input
                    type="text"
                    value={formData.convergeMerchantId}
                    onChange={(e) => setFormData({ ...formData, convergeMerchantId: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-900">Converge User ID</label>
                  <input
                    type="text"
                    value={formData.convergeUserId}
                    onChange={(e) => setFormData({ ...formData, convergeUserId: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-900">Converge PIN</label>
                  <input
                    type="password"
                    value={formData.convergePin}
                    onChange={(e) => setFormData({ ...formData, convergePin: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* Message Display */}
      {message && (
        <div
          className={`p-4 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Documentation */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 space-y-2">
        <h3 className="text-lg font-semibold text-blue-900">📚 Documentation</h3>
        <p className="text-sm text-blue-800">
          This integration supports dual payment providers (Elavon + Stripe) with both terminal and mobile checkout
          capabilities.
        </p>
        <ul className="list-disc list-inside text-sm text-blue-800 space-y-1">
          <li>
            <strong>Elavon Terminal:</strong> Pre-authorization at check-in, completion at checkout
          </li>
          <li>
            <strong>Elavon Mobile:</strong> Send payment link via Converge (SMS or email)
          </li>
          <li>
            <strong>Stripe Checkout:</strong> Send payment link via Stripe (email)
          </li>
        </ul>
      </div>
    </div>
  );
}
