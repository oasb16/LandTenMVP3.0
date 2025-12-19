'use client';

/**
 * Check-Out Dialog Component
 *
 * Handles guest checkout with multiple payment methods:
 * 1. Terminal Payment (capture pre-auth)
 * 2. Mobile Checkout (Elavon Converge or Stripe)
 * 3. Send payment link via SMS or Email
 */

import React, { useState } from 'react';
import { usePayment } from '@/contexts/PaymentContext';

interface CheckOutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  guestName: string;
  guestEmail: string;
  totalAmount: number;
  preAuthTransactionId?: string;
  onSuccess: () => void;
}

export function CheckOutDialog({
  open,
  onOpenChange,
  guestName,
  guestEmail,
  totalAmount,
  preAuthTransactionId,
  onSuccess,
}: CheckOutDialogProps) {
  const [paymentMethod, setPaymentMethod] = useState<'terminal' | 'mobile'>('terminal');
  const [deliveryMethod, setDeliveryMethod] = useState<'sms' | 'email'>('sms');
  const [mobileNumber, setMobileNumber] = useState('');
  const [emailAddress, setEmailAddress] = useState(guestEmail);
  const [isProcessing, setIsProcessing] = useState(false);
  const [linkSent, setLinkSent] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const { elavonConfig, paymentConfig } = usePayment();

  // Terminal Payment (Capture Pre-Auth)
  const handleTerminalCheckout = async () => {
    setIsProcessing(true);
    setMessage(null);

    try {
      const response = await fetch('/api/payment/elavon/completion', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: elavonConfig?.token,
          originalTransactionId: preAuthTransactionId,
          amount: totalAmount,
          terminalId: elavonConfig?.terminalId,
          merchantId: elavonConfig?.merchantId,
        }),
      });

      const data = await response.json();

      if (!response.ok || data.status === 'DECLINED') {
        throw new Error(data.error || data.detail || 'Payment failed');
      }

      // Send receipt email
      await fetch('/api/payment/send-checkout-email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          guestEmail: emailAddress,
          guestName,
          amount: totalAmount,
          type: 'receipt',
          transactionId: data.transactionId,
        }),
      });

      setMessage({ type: 'success', text: 'Checkout complete!' });
      setTimeout(() => {
        onSuccess();
        onOpenChange(false);
      }, 1500);
    } catch (error) {
      console.error('Checkout error:', error);
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Payment failed',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Mobile Checkout (Send Payment Link)
  const handleMobileCheckout = async () => {
    const isSms = deliveryMethod === 'sms';
    const contact = isSms ? mobileNumber.trim() : emailAddress.trim();

    if (!contact) {
      setMessage({
        type: 'error',
        text: isSms ? 'Please enter a mobile number' : 'Please enter an email address',
      });
      return;
    }

    setIsProcessing(true);
    setMessage(null);

    try {
      const isStripe = paymentConfig?.activeProvider === 'stripe';
      let checkoutUrl: string;

      if (isStripe) {
        // Stripe Checkout
        const response = await fetch('/api/payment/stripe/checkout-session', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            amount: totalAmount,
            guestName,
            guestEmail: emailAddress,
            guestPhone: mobileNumber,
            reservationId: `res_${Date.now()}`,
            hotelName: 'Your Hotel',
          }),
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
          throw new Error(data.error || data.detail || 'Failed to create checkout session');
        }

        checkoutUrl = data.checkoutUrl;
      } else {
        // Elavon Checkout.js
        if (!elavonConfig?.checkoutJsEnabled) {
          setMessage({ type: 'error', text: 'Mobile checkout not configured' });
          return;
        }

        const nameParts = guestName.split(' ');
        const firstName = nameParts[0];
        const lastName = nameParts.slice(1).join(' ');

        const response = await fetch('/api/payment/elavon/checkout-session', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            merchantId: elavonConfig.convergeMerchantId,
            userId: elavonConfig.convergeUserId,
            pin: elavonConfig.convergePin,
            amount: totalAmount,
            transactionType: 'ccsale',
            firstName,
            lastName,
            email: emailAddress,
            isTestMode: elavonConfig.isTestMode,
          }),
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
          throw new Error(data.error || data.detail || 'Failed to create checkout session');
        }

        checkoutUrl = data.checkoutUrl;
      }

      // Send link via SMS or Email
      if (isSms) {
        await fetch('/api/payment/send-checkout-sms', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            phoneNumber: mobileNumber,
            checkoutUrl,
            guestName,
            amount: totalAmount,
            hotelName: 'Your Hotel',
          }),
        });

        setMessage({ type: 'success', text: `Payment link sent to ${mobileNumber}` });
      } else {
        await fetch('/api/payment/send-checkout-email', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            guestEmail: emailAddress,
            guestName,
            amount: totalAmount,
            checkoutUrl,
            type: 'payment_link',
            hotelName: 'Your Hotel',
          }),
        });

        setMessage({ type: 'success', text: `Payment link sent to ${emailAddress}` });
      }

      setLinkSent(true);
    } catch (error) {
      console.error('Mobile checkout error:', error);
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to send payment link',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full p-6 space-y-6 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Guest Checkout</h2>
        </div>

        {/* Guest Info */}
        <div className="bg-gray-50 p-4 rounded-lg">
          <p className="font-semibold text-gray-900">{guestName}</p>
          <p className="text-2xl font-bold text-gray-900 mt-2">Total: ${totalAmount.toFixed(2)}</p>
        </div>

        {/* Payment Method Selection */}
        <div className="space-y-3">
          <label className="text-sm font-medium text-gray-900">Payment Method</label>
          <div className="space-y-2">
            <label className="flex items-center gap-3 p-3 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50">
              <input
                type="radio"
                value="terminal"
                checked={paymentMethod === 'terminal'}
                onChange={(e) => setPaymentMethod(e.target.value as 'terminal')}
                className="w-4 h-4"
              />
              <span className="text-gray-900">Terminal Payment (Capture Pre-Auth)</span>
            </label>
            <label className="flex items-center gap-3 p-3 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50">
              <input
                type="radio"
                value="mobile"
                checked={paymentMethod === 'mobile'}
                onChange={(e) => setPaymentMethod(e.target.value as 'mobile')}
                className="w-4 h-4"
              />
              <span className="text-gray-900">Mobile Checkout (Send Link)</span>
            </label>
          </div>
        </div>

        {/* Mobile Checkout Options */}
        {paymentMethod === 'mobile' && (
          <div className="border border-gray-300 rounded-lg p-4 space-y-4">
            <div className="flex gap-2">
              <button
                onClick={() => setDeliveryMethod('sms')}
                className={`flex-1 py-2 px-4 rounded-lg border ${
                  deliveryMethod === 'sms'
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                }`}
              >
                📱 SMS
              </button>
              <button
                onClick={() => setDeliveryMethod('email')}
                className={`flex-1 py-2 px-4 rounded-lg border ${
                  deliveryMethod === 'email'
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                }`}
              >
                ✉️ Email
              </button>
            </div>

            {deliveryMethod === 'sms' ? (
              <input
                type="tel"
                placeholder="+1 555 0123"
                value={mobileNumber}
                onChange={(e) => setMobileNumber(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            ) : (
              <input
                type="email"
                placeholder="guest@email.com"
                value={emailAddress}
                onChange={(e) => setEmailAddress(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            )}

            {linkSent && (
              <div className="flex items-center gap-2 text-green-700 p-3 bg-green-50 rounded-lg border border-green-200">
                <span className="text-xl">✓</span>
                <span>Payment link sent successfully!</span>
              </div>
            )}

            <button
              onClick={handleMobileCheckout}
              disabled={isProcessing || linkSent}
              className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isProcessing ? 'Sending...' : 'Send Payment Link'}
            </button>
          </div>
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

        {/* Terminal Checkout Button */}
        {paymentMethod === 'terminal' && (
          <button
            onClick={handleTerminalCheckout}
            disabled={isProcessing}
            className="w-full py-3 px-6 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-lg font-medium flex items-center justify-center gap-2"
          >
            {isProcessing ? (
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
              '💳 Complete Payment'
            )}
          </button>
        )}

        {/* Close Button */}
        <div className="flex justify-end">
          <button
            onClick={() => onOpenChange(false)}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
            disabled={isProcessing}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
