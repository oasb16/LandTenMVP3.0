# Contractor Onboarding Testing Guide

Complete guide to testing the magic link contractor onboarding flow.

## Quick Start

### 1. Create DynamoDB Table (One-Time Setup)

```bash
cd /home/user/LandTenMVP3.0
python scripts/create_magic_links_table.py
```

### 2. Run Automated Tests

```bash
python scripts/test_contractor_onboarding.py
```

This will test the entire flow and give you a magic link URL to test in the browser.

---

## Manual Testing with cURL

### Step 1: Create a Magic Link

```bash
curl -X POST https://landtenmvp3-55ce0053f28a.herokuapp.com/api/v1/magic-links/create \
  -H "Content-Type: application/json" \
  -d '{
    "email": "contractor@example.com",
    "job_id": "job_123",
    "landlord_id": "landlord_456",
    "property_id": "prop_789",
    "tenant_id": "tenant_012"
  }'
```

**Expected Response:**
```json
{
  "token": "abc123...",
  "magic_link_url": "https://land-ten-mvp-3-0.vercel.app/contractor-onboarding?token=abc123...",
  "email": "contractor@example.com",
  "job_id": "job_123",
  "expires_at": "2025-12-22T01:00:00Z"
}
```

### Step 2: Verify the Magic Link

```bash
curl -X POST https://landtenmvp3-55ce0053f28a.herokuapp.com/api/v1/magic-links/verify \
  -H "Content-Type: application/json" \
  -d '{
    "token": "YOUR_TOKEN_HERE"
  }'
```

**Expected Response (New Contractor):**
```json
{
  "valid": true,
  "email": "contractor@example.com",
  "job_id": "job_123",
  "landlord_id": "landlord_456",
  "property_id": "prop_789",
  "tenant_id": "tenant_012",
  "contractor_id": null,
  "message": "Please complete your contractor registration"
}
```

**Expected Response (Existing Contractor):**
```json
{
  "valid": true,
  "email": "contractor@example.com",
  "job_id": "job_123",
  "landlord_id": "landlord_456",
  "property_id": "prop_789",
  "tenant_id": "tenant_012",
  "contractor_id": "cont_abc123",
  "message": "Welcome back! Redirecting to your dashboard..."
}
```

### Step 3: Test Frontend Flow

1. Copy the `magic_link_url` from Step 1
2. Open it in a browser
3. **If new contractor**: You'll see the registration form
4. **If existing contractor**: You'll see the dashboard

---

## Browser Testing Flow

### For New Contractors:

1. **Click Magic Link** → Opens `/contractor-onboarding?token=...`
2. **See Registration Form** with fields:
   - Business Name
   - Email (pre-filled, disabled)
   - Phone Number
   - Service Categories
   - Service ZIP Codes
   - License Number (optional)
3. **Submit Form** → Creates contractor account
4. **Redirected to Dashboard** showing:
   - Profile information
   - Jobs overview (available, active, completed)
   - Payment summary
   - Stats cards

### For Existing Contractors:

1. **Click Magic Link** → Opens `/contractor-onboarding?token=...`
2. **Immediately see Dashboard** with:
   - Welcome message with business name
   - Profile section
   - Jobs assigned to this contractor
   - Available jobs to bid on
   - Payment summary
   - Quick action buttons

---

## API Endpoints Reference

### Create Magic Link
```
POST /api/v1/magic-links/create
```
**Body:**
```json
{
  "email": "string",
  "job_id": "string",
  "landlord_id": "string",
  "property_id": "string",
  "tenant_id": "string"
}
```

### Verify Magic Link
```
POST /api/v1/magic-links/verify
```
**Body:**
```json
{
  "token": "string"
}
```

### Mark Magic Link as Used
```
POST /api/v1/magic-links/mark-used/{token}?contractor_id=cont_123
```

### Get Dashboard Data
```
GET /api/v1/magic-links/onboarding-dashboard/{contractor_id}
```

**Response:**
```json
{
  "contractor": { ... },
  "jobs": {
    "available": [...],
    "active": [...],
    "completed": [...],
    "total_available": 0,
    "total_active": 0,
    "total_completed": 0
  },
  "bids": {
    "submitted": [...],
    "total": 0
  },
  "payments": {
    "total_earnings": 0.0,
    "pending": 0.0,
    "completed": 0.0
  }
}
```

---

## Testing Scenarios

### Scenario 1: First-Time Contractor

1. Create magic link for `newcontractor@example.com`
2. Open link in browser
3. Fill out registration form:
   - Business: "ABC Plumbing"
   - Phone: "(555) 123-4567"
   - Categories: "plumbing, hvac"
   - ZIP Codes: "10001, 10002"
4. Submit → Should see dashboard with 0 jobs/payments

### Scenario 2: Returning Contractor

1. Create magic link for existing contractor email
2. Open link in browser
3. Should immediately see dashboard with:
   - Existing profile info
   - Active/completed jobs
   - Payment history

### Scenario 3: Expired Token

1. Create magic link
2. Wait 48+ hours (or manually set expiry in DB)
3. Try to verify → Should get "Invalid or expired token"

### Scenario 4: Invalid Token

1. Try to verify with random token
2. Should get "Invalid or expired token"

---

## Troubleshooting

### "No module named 'app'" Error
**Fix:** Imports should use relative paths (`from ..models` not `from app.models`)

### "You must specify a region" Error
**Fix:** Ensure `AWS_REGION` environment variable is set in Heroku

### "Table not found" Error
**Fix:** Run `python scripts/create_magic_links_table.py`

### Frontend build fails with "useSearchParams" error
**Fix:** Ensure `useSearchParams()` is wrapped in `<Suspense>` boundary

### 401 Unauthorized on contractor registration
**Fix:** May need to temporarily disable auth for testing or pass valid Firebase token

---

## Environment Variables Needed

### Backend (Heroku)
```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
TABLE_PREFIX=landten
FRONTEND_URL=https://land-ten-mvp-3-0.vercel.app
```

### Frontend (Vercel)
```
NEXT_PUBLIC_BACKEND_URL=https://landtenmvp3-55ce0053f28a.herokuapp.com/api/v1
```

---

## Integration with Existing Flow

To integrate magic link creation into your landlord workflow:

```typescript
// In landlord's "Invite Contractor" flow
async function inviteContractor(email: string, jobId: string) {
  const response = await fetch(`${BACKEND_URL}/magic-links/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      job_id: jobId,
      landlord_id: currentUser.landlord_id,
      property_id: job.property_id,
      tenant_id: job.tenant_id,
    }),
  });

  const { magic_link_url } = await response.json();

  // Send email with magic_link_url
  await sendEmail({
    to: email,
    subject: 'You\'re invited to a new job on LandTen',
    html: `Click here to view and accept the job: ${magic_link_url}`,
  });
}
```

---

## Success Criteria

✅ Magic link created successfully
✅ Token verifies correctly
✅ New contractor can register
✅ Existing contractor sees dashboard
✅ Dashboard shows profile, jobs, payments
✅ Token marked as used after registration
✅ Expired/invalid tokens rejected
✅ Frontend handles all edge cases (loading, errors)

---

## Next Steps

1. **Email Integration**: Add email service to send magic links
2. **Token Cleanup**: Add cron job to delete expired tokens
3. **Analytics**: Track magic link usage and conversion rates
4. **Security**: Add rate limiting to prevent abuse
5. **Notifications**: Notify landlord when contractor accepts invitation
