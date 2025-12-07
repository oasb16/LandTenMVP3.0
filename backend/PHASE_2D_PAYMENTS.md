# Phase 2D: Stripe Payment Processing - Implementation Guide

## Overview
Complete Stripe payment integration with **15% platform fee** for contractor job payments.

**Flow**: Landlord approves completed work → Initiates payment → Stripe processes → Platform takes 15% → Contractor receives 85%

## Architecture

### Payment Models
- **Payment** (`backend/app/models/payment.py`): Complete payment tracking with Stripe IDs
- **Job** (`backend/app/models/job.py`): Updated with `payment_status` and `stripe_payment_intent_id`
- **Contractor** (`backend/app/models/contractor.py`): Includes `stripe_account_id` for Stripe Connect

### API Endpoints (`backend/app/routes/payments.py`)

#### 1. Initiate Payment
```http
POST /api/v1/payments/jobs/{job_id}/initiate
Authorization: Bearer <landlord_token>
```

**Flow**:
1. Verifies landlord owns the job
2. Checks job status is `COMPLETED`
3. Gets awarded bid amount
4. Verifies contractor has Stripe Connect account
5. Calculates: `platform_fee = 15%`, `contractor_payout = 85%`
6. Creates Stripe PaymentIntent with destination charge
7. Creates Payment record in DynamoDB
8. Updates job `payment_status = 'processing'`
9. Returns `client_secret` for frontend

**Response**:
```json
{
  "success": true,
  "payment_id": "pay_a1b2c3d4e5f6",
  "client_secret": "pi_xxx_secret_yyy",
  "amounts": {
    "gross_amount": 250.0,
    "platform_fee": 37.5,
    "contractor_payout": 212.5
  },
  "status": "processing",
  "stripe_payment_intent_id": "pi_xxx"
}
```

**Error Cases**:
- `403`: Not the landlord who owns the job
- `400`: Job not in COMPLETED status
- `409`: Payment already initiated/completed
- `400`: Contractor hasn't completed Stripe onboarding
- `500`: Stripe API error

#### 2. Stripe Webhook Handler
```http
POST /api/v1/payments/webhooks/stripe
Stripe-Signature: <signature_header>
```

**Handles Events**:
- `payment_intent.succeeded`: Payment completed successfully
- `payment_intent.payment_failed`: Payment failed

**Flow for `payment_intent.succeeded`**:
1. Verifies webhook signature with `STRIPE_WEBHOOK_SECRET`
2. Finds Payment by `stripe_payment_intent_id`
3. Updates Payment status to `COMPLETED`
4. Updates Job status to `PAID`
5. Increments contractor's `completed_jobs` count
6. Returns 200 OK (idempotent - safe to replay)

**Idempotency**: If payment already marked as completed, returns success without re-processing.

#### 3. Get Payment Status
```http
GET /api/v1/payments/jobs/{job_id}/status
Authorization: Bearer <token>
```

**Access**: Landlord or contractor for the job

**Response**:
```json
{
  "status": "completed",
  "payment_id": "pay_a1b2c3d4e5f6",
  "job_id": "job_123456789abc",
  "gross_amount": 250.0,
  "platform_fee": 37.5,
  "contractor_payout": 212.5,
  "stripe_payment_intent_id": "pi_xxx",
  "created_at": "2025-12-07T10:00:00Z",
  "completed_at": "2025-12-07T10:05:00Z"
}
```

If no payment initiated:
```json
{
  "status": "not_initiated",
  "job_id": "job_123456789abc",
  "payment_status": "pending"
}
```

#### 4. Stripe Connect Onboarding
```http
POST /api/v1/contractors/stripe/connect
Authorization: Bearer <contractor_token>
Content-Type: application/json

{
  "contractor_id": "cont_a1b2c3d4e5f6"
}
```

**Flow**:
1. Verifies user owns the contractor account
2. Creates Stripe Connect Express account
3. Generates onboarding link
4. Stores `stripe_account_id` in contractor record
5. Returns onboarding URL for contractor to complete KYC

