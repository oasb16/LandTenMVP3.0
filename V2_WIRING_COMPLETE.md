# ✅ AI Reasoning V2 - Wiring Complete

**Date:** 2025-11-21
**Status:** ✅ V2 FULLY WIRED AND READY
**Branch:** `claude/landten-architecture-analysis-01HcEvE5nYrWvSsLefsuYj9i`

---

## 🎯 Problem Summary

The V2 reasoning engine was created but **never wired up**. The backend was still using the OLD `ai_reasoning.py` instead of the NEW `ai_reasoning_v2.py`.

**Evidence from logs:**
```
[ai-reasoning] ...           ← OLD V1 system running
```

**No evidence of V2:**
```
[ai-reasoning-v2] ...        ← Missing - V2 not running
```

**Flow engine showing wrong transitions:**
```
Transition: report_issue → general.chat
```

V2 would NEVER allow this transition.

---

## ✅ What Was Fixed

### 1. Updated All Imports (3 files)

#### File: `backend/app/routes/ai_webhooks.py`

**BEFORE:**
```python
from ..services.ai_reasoning import get_ai_reasoning, Intent
```

**AFTER:**
```python
from ..services.ai_reasoning_v2 import get_ai_reasoning_v2 as get_ai_reasoning, Intent
```

#### File: `backend/app/routes/chat_stream.py`

**BEFORE:**
```python
from ..services.ai_reasoning import get_ai_reasoning
from ..services.ai_reasoning import AIReasoning
```

**AFTER:**
```python
from ..services.ai_reasoning_v2 import get_ai_reasoning_v2 as get_ai_reasoning
from ..services.ai_reasoning_v2 import AIReasoningV2 as AIReasoning
```

### 2. Added Explicit V2 Logging

#### File: `backend/app/services/ai_reasoning_v2.py`

Added START logging in `post_process_reasoning()`:

```python
logger.info(
    "[ai-reasoning-v2] ========== START V2 PIPELINE ==========\n"
    "  Message: %s\n"
    "  Persona: %s\n"
    "  Flow Stage: %s",
    message[:100],
    persona,
    context.get("flow_state", {}).get("stage", "idle")
)
```

### 3. Fixed Flow Engine Intent-to-Stage Mappings

#### File: `backend/app/services/flow_engine.py`

**BEFORE:**
```python
def determine_next_stage(...):
    # ...
    return "general.chat"  # ❌ Always falls back to general.chat
```

**AFTER:**
```python
def determine_next_stage(...):
    intent_to_stage_map = {
        "incident.report": "discovery",        # ✅ Correct
        "discovery.response": "discovery",     # ✅ Correct
        "job.request": "job",                  # ✅ Correct
        "approval.decision": "job",            # ✅ Correct
        # ... complete mapping
    }
    return intent_to_stage_map.get(intent, intent)
```

---

## 🧪 Verification Results

```bash
$ ./verify_v2_wiring.sh

✅ ai_webhooks.py imports V2
✅ chat_stream.py imports V2
✅ V2 has explicit START logging
✅ flow_engine maps incident.report → discovery
✅ flow_engine maps discovery.response → discovery
✅ flow_engine maps job.request → job
✅ ai_reasoning_v2.py exists
✅ intent_classifier.py exists
✅ flow_state_machine.py exists

Summary: V2 Wiring Verified ✅
```

---

## 📊 Expected Log Output

### When V2 is Running Correctly

