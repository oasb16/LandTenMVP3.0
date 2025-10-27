# Stream Integration Test Plan

**Last Updated:** October 27, 2025

## Overview

This document provides a complete curl-based test plan for verifying the Stream Chat + FastAPI + DynamoDB integration in LandTenMVP3.0.

---

## Prerequisites

1. **Backend running:**
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn app.main:app --reload
   ```

2. **Environment variables configured:**
   - `STREAM_CHAT_API_KEY`
   - `STREAM_CHAT_API_SECRET`
   - `STREAM_WEBHOOK_SECRET`
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_REGION=us-east-1`

3. **DynamoDB tables created:**
   - `landten_incidents`
   - `landten_jobs`
   - `landten_job_bids`
   - `landten_property`
   - `landten_users`

---

## Test 1: Bot Status Check

**Purpose:** Verify AI bot system is running and configured

**Command:**
```bash
curl -X GET http://localhost:8000/ai/bot-status \
  -H "Content-Type: application/json" \
  | jq
```

**Expected Response:**
```json
{
  "status": "active",
  "service": "PropertyAI Bot System",
  "version": "1.0",
  "bots": {
    "tenant": {
      "id": "ai-tenant-bot",
      "name": "PropertyHelper",
      "description": "AI assistant for tenants - helps troubleshoot issues and report incidents"
    },
    "landlord": {
      "id": "ai-landlord-bot",
      "name": "PropertyManager",
      "description": "AI assistant for landlords - automates property management tasks"
    },
    "contractor": {
      "id": "ai-contractor-bot",
      "name": "JobAssistant",
      "description": "AI assistant for contractors - manages jobs, bids, and payments"
    }
  },
  "configuration": {
    "webhook_secret_configured": true,
    "stream_api_key_configured": true,
    "stream_api_secret_configured": true
  },
  "personas_available": ["tenant", "landlord", "contractor"]
}
```

**Log Output to Check:**
```
[ai-webhook] Checking bot status...
[ai-webhook] Bot status check completed successfully
```

**✅ Success Criteria:**
- Status code: 200
- `status: "active"`
- All three bot personas listed
- All configuration flags are `true`

---

## Test 2: Initialize AI Channel

**Purpose:** Add AI bot to a Stream Chat channel

**Command:**
```bash
curl -X POST http://localhost:8000/ai/init-channel \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "test-channel-tenant-001",
    "persona": "tenant"
  }' \
  | jq
```

**Expected Response:**
```json
{
  "status": "success",
  "channel_id": "test-channel-tenant-001",
  "bot_id": "ai-tenant-bot",
  "persona": "tenant",
  "message": "AI bot initialized for tenant persona"
}
```

**Log Output to Check:**
```
[ai-webhook] Initializing AI channel:
[ai-webhook]   - Channel ID: test-channel-tenant-001
[ai-webhook]   - Persona: tenant
[stream-bot] Created/updated bot: PropertyHelper (ai-tenant-bot)
[ai-webhook] SUCCESS: Added bot ai-tenant-bot to channel test-channel-tenant-001
```

**✅ Success Criteria:**
- Status code: 200
- `status: "success"`
- Bot added to channel
- Welcome message appears in Stream Chat

**Test Variations:**

**2a. Landlord persona:**
```bash
curl -X POST http://localhost:8000/ai/init-channel \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "test-channel-landlord-001",
    "persona": "landlord"
  }' \
  | jq
```

**2b. Contractor persona:**
```bash
curl -X POST http://localhost:8000/ai/init-channel \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "test-channel-contractor-001",
    "persona": "contractor"
  }' \
  | jq
```

**2c. Invalid persona (should fail):**
```bash
curl -X POST http://localhost:8000/ai/init-channel \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "test-channel-invalid",
    "persona": "invalid"
  }' \
  | jq
```

**Expected Error:**
```json
{
  "detail": {
    "error": "Invalid persona: invalid",
    "hint": "Must be one of: tenant, landlord, contractor"
  }
}
```

---

## Test 3: Send Action Message

**Purpose:** Send AI message with interactive action buttons

