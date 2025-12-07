# LandTen MVP 3.0 - Complete Workflow Verification Checklist

This checklist ensures all features from Phases 2A-2D and 3A-3B are working correctly end-to-end.

## Prerequisites

- [ ] Backend running on http://localhost:8000
- [ ] Frontend running on http://localhost:3000
- [ ] DynamoDB tables created
- [ ] S3 buckets configured with CORS
- [ ] Stripe test keys configured
- [ ] Test users created (tenant, landlord, contractor)

## Phase 2A + 3A: Tenant Incident Reporting Flow

### Tenant Can Report Incident

- [ ] Navigate to incident reporting page
- [ ] Fill out incident form with all required fields:
  - [ ] Property selection
  - [ ] Unit selection
  - [ ] Title (e.g., "Leaking faucet")
  - [ ] Description
  - [ ] Category (plumbing, electrical, etc.)
  - [ ] Urgency level (low, medium, high)
- [ ] Submit incident successfully
- [ ] Receive incident ID in response

### Photo Upload

- [ ] Upload at least one photo of the incident
- [ ] Verify photo appears in incident details
- [ ] Upload multiple photos (test multi-upload)
- [ ] Verify all photos are stored in S3
- [ ] Verify photos display correctly with presigned URLs

### Discovery Questions

- [ ] Answer discovery questions:
  - [ ] When did the problem start?
  - [ ] How often does it occur?
  - [ ] Have you attempted any fixes?
- [ ] Submit discovery answers
- [ ] Verify answers saved to DynamoDB
- [ ] Verify incident status updated

### Incident Status Tracking

- [ ] View incident in tenant dashboard
- [ ] Verify incident shows correct status (PENDING, IN_REVIEW, etc.)
- [ ] Verify incident details are complete and accurate
- [ ] Receive notification when status changes

## Phase 2B + 3B: Landlord Job Creation and Bid Management

### Landlord Can View Pending Incidents

- [ ] Log in as landlord
- [ ] Navigate to incidents dashboard
- [ ] See all pending incidents for landlord's properties
- [ ] Filter incidents by status
- [ ] Filter incidents by urgency

### View Incident Details

- [ ] Click on incident to view full details
- [ ] See all incident information:
  - [ ] Title and description
  - [ ] Category and urgency
  - [ ] Tenant information
  - [ ] Property and unit
  - [ ] Photos (all uploaded photos visible)
  - [ ] Discovery answers
  - [ ] Timeline/history

### Create Job from Incident

- [ ] Click "Create Job" from incident details
- [ ] Job form pre-populated with incident info
- [ ] Set budget range (min/max)
- [ ] Set deadline
- [ ] Add job-specific requirements
- [ ] Submit job successfully
- [ ] Verify job created in DynamoDB
- [ ] Verify incident linked to job

### View and Manage Bids

- [ ] Navigate to job details page
- [ ] See "Awaiting Bids" status if no bids yet
- [ ] View list of all submitted bids when available
- [ ] See bid details for each contractor:
  - [ ] Contractor name and rating
  - [ ] Bid amount
  - [ ] Estimated hours
  - [ ] Proposed start date
  - [ ] Contractor's description/pitch
  - [ ] Contractor profile (specialties, experience)

### Award Job

- [ ] Select best bid from list
- [ ] Click "Award Job"
- [ ] Confirm award decision
- [ ] Verify job status changed to AWARDED
- [ ] Verify winning bid status changed to ACCEPTED
- [ ] Verify other bids status changed to REJECTED
- [ ] Verify contractor receives notification

## Phase 2C + 3B: Contractor Work Scheduling and Completion

### Contractor Profile Setup

- [ ] Create contractor profile
- [ ] Add specialties (plumbing, electrical, etc.)
- [ ] Add years of experience
- [ ] Connect Stripe account for payouts
- [ ] Verify profile saved

### View Available Jobs

- [ ] Log in as contractor
- [ ] Navigate to available jobs page
- [ ] See list of open jobs
- [ ] Filter by category/specialty
- [ ] View job details

### Submit Bid

- [ ] Click on job to view details
- [ ] Click "Submit Bid"
- [ ] Fill out bid form:
  - [ ] Bid amount (within budget range)
  - [ ] Estimated hours
  - [ ] Proposed start date
  - [ ] Description/pitch
- [ ] Submit bid successfully
- [ ] Verify bid appears in landlord's bid list
- [ ] Verify bid status is SUBMITTED

### Schedule Awarded Job

- [ ] Receive notification of job award
- [ ] Navigate to awarded jobs
- [ ] Set scheduled date/time
- [ ] Confirm schedule
- [ ] Verify job status changed to SCHEDULED
- [ ] Verify landlord and tenant notified

### Complete Work

- [ ] Mark work as started (optional)
- [ ] Complete the work
- [ ] Upload completion photos to S3
- [ ] Add completion notes:
  - [ ] What was done
  - [ ] Actual hours worked
  - [ ] Any issues encountered
  - [ ] Recommendations
- [ ] Submit completion report
- [ ] Verify job status changed to COMPLETED
- [ ] Verify completion photos visible to landlord

## Phase 2D + 3B: Stripe Payment Processing

### Payment Initiation