```
[ai-reasoning-v2] ========== START V2 PIPELINE ==========
  Message: My garage door is broken
  Persona: tenant
  Flow Stage: idle

[ai-reasoning-v2] ========== Starting Intent Inference ==========
  Message: My garage door is broken
  Persona: tenant
  Flow Stage: idle
  Active Incident: None

[ai-reasoning-v2] LAYER 1 - Raw Intent Detection:
  Raw Intent: incident.report (confidence: 0.90)
  Entities: {'category': 'appliance', 'severity': 'medium'}

[intent-classifier] LAYER 2 - Flow override: incident.report → incident.report | reason: No override needed

[intent-classifier] LAYER 3 - Safety guard: incident.report → incident.report | reason: No safety override needed

[intent-classifier] LAYER 4 - Short message resolver: incident.report → incident.report | reason: Not a short message

[ai-reasoning-v2] LAYERS 2-4 - Multi-Layer Classification:
  Raw Intent: incident.report
  Final Intent: incident.report
  Layers Applied: 3

[ai-reasoning-v2] ========== Intent Inference Complete ==========
  Final Intent: incident.report
  Stage: idle
  Confidence: 0.90

[flow-engine] Intent 'incident.report' → Stage 'discovery'

[ai-reasoning-v2] Post-processing complete:
  Intent: incident.report
  Summary: Appliance issue reported
  Reply: I've detected an issue. Let me help you create an incident report.
```

### You Should NOT See

```
[ai-reasoning] ...           ← OLD V1 logs
[flow-engine] Transition: ... → general.chat  ← Wrong transitions
```

---

## 🚀 How to Test

### 1. Restart Backend

```bash
cd /home/user/LandTenMVP3.0/backend

# Kill existing process
pkill -f uvicorn

# Start with V2
uvicorn app.main:app --reload
```

### 2. Run End-to-End Test

```bash
cd /home/user/LandTenMVP3.0

# Run test script
./test_v2_pipeline.sh
```

### 3. Monitor Logs

```bash
# Watch for V2 logs
tail -f backend.log | grep -E "(ai-reasoning-v2|flow-engine|intent-classifier)"
```

### 4. Manual Testing

**Test 1: Report Incident**
```bash
curl -X POST http://localhost:8000/api/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message.new",
    "message": {"text": "My garage door is broken", "user": {"id": "t1"}},
    "channel_id": "ch1"
  }'
```

**Expected logs:**
```
[ai-reasoning-v2] START V2 PIPELINE
[ai-reasoning-v2] Final Intent: incident.report
[flow-engine] Intent 'incident.report' → Stage 'discovery'
```

**Test 2: Discovery "yes"**
```bash
curl -X POST http://localhost:8000/api/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message.new",
    "message": {"text": "yes", "user": {"id": "t1"}},
    "channel_id": "ch1"
  }'
```

**Expected logs:**
```
[ai-reasoning-v2] START V2 PIPELINE
[intent-classifier] LAYER 2 - Flow override: general.chat → discovery.response
[ai-reasoning-v2] Final Intent: discovery.response
[flow-engine] Intent 'discovery.response' → Stage 'discovery'
```

**Test 3: Job Request**
```bash
curl -X POST http://localhost:8000/api/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message.new",
    "message": {"text": "Create a work order", "user": {"id": "t1"}},
    "channel_id": "ch1"
  }'
```

**Expected logs:**
```
[ai-reasoning-v2] START V2 PIPELINE
[ai-reasoning-v2] Final Intent: job.request
[flow-engine] Intent 'job.request' → Stage 'job'
```

---

## 📝 Files Changed

### Modified Files

1. **`backend/app/routes/ai_webhooks.py`**
   - Line 17: Changed import to V2

2. **`backend/app/routes/chat_stream.py`**
   - Line 36: Changed import to V2
   - Line 813: Changed class import to V2

3. **`backend/app/services/ai_reasoning_v2.py`**
   - Added START V2 PIPELINE logging (lines 330-339)

4. **`backend/app/services/flow_engine.py`**
   - Complete rewrite of `determine_next_stage()` function
   - Added proper intent-to-stage mapping (lines 29-76)

### New Files

5. **`verify_v2_wiring.sh`**
   - Verification script to check V2 wiring

6. **`test_v2_pipeline.sh`**
   - End-to-end pipeline test script

7. **`V2_WIRING_COMPLETE.md`**
   - This documentation

---

## 🎯 Intent → Stage Mapping

