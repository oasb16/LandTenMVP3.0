# Payment Flow Setup Guide

This guide explains the contractor payment flow implementation using Stripe for LandTen MVP 3.0.

## Overview

The payment system allows:
1. **Contractors** to add their bank account details (account number and routing number)
2. **Landlords** to send payments directly to contractors for completed work
3. **Secure transfers** via Stripe Connect and bank transfers

## Architecture

### Backend Components

- **Stripe Service** (`backend/app/services/stripe_service.py`): Handles all Stripe API interactions
  - Create Stripe Express accounts for contractors
  - Add external bank accounts
  - Create transfers/payouts

- **Payment API Routes** (`backend/app/routes/contractor.py`): REST endpoints
  - `POST /contractor/bank-account` - Add/update contractor bank account
  - `GET /contractor/payment-info/{contractor_id}` - Get payment status
  - `POST /contractor/payment/initiate` - Initiate payment to contractor

- **Contractor Profile Model**: Extended to include payment fields
  - `stripe_account_id`: Stripe Connect account ID
  - `bank_account_last4`: Last 4 digits of bank account
  - `bank_account_status`: Status of bank account verification
  - `payment_enabled`: Whether contractor can receive payments

### Frontend Components

- **ContractorBankAccountForm** (`frontend/src/components/ContractorBankAccountForm.tsx`)
  - Form for contractors to input bank details
  - Shows current payment status
  - Validates routing and account numbers

- **PaymentInitiator** (`frontend/src/components/PaymentInitiator.tsx`)
  - Form for landlords to send payments
  - Links payments to jobs/incidents
  - Shows payment confirmation

- **API Client** (`frontend/src/lib/api.ts`)
  - `addBankAccount()`: Add bank account details
  - `getPaymentInfo()`: Get payment info for contractor
  - `initiatePayment()`: Send payment to contractor

## Setup Instructions

### 1. Install Dependencies

#### Backend
```bash
cd backend
pip install -r requirements.txt
```

The `stripe>=7.0.0` package is already included in requirements.txt.

#### Frontend
No additional packages needed - using native fetch API.

### 2. Configure Stripe

1. **Create a Stripe Account**
   - Sign up at https://stripe.com
   - Complete business verification

2. **Get API Keys**
   - Go to Developers → API keys
   - Copy your Secret key and Publishable key
   - For testing, use Test mode keys

3. **Set up Stripe Connect**
   - Go to Connect → Settings
   - Enable Express accounts
   - Configure branding and settings

### 3. Environment Variables

#### Backend `.env`
```bash
# Stripe Payment Configuration
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

#### Frontend `.env.local`
```bash
# Stripe (for payment processing)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
```

### 4. Database Migration

The contractor profile table needs to support the new payment fields. Since you're using DynamoDB, no schema migration is needed - fields are added dynamically.

## Usage

### For Contractors: Setting Up Bank Account

1. Navigate to contractor profile/settings
2. Use the `ContractorBankAccountForm` component:

```tsx
import ContractorBankAccountForm from '@/components/ContractorBankAccountForm';

function ContractorSettings() {
  return (
    <ContractorBankAccountForm
      contractorId="contractor-123"
      onSuccess={() => {
        console.log('Bank account added successfully!');
      }}
    />
  );
}
```

3. Enter bank details:
   - Account holder name
   - 9-digit routing number
   - 4-17 digit account number
   - Account type (individual/company)

4. Submit form - creates Stripe Connect account and adds bank account

### For Landlords: Sending Payments

1. Navigate to contractor job/incident details
2. Use the `PaymentInitiator` component:

```tsx
import PaymentInitiator from '@/components/PaymentInitiator';

