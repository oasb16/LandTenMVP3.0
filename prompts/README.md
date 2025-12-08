# LandTen Unified Prompt - Setup Guide

This directory contains the unified prompt for LandTen's Responses API migration.

## Files

- **landten-unified-prompt-v1.md**: The main prompt content (paste into OpenAI dashboard)
- **prompt-config.json**: Metadata and tool definitions
- **README.md**: This setup guide

---

## Setup Instructions

### Step 1: Create Prompt in OpenAI Dashboard

1. Go to **[OpenAI Platform - Prompts](https://platform.openai.com/prompts)**
2. Click **"Create prompt"**
3. Give it a name: **"LandTen Maintenance Assistant v1"**
4. Copy the **entire contents** of `landten-unified-prompt-v1.md`
5. Paste into the prompt editor
6. Click **"Save"**

### Step 2: Get the Prompt ID

1. After saving, you'll see a prompt ID in the format: `prompt_xxxxxxxxxxxxx`
2. **Copy this prompt ID** - you'll need it for the next step
3. The prompt ID appears in the URL and in the prompt details

### Step 3: Configure Environment Variable

Add the prompt ID to your environment:

```bash
# In your .env file or environment
export LANDTEN_PROMPT_ID=prompt_xxxxxxxxxxxxx
```

Replace `prompt_xxxxxxxxxxxxx` with your actual prompt ID from Step 2.

### Step 4: Deploy

1. Ensure your code has the Responses API integration (completed in migration phases 2-4)
2. Deploy to your environment (Heroku, AWS, etc.)
3. Verify the `LANDTEN_PROMPT_ID` environment variable is set

---

## Prompt Versioning

### Creating New Versions

When you need to update the prompt:

1. Go to the OpenAI dashboard
2. Navigate to your existing prompt
3. Click **"Create version"** or **"Duplicate"**
4. Make your changes
5. Save with a new version number (e.g., "v1.1", "v2.0")
6. Update `LANDTEN_PROMPT_ID` if you want to use the new version

### Version Control

**Recommended workflow:**

```bash
# Keep prompt content in git
prompts/
  landten-unified-prompt-v1.md       # Current version
  landten-unified-prompt-v1.1.md     # Next version (if needed)
  landten-unified-prompt-v2.md       # Major revision (if needed)
```

**Always:**
- Export prompt from dashboard after changes
- Commit to git for version control
- Document changes in commit messages

---

## A/B Testing Prompts

The Responses API makes A/B testing easy:

### Option 1: Create Two Versions

1. Create **Prompt A** (current version)
2. Create **Prompt B** (experimental version)
3. Get both prompt IDs
4. In your code, randomly select which prompt ID to use:

```python
import random

# 50/50 split
prompt_id = random.choice([
    os.getenv("LANDTEN_PROMPT_ID_A"),  # Control
    os.getenv("LANDTEN_PROMPT_ID_B"),  # Experiment
])

response = openai.responses.create(
    prompt={"id": prompt_id},
    conversation=conversation_id,
    input=[...]
)
```

### Option 2: Feature Flags

Use feature flags (LaunchDarkly, Unleash, etc.) to control which users see which prompt:

```python
if feature_flags.is_enabled("use_prompt_v2", user_id):
    prompt_id = os.getenv("LANDTEN_PROMPT_ID_V2")
else:
    prompt_id = os.getenv("LANDTEN_PROMPT_ID_V1")
```

---

## Monitoring & Metrics

### Key Metrics to Track

After deploying the new prompt, monitor:

**Conversation Quality:**
- User satisfaction scores
- Number of back-and-forth messages
- Successful incident creations

**Function Calling:**
- Function call success rate
- Average functions called per conversation
- Function call errors

**Discovery Flow:**
- Discovery completion rate
- Average time to complete Q1-Q5
- Discovery abandonment rate

**Performance:**
- Response latency
- Token usage per conversation
- API error rates

### Logging

Add logging to track prompt performance:

```python
logger.info(f"Using prompt: {prompt_id}")
logger.info(f"Conversation: {conversation_id}")
logger.info(f"Functions called: {[tc.function.name for tc in tool_calls]}")
logger.info(f"Response time: {response_time}ms")
```

---

## Troubleshooting

### Prompt Not Found Error

**Error:** `Prompt with ID 'prompt_xxx' not found`

**Solutions:**
1. Verify `LANDTEN_PROMPT_ID` is set correctly
2. Check the prompt ID in OpenAI dashboard
3. Ensure the prompt wasn't deleted
4. Verify API key has access to the prompt

### Function Calls Not Working

**Symptoms:** LLM responds with text instead of calling functions

**Solutions:**
1. Check tool definitions in prompt match actual functions
2. Verify function schemas are correct
3. Ensure prompt emphasizes function calling over natural language
4. Add more explicit examples in the prompt

### Wrong Function Called

**Symptoms:** LLM calls unexpected functions

**Solutions:**
1. Review function descriptions - make them more specific
2. Add examples of when to use each function
3. Add negative examples (when NOT to use)
4. Strengthen the "Critical Operating Rules" section

### Empathy Lost

**Symptoms:** Responses feel robotic, not empathetic

**Solutions:**
1. Review "Your Personality & Tone" section
2. Add more example responses
3. Reduce emphasis on rules, increase emphasis on personality
4. Test with real tenant messages

---

## Migration Notes

### What Changed

**Before (Dual-Agent):**
- TenantAgent handled empathy
- Orchestrator handled function calling
- Two separate API calls per message
- State stored in DynamoDB

**After (Unified Prompt):**
- Single prompt handles both empathy + function calling
- One Responses API call per message (+ tool loops)
- State stored in Conversations API
- Faster, simpler, more fluid

### Rollback Plan

If you need to rollback:

1. Uncomment old dual-agent code in `ai_webhooks_v3.py`
2. Comment out new ResponseHandler code
3. Restart services
4. File issue in GitHub with details

---

## Support

For questions or issues:

1. Check [OpenAI Responses API docs](https://platform.openai.com/docs/api-reference/responses)
2. Review migration guide in repo: `MIGRATION_SUMMARY.md`
3. File GitHub issue: `https://github.com/oasb16/LandTenMVP3.0/issues`

---

## Changelog

### v1.0.0 (2025-12-08)

**Initial unified prompt release**

- Merged TenantAgent + Orchestrator into single prompt
- Optimized for Responses API
- Includes all 17 tool definitions
- Discovery-first incident creation
- Pre-incident discovery support
- Automatic topic switching
- Category-specific diagnosis rules
- Empathetic + efficient communication