**Response**:
```json
{
  "success": true,
  "onboarding_complete": false,
  "url": "https://connect.stripe.com/setup/s/xxx",
  "stripe_account_id": "acct_xxx"
}
```

If onboarding already complete:
```json
{
  "success": true,
  "onboarding_complete": true,
  "url": "https://connect.stripe.com/express/xxx",
  "stripe_account_id": "acct_xxx"
}
```

#### 5. Stripe Connect Webhook (Optional)
```http
POST /api/v1/contractors/stripe/webhook
Stripe-Signature: <signature_header>
```

**Handles Events**:
- `account.updated`: Updates contractor's `stripe_onboarding_complete` when charges are enabled

## Stripe Configuration

### Required Environment Variables
```bash
# Stripe Secret Key (sk_test_... for test, sk_live_... for production)
STRIPE_SECRET_KEY=sk_test_...

# Webhook signing secret from Stripe Dashboard
STRIPE_WEBHOOK_SECRET=whsec_...

# Optional: Stripe Connect Client ID
STRIPE_CONNECT_CLIENT_ID=ca_...

# Return URLs after Stripe Connect onboarding
STRIPE_RETURN_URL=https://landten.app/contractor/dashboard
STRIPE_REFRESH_URL=https://landten.app/contractor/stripe-connect
```

### Stripe Dashboard Setup

#### 1. Create Webhook Endpoint
1. Go to https://dashboard.stripe.com/webhooks
2. Click "Add endpoint"
3. URL: `https://your-domain.com/api/v1/payments/webhooks/stripe`
4. Events to listen for:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
5. Copy the webhook signing secret to `STRIPE_WEBHOOK_SECRET`

#### 2. Enable Stripe Connect (for contractor payouts)
1. Go to https://dashboard.stripe.com/settings/connect
2. Enable "Express" accounts
3. Set branding (optional)
4. Copy Connect Client ID to `STRIPE_CONNECT_CLIENT_ID` (optional)

#### 3. (Optional) Create Connect Webhook
1. Go to https://dashboard.stripe.com/webhooks
2. Add another endpoint: `https://your-domain.com/api/v1/contractors/stripe/webhook`
3. Events:
   - `account.updated`
4. Use the same `STRIPE_WEBHOOK_SECRET`

## DynamoDB Schema

### Payments Table
```
Table: payments
Partition Key: payment_id (String)

Attributes:
- payment_id: "pay_xxx"
- job_id: "job_xxx"
- bid_id: "bid_xxx"
- landlord_id: "user_xxx"
- contractor_id: "cont_xxx"
- gross_amount: 250.0
- platform_fee: 37.5
- contractor_payout: 212.5
- stripe_payment_intent_id: "pi_xxx"
- stripe_transfer_id: "tr_xxx" (optional, future use)
- status: "pending" | "processing" | "completed" | "failed"
- created_at: ISO timestamp
- completed_at: ISO timestamp
- error_message: String (if failed)
```

**Note**: Payment amounts are calculated automatically based on 15% platform fee:
- `platform_fee = gross_amount * 0.15`
- `contractor_payout = gross_amount * 0.85`

### Jobs Table Updates
```
New Fields:
- payment_status: "pending" | "processing" | "completed" | "failed"
- stripe_payment_intent_id: "pi_xxx"
```

### Contractors Table Updates
```
New Fields:
- stripe_account_id: "acct_xxx"
- stripe_onboarding_complete: boolean
- completed_jobs: integer (incremented on payment success)
```

### Users Table (auto-created if needed)
```
New Fields:
- stripe_customer_id: "cus_xxx" (for landlords)
```

## Testing Checklist

### 1. Contractor Onboarding
- [ ] Call `POST /api/v1/contractors/stripe/connect`
- [ ] Visit returned URL and complete Stripe onboarding
- [ ] Verify `stripe_account_id` saved in contractors table
- [ ] Verify `stripe_onboarding_complete = true` after completion

### 2. Payment Initiation
- [ ] Create job and complete work (status = COMPLETED)
- [ ] Call `POST /api/v1/payments/jobs/{job_id}/initiate`
- [ ] Verify PaymentIntent created in Stripe Dashboard
- [ ] Verify Payment record created in DynamoDB
- [ ] Verify job `payment_status = 'processing'`
- [ ] Verify amounts: 15% platform fee, 85% contractor payout