| Intent | Stage | Notes |
|--------|-------|-------|
| `incident.report` | `discovery` | Start discovery flow |
| `incident.followup` | `discovery` | Continue discovery |
| `discovery.response` | `discovery` | Stay in discovery |
| `discovery.continue` | `discovery` | Stay in discovery |
| `job.request` | `job` | Create job |
| `job.inquiry` | `job` | Job question |
| `job.status` | `job` | Check job status |
| `bids.request` | `bids` | Show bids |
| `bids.compare` | `bids` | Compare bids |
| `approval.request` | `approval_pending` | Need approval |
| `approval.decision` | `job` | After approval |
| `general.chat` | `idle` | General conversation |
| `greeting` | `idle` | Hello |
| `help` | `idle` | Help request |

---

## ✅ Checklist

- [x] Updated ai_webhooks.py import to V2
- [x] Updated chat_stream.py imports to V2
- [x] Added explicit V2 START logging
- [x] Fixed flow_engine intent-to-stage mappings
- [x] Created verification script
- [x] Created test script
- [x] Verified V2 wiring
- [x] Created documentation
- [ ] **Restart backend**
- [ ] **Run end-to-end test**
- [ ] **Verify V2 logs appear**
- [ ] **Confirm discovery flow works**
- [ ] **Confirm "yes" becomes discovery.response**

---

## 🔄 Complete Flow Example

```
User: "My garage door is broken"
  ↓
[ai-reasoning-v2] START V2 PIPELINE
  ↓
[ai-reasoning-v2] Raw Intent: incident.report
  ↓
[intent-classifier] Layers 2-4: No overrides needed
  ↓
[ai-reasoning-v2] Final Intent: incident.report
  ↓
[flow-engine] Intent 'incident.report' → Stage 'discovery'
  ↓
AI: Creates incident card, starts discovery
  ↓
AI: "Is the garage door stuck open or closed?"

User: "yes"
  ↓
[ai-reasoning-v2] START V2 PIPELINE
  ↓
[ai-reasoning-v2] Raw Intent: general.chat (OpenAI misclassified)
  ↓
[intent-classifier] LAYER 2 - Flow override: discovery stage forces discovery.response
  ↓
[ai-reasoning-v2] Final Intent: discovery.response (CORRECTED!)
  ↓
[flow-engine] Intent 'discovery.response' → Stage 'discovery'
  ↓
AI: Records answer, asks next question
  ↓
AI: "Where is the garage door located?"

User: "In the driveway"
  ↓
[ai-reasoning-v2] Final Intent: discovery.response
  ↓
AI: Records answer, continues discovery...

(After 4 questions)
  ↓
AI: "Discovery complete. Should I create a work order?"

User: "yes"
  ↓
[ai-reasoning-v2] Raw Intent: general.chat
  ↓
[intent-classifier] LAYER 4 - Short message resolver: "yes" in job-ready → job.request
  ↓
[ai-reasoning-v2] Final Intent: job.request (CORRECTED!)
  ↓
[flow-engine] Intent 'job.request' → Stage 'job'
  ↓
AI: Creates job card, generates contractor bids
  ↓
AI: "I've created job JOB-123. Here are 3 contractor bids..."
```

---

## 🎉 Summary

**V2 is now FULLY WIRED and ready to run!**

**What was fixed:**
- ✅ All imports updated to use V2
- ✅ Explicit START logging added
- ✅ Flow engine mappings corrected
- ✅ Verification script created
- ✅ Test script created

**What happens now:**
1. Restart backend
2. V2 pipeline runs for every message
3. Logs show `[ai-reasoning-v2]` instead of `[ai-reasoning]`
4. Flow engine maps intents correctly
5. "yes" becomes `discovery.response` (not `general.chat`)
6. Discovery completes full 4 questions
7. Job creation works correctly

**Your action:**
```bash
# 1. Restart backend
cd backend && pkill -f uvicorn && uvicorn app.main:app --reload

# 2. Run test
cd .. && ./test_v2_pipeline.sh

# 3. Watch logs
tail -f backend.log | grep "ai-reasoning-v2"
```

---

**Status: READY TO TEST** ✅