**Command:**
```bash
curl -X POST http://localhost:8000/ai/send-action \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "test-channel-tenant-001",
    "persona": "tenant",
    "text": "I detected a potential plumbing issue. Would you like to start the discovery process?",
    "actions": [
      {
        "name": "start_discovery",
        "text": "Start Discovery",
        "value": "action:start_discovery:INC-001",
        "style": "primary"
      },
      {
        "name": "dismiss",
        "text": "Dismiss",
        "value": "action:dismiss:INC-001",
        "style": "default"
      }
    ]
  }' \
  | jq
```

**Expected Response:**
```json
{
  "status": "success",
  "message": {
    "id": "message-id-here",
    "type": "ai-message",
    "text": "I detected a potential plumbing issue..."
  },
  "channel_id": "test-channel-tenant-001",
  "action_count": 2
}
```

**Log Output to Check:**
```
[ai-webhook] Sending action message:
[ai-webhook]   - Channel: test-channel-tenant-001
[ai-webhook]   - Persona: tenant
[ai-webhook]   - Text: I detected a potential plumbing issue...
[ai-webhook]   - Actions: 2 buttons
[ai-webhook] SUCCESS: Action message sent to channel test-channel-tenant-001
```

**✅ Success Criteria:**
- Status code: 200
- Message appears in Stream Chat with 2 buttons
- Buttons are clickable
- Message has AI styling (blue gradient bubble)

---

## Test 4: Webhook - Health Check

**Purpose:** Verify webhook endpoint responds to Stream health checks

**Command:**
```bash
curl -X POST http://localhost:8000/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "health.check"
  }' \
  | jq
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "ai-webhook",
  "version": "1.0"
}
```

**Log Output to Check:**
```
[ai-webhook] ========== Incoming webhook request ==========
[ai-webhook] Received XXX bytes of payload
[ai-webhook] Event type: health.check
[ai-webhook] Health check received - responding healthy
```

**✅ Success Criteria:**
- Status code: 200
- `status: "healthy"`

---

## Test 5: Webhook - Message.new (Incident Detection)

**Purpose:** Simulate user sending a message that triggers incident detection

**Command:**
```bash
curl -X POST http://localhost:8000/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message.new",
    "channel_id": "test-channel-tenant-001",
    "user": {
      "id": "user-123",
      "name": "Test User",
      "is_bot": false,
      "persona": "tenant"
    },
    "message": {
      "id": "msg-001",
      "text": "My kitchen sink is leaking water everywhere",
      "type": "regular",
      "attachments": []
    }
  }' \
  | jq
```

**Expected Response:**
```json
{
  "status": "processed",
  "message_sent": true,
  "channel_id": "test-channel-tenant-001",
  "user_id": "user-123"
}
```

**Log Output to Check:**
```
[ai-webhook] ========== Incoming webhook request ==========
[ai-webhook] Event type: message.new
[ai-webhook] Routing to handle_new_message()
[ai-webhook] Processing message.new event:
[ai-webhook]   - Channel: test-channel-tenant-001
[ai-webhook]   - User: user-123 (Test User)
[ai-webhook]   - Message: My kitchen sink is leaking water everywhere
[ai-webhook]   - Is bot: False
[PropertyAIBot] Creating incident: INC-XXXXXXXXXX
[PropertyAIBot] Incident persisted to DynamoDB: INC-XXXXXXXXXX
[ai-webhook] SUCCESS: AI bot responded to message in channel test-channel-tenant-001
```

**DynamoDB Verification:**
```bash
# Check landten_incidents table for new record
aws dynamodb scan --table-name landten_incidents --region us-east-1 \
  --filter-expression "contains(description, :text)" \
  --expression-attribute-values '{":text":{"S":"kitchen sink is leaking"}}' \
  | jq
```

**✅ Success Criteria:**
- Status code: 200
- `status: "processed"`
- Incident card appears in Stream Chat
- Incident record created in DynamoDB
- Card has "Start Discovery" and "Dismiss" buttons

---

## Test 6: Webhook - Action Click (Start Discovery)

**Purpose:** Simulate user clicking "Start Discovery" button

**Command:**
```bash
curl -X POST http://localhost:8000/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message.new",
    "channel_id": "test-channel-tenant-001",
    "user": {
      "id": "user-123",
      "name": "Test User",
      "is_bot": false,
      "persona": "tenant"
    },
    "message": {
      "id": "msg-002",
      "text": "action:start_discovery:INC-001",
      "type": "regular"
    }
  }' \
  | jq
```