### 3. Payment Completion (Test Mode)
Use Stripe test card to complete payment:
```
Card Number: 4242 4242 4242 4242
Expiry: Any future date
CVC: Any 3 digits
ZIP: Any 5 digits
```

- [ ] Complete payment in test frontend
- [ ] Webhook triggered: `payment_intent.succeeded`
- [ ] Verify Payment status updated to `COMPLETED`
- [ ] Verify Job status updated to `PAID`
- [ ] Verify contractor `completed_jobs` incremented
- [ ] Verify funds transferred to contractor account (check Stripe Dashboard)

### 4. Webhook Idempotency
- [ ] Replay webhook event in Stripe Dashboard
- [ ] Verify payment not processed twice
- [ ] Verify returns 200 OK with "already processed" message

### 5. Error Handling
- [ ] Try payment without contractor Stripe account → 400 error
- [ ] Try payment on non-COMPLETED job → 400 error
- [ ] Try payment with invalid Stripe key → 500 error
- [ ] Verify failed payments update status to `FAILED`

### 6. Payment Status Retrieval
- [ ] Call `GET /api/v1/payments/jobs/{job_id}/status` as landlord
- [ ] Call same endpoint as contractor
- [ ] Verify amounts breakdown returned
- [ ] Call on job without payment → returns "not_initiated"

## Deployment Steps

### 1. Environment Setup
```bash
# Add to .env or environment variables
STRIPE_SECRET_KEY=sk_test_...  # or sk_live_... for production
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_RETURN_URL=https://landten.app/contractor/dashboard
STRIPE_REFRESH_URL=https://landten.app/contractor/stripe-connect
```

### 2. Deploy Backend
```bash
cd backend
# Ensure stripe is in requirements.txt (already added)
pip install -r requirements.txt

# Deploy to your hosting (Heroku, AWS, etc.)
# Example for Heroku:
git push heroku main
```

### 3. Configure Stripe Webhooks
1. Get your deployed URL (e.g., `https://api.landten.app`)
2. Add webhook endpoint: `https://api.landten.app/api/v1/payments/webhooks/stripe`
3. Select events: `payment_intent.succeeded`, `payment_intent.payment_failed`
4. Copy webhook secret to environment variables
5. Redeploy if environment variables changed

### 4. Test in Production
1. Switch to Stripe test mode
2. Complete contractor onboarding
3. Create test job and complete it
4. Initiate payment
5. Use test card to complete payment
6. Verify webhook processing
7. Check all database updates

### 5. Go Live
1. Switch Stripe keys to live mode (`sk_live_...`)
2. Update webhook to use live mode secret
3. Test with real bank account (small amount)
4. Monitor Stripe Dashboard for successful transfers

## Security Considerations

### 1. Webhook Signature Verification
**Critical**: All webhook endpoints verify Stripe signatures to prevent spoofing.

```python
event = stripe.Webhook.construct_event(
    payload,
    sig_header,
    STRIPE_WEBHOOK_SECRET
)
```

### 2. Payment Authorization
- Only landlord who owns the job can initiate payment
- Only users associated with the job can view payment status

### 3. Idempotency
- Webhook handler is idempotent (safe to replay)
- Payment already completed returns success without re-processing

### 4. Error Handling
- All Stripe API errors caught and returned as HTTP 500
- Database errors caught and payment rolled back when possible
- Failed payments logged with error messages

## Monitoring & Logs

### Log Messages
```
[payments] Created Stripe customer {customer_id} for user {user_id}
[payments] Created PaymentIntent {intent_id} for job {job_id}
[payments] Created payment record {payment_id}
[payments] Received webhook event: payment_intent.succeeded
[payments] Updated payment {payment_id} to COMPLETED
[payments] Updated job {job_id} to PAID
[payments] Updated stats for contractor {contractor_id}
[payments] Payment {payment_id} already completed (idempotent)
```