- [ ] Log in as landlord
- [ ] Navigate to completed job
- [ ] View completion details and photos
- [ ] Click "Process Payment"
- [ ] Verify payment amount matches bid amount
- [ ] See payment breakdown:
  - [ ] Total amount
  - [ ] Contractor payout (85%)
  - [ ] Platform fee (15%)

### Stripe Payment Form

- [ ] Stripe payment form loads correctly
- [ ] Form shows correct amount
- [ ] Enter test card details:
  - [ ] Card: 4242 4242 4242 4242
  - [ ] Expiry: Any future date
  - [ ] CVC: Any 3 digits
  - [ ] ZIP: Any 5 digits
- [ ] Submit payment

### Payment Processing

- [ ] Payment processes successfully
- [ ] Receive success confirmation
- [ ] Verify PaymentIntent created in Stripe Dashboard
- [ ] Verify payment record created in DynamoDB
- [ ] Verify job status changed to PAID

### Webhook Handling

- [ ] Verify webhook endpoint receives Stripe event
- [ ] Verify webhook signature validated
- [ ] Verify idempotency key prevents duplicate processing
- [ ] Verify payment status updated correctly
- [ ] Test webhook retry (simulate webhook failure)
- [ ] Verify retry handling works correctly

### Contractor Payout

- [ ] Verify contractor receives 85% of payment
- [ ] Verify transfer to contractor's Stripe account
- [ ] Platform retains 15% fee
- [ ] Verify payment history visible to contractor
- [ ] Verify contractor receives payout notification

### Payment Notifications

- [ ] Landlord receives payment confirmation
- [ ] Contractor receives payment notification
- [ ] Tenant receives job completion notification
- [ ] All notifications include relevant details

## Edge Cases and Error Handling

### Photo Upload Failures

- [ ] Test upload with invalid file type
- [ ] Test upload with file too large (>10MB)
- [ ] Test S3 connection failure
- [ ] Verify error messages are user-friendly
- [ ] Verify partial upload recovery

### Stripe Payment Failures

- [ ] Test with declined card (4000 0000 0000 0002)
- [ ] Test with insufficient funds card (4000 0000 0000 9995)
- [ ] Test with expired card
- [ ] Verify error handling and user messaging
- [ ] Verify failed payment doesn't change job status

### Webhook Failures

- [ ] Test invalid webhook signature
- [ ] Test duplicate webhook events (idempotency)
- [ ] Test webhook timeout
- [ ] Test malformed webhook payload
- [ ] Verify all failures logged properly

### Concurrent Operations

- [ ] Test two contractors bidding simultaneously
- [ ] Test job awarded while new bid being submitted
- [ ] Test concurrent photo uploads
- [ ] Verify race conditions handled correctly

### Invalid Status Transitions

- [ ] Try to award job that's already awarded
- [ ] Try to complete job that's not awarded
- [ ] Try to pay for incomplete job
- [ ] Verify all invalid transitions rejected with proper errors

## Performance and Scalability

- [ ] Test with 10+ photos on single incident
- [ ] Test with 20+ bids on single job
- [ ] Monitor API response times (< 500ms for most endpoints)
- [ ] Monitor photo upload/download times
- [ ] Verify pagination works on all list endpoints

## Security

- [ ] Verify JWT authentication required for all endpoints
- [ ] Verify users can only access their own data
- [ ] Test CORS headers configured correctly
- [ ] Test S3 presigned URLs expire correctly
- [ ] Verify Stripe webhook signature validation
- [ ] Test SQL injection attempts (should be prevented by DynamoDB)
- [ ] Test XSS attempts in form inputs

## Integration Points

### Frontend ↔ Backend

- [ ] All API calls use correct endpoints
- [ ] Authentication headers sent correctly
- [ ] Error responses handled properly
- [ ] Loading states work correctly
- [ ] Success messages displayed

### Backend ↔ DynamoDB

- [ ] All tables accessible
- [ ] GSIs working correctly
- [ ] Queries returning expected results
- [ ] Updates atomic and consistent

### Backend ↔ S3

- [ ] Photos uploaded successfully
- [ ] Presigned URLs generated correctly
- [ ] CORS allows frontend uploads
- [ ] Bucket policies configured correctly

### Backend ↔ Stripe

- [ ] API keys valid
- [ ] PaymentIntents created successfully
- [ ] Webhooks received and processed
- [ ] Transfers to contractors working

## Deployment Verification

- [ ] Docker containers build successfully
- [ ] Docker Compose stack starts correctly
- [ ] Environment variables loaded properly
- [ ] Health checks pass for all services
- [ ] CI/CD pipeline runs successfully
- [ ] Production deployment successful

## Documentation

- [ ] API documentation up to date
- [ ] Frontend component documentation complete
- [ ] Deployment instructions accurate
- [ ] Environment setup guide complete
- [ ] Troubleshooting guide helpful

## Final Acceptance

- [ ] Complete workflow tested end-to-end
- [ ] All critical bugs fixed
- [ ] Performance acceptable
- [ ] Security review completed
- [ ] Ready for production deployment

---

## Test Results

**Date:** _________________

**Tested by:** _________________

**Overall Status:** ☐ PASS | ☐ FAIL

**Notes:**

```
[Add any notes, issues found, or recommendations here]
```

**Sign-off:**

- Backend: ☐ Approved by _________________
- Frontend: ☐ Approved by _________________
- DevOps: ☐ Approved by _________________
- Product: ☐ Approved by _________________
