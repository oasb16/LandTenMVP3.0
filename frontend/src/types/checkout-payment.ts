/**
 * TypeScript types for LandTen Stripe Checkout integration.
 *
 * Supports three payment flows:
 * 1. Landlord → Contractor payments (job completion)
 * 2. Tenant → Landlord payments (rent/fees)
 * 3. Landlord → Platform payments (platform fees)
 */

export type PaymentType = 'job_completion' | 'rent' | 'platform_fee';

export type PaymentSessionStatus = 'pending' | 'completed' | 'failed' | 'cancelled';

// Request types

export interface JobPaymentRequest {
  job_id: string;
  bid_id: string;
  contractor_name: string;
  contractor_email: string;
  landlord_email: string;
  amount: number;
  description?: string;
  success_url?: string;
  cancel_url?: string;
}

export interface RentPaymentRequest {
  property_id: string;
  tenant_name: string;
  tenant_email: string;
  landlord_email: string;
  amount: number;
  period?: string; // e.g., "January 2024"
  success_url?: string;
  cancel_url?: string;
}

export interface PlatformFeeRequest {
  landlord_id: string;
  landlord_email: string;
  landlord_name: string;
  amount: number;
  description?: string;
  success_url?: string;
  cancel_url?: string;
}

// Response types

export interface CheckoutSessionResponse {
  success: boolean;
  checkoutUrl?: string;
  sessionId?: string;
  error?: string;
}

// Payment record types (for displaying payment history)

export interface PaymentRecord {
  id: string;
  payment_type: PaymentType;
  stripe_session_id: string;
  amount: number;
  status: PaymentSessionStatus;

  // Payer info
  payer_email: string;
  payer_name?: string;

  // Receiver info
  receiver_email?: string;

  // Related entity IDs
  job_id?: string;
  bid_id?: string;
  property_id?: string;
  landlord_id?: string;

  // Timestamps
  created_at: string;
  completed_at?: string;

  // Metadata
  period?: string;
  description?: string;
}
