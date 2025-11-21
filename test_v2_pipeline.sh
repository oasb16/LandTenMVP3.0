#!/bin/bash
# End-to-End V2 Pipeline Test
# Tests the complete flow: incident → discovery → job → bids → approval

echo "========================================="
echo "AI Reasoning V2 - End-to-End Pipeline Test"
echo "========================================="
echo ""

BASE_URL="${BASE_URL:-http://localhost:8000}"
WEBHOOK_URL="$BASE_URL/api/ai/stream-webhook"

echo "Testing against: $WEBHOOK_URL"
echo ""

# Test 1: Report incident
echo "📋 Test 1: Report Incident"
echo "  Message: 'My garage door is broken'"
echo ""

RESPONSE1=$(curl -s -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message.new",
    "message": {
      "text": "My garage door is broken",
      "user": {"id": "test-user-1", "is_bot": false}
    },
    "channel_id": "test-channel-1",
    "user": {"id": "test-user-1", "is_bot": false}
  }')

echo "Response 1:"
echo "$RESPONSE1" | jq -r '.status, .intent' 2>/dev/null || echo "$RESPONSE1"
echo ""

# Wait between requests
sleep 2

# Test 2: Answer discovery question with "yes"
echo "📋 Test 2: Discovery Response"
echo "  Message: 'yes'"
echo ""

RESPONSE2=$(curl -s -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message.new",
    "message": {
      "text": "yes",
      "user": {"id": "test-user-1", "is_bot": false}
    },
    "channel_id": "test-channel-1",
    "user": {"id": "test-user-1", "is_bot": false}
  }')

echo "Response 2:"
echo "$RESPONSE2" | jq -r '.status, .intent' 2>/dev/null || echo "$RESPONSE2"
echo ""

# Wait between requests
sleep 2

# Test 3: Request job creation
echo "📋 Test 3: Job Request"
echo "  Message: 'Create a work order'"
echo ""

RESPONSE3=$(curl -s -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message.new",
    "message": {
      "text": "Create a work order",
      "user": {"id": "test-user-1", "is_bot": false}
    },
    "channel_id": "test-channel-1",
    "user": {"id": "test-user-1", "is_bot": false}
  }')

echo "Response 3:"
echo "$RESPONSE3" | jq -r '.status, .intent' 2>/dev/null || echo "$RESPONSE3"
echo ""

echo "========================================="
echo "Test Complete"
echo "========================================="
echo ""
echo "Check backend logs for:"
echo "  [ai-reasoning-v2] START V2 PIPELINE"
echo "  [ai-reasoning-v2] Final Intent: ..."
echo "  [flow-engine] Intent '...' → Stage '...'"
echo ""
echo "You should NOT see:"
echo "  [ai-reasoning] (old V1 logs)"
echo ""