**Expected Response:**
```json
{
  "status": "processed",
  "message_sent": true,
  "channel_id": "test-channel-tenant-001",
  "user_id": "user-123"
}
```

**Log Output to Check:**
```
[ai-webhook] Event type: message.new
[stream-bot] Handling action: start_discovery with params: ['INC-001']
[PropertyAIBot] Discovery card sent with first question
```

**✅ Success Criteria:**
- Discovery card appears in chat
- AI asks first question about location
- Progress indicator shows 0/4 questions

---

## Test 7: Webhook - Create Work Order

**Purpose:** Test job creation and DynamoDB persistence

**Command:**
```bash
curl -X POST http://localhost:8000/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message.new",
    "channel_id": "test-channel-landlord-001",
    "user": {
      "id": "landlord-456",
      "name": "Property Owner",
      "is_bot": false,
      "persona": "landlord"
    },
    "message": {
      "id": "msg-003",
      "text": "action:create_work_order:INC-001",
      "type": "regular"
    }
  }' \
  | jq
```

**Expected Response:**
```json
{
  "status": "processed",
  "message_sent": true,
  "channel_id": "test-channel-landlord-001",
  "user_id": "landlord-456"
}
```

**Log Output to Check:**
```
[stream-bot] Handling action: create_work_order with params: ['INC-001']
[PropertyAIBot] Creating work order - incident: INC-001, job: JOB-XXXXXXXXXX
[PropertyAIBot] Job persisted to DynamoDB: JOB-XXXXXXXXXX
[PropertyAIBot] Updated incident INC-001 status to work_order
```

**DynamoDB Verification:**
```bash
# Check landten_jobs table
aws dynamodb scan --table-name landten_jobs --region us-east-1 \
  --filter-expression "incident_id = :iid" \
  --expression-attribute-values '{":iid":{"S":"INC-001"}}' \
  | jq

# Check incident status updated
aws dynamodb get-item --table-name landten_incidents --region us-east-1 \
  --key '{"incident_id":{"S":"INC-001"}}' \
  | jq '.Item.status.S'  # Should be "work_order"
```

**✅ Success Criteria:**
- Work order card appears in chat
- Job record created in landten_jobs table
- Incident status updated to "work_order"
- Job has correct incident_id linkage

---

## Test 8: View Contractor Bids

**Purpose:** Test bid generation and DynamoDB persistence

**Command:**
```bash
curl -X POST http://localhost:8000/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message.new",
    "channel_id": "test-channel-landlord-001",
    "user": {
      "id": "landlord-456",
      "name": "Property Owner",
      "is_bot": false,
      "persona": "landlord"
    },
    "message": {
      "id": "msg-004",
      "text": "action:view_bids:INC-001:JOB-001",
      "type": "regular"
    }
  }' \
  | jq
```

**Log Output to Check:**
```
[stream-bot] Handling action: view_bids with params: ['INC-001', 'JOB-001']
[PropertyAIBot] Viewing bids for job: JOB-001
[PropertyAIBot] Bid persisted to DynamoDB: BID-XXXXXXXXXX-0 from Contractor Name
[PropertyAIBot] Bid persisted to DynamoDB: BID-XXXXXXXXXX-1 from Contractor Name
[PropertyAIBot] Bid persisted to DynamoDB: BID-XXXXXXXXXX-2 from Contractor Name
```

**DynamoDB Verification:**
```bash
# Check landten_job_bids table
aws dynamodb scan --table-name landten_job_bids --region us-east-1 \
  --filter-expression "job_id = :jid" \
  --expression-attribute-values '{":jid":{"S":"JOB-001"}}' \
  | jq
```

**✅ Success Criteria:**
- Bids card appears with 3 contractors
- Each bid has quote, ETA, rating, distance
- Recommended bid highlighted
- 3 bid records created in landten_job_bids table

---

## Test 9: Approve Contractor

**Purpose:** Test contractor hiring and job update

