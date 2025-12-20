# Quick Testing Guide for Contractor Onboarding

## Step 1: Create the DynamoDB Table (REQUIRED - Do this first!)

```bash
python scripts/create_magic_links_table.py
```

This creates the `landten-magic-links` table in DynamoDB.

## Step 2: Run the Test Suite

```bash
python scripts/test_contractor_onboarding.py
```

## What to Expect

### ✓ Test 1: Create Magic Link
- Should PASS
- Creates a magic link token in DynamoDB
- Returns a URL you can use for testing

### ✓ Test 2: Verify Magic Link
- Should PASS (after creating the table)
- Verifies the token exists and is valid

### ⚠️ Test 3: Register Contractor
- Will SKIP - Requires Firebase authentication
- Use the frontend form to test this instead

### ✓ Test 4: Get Dashboard Data
- Will work once you have a real contractor ID
- Or skip if registration wasn't tested

## Manual Frontend Testing

The test script gives you a magic link URL. Copy it and:

1. **For Production:** Replace `http://localhost:3000` with `https://land-ten-mvp-3-0.vercel.app`
2. **Open in Browser:** You'll see the onboarding page
3. **Fill the Form:** For new contractors
4. **See Dashboard:** For existing contractors

## Quick cURL Test (No Table Required)

### Test Magic Link Creation:
```bash
curl -X POST https://landtenmvp3-55ce0053f28a.herokuapp.com/api/v1/magic-links/create \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "job_id": "job_123",
    "landlord_id": "ll_456",
    "property_id": "prop_789",
    "tenant_id": "ten_012"
  }'
```

### Test Token Verification:
```bash
# Use the token from the create response
curl -X POST https://landtenmvp3-55ce0053f28a.herokuapp.com/api/v1/magic-links/verify \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_TOKEN_HERE"}'
```

## Troubleshooting

### "Invalid or expired token"
- ✅ Run `python scripts/create_magic_links_table.py` first
- ✅ Make sure you're using the token from the create response
- ✅ Check that the token hasn't expired (48 hours)

### "Table not found"
- ✅ Run `python scripts/create_magic_links_table.py`

### URLs are wrong in test output
- ✅ Set environment variables:
  ```bash
  export BACKEND_URL=https://landtenmvp3-55ce0053f28a.herokuapp.com
  export FRONTEND_URL=https://land-ten-mvp-3-0.vercel.app
  ```

## Success Criteria

✅ Can create magic link
✅ Can verify token
✅ Can open magic link in browser
✅ Frontend shows registration form or dashboard
✅ Registration works (test via frontend)
