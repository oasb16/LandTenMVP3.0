# Diagnosis Loop Fix - Test Validation Plan

## 🚨 CRITICAL BUG FIXED
**Problem:** Orchestrator was looping on `start_diagnosis` instead of calling `create_work_order` when user says "Yes" after diagnosis.

## ✅ FIXES IMPLEMENTED

### 1. orchestrator_prompt.txt
- Added explicit post-diagnosis rules
- Defined allowed actions after diagnosis completes
- Forbidden: Repeated `start_diagnosis` calls

### 2. orchestrator.py
- Guardrail #2B: Blocks repeated `start_diagnosis` calls
- Guardrail #2C: Detects "yes" pattern → overrides to `create_work_order`
- Enhanced LLM hints with diagnosis tracking status

### 3. meta_context_manager.py
- Added `set_diagnosis_complete()`
- Added `track_function_call()`
- Added `get_diagnosis_status()`
- Added `clear_diagnosis_tracking()`

### 4. function_registry.py
- `start_diagnosis`: Prevents duplicates, sets `diagnosis_complete=True`
- `create_work_order`: Clears diagnosis tracking

### 5. ai_webhooks_v3.py
- Metadata tracking integration
- Sets `diagnosis_complete` when diagnosis finishes
- Clears tracking when work order created

---

## 🧪 TEST SCENARIOS

### Test 1: Diagnosis Loop Fix (THE BIGGEST BUG)
**Expected Flow:**
```
1. User: "my sink is leaking"
   → LLM: create_incident
   → Status: detected

2. Auto-start discovery Q1-Q5
   → Status: discovery

3. User answers Q5
   → Status: discovery_complete

4. LLM: start_diagnosis (FIRST TIME)
   → Status: diagnosing
   → metadata.diagnosis_complete = True
   → metadata.last_tool_called = "start_diagnosis"
   → Sends diagnosis card

5. User: "Yes"
   → 🚨 CRITICAL: Should call create_work_order
   → ✅ NOT start_diagnosis again!
   → Status: work_order
```

**How Fixes Prevent Loop:**
- Guardrail #2B: Blocks if `last_tool_called = "start_diagnosis"`
- Guardrail #2C: Detects "yes" → overrides to `create_work_order`
- Prompt rules: Explicit "yes" → `create_work_order` mapping
- Function check: `start_diagnosis` returns `already_diagnosed` if called twice

---

### Test 2: Multi-Incident Handling
**Expected Flow:**
```
1. User: "my garage door is broken"
   → create_incident #1
   → discovery → diagnosis → work_order

2. User: "my fridge is broken" (DIFFERENT incident)
   → create_incident #2 (allowed, different category)
   → diagnosis_complete cleared for new incident
```

---

### Test 3: Post-Diagnosis Confirmation
**Expected Flow:**
```
Stage: diagnosing
diagnosis_complete: true

User: "yes" → create_work_order ✅
User: "ok" → create_work_order ✅
User: "sure" → create_work_order ✅
User: "no" → general.chat ✅
User: "more details" → record_diagnosis_result ✅
```

---

## 🔍 VERIFICATION CHECKLIST

### ✅ Orchestrator Prompt
- [x] Added post-diagnosis rules (lines 251-329)
- [x] Forbidden repeated `start_diagnosis` calls
- [x] Defined "yes" → `create_work_order` mapping

### ✅ Orchestrator Guardrails
- [x] Guardrail #2B prevents repeated diagnosis
- [x] Guardrail #2C detects "yes" pattern
- [x] Injects diagnosis tracking into LLM context

### ✅ Meta-Context Manager
- [x] `set_diagnosis_complete()` method
- [x] `track_function_call()` method
- [x] `get_diagnosis_status()` method
- [x] `clear_diagnosis_tracking()` method

### ✅ Function Registry
- [x] `start_diagnosis` prevents duplicates
- [x] `start_diagnosis` sets `diagnosis_complete=True`
- [x] `create_work_order` clears diagnosis tracking

### ✅ Webhook Handler
- [x] Tracks diagnosis completion in metadata
- [x] Clears tracking when work order created
- [x] Tracks all function calls for debugging

---

## 📊 EXPECTED BEHAVIOR AFTER FIXES

### Before (BROKEN):
```
discovery_complete → start_diagnosis → "yes" → start_diagnosis → "yes" → start_diagnosis (LOOP!)
```

### After (FIXED):
```
discovery_complete → start_diagnosis (once) → "yes" → create_work_order → work_order stage ✅
```

---

## 🚀 DEPLOYMENT NOTES

All changes are **backward compatible** - they only add new guardrails and tracking, without breaking existing functionality.

### Files Modified:
1. `backend/system_prompts/orchestrator_prompt.txt`
2. `backend/app/services/orchestrator.py`
3. `backend/app/services/meta_context_manager.py`
4. `backend/app/functions/function_registry.py`
5. `backend/app/routes/ai_webhooks_v3.py`

### No Database Changes Required
All tracking uses existing `metadata` field in meta-context (JSON dict).

---

## 🎯 SUCCESS CRITERIA

✅ **Primary:** User says "yes" after diagnosis → calls `create_work_order` (NOT `start_diagnosis`)
✅ **Secondary:** `start_diagnosis` can only be called once per incident
✅ **Tertiary:** Diagnosis loop is impossible due to multiple layers of protection

---

## 🛡️ DEFENSE IN DEPTH

We implemented **4 layers of protection** against diagnosis loops:

1. **Prompt Layer:** Explicit rules in orchestrator_prompt.txt
2. **Guardrail Layer:** Python guardrails in orchestrator.py
3. **Function Layer:** Duplicate detection in start_diagnosis()
4. **Metadata Layer:** Tracking in meta-context prevents repeated calls

Even if one layer fails, the others prevent the bug!
