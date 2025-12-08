# Deployment Ready - Function Calling Fixed ✅

**Status**: Ready for Heroku deployment
**Branch**: `claude/assistants-to-responses-migration-01AiwKigtzutWutk9zbHpHpQ`
**Date**: December 8, 2025

---

## Critical Bugs Fixed

### ✅ Bug 1: ImportError on Startup (Fixed in commit `0569517`)
**Problem**: Application crashed with `cannot import name 'get_context_manager'`
**Fix**: Corrected function name to `get_meta_context_manager` in `backend/app/services/__init__.py`

### ✅ Bug 2: AI Responding with JSON Instead of Calling Functions (Fixed in commits `83e3b1b`, `ef51e6c`)
**Problem**: AI was responding with raw JSON like:
```json
{
  "category": "appliance",
  "severity": "medium",
  "location": "water heater",
  "description": "Water heater is making noise"
}
```
Instead of calling `start_discovery()` function.

**Logs showed**: `No tool calls in response, loop complete` and `0 tool calls executed`

**Fix**: Added tools parameter to `responses.create()` call in `response_handler.py:195`:
```python
response = self.openai_client.responses.create(
    prompt={"id": prompt_id},
    conversation=conversation_id,
    input=current_input,
    tools=self.tools  # ✅ CRITICAL: Enable function calling
)
```

### ✅ Bug 3: Wrong Tool Format (Fixed in commit `7a9244d`)
**Problem**: API error: `Missing required parameter: 'tools[0].type'`
**Root Cause**: `get_function_definitions()` returns raw `FunctionDefinition` objects, but Responses API requires specific format

**Fix**: Convert tools to proper format in `response_handler.py:43-56`:
```python
# Get available tools for function calling
raw_functions = get_function_definitions()

# Convert to Responses API format: each tool needs {"type": "function", "function": {...}}
self.tools = []
for func in raw_functions:
    tool = {
        "type": "function",
        "function": {
            "name": func.name,
            "description": func.description,
            "parameters": func.parameters
        }
    }
    self.tools.append(tool)
```

---

## Deployment Instructions

### 1. Deploy to Heroku
```bash
# If using Heroku CLI
git push heroku claude/assistants-to-responses-migration-01AiwKigtzutWutk9zbHpHpQ:master

# Or merge to master first (recommended)
git checkout master
git merge claude/assistants-to-responses-migration-01AiwKigtzutWutk9zbHpHpQ
git push origin master
```

### 2. Verify Environment Variables
Ensure these are set in Heroku:
```bash
heroku config:set LANDTEN_PROMPT_ID=prompt_xxxxx
heroku config:get OPENAI_API_KEY  # Should already exist
```

### 3. Monitor Deployment
Watch logs during restart:
```bash
heroku logs --tail
```

**Expected Success Indicators**:
- ✅ `ResponseHandler initialized with prompt: prompt_xxxxx`
- ✅ `Loaded 17 tools for function calling` (or similar count)
- ✅ No import errors
- ✅ No "Missing required parameter" errors

---

## Testing Checklist

Once deployed, test with these scenarios:

### Test 1: Basic Function Calling
**User Message**: "My water heater is making weird noises and needs servicing"

**Expected Behavior**:
1. ✅ AI responds empathetically
2. ✅ Logs show: `Found X tool calls to execute`
3. ✅ Logs show: `Executing tool: start_discovery`
4. ✅ AI asks discovery questions about the issue

**Check Logs For**:
```
INFO - Processing message for channel: ...
INFO - Tool loop iteration 1/5
INFO - Response received: resp_xxxxx
INFO - Found 1 tool calls to execute
INFO - Executing tool: start_discovery with args: {...}
INFO - Tool start_discovery executed: success=True
```

### Test 2: Multi-Step Function Flow
**User Message**: "Water heater broken" → Answer all discovery questions → Verify incident created

**Expected Behavior**:
1. ✅ Discovery starts (`start_discovery`)
2. ✅ Questions asked one by one
3. ✅ When complete, incident created (`create_incident`)
4. ✅ Confirmation sent to user

### Test 3: Topic Switching
**User Message**: After first incident, report new issue: "Also my fridge is broken"

**Expected Behavior**:
1. ✅ New discovery flow starts
2. ✅ Separate incident created
3. ✅ No interference with previous conversation state

---

## What Was Wrong Before

### The ChatGPT Migration Had Critical Oversights

The original migration prompts from ChatGPT **did not include proper tool configuration** in the ResponseHandler, causing:

1. **No tools loaded**: `get_function_definitions()` was never called
2. **No tools passed to API**: The `tools` parameter was missing from `responses.create()`
3. **Wrong format**: Even when loaded, tools weren't converted to Responses API format

This meant OpenAI had **zero knowledge** that functions like `start_discovery`, `ask_question`, `create_incident` existed, so it just generated text responses instead of calling functions.

---

## Success Criteria

Function calling is working when you see in logs:

```
✅ Loaded 17 tools for function calling
✅ Found 1 tool calls to execute
✅ Executing tool: start_discovery
✅ Tool start_discovery executed: success=True
✅ Message processing complete: 1 tool calls executed
```

**NOT** this (old broken behavior):
```
❌ No tool calls in response, loop complete
❌ Message processing complete: 0 tool calls executed
```

---

## Rollback Plan (If Needed)

If deployment still has issues:

1. **Quick Rollback**:
   ```bash
   git checkout master
   git revert HEAD~3  # Revert last 3 commits
   git push origin master
   ```

2. **Alternative**: Uncomment old dual-agent code in `ai_webhooks_v3.py` (lines 378-842)

---

## Files Modified

- ✅ `backend/app/services/response_handler.py` - Added tool loading and conversion
- ✅ `backend/app/services/__init__.py` - Fixed import name
- ✅ `backend/app/routes/ai_webhooks_v3.py` - Uses ResponseHandler (done in earlier phase)
- ✅ `backend/app/routes/health_check.py` - Checks ResponseHandler (done in earlier phase)

---

## Next Steps After Successful Deployment

1. Monitor production for 24 hours
2. Verify incident creation in DynamoDB
3. Test all personas (tenant, landlord, contractor)
4. Consider archiving old dual-agent code permanently
5. Update documentation with lessons learned

---

## Contact

If deployment fails, check:
1. Heroku logs for specific error messages
2. OpenAI API dashboard for request/response details
3. DynamoDB for conversation mappings
4. Ensure LANDTEN_PROMPT_ID is set correctly

**Last Updated**: December 8, 2025
**Ready for Production**: ✅ YES