function JobPayment() {
  return (
    <PaymentInitiator
      contractorId="contractor-123"
      contractorName="John Doe"
      jobId="job-456"
      incidentId="incident-789"
      defaultAmount={150.00}
      defaultDescription="Payment for plumbing repair"
      onSuccess={(payment) => {
        console.log('Payment sent:', payment);
      }}
    />
  );
}
```

3. Enter payment details:
   - Amount in USD
   - Description of work
   - (Job/Incident IDs auto-populated)

4. Submit - initiates Stripe transfer

## API Reference

### Add Bank Account

**Endpoint:** `POST /contractor/bank-account`

**Request Body:**
```json
{
  "contractor_id": "contractor-123",
  "account_number": "000123456789",
  "routing_number": "110000000",
  "account_holder_name": "John Doe",
  "account_holder_type": "individual"
}
```

**Response:**
```json
{
  "status": "success",
  "contractor_id": "contractor-123",
  "bank_account_last4": "6789",
  "bank_name": "STRIPE TEST BANK",
  "payment_enabled": true
}
```

### Get Payment Info

**Endpoint:** `GET /contractor/payment-info/{contractor_id}`

**Response:**
```json
{
  "contractor_id": "contractor-123",
  "payment_enabled": true,
  "bank_account_last4": "6789",
  "bank_account_status": "new",
  "has_stripe_account": true
}
```

### Initiate Payment

**Endpoint:** `POST /contractor/payment/initiate`

**Request Body:**
```json
{
  "contractor_id": "contractor-123",
  "amount": 150.50,
  "description": "Payment for plumbing repair",
  "job_id": "job-456",
  "incident_id": "incident-789"
}
```

**Response:**
```json
{
  "status": "success",
  "transfer_id": "tr_1234567890",
  "amount": 150.50,
  "contractor_id": "contractor-123",
  "contractor_name": "John Doe",
  "description": "Payment for plumbing repair",
  "transfer_status": "pending"
}
```

## Payment Flow

1. **Contractor Onboarding**
   ```
   Contractor → Add Bank Details → Create Stripe Account → Link Bank Account → Ready for Payments
   ```

2. **Payment Processing**
   ```
   Landlord → Initiate Payment → Stripe Transfer → Contractor Bank Account
   ```

3. **Timeline**
   - Transfer initiated: Immediate
   - Funds available in Stripe: 2-3 business days
   - Funds in contractor bank: 5-7 business days (standard ACH)

## Security Considerations

1. **Data Storage**
   - Full account numbers are NEVER stored in your database
   - Only last 4 digits stored for display
   - All sensitive data handled by Stripe

2. **Authentication**
   - All endpoints require Firebase authentication
   - Contractors can only update their own bank accounts
   - Landlords can only pay for their properties/incidents

3. **Validation**
   - Routing numbers validated (9 digits)
   - Account numbers validated (4-17 digits)
   - Amount validation (must be > 0)

4. **PCI Compliance**
   - Using Stripe handles PCI compliance
   - No credit card data stored on your servers

## Testing

### Test Mode

Use Stripe test mode for development:

**Test Routing Numbers:**
- `110000000` - Valid routing number
- `111000025` - Valid routing number

**Test Account Numbers:**
- `000123456789` - Valid account number
- Any 4-17 digit number works in test mode

### Test Payments

1. Create a contractor profile
2. Add bank account with test numbers
3. Initiate a payment
4. Check Stripe dashboard for transfer

### Error Handling

Common errors:
- `404`: Contractor profile not found
- `400`: Invalid bank account details
- `400`: Contractor has not set up payment information
- `400`: Amount must be greater than 0

## Production Checklist

- [ ] Switch to Stripe live mode keys
- [ ] Update environment variables with live keys
- [ ] Complete Stripe account verification
- [ ] Set up Stripe webhooks for payment notifications
- [ ] Implement proper error logging
- [ ] Add email notifications for payments
- [ ] Set up payment reconciliation
- [ ] Configure payout schedules in Stripe
- [ ] Add terms of service for payments
- [ ] Implement fraud detection rules

## Webhooks (Future Enhancement)

To receive real-time payment updates, set up Stripe webhooks:

```python
@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )

        if event.type == "transfer.created":
            # Handle successful transfer
            pass
        elif event.type == "transfer.failed":
            # Handle failed transfer
            pass

        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## Support

For issues or questions:
- Stripe Documentation: https://stripe.com/docs
- Stripe Support: https://support.stripe.com
- API Reference: See above

## License

This payment integration is part of LandTen MVP 3.0.