**Command:**
```bash
curl -X POST http://localhost:8000/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message.new",
    "channel_id": "test-channel-landlord-001",
    "user": {
      "id": "landlord-456",
      "name": "Property Owner",
      "is_bot": false,
      "persona": "landlord"
    },
    "message": {
      "id": "msg-005",
      "text": "action:approve_contractor:JOB-001:Joe Plumbing:175:INC-001",
      "type": "regular"
    }
  }' \
  | jq
```

**Log Output to Check:**
```
[stream-bot] Handling action: approve_contractor with params: ['JOB-001', 'Joe Plumbing', '175', 'INC-001']
[PropertyAIBot] Approving contractor Joe Plumbing for job: JOB-001
[PropertyAIBot] Job JOB-001 updated with contractor Joe Plumbing
[PropertyAIBot] Updated incident INC-001 status to scheduled
```

**DynamoDB Verification:**
```bash
# Check job updated with contractor
aws dynamodb get-item --table-name landten_jobs --region us-east-1 \
  --key '{"job_id":{"S":"JOB-001"}}' \
  | jq '.Item | {contractor_id, final_cost, status, scheduled_date}'

# Check incident status
aws dynamodb get-item --table-name landten_incidents --region us-east-1 \
  --key '{"incident_id":{"S":"INC-001"}}' \
  | jq '.Item.status.S'  # Should be "scheduled"
```

**✅ Success Criteria:**
- Approval card appears in chat
- Job record updated with contractor_id and final_cost
- Job status changed to "approved"
- Incident status changed to "scheduled"
- Scheduled date populated

---

## Test 10: Webhook Signature Verification

**Purpose:** Verify webhook rejects invalid signatures

**10a. Valid Signature (if STREAM_WEBHOOK_SECRET is set):**
```bash
# Calculate HMAC SHA256 signature
PAYLOAD='{"type":"health.check"}'
SECRET="your-webhook-secret"
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/^.* //')

curl -X POST http://localhost:8000/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -H "x-signature: $SIGNATURE" \
  -d "$PAYLOAD" \
  | jq
```

**Expected:** Status 200, webhook processed

**10b. Invalid Signature:**
```bash
curl -X POST http://localhost:8000/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -H "x-signature: invalid-signature-12345" \
  -d '{"type":"health.check"}' \
  | jq
```

**Expected Response:**
```json
{
  "detail": {
    "error": "Invalid webhook signature",
    "hint": "Check STREAM_WEBHOOK_SECRET configuration"
  }
}
```

**Log Output:**
```
[ai-webhook] ERROR: Invalid webhook signature - expected: abcd1234..., got: invalid-...
[ai-webhook] ERROR: Webhook signature verification FAILED
```

**✅ Success Criteria:**
- Status code: 401
- Request rejected with clear error message

---

## Test 11: End-to-End Workflow

**Purpose:** Complete incident → job → bids → approval flow

**Steps:**

1. **Initialize channel:**
   ```bash
   curl -X POST http://localhost:8000/ai/init-channel \
     -H "Content-Type: application/json" \
     -d '{"channel_id": "e2e-test-001", "persona": "tenant"}' | jq
   ```

2. **User reports issue:**
   ```bash
   curl -X POST http://localhost:8000/ai/stream-webhook \
     -H "Content-Type: application/json" \
     -d '{
       "type": "message.new",
       "channel_id": "e2e-test-001",
       "user": {"id": "tenant-789", "name": "Jane Doe", "is_bot": false, "persona": "tenant"},
       "message": {"id": "e2e-msg-1", "text": "My bathroom sink is broken"}
     }' | jq
   ```
   - **Check:** Incident card appears
   - **Check:** DynamoDB has incident record

3. **User starts discovery:**
   ```bash
   curl -X POST http://localhost:8000/ai/stream-webhook \
     -H "Content-Type: application/json" \
     -d '{
       "type": "message.new",
       "channel_id": "e2e-test-001",
       "user": {"id": "tenant-789", "name": "Jane Doe", "is_bot": false},
       "message": {"id": "e2e-msg-2", "text": "action:start_discovery:INC-XXXXXX"}
     }' | jq
   ```
   - **Check:** Discovery card appears