### Error Logs
```
[payments] DynamoDB error fetching job: ...
[payments] Stripe error creating PaymentIntent: ...
[payments] Error updating payment status: ...
[payments] Invalid webhook signature: ...
```

### Stripe Dashboard Monitoring
- View payments: https://dashboard.stripe.com/payments
- View payouts: https://dashboard.stripe.com/payouts
- View webhook events: https://dashboard.stripe.com/webhooks
- View Connect accounts: https://dashboard.stripe.com/connect/accounts

## Platform Fee Breakdown

For a $250 job:
- **Gross Amount**: $250.00 (paid by landlord)
- **Platform Fee (15%)**: $37.50 (kept by platform)
- **Contractor Payout (85%)**: $212.50 (transferred to contractor)

Stripe fees (~2.9% + 30¢) are deducted from the platform fee, not the contractor payout.

## API Integration Example

### Frontend Flow (React/Next.js)

```typescript
// 1. Contractor completes Stripe onboarding
const onboardStripe = async (contractorId: string) => {
  const response = await fetch('/api/v1/contractors/stripe/connect', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ contractor_id: contractorId })
  });

  const { url } = await response.json();
  window.location.href = url; // Redirect to Stripe onboarding
};

// 2. Landlord initiates payment for completed job
const initiatePayment = async (jobId: string) => {
  const response = await fetch(`/api/v1/payments/jobs/${jobId}/initiate`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${landlordToken}`
    }
  });

  const { client_secret, amounts } = await response.json();

  // Use Stripe.js to complete payment
  const stripe = await loadStripe(STRIPE_PUBLISHABLE_KEY);
  const { error } = await stripe.confirmCardPayment(client_secret, {
    payment_method: {
      card: cardElement,
      billing_details: { name: landlordName }
    }
  });

  if (error) {
    console.error('Payment failed:', error);
  } else {
    console.log('Payment successful!');
    // Poll payment status or listen for webhook
  }
};

// 3. Check payment status
const checkPaymentStatus = async (jobId: string) => {
  const response = await fetch(`/api/v1/payments/jobs/${jobId}/status`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  const status = await response.json();
  console.log('Payment status:', status);
};
```

## Troubleshooting

### Payment Intent Not Created
**Issue**: 500 error when initiating payment
**Check**:
- Is `STRIPE_SECRET_KEY` set correctly?
- Does contractor have `stripe_account_id`?
- Is contractor's Stripe onboarding complete?
- Check backend logs for Stripe API errors

### Webhook Not Received
**Issue**: Payment completed but job status not updated
**Check**:
- Is webhook endpoint configured in Stripe Dashboard?
- Is `STRIPE_WEBHOOK_SECRET` correct?
- Is webhook URL publicly accessible?
- Check Stripe Dashboard → Webhooks → Event log for errors
- Manually replay webhook event from Stripe Dashboard

### Contractor Not Receiving Payout
**Issue**: Payment succeeded but contractor not paid
**Check**:
- Verify PaymentIntent in Stripe Dashboard shows transfer
- Check contractor's Stripe account (use login link)
- Verify transfer_data was set correctly on PaymentIntent
- Check Stripe Connect account is fully verified

### Platform Fee Incorrect
**Issue**: Platform receiving wrong amount
**Check**:
- Verify `PLATFORM_FEE_PERCENT = 0.15` in code
- Check `application_fee_amount` in Stripe Dashboard
- Formula: `platform_fee = gross_amount * 0.15`

## Support Resources

- **Stripe Documentation**: https://stripe.com/docs/connect
- **Stripe API Reference**: https://stripe.com/docs/api
- **Stripe Webhooks Guide**: https://stripe.com/docs/webhooks
- **Test Cards**: https://stripe.com/docs/testing

## Future Enhancements

- [ ] Refund processing endpoint
- [ ] Dispute handling
- [ ] Payment retry logic for failed payments
- [ ] Email notifications on payment success/failure
- [ ] Payment analytics dashboard
- [ ] Support for multiple currencies
- [ ] Installment payments for large jobs
- [ ] Escrow service (hold funds until work verified)
- [ ] Contractor payout scheduling (daily, weekly, monthly)
