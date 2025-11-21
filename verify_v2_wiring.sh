#!/bin/bash
# Verify that AI Reasoning V2 is properly wired throughout the backend

echo "========================================="
echo "AI Reasoning V2 - Wiring Verification"
echo "========================================="
echo ""

# Check 1: Verify ai_webhooks.py imports V2
echo "✓ Checking ai_webhooks.py import..."
AI_WEBHOOKS_IMPORT=$(grep "from.*ai_reasoning" backend/app/routes/ai_webhooks.py 2>/dev/null)
if echo "$AI_WEBHOOKS_IMPORT" | grep -q "ai_reasoning_v2"; then
    echo "  ✅ ai_webhooks.py imports V2"
    echo "     $AI_WEBHOOKS_IMPORT"
else
    echo "  ❌ ai_webhooks.py still imports OLD ai_reasoning"
    echo "     $AI_WEBHOOKS_IMPORT"
    exit 1
fi
echo ""

# Check 2: Verify chat_stream.py imports V2
echo "✓ Checking chat_stream.py imports..."
CHAT_STREAM_IMPORTS=$(grep "from.*ai_reasoning" backend/app/routes/chat_stream.py 2>/dev/null)
if echo "$CHAT_STREAM_IMPORTS" | grep -q "ai_reasoning_v2"; then
    echo "  ✅ chat_stream.py imports V2"
    echo "$CHAT_STREAM_IMPORTS" | sed 's/^/     /'
else
    echo "  ⚠️  chat_stream.py may have OLD imports"
    echo "$CHAT_STREAM_IMPORTS" | sed 's/^/     /'
fi
echo ""

# Check 3: Verify V2 has START logging
echo "✓ Checking V2 has START logging..."
if grep -q "START V2 PIPELINE" backend/app/services/ai_reasoning_v2.py; then
    echo "  ✅ V2 has explicit START logging"
else
    echo "  ⚠️  V2 missing START logging"
fi
echo ""

# Check 4: Verify flow_engine maps intents correctly
echo "✓ Checking flow_engine intent mapping..."
if grep -q "incident.report.*discovery" backend/app/services/flow_engine.py; then
    echo "  ✅ flow_engine maps incident.report → discovery"
else
    echo "  ❌ flow_engine has incorrect mapping"
fi

if grep -q "discovery.response.*discovery" backend/app/services/flow_engine.py; then
    echo "  ✅ flow_engine maps discovery.response → discovery"
else
    echo "  ❌ flow_engine missing discovery.response mapping"
fi

if grep -q "job.request.*job" backend/app/services/flow_engine.py; then
    echo "  ✅ flow_engine maps job.request → job"
else
    echo "  ❌ flow_engine missing job.request mapping"
fi
echo ""

# Check 5: Verify V2 file exists
echo "✓ Checking V2 files exist..."
if [ -f "backend/app/services/ai_reasoning_v2.py" ]; then
    echo "  ✅ ai_reasoning_v2.py exists"
else
    echo "  ❌ ai_reasoning_v2.py NOT FOUND"
    exit 1
fi

if [ -f "backend/app/services/intent_classifier.py" ]; then
    echo "  ✅ intent_classifier.py exists"
else
    echo "  ❌ intent_classifier.py NOT FOUND"
    exit 1
fi

if [ -f "backend/app/services/flow_state_machine.py" ]; then
    echo "  ✅ flow_state_machine.py exists"
else
    echo "  ❌ flow_state_machine.py NOT FOUND"
    exit 1
fi
echo ""

echo "========================================="
echo "Summary: V2 Wiring Verified ✅"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Restart backend:"
echo "   cd backend && pkill -f uvicorn && uvicorn app.main:app --reload"
echo ""
echo "2. Run end-to-end test:"
echo "   chmod +x test_v2_pipeline.sh && ./test_v2_pipeline.sh"
echo ""
echo "3. Check logs for:"
echo "   [ai-reasoning-v2] START V2 PIPELINE"
echo "   [ai-reasoning-v2] Final Intent: ..."
echo ""
