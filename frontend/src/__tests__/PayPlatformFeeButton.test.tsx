/**
 * Tests for PayPlatformFeeButton component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PayPlatformFeeButton } from '@/components/payments/PayPlatformFeeButton';

global.fetch = jest.fn();

describe('PayPlatformFeeButton', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    delete (window as any).location;
    (window as any).location = { href: '' };
  });

  const defaultProps = {
    landlordId: 'landlord_123',
    landlordEmail: 'bob@landlord.com',
    landlordName: 'Bob Landlord',
    amount: 49.99,
    description: 'Monthly subscription',
  };

  it('renders button with correct amount', () => {
    render(<PayPlatformFeeButton {...defaultProps} />);

    const button = screen.getByRole('button');
    expect(button).toHaveTextContent('Pay $49.99');
  });

  it('calls API with correct payload', async () => {
    const mockResponse = {
      success: true,
      checkoutUrl: 'https://checkout.stripe.com/fee',
      sessionId: 'cs_fee_123',
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    render(<PayPlatformFeeButton {...defaultProps} />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/checkout/platform-fee', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          landlord_id: 'landlord_123',
          landlord_email: 'bob@landlord.com',
          landlord_name: 'Bob Landlord',
          amount: 49.99,
          description: 'Monthly subscription',
        }),
      });
    });
  });

  it('uses default description when not provided', async () => {
    const propsWithoutDesc = { ...defaultProps };
    delete propsWithoutDesc.description;

    const mockResponse = {
      success: true,
      checkoutUrl: 'https://checkout.stripe.com/fee',
      sessionId: 'cs_fee_123',
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    render(<PayPlatformFeeButton {...propsWithoutDesc} />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    await waitFor(() => {
      const fetchCall = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(fetchCall[1].body);
      expect(body.description).toBe('Platform subscription fee');
    });
  });

  it('redirects to Stripe checkout on success', async () => {
    const mockResponse = {
      success: true,
      checkoutUrl: 'https://checkout.stripe.com/fee_session',
      sessionId: 'cs_fee_123',
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    render(<PayPlatformFeeButton {...defaultProps} />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(window.location.href).toBe('https://checkout.stripe.com/fee_session');
    });
  });
});
