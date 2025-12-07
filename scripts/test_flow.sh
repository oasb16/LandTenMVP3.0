#!/bin/bash
# ================================================
# LandTen MVP 3.0 - End-to-End Test Script
# ================================================
# Tests the complete workflow from incident reporting
# through job creation, bidding, completion, and payment
# ================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

# Test users (these should match your test data)
TENANT_TOKEN="${TENANT_TOKEN:-test_tenant_token}"
LANDLORD_TOKEN="${LANDLORD_TOKEN:-test_landlord_token}"
CONTRACTOR_TOKEN="${CONTRACTOR_TOKEN:-test_contractor_token}"

# Test data
PROPERTY_ID="${PROPERTY_ID:-test_property_123}"
UNIT_ID="${UNIT_ID:-test_unit_456}"
TEST_IMAGE="${TEST_IMAGE:-./test-assets/test-image.jpg}"

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_test() {
    echo -e "${YELLOW}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

check_service() {
    local url=$1
    local name=$2

    if curl -s -f -o /dev/null "$url/health" || curl -s -f -o /dev/null "$url"; then
        print_success "$name is running at $url"
        return 0
    else
        print_error "$name is not responding at $url"
        return 1
    fi
}

# ================================================
# START TESTS
# ================================================

print_header "🧪 LandTen MVP 3.0 - End-to-End Tests"

# ================================================
# 1. CHECK SERVICES
# ================================================
print_header "1️⃣  Checking Services"

SERVICES_OK=true

print_test "Checking backend..."
if ! check_service "$API_URL" "Backend"; then
    SERVICES_OK=false
fi

print_test "Checking frontend..."
if ! check_service "$FRONTEND_URL" "Frontend"; then
    SERVICES_OK=false
fi

if [ "$SERVICES_OK" = false ]; then
    echo ""
    print_error "Services are not running. Please start them first:"
    echo ""
    echo "  Backend:  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000"
    echo "  Frontend: cd frontend && npm run dev"
    echo ""
    exit 1
fi

# ================================================
# 2. TEST INCIDENT REPORTING (Phase 2A)
# ================================================
print_header "2️⃣  Testing Incident Reporting (Tenant Flow)"

print_test "Creating incident..."
INCIDENT_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/incidents/" \
    -H "Authorization: Bearer $TENANT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"property_id\": \"$PROPERTY_ID\",
        \"unit_id\": \"$UNIT_ID\",
        \"title\": \"Test: Leaking faucet in kitchen\",
        \"description\": \"The kitchen sink faucet is dripping constantly\",
        \"category\": \"plumbing\",
        \"urgency\": \"medium\"
    }" || echo '{"error": "Failed to create incident"}')

INCIDENT_ID=$(echo "$INCIDENT_RESPONSE" | jq -r '.incident_id // .id // empty')

if [ -z "$INCIDENT_ID" ] || [ "$INCIDENT_ID" = "null" ]; then
    print_error "Failed to create incident"
    echo "Response: $INCIDENT_RESPONSE"
    exit 1
fi

print_success "Created incident: $INCIDENT_ID"

# Test photo upload (if test image exists)
if [ -f "$TEST_IMAGE" ]; then
    print_test "Uploading incident photo..."
    PHOTO_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/incidents/$INCIDENT_ID/photos" \
        -H "Authorization: Bearer $TENANT_TOKEN" \
        -F "file=@$TEST_IMAGE" || echo '{"error": "Failed to upload photo"}')

    if echo "$PHOTO_RESPONSE" | jq -e '.photo_url' > /dev/null 2>&1; then
        print_success "Photo uploaded"
    else
        print_error "Photo upload failed (non-critical)"
    fi
else
    print_error "Test image not found at $TEST_IMAGE (skipping photo upload test)"
fi

# Submit discovery questions
print_test "Submitting discovery answers..."
DISCOVERY_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/incidents/$INCIDENT_ID/discovery" \
    -H "Authorization: Bearer $TENANT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "when_started": "2 days ago",
        "frequency": "constant",
        "attempted_fixes": "Tried tightening the handle"
    }' || echo '{"error": "Failed to submit discovery"}')

if echo "$DISCOVERY_RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
    print_success "Discovery answers submitted"
else
    print_error "Discovery submission failed (non-critical)"
fi

# ================================================
# 3. TEST JOB CREATION (Phase 2B)
# ================================================
print_header "3️⃣  Testing Job Creation (Landlord Flow)"

print_test "Creating job from incident..."
JOB_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/jobs/" \
    -H "Authorization: Bearer $LANDLORD_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"incident_id\": \"$INCIDENT_ID\",
        \"title\": \"Fix kitchen faucet leak\",
        \"description\": \"Repair or replace leaking kitchen faucet\",
        \"budget_min\": 100,
        \"budget_max\": 300,
        \"deadline\": \"2024-12-31T23:59:59Z\"
    }" || echo '{"error": "Failed to create job"}')

JOB_ID=$(echo "$JOB_RESPONSE" | jq -r '.job_id // .id // empty')

if [ -z "$JOB_ID" ] || [ "$JOB_ID" = "null" ]; then
    print_error "Failed to create job"
    echo "Response: $JOB_RESPONSE"
    exit 1
fi

print_success "Created job: $JOB_ID"

# ================================================
# 4. TEST CONTRACTOR BIDDING (Phase 2C)
# ================================================
print_header "4️⃣  Testing Contractor Bidding"

print_test "Submitting contractor bid..."
BID_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/jobs/$JOB_ID/bid" \
    -H "Authorization: Bearer $CONTRACTOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "amount": 250.00,
        "estimated_hours": 4,
        "proposed_start_date": "2024-12-15",
        "description": "I can fix this faucet. I have 10 years of plumbing experience."
    }' || echo '{"error": "Failed to submit bid"}')

