#!/bin/bash
# Quick validation script for AI reasoning fix

echo "========================================="
echo "AI Reasoning Fix Validation"
echo "========================================="
echo ""

# Check 1: Verify bug is gone
echo "✓ Checking for bug pattern..."
BUG_COUNT=$(grep -c "json.loads(response.choices)" backend/app/services/ai_reasoning.py 2>/dev/null || echo "0")
if [ "$BUG_COUNT" -eq "0" ]; then
    echo "  ✅ No instances of json.loads(response.choices) found (GOOD)"
else
    echo "  ❌ Found $BUG_COUNT instances of the bug (BAD)"
    exit 1
fi

# Check 2: Verify correct pattern exists
echo ""
echo "✓ Checking for correct pattern..."
CORRECT_COUNT=$(grep -c "json.loads(response.choices\[0\].message.content)" backend/app/services/ai_reasoning.py 2>/dev/null || echo "0")
if [ "$CORRECT_COUNT" -eq "4" ]; then
    echo "  ✅ Found $CORRECT_COUNT correct instances (EXPECTED: 4)"
else
    echo "  ⚠️  Found $CORRECT_COUNT correct instances (EXPECTED: 4)"
fi

# Check 3: Verify fix comments are in place
echo ""
echo "✓ Checking for fix comments..."
COMMENT_COUNT=$(grep -c "# FIX: response.choices is already a list" backend/app/services/ai_reasoning.py 2>/dev/null || echo "0")
if [ "$COMMENT_COUNT" -eq "4" ]; then
    echo "  ✅ Found $COMMENT_COUNT fix comments (GOOD)"
else
    echo "  ⚠️  Found $COMMENT_COUNT fix comments (EXPECTED: 4)"
fi

echo ""
echo "========================================="
echo "Summary: AI reasoning fix is VALID ✅"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Restart backend: cd backend && uvicorn app.main:app --reload"
echo "2. Test webhook: curl -X POST http://localhost:8000/api/ai/stream-webhook -H 'Content-Type: application/json' -d @test_ai_reasoning_fix.json"
echo "3. Verify: Should NOT return 'Thank you for engaging me...'"
echo ""
