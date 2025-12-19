'use client';

/**
 * Payment Context Provider
 *
 * Manages payment configuration state for Elavon and Stripe integration.
 * Provides payment config to all components in the app.
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import { PaymentConfig, ElavonConfig, PaymentProvider } from '@/types/payment';

interface PaymentContextType {
  paymentConfig: PaymentConfig;
  elavonConfig: ElavonConfig | null;
  setElavonConfig: (config: ElavonConfig) => void;
  setElavonToken: (token: string, expiresAt?: Date) => void;
  setActivePaymentProvider: (provider: PaymentProvider) => void;
  setStripeEnabled: (enabled: boolean) => void;
}

const PaymentContext = createContext<PaymentContextType | undefined>(undefined);

export function PaymentProvider({ children }: { children: React.ReactNode }) {
  // Initialize state from localStorage if available
  const [paymentConfig, setPaymentConfig] = useState<PaymentConfig>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('payment-config');
      if (stored) {
        try {
          return JSON.parse(stored);
        } catch (e) {
          console.error('Failed to parse stored payment config:', e);
        }
      }
    }
    return {
      activeProvider: 'elavon',
      elavon: null,
      stripeEnabled: true,
    };
  });

  const [elavonConfig, setElavonConfigState] = useState<ElavonConfig | null>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('elavon-config');
      if (stored) {
        try {
          const config = JSON.parse(stored);
          // Convert tokenExpiresAt back to Date if it exists
          if (config.tokenExpiresAt) {
            config.tokenExpiresAt = new Date(config.tokenExpiresAt);
          }
          return config;
        } catch (e) {
          console.error('Failed to parse stored elavon config:', e);
        }
      }
    }
    return null;
  });

  // Sync to localStorage whenever state changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('payment-config', JSON.stringify(paymentConfig));
    }
  }, [paymentConfig]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      if (elavonConfig) {
        localStorage.setItem('elavon-config', JSON.stringify(elavonConfig));
      } else {
        localStorage.removeItem('elavon-config');
      }
    }
  }, [elavonConfig]);

  const setElavonConfig = (config: ElavonConfig) => {
    setElavonConfigState(config);
    setPaymentConfig(prev => ({
      ...prev,
      elavon: config,
    }));
  };

  const setElavonToken = (token: string, expiresAt?: Date) => {
    if (!elavonConfig) return;

    const updatedConfig = {
      ...elavonConfig,
      token,
      tokenExpiresAt: expiresAt,
    };

    setElavonConfigState(updatedConfig);
    setPaymentConfig(prev => ({
      ...prev,
      elavon: updatedConfig,
    }));
  };

  const setActivePaymentProvider = (provider: PaymentProvider) => {
    setPaymentConfig(prev => ({
      ...prev,
      activeProvider: provider,
    }));
  };

  const setStripeEnabled = (enabled: boolean) => {
    setPaymentConfig(prev => ({
      ...prev,
      stripeEnabled: enabled,
    }));
  };

  return (
    <PaymentContext.Provider
      value={{
        paymentConfig,
        elavonConfig,
        setElavonConfig,
        setElavonToken,
        setActivePaymentProvider,
        setStripeEnabled,
      }}
    >
      {children}
    </PaymentContext.Provider>
  );
}

export function usePayment() {
  const context = useContext(PaymentContext);
  if (context === undefined) {
    throw new Error('usePayment must be used within a PaymentProvider');
  }
  return context;
}
