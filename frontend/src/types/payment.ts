/**
 * Payment types for dual payment provider integration (Elavon + Stripe)
 * Supports terminal and mobile checkout capabilities
 */

export type PaymentProvider = 'elavon' | 'stripe';

export interface ElavonConfig {
  // Terminal payment credentials
  merchantId: string;
  userId: string;
  pin: string;
  terminalId: string;
  apiEndpoint: string;
  isTestMode: boolean;

  // Authentication token (retrieved dynamically)
  token?: string;
  tokenExpiresAt?: Date;

  // Mobile checkout (Converge) credentials
  checkoutJsEnabled?: boolean;
  convergeMerchantId?: string;
  convergeUserId?: string;
  convergePin?: string;
  convergeEndpoint?: string;
}

export interface PaymentConfig {
  activeProvider: PaymentProvider;
  elavon: ElavonConfig | null;
  stripeEnabled: boolean;
}

export interface Reservation {
  id: string;
  guestId: string;
  roomId: string;
  checkInDate: Date;
  checkOutDate: Date;
  status: 'pending' | 'checked_in' | 'checked_out' | 'cancelled';

  // Payment fields
  preAuthTransactionId?: string;
  preAuthAmount?: number;
  totalCharges: number;
  roomCharges: number;
  additionalCharges: Charge[];
  paymentStatus: 'pending' | 'pre_authorized' | 'completed' | 'refunded';
  createdAt: Date;
}

export interface Charge {
  id: string;
  reservationId: string;
  description: string;
  amount: number;
  category: 'room' | 'restaurant' | 'bar' | 'spa' | 'laundry' | 'minibar' | 'other';
  createdAt: Date;
}

// API Request/Response Types
export interface ElavonTokenRequest {
  merchantId: string;
  userId: string;
  pin: string;
  apiEndpoint: string;
}

export interface ElavonTokenResponse {
  token: string;
  expiresAt: string;
}

export interface ElavonPreAuthRequest {
  token: string;
  amount: number;
  terminalId: string;
  merchantId: string;
}

export interface ElavonPreAuthResponse {
  transactionId: string;
  status: 'APPROVED' | 'DECLINED' | 'ERROR';
  amount: number;
  message?: string;
  error?: string;
}

export interface ElavonCompletionRequest {
  token: string;
  originalTransactionId: string;
  amount: number;
  terminalId: string;
  merchantId: string;
}

export interface ElavonCompletionResponse {
  transactionId: string;
  status: 'APPROVED' | 'DECLINED' | 'ERROR';
  amount: number;
  message?: string;
  error?: string;
}

export interface StripeCheckoutRequest {
  amount: number;
  guestName: string;
  guestEmail: string;
  guestPhone?: string;
  reservationId: string;
  hotelName?: string;
}

export interface StripeCheckoutResponse {
  success: boolean;
  checkoutUrl?: string;
  sessionId?: string;
  error?: string;
}

export interface ElavonCheckoutRequest {
  merchantId: string;
  userId: string;
  pin: string;
  amount: number;
  transactionType?: string;
  firstName?: string;
  lastName?: string;
  email?: string;
  invoiceNumber?: string;
  isTestMode: boolean;
}

export interface ElavonCheckoutResponse {
  success: boolean;
  checkoutUrl?: string;
  token?: string;
  error?: string;
}

export interface SendEmailRequest {
  guestEmail: string;
  guestName: string;
  amount: number;
  hotelName?: string;
  checkoutUrl?: string;
  type: 'payment_link' | 'receipt';
  roomNumber?: string;
  nights?: number;
  checkInDate?: string;
  checkOutDate?: string;
  roomCharges?: number;
  additionalCharges?: Array<{
    description: string;
    amount: number;
  }>;
  transactionId?: string;
}

export interface SendEmailResponse {
  success: boolean;
  emailId?: string;
  error?: string;
}

export interface SendSMSRequest {
  phoneNumber: string;
  guestName: string;
  amount: number;
  checkoutUrl: string;
  hotelName?: string;
}

export interface SendSMSResponse {
  success: boolean;
  messageId?: string;
  error?: string;
}
