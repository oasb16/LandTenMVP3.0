# OpenAI Dashboard Setup Guide - LandTen MVP 3.0

**Last Updated:** 2025-12-14
**Prompt Version:** 11
**Model:** gpt-4o-mini

This guide shows you how to properly configure the OpenAI Dashboard to work with the LandTen property management AI system.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Dashboard Access](#dashboard-access)
3. [Prompt Configuration](#prompt-configuration)
4. [Model Settings](#model-settings)
5. [Function Calling Setup](#function-calling-setup)
6. [Testing the Configuration](#testing-the-configuration)
7. [Troubleshooting](#troubleshooting)
8. [References](#references)

---

## Prerequisites

Before starting, ensure you have:

- ✅ OpenAI API key with access to Responses API
- ✅ Prompt ID: `pmpt_69372d719cbc81979d5bd4c8fa43d248007953d6d1c462aa`
- ✅ Updated prompt file: `backend/system_prompts/tenant_agent_prompt.txt`
- ✅ Access to OpenAI Dashboard: https://platform.openai.com/

---

## Dashboard Access

### Step 1: Navigate to Prompts Section

1. Go to https://platform.openai.com/prompts
2. Log in with your OpenAI account
3. Find prompt: `pmpt_69372d719cbc81979d5bd4c8fa43d248007953d6d1c462aa`

### Step 2: Open Prompt Editor

1. Click on the prompt name to open it
2. You should see the current version number (v10)
3. Click **"Edit"** or **"New Version"** button

---

## Prompt Configuration

### Step 1: Upload New Prompt Content

**🚨 CRITICAL: The prompt content MUST match your local file exactly**

1. **Local file location:**
   ```
   /home/user/LandTenMVP3.0/backend/system_prompts/tenant_agent_prompt.txt
   ```

2. **Copy the entire file content:**
   ```bash
   cat backend/system_prompts/tenant_agent_prompt.txt | pbcopy
   # Or manually copy the file content
   ```

3. **Paste into Dashboard:**
   - In the prompt editor, delete ALL existing content
   - Paste the new content from your local file
   - Verify the first few lines match your local file

4. **Save as NEW version:**
   - Click **"Save as new version"**
   - Version should increment to **v11**
   - Add version note: "Fixed anti-hallucination rules for tool output"

### Step 2: Configure Prompt Variables

The prompt expects these variables to be passed at runtime:

| Variable Name | Type | Description | Example |
|---------------|------|-------------|---------|
| `property_address` | string | Full property address | "123 Main St, San Francisco, CA 94105" |
| `landlord_name` | string | Landlord/owner name | "John Smith" |
| `tenant_name` | string | Current tenant name | "Jane Doe" |
| `building_manager` | string | Building manager contact | "Mike Johnson" or "None on file" |
| `persona` | string | User role | "tenant", "landlord", or "contractor" |
| `channel_id` | string | Conversation channel ID | "messaging:landten-agent-landtencon-gmail-com" |

**⚠️ Important:** These variables are populated by your backend code (in `response_handler.py`). You should NOT set default values in the dashboard - they're passed dynamically per request.

---

## Model Settings

### Step 1: Select Model

**🎯 Recommended Model:**
```
gpt-4o-mini
```

**Why gpt-4o-mini?**
- ✅ Best cost/performance ratio
- ✅ Excellent function calling support
- ✅ Fast response times
- ✅ Supports all required parameters

**Alternative Models:**
- `gpt-4o` (more expensive but higher quality)
- `gpt-4-turbo` (legacy, not recommended)

**❌ DO NOT USE:**
- `gpt-3.5-turbo` (poor function calling)
- `gpt-5-nano` (experimental, unreliable)
- Any model without function calling support

### Step 2: Configure Temperature

```
Temperature: 0.3
```

**Why 0.3?**
- Consistent, predictable responses
- Follows instructions more reliably
- Less creative (good for diagnostic AI)
- Reduces hallucination risk

### Step 3: Max Tokens

```
Max Tokens: 4096
```

**Reasoning:**
- Allows for detailed diagnostic responses
- Accommodates long property maintenance explanations
- Includes room for function calls + reasoning

### Step 4: Remove Unsupported Parameters

**🚨 CRITICAL: Remove these parameters if present:**

| Parameter | Status | Action |
|-----------|--------|--------|
| `top_p` | ❌ Unsupported | **DELETE** this parameter |
| `frequency_penalty` | ❌ Unsupported | **DELETE** this parameter |
| `presence_penalty` | ❌ Unsupported | **DELETE** this parameter |

**Why?**
Your logs showed this error:
```
Error code: 400 - Unsupported parameter: 'top_p' is not supported with this model
```

The Responses API + gpt-4o-mini combination does NOT support these parameters.

### Step 5: Final Model Configuration

Your dashboard should show:

```yaml
Model: gpt-4o-mini
Temperature: 0.3
Max Tokens: 4096
# NO other parameters should be set
```

---

## Function Calling Setup

### Step 1: Enable Function Calling

In the prompt settings, ensure:

```
✅ Function Calling: ENABLED
✅ Tools: ENABLED
```

### Step 2: Understand Tool Passing

**Important:** You do NOT configure individual functions in the dashboard.

**Why?**
- Functions are defined in your backend code (`backend/app/functions/`)
- They're passed dynamically in each API request
- The dashboard only needs to know that function calling is ENABLED

**What your backend sends:**

```python
response = await openai_client.responses.create(
    prompt={
        "id": "pmpt_xxx",
        "version": "11",
        "variables": {
            "property_address": "123 Main St",
            ...
        }
    },
    conversation="conv_xxx",
    input=[...],
    tools=[  # ← These are passed by your backend
        {
            "type": "function",
            "name": "diagnose_water_leak",
            "description": "...",
            "parameters": {...}
        },
        # ... 26 more tools
    ]
)
```

### Step 3: Verify Function Calling in Logs

After deployment, check your Heroku logs:

```
✅ Expected logs:
🔧 Tools Available: 27 tool(s)
First 10 tools: create_incident, update_incident, diagnose_water_leak, ...
🔧 FUNCTION CALL DETECTED!
Function: diagnose_water_leak
Tool Calls Found: 1
```

---

## Testing the Configuration

### Step 1: Test in Dashboard Playground

1. Go to your prompt in the dashboard
2. Click **"Test"** or **"Playground"**
3. Enter test input:
   ```
   My backyard swimming pool is overflowing
   ```

4. **Manually add variables** (for testing only):
   ```json
   {
     "property_address": "123 Test St, San Francisco, CA 94105",
     "landlord_name": "Test Landlord",
     "tenant_name": "Test Tenant",
     "building_manager": "None on file",
     "persona": "tenant",
     "channel_id": "test-channel-123"
   }
   ```

5. **Manually add tools** (for testing only):
   - In the playground, click "Add Function"
   - Copy function definitions from `backend/app/functions/`
   - Add `diagnose_water_leak` function

6. Click **"Run"**

### Step 2: Expected Dashboard Test Output

**✅ CORRECT Response:**
```
I'm really sorry your backyard pool is overflowing—that sounds stressful.

⛑️ Quick safety steps
- Keep kids and pets away...
- Avoid electrical equipment...

📸 Photos help tremendously
Please upload photos of:
- Wide shot of pool area
- Pool equipment (pump, filter, backwash valve)

🔎 Diagnostic results (from diagnostic tool):
- Diagnosis: Backwash valve stuck in waste mode  ← Real data from tool
- Severity: High  ← Real data from tool
- Urgency: Urgent  ← Real data from tool
- Estimated cost: $350-$600  ← Real data from tool
```

**❌ WRONG Response (Old Behavior):**
```
🔎 Diagnostic results (pool overflow)
- Diagnosis: Unknown leak  ← Generic placeholder!
- Severity: Medium  ← Generic placeholder!
- Estimated cost: $200-$500  ← Generic placeholder!
```

### Step 3: Test in Production

1. Deploy your updated code:
   ```bash
   git push heroku claude/fix-openai-response-handler-Ckhe4:main
   ```

2. Update environment variable:
   ```bash
   heroku config:set LANDTEN_PROMPT_VERSION=11 -a landtenmvp3
   ```

3. Restart app:
   ```bash
   heroku restart -a landtenmvp3
   ```

4. Test with real message:
   - Send message via app: "My pool is overflowing"
   - Check Heroku logs: `heroku logs --tail -a landtenmvp3`

5. Verify logs show:
   ```
   ✅ ResponseHandler initialized with prompt: pmpt_xxx v11
   ✅ Version: 11
   ✅ Tools Available: 27 tool(s)
   ✅ FUNCTION CALL DETECTED!
   ✅ Function: diagnose_water_leak
   ✅ Tool Calls Found: 1
   ```

---

## Troubleshooting

### Issue 1: "Unsupported parameter: 'top_p'" Error

**Symptom:**
```
Error code: 400 - Unsupported parameter: 'top_p' is not supported
```

**Solution:**
1. Go to dashboard → Edit prompt
2. Look for "Model configuration" or "Advanced settings"
3. **DELETE** any `top_p`, `frequency_penalty`, or `presence_penalty` settings
4. Save new version

---

### Issue 2: AI Shows Generic "Unknown leak" Data

**Symptom:**
```
Logs show: ✅ Tool called successfully
But response shows: ❌ "Diagnosis: Unknown leak, Severity: Medium"
```

**Solution:**
1. **Check prompt version in logs:**
   ```
   ResponseHandler initialized with prompt: pmpt_xxx v??
   ```
   - If showing v10 or lower → Upload new prompt (v11)

2. **Update environment variable:**
   ```bash
   heroku config:set LANDTEN_PROMPT_VERSION=11 -a landtenmvp3
   ```

3. **Restart app:**
   ```bash
   heroku restart -a landtenmvp3
   ```

4. **Verify new prompt is active:**
   - Test again
   - Check logs show "prompt v11"
   - Response should show real tool data

---

### Issue 3: No Tools Being Called

**Symptom:**
```
Logs show: Tool Calls Found: 0
Response has no diagnostic data
```

**Solution:**

1. **Check tools are loaded:**
   ```
   Logs should show: 🔧 Tools Available: 27 tool(s)
   ```
   - If 0 tools → Backend issue, check function registry

2. **Verify function calling is enabled:**
   - Dashboard → Prompt settings
   - Ensure "Function Calling: ENABLED"

3. **Check model supports function calling:**
   - Model should be: `gpt-4o-mini` or `gpt-4o`
   - NOT: `gpt-3.5-turbo`, `gpt-5-nano`

---

### Issue 4: Dashboard Test vs Production Different Behavior

**Symptom:**
- Dashboard test works correctly
- Production app shows different response

**Explanation:**
Dashboard tests use manually added variables and tools. Production passes them dynamically from backend code.

**Solution:**

1. **Check backend is passing variables:**
   ```
   Logs should show:
   📋 Prompt Object:
     - Version: 11
     - Variables: {
         "property_address": "...",
         "landlord_name": "...",
         ...
       }
   ```

2. **Check backend is passing tools:**
   ```
   Logs should show:
   🔧 Tools Available: 27 tool(s)
   First 10 tools: create_incident, ...
   ```

3. **If variables missing:**
   - Check `response_handler.py` → `_get_property_context()`
   - Ensure it's fetching from DynamoDB correctly

4. **If tools missing:**
   - Check `function_registry.py` → `get_function_definitions()`
   - Ensure tools are loading from disk + DynamoDB

---

## References

### OpenAI Documentation

- **Function Calling Guide:**
  https://platform.openai.com/docs/guides/function-calling

- **Responses API Reference:**
  https://platform.openai.com/docs/api-reference/responses

- **Prompts Dashboard:**
  https://platform.openai.com/prompts

### LandTen Codebase

- **Prompt File:**
  `backend/system_prompts/tenant_agent_prompt.txt`

- **Response Handler:**
  `backend/app/services/response_handler.py`

- **Function Registry:**
  `backend/app/functions/function_registry.py`

- **Environment Variables:**
  - `LANDTEN_PROMPT_ID` - Prompt ID from dashboard
  - `LANDTEN_PROMPT_VERSION` - Current version number (11)
  - `OPENAI_API_KEY` - Your OpenAI API key

---

## Quick Reference: Correct Dashboard Settings

```yaml
Prompt Configuration:
  Prompt ID: pmpt_69372d719cbc81979d5bd4c8fa43d248007953d6d1c462aa
  Version: 11 (latest)
  Content: Matches backend/system_prompts/tenant_agent_prompt.txt

Model Settings:
  Model: gpt-4o-mini
  Temperature: 0.3
  Max Tokens: 4096

Parameters to REMOVE:
  ❌ top_p
  ❌ frequency_penalty
  ❌ presence_penalty

Function Calling:
  ✅ Function Calling: ENABLED
  ✅ Tools: ENABLED
  ℹ️  Individual functions: Passed by backend (not configured in dashboard)

Variables:
  ℹ️  Variables: Passed dynamically by backend (no defaults in dashboard)
  Expected: property_address, landlord_name, tenant_name, building_manager, persona, channel_id
```

---

## Environment Variables Checklist

Update these in Heroku (or your `.env` file):

```bash
# Required
LANDTEN_PROMPT_ID=pmpt_69372d719cbc81979d5bd4c8fa43d248007953d6d1c462aa
LANDTEN_PROMPT_VERSION=11  # ← UPDATE THIS!
OPENAI_API_KEY=sk-proj-...

# Verify with:
heroku config -a landtenmvp3 | grep LANDTEN
```

---

## Testing Checklist

After making dashboard changes:

- [ ] Uploaded new prompt content (v11)
- [ ] Set model to `gpt-4o-mini`
- [ ] Set temperature to `0.3`
- [ ] Set max tokens to `4096`
- [ ] Removed `top_p` parameter
- [ ] Enabled function calling
- [ ] Updated `LANDTEN_PROMPT_VERSION=11` in Heroku
- [ ] Restarted Heroku app
- [ ] Tested with "My pool is overflowing"
- [ ] Verified logs show "prompt v11"
- [ ] Verified logs show "Tools Available: 27"
- [ ] Verified logs show "FUNCTION CALL DETECTED"
- [ ] Verified response shows REAL tool data (not "Unknown leak")

---

## Support

If you encounter issues not covered in this guide:

1. **Check Heroku logs:**
   ```bash
   heroku logs --tail -a landtenmvp3 | grep "response_handler\|RESPONSES API"
   ```

2. **Look for these debug sections:**
   - `🔍 RESPONSES API REQUEST` - Shows what's being sent
   - `✅ RESPONSES API RESPONSE` - Shows what OpenAI returned
   - `🔍 EXTRACTED CONTENT` - Shows tool calls found

3. **Common log indicators:**
   - `Version: 11` ✅ Using latest prompt
   - `Version: NOT SET` ❌ Version not being passed
   - `Tools Available: 27` ✅ Tools loaded
   - `Tools Available: 0` ❌ Tools not loaded
   - `FUNCTION CALL DETECTED!` ✅ AI is calling tools
   - `NO TOOL CALLS EXTRACTED` ❌ AI not calling tools
   - `Diagnosis: Unknown leak` ❌ Showing fake data
   - `Diagnosis: Backwash valve stuck` ✅ Showing real data

---

**Last Updated:** 2025-12-14
**Document Version:** 1.0
**Prompt Version:** 11
**Model:** gpt-4o-mini