4. **Create work order:**
   ```bash
   curl -X POST http://localhost:8000/ai/stream-webhook \
     -H "Content-Type: application/json" \
     -d '{
       "type": "message.new",
       "channel_id": "e2e-test-001",
       "user": {"id": "landlord-456", "name": "Owner", "is_bot": false, "persona": "landlord"},
       "message": {"id": "e2e-msg-3", "text": "action:create_work_order:INC-XXXXXX"}
     }' | jq
   ```
   - **Check:** Work order card appears
   - **Check:** DynamoDB has job record
   - **Check:** Incident status = "work_order"

5. **View bids:**
   ```bash
   curl -X POST http://localhost:8000/ai/stream-webhook \
     -H "Content-Type: application/json" \
     -d '{
       "type": "message.new",
       "channel_id": "e2e-test-001",
       "user": {"id": "landlord-456", "name": "Owner", "is_bot": false},
       "message": {"id": "e2e-msg-4", "text": "action:view_bids:INC-XXXXXX:JOB-YYYYYY"}
     }' | jq
   ```
   - **Check:** Bids card appears with 3 contractors
   - **Check:** DynamoDB has 3 bid records

6. **Approve contractor:**
   ```bash
   curl -X POST http://localhost:8000/ai/stream-webhook \
     -H "Content-Type: application/json" \
     -d '{
       "type": "message.new",
       "channel_id": "e2e-test-001",
       "user": {"id": "landlord-456", "name": "Owner", "is_bot": false},
       "message": {"id": "e2e-msg-5", "text": "action:approve_contractor:JOB-YYYYYY:Contractor:175:INC-XXXXXX"}
     }' | jq
   ```
   - **Check:** Approval card appears
   - **Check:** Job updated with contractor_id
   - **Check:** Incident status = "scheduled"

**Final DynamoDB State Check:**
```bash
# Incident should be scheduled
aws dynamodb get-item --table-name landten_incidents --key '{"incident_id":{"S":"INC-XXXXXX"}}'

# Job should be approved with contractor
aws dynamodb get-item --table-name landten_jobs --key '{"job_id":{"S":"JOB-YYYYYY"}}'

# Should have 3 bids
aws dynamodb scan --table-name landten_job_bids \
  --filter-expression "job_id = :jid" \
  --expression-attribute-values '{":jid":{"S":"JOB-YYYYYY"}}'
```

**✅ Success Criteria:**
- Complete flow executes without errors
- All cards render correctly
- All DynamoDB records created with correct linkages
- Statuses updated correctly at each stage

---

## Troubleshooting

### Issue: Webhook returns 401 "Invalid signature"

**Solution:**
1. Verify `STREAM_WEBHOOK_SECRET` environment variable is set
2. For local testing, set `AUTH_DISABLED=true` to skip verification
3. Check signature calculation matches Stream's format (HMAC SHA256)

### Issue: Bot doesn't respond to messages

**Check:**
1. Bot status endpoint: `curl http://localhost:8000/ai/bot-status`
2. Stream Chat API credentials configured
3. Bot is member of channel
4. User message not from bot itself (`is_bot: false`)

### Issue: Cards don't appear in frontend

**Check:**
1. Attachment `type` field matches MessageCards.tsx expectations
2. CustomMessageUI is being used in StreamChatPane
3. Browser console for React errors
4. Network tab shows attachment data in Stream API response

### Issue: DynamoDB errors

**Check:**
1. AWS credentials configured correctly
2. Tables exist in us-east-1 region
3. IAM permissions allow PutItem/GetItem/UpdateItem/Scan
4. Backend logs show specific DynamoDB error

---

## Success Checklist

After running all tests, verify:

- [ ] All 11 tests pass with expected responses
- [ ] Backend logs show structured logging with prefixes
- [ ] DynamoDB tables populated correctly
- [ ] No uncaught exceptions in logs
- [ ] Webhook signature verification works
- [ ] All three personas (tenant/landlord/contractor) functional
- [ ] Complete E2E workflow executes successfully
- [ ] Error messages are helpful and include hints
- [ ] All JSON responses are valid and documented

---

## Next Steps

After tests pass:

1. Test with real Stream Chat frontend (not just curl)
2. Verify UI rendering of all card types
3. Test button interactions from browser
4. Add more sophisticated test data
5. Implement automated integration tests
6. Set up CI/CD pipeline

---

**Document Status:** Ready for testing
**Last Verified:** Pending initial run
**Owner:** Claude Code / PropertyAI Team