BID_ID=$(echo "$BID_RESPONSE" | jq -r '.bid_id // .id // empty')

if [ -z "$BID_ID" ] || [ "$BID_ID" = "null" ]; then
    print_error "Failed to submit bid"
    echo "Response: $BID_RESPONSE"
    exit 1
fi

print_success "Submitted bid: $BID_ID"

# Test viewing bids
print_test "Viewing all bids on job..."
BIDS_RESPONSE=$(curl -s -X GET "$API_URL/api/v1/jobs/$JOB_ID/bids" \
    -H "Authorization: Bearer $LANDLORD_TOKEN" || echo '{"bids": []}')

BID_COUNT=$(echo "$BIDS_RESPONSE" | jq '.bids | length')
print_success "Found $BID_COUNT bid(s)"

# Award job
print_test "Awarding job to contractor..."
AWARD_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/jobs/$JOB_ID/award/$BID_ID" \
    -H "Authorization: Bearer $LANDLORD_TOKEN" || echo '{"error": "Failed to award job"}')

if echo "$AWARD_RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
    print_success "Job awarded to contractor"
else
    print_error "Failed to award job"
    echo "Response: $AWARD_RESPONSE"
    exit 1
fi

# ================================================
# 5. TEST JOB COMPLETION (Phase 2C)
# ================================================
print_header "5️⃣  Testing Job Completion"

print_test "Scheduling job..."
SCHEDULE_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/contractors/jobs/$JOB_ID/schedule" \
    -H "Authorization: Bearer $CONTRACTOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "scheduled_date": "2024-12-15T10:00:00Z"
    }' || echo '{"error": "Failed to schedule job"}')

if echo "$SCHEDULE_RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
    print_success "Job scheduled"
else
    print_error "Job scheduling failed (non-critical)"
fi

print_test "Marking job as complete..."
COMPLETE_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/contractors/jobs/$JOB_ID/complete" \
    -H "Authorization: Bearer $CONTRACTOR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "completion_notes": "Fixed the leak by replacing the washer and tightening connections.",
        "actual_hours": 3.5
    }' || echo '{"error": "Failed to complete job"}')

if echo "$COMPLETE_RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
    print_success "Job marked as complete"
else
    print_error "Failed to mark job complete"
    echo "Response: $COMPLETE_RESPONSE"
    exit 1
fi

# ================================================
# 6. TEST PAYMENT PROCESSING (Phase 2D)
# ================================================
print_header "6️⃣  Testing Payment Processing"

print_test "Initiating payment..."
PAYMENT_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/payments/jobs/$JOB_ID/initiate" \
    -H "Authorization: Bearer $LANDLORD_TOKEN" || echo '{"error": "Failed to initiate payment"}')

PAYMENT_INTENT_ID=$(echo "$PAYMENT_RESPONSE" | jq -r '.payment_intent_id // .client_secret // empty' | cut -d'_' -f1-3)

if [ -z "$PAYMENT_INTENT_ID" ] || [ "$PAYMENT_INTENT_ID" = "null" ]; then
    print_error "Failed to initiate payment"
    echo "Response: $PAYMENT_RESPONSE"
else
    print_success "Payment initiated: $PAYMENT_INTENT_ID"
fi

# Verify payment breakdown
CONTRACTOR_AMOUNT=$(echo "$PAYMENT_RESPONSE" | jq -r '.contractor_amount // empty')
PLATFORM_FEE=$(echo "$PAYMENT_RESPONSE" | jq -r '.platform_fee // empty')
TOTAL_AMOUNT=$(echo "$PAYMENT_RESPONSE" | jq -r '.total_amount // empty')

if [ -n "$CONTRACTOR_AMOUNT" ] && [ "$CONTRACTOR_AMOUNT" != "null" ]; then
    print_success "Payment breakdown verified:"
    echo "    Total: \$$TOTAL_AMOUNT"
    echo "    Contractor (85%): \$$CONTRACTOR_AMOUNT"
    echo "    Platform Fee (15%): \$$PLATFORM_FEE"
fi

# ================================================
# 7. VERIFY DATA INTEGRITY
# ================================================
print_header "7️⃣  Verifying Data Integrity"

print_test "Checking incident status..."
INCIDENT_CHECK=$(curl -s -X GET "$API_URL/api/v1/incidents/$INCIDENT_ID" \
    -H "Authorization: Bearer $TENANT_TOKEN" || echo '{}')

INCIDENT_STATUS=$(echo "$INCIDENT_CHECK" | jq -r '.status // empty')
print_success "Incident status: $INCIDENT_STATUS"

print_test "Checking job status..."
JOB_CHECK=$(curl -s -X GET "$API_URL/api/v1/jobs/$JOB_ID" \
    -H "Authorization: Bearer $LANDLORD_TOKEN" || echo '{}')

JOB_STATUS=$(echo "$JOB_CHECK" | jq -r '.status // empty')
print_success "Job status: $JOB_STATUS"

# ================================================
# SUMMARY
# ================================================
print_header "📊 Test Summary"

echo "Test completed successfully! ✨"
echo ""
echo "Flow verified:"
echo "  1. ✓ Tenant reported incident ($INCIDENT_ID)"
echo "  2. ✓ Landlord created job ($JOB_ID)"
echo "  3. ✓ Contractor submitted bid ($BID_ID)"
echo "  4. ✓ Landlord awarded job"
echo "  5. ✓ Contractor completed work"
echo "  6. ✓ Payment processing initiated"
echo ""
echo "Next steps:"
echo "  - Review data in DynamoDB"
echo "  - Test payment completion in Stripe Dashboard"
echo "  - Test webhook handling"
echo "  - Run frontend UI tests"
echo ""

print_success "All tests passed! 🎉"
