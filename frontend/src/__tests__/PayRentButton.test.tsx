/**
 * Tests for PayRentButton component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PayRentButton } from '@/components/payments/PayRentButton';

global.fetch = jest.fn();

describe('PayRentButton', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    delete (window as any).location;
    (window as any).location = { href: '' };
  });

  const defaultProps = {
    propertyId: 'prop_123',
    tenantName: 'Alice Tenant',
    tenantEmail: 'alice@tenant.com',
    landlordEmail: 'bob@landlord.com',
    amount: 1500.00,
    period: 'January 2024',
  };

  it('renders button with correct amount', () => {
    render(<PayRentButton {...defaultProps} />);

    const button = screen.getByRole('button');
    expect(button).toHaveTextContent('Pay Rent $1500.00');
  });

  it('calls API with correct payload including period', async () => {
    const mockResponse = {
      success: true,
      checkoutUrl: 'https://checkout.stripe.com/rent',
      sessionId: 'cs_rent_123',
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    render(<PayRentButton {...defaultProps} />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/checkout/rent-payment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          property_id: 'prop_123',
          tenant_name: 'Alice Tenant',
          tenant_email: 'alice@tenant.com',
          landlord_email: 'bob@landlord.com',
          amount: 1500.00,
          period: 'January 2024',
        }),
      });
    });
  });

  it('works without optional period', async () => {
    const propsWithoutPeriod = { ...defaultProps };
    delete propsWithoutPeriod.period;

    const mockResponse = {
      success: true,
      checkoutUrl: 'https://checkout.stripe.com/rent',
      sessionId: 'cs_rent_123',
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    render(<PayRentButton {...propsWithoutPeriod} />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });
  });

  it('redirects to Stripe checkout on success', async () => {
    const mockResponse = {
      success: true,
      checkoutUrl: 'https://checkout.stripe.com/rent_session',
      sessionId: 'cs_rent_123',
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    render(<PayRentButton {...defaultProps} />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(window.location.href).toBe('https://checkout.stripe.com/rent_session');
    });
  });

  it('shows loading state', async () => {
    (global.fetch as jest.Mock).mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );

    render(<PayRentButton {...defaultProps} />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    expect(button).toBeDisabled();
    expect(screen.getByText('Processing...')).toBeInTheDocument();
  });
});
