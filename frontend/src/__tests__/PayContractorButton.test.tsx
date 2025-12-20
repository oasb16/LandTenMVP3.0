/**
 * Tests for PayContractorButton component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PayContractorButton } from '@/components/payments/PayContractorButton';

// Mock fetch
global.fetch = jest.fn();

describe('PayContractorButton', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    delete (window as any).location;
    (window as any).location = { href: '' };
  });

  const defaultProps = {
    jobId: 'job_123',
    bidId: 'bid_456',
    contractorName: 'John Contractor',
    contractorEmail: 'john@contractor.com',
    landlordEmail: 'jane@landlord.com',
    amount: 500.00,
    description: 'Plumbing repair',
  };

  it('renders button with correct amount', () => {
    render(<PayContractorButton {...defaultProps} />);

    const button = screen.getByRole('button');
    expect(button).toHaveTextContent('Pay $500.00');
  });

  it('calls API with correct payload when clicked', async () => {
    const mockResponse = {
      success: true,
      checkoutUrl: 'https://checkout.stripe.com/test',
      sessionId: 'cs_test_123',
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    render(<PayContractorButton {...defaultProps} />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/checkout/job-payment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          job_id: 'job_123',
          bid_id: 'bid_456',
          contractor_name: 'John Contractor',
          contractor_email: 'john@contractor.com',
          landlord_email: 'jane@landlord.com',
          amount: 500.00,
          description: 'Plumbing repair',
        }),
      });
    });
  });

  it('redirects to Stripe checkout URL on success', async () => {
    const mockResponse = {
      success: true,
      checkoutUrl: 'https://checkout.stripe.com/test_session',
      sessionId: 'cs_test_123',
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    render(<PayContractorButton {...defaultProps} />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(window.location.href).toBe('https://checkout.stripe.com/test_session');
    });
  });

  it('shows loading state while processing', async () => {
    (global.fetch as jest.Mock).mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );

    render(<PayContractorButton {...defaultProps} />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    expect(button).toBeDisabled();
    expect(screen.getByText('Processing...')).toBeInTheDocument();
  });

  it('calls onError callback when API fails', async () => {
    const onError = jest.fn();
    const mockResponse = {
      success: false,
      error: 'Payment failed',
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => mockResponse,
    });

    render(<PayContractorButton {...defaultProps} onError={onError} />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('Payment failed');
    });
  });

  it('calls onSuccess callback when payment succeeds', async () => {
    const onSuccess = jest.fn();
    const mockResponse = {
      success: true,
      checkoutUrl: 'https://checkout.stripe.com/test',
      sessionId: 'cs_test_123',
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    render(<PayContractorButton {...defaultProps} onSuccess={onSuccess} />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it('handles network errors gracefully', async () => {
    const onError = jest.fn();

    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

    render(<PayContractorButton {...defaultProps} onError={onError} />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('Network error');
    });
  });

  it('disables button when disabled prop is true', () => {
    render(<PayContractorButton {...defaultProps} />);

    const button = screen.getByRole('button');

    // Initially enabled
    expect(button).not.toBeDisabled();

    // Click to start loading
    fireEvent.click(button);

    // Should be disabled while loading
    expect(button).toBeDisabled();
  });
});
