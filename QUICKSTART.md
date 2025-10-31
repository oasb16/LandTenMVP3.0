# PropertyAI Intelligent System - Quick Start Guide

Get up and running with the intelligent context-aware ecosystem in 10 minutes.

---

## 🚀 Prerequisites

- Python 3.10+
- Node.js 16+
- OpenAI API key
- Stream Chat credentials
- AWS credentials (or local DynamoDB)

---

## 📦 Installation

### 1. Clone & Setup Backend

```bash
cd /home/user/LandTenMVP3.0/backend

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

### 2. Configure Environment

Edit `backend/.env`:

```bash
# Required: OpenAI API
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.3

# Required: Stream Chat
STREAM_CHAT_API_KEY=your-stream-key
STREAM_CHAT_API_SECRET=your-stream-secret
STREAM_WEBHOOK_SECRET=your-webhook-secret

# Required: DynamoDB (local or AWS)
TABLE_PREFIX=landtenmvp
STAGE=dev
AWS_REGION=us-east-1

# For local development:
DYNAMO_ENDPOINT_URL=http://localhost:8000
AUTH_DISABLED=true

# Context Configuration
CONTEXT_TTL_HOURS=24
CONTEXT_MAX_HISTORY=20
```

### 3. Initialize Context Table

```bash
# For local DynamoDB:
python scripts/init_context_table.py --local

# For AWS:
python scripts/init_context_table.py --stage dev
```

Expected output:
```
============================================================
  PropertyAI Context Table Initialization
============================================================
✅ Table 'landtenmvp_dev_chat_contexts' created successfully!
⏰ TTL enabled successfully!
🎉 Context table initialization complete!
```

### 4. Start Backend

```bash
uvicorn app.main:app --reload --port 8000
```

Verify it's running:
```bash
curl http://localhost:8000/ai/bot-status
```

### 5. Setup Frontend

```bash
cd /home/user/LandTenMVP3.0/frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend will be available at `http://localhost:3000`

---

## 🧪 Test the Intelligent System

### Test 1: Intent Detection (Console)

Create `test_intent.py`:

```python
from app.services.ai_reasoning import get_ai_reasoning

ai = get_ai_reasoning()

# Test incident report
result = ai.infer_intent(
    message="there's water leaking from my kitchen sink",
    context={},
    persona="tenant"
)

print(f"Intent: {result['intent']}")
print(f"Confidence: {result['confidence']:.2f}")
print(f"Entities: {result['entities']}")
print(f"Card Type: {result['card_type']}")
```

Run:
```bash
python test_intent.py
```

Expected:
```
Intent: incident.report
Confidence: 0.95
Entities: {'category': 'plumbing', 'location': 'kitchen', 'severity': 'medium'}
Card Type: incident
```

### Test 2: Context Management

```python
from app.services.context_manager import get_context_manager

cm = get_context_manager()

# Create context
context = cm.get_context("test-user", "test-channel")
print(f"Context ID: {context['context_id']}")

# Append message
cm.append_message("test-user", "test-channel", "user", "my sink is broken")

# Get history
history = cm.get_conversation_history("test-user", "test-channel")
print(f"History: {history}")

# Update with incident
cm.set_active_incident("test-user", "test-channel", "INC-123")

# Verify
context = cm.get_context("test-user", "test-channel")
print(f"Active Incident: {context['active_incident_id']}")
```

### Test 3: Policy Validation

```python
from app.services.policy_validator import get_policy_validator

pv = get_policy_validator()

# Test tenant trying to approve
is_valid, error = pv.validate_intent("approval.decision", "tenant")
print(f"Tenant can approve? {is_valid}")
if not is_valid:
    print(f"Error: {error}")

# Test landlord cost approval
can_approve, type_ = pv.validate_cost_approval(350.00, "landlord")
print(f"Landlord can approve $350? {can_approve} ({type_})")

# Test capabilities
caps = pv.get_persona_capabilities("tenant")
print(f"Tenant allowed intents: {caps['allowed_intents']}")
```

### Test 4: End-to-End Webhook

Send test webhook:

```bash
curl -X POST http://localhost:8000/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message.new",
    "channel_id": "test-channel",
    "user": {
      "id": "test-user",
      "name": "Test Tenant"
    },
    "message": {
      "text": "there is a water leak in my bathroom",
      "metadata": {
        "agentEnabled": true
      }
    }
  }'
```

Expected logs:
```
[ai-webhook] ========== Incoming Message ==========
[ai-webhook] Channel: test-channel
[ai-webhook] User: test-user (Test Tenant)
[ai-webhook] Message: there is a water leak in my bathroom
[ai-webhook] Context retrieved: flow_type=general
[ai-webhook] Detected persona: tenant
[ai-webhook] Inferring intent with AI reasoning...
[ai-reasoning] Intent detected: incident.report (confidence: 0.95)
[ai-webhook] Entities: {category: plumbing, location: bathroom, severity: medium}
[ai-webhook] Card type: incident
[ai-webhook] 🔧 Handling incident report...
[ai-webhook] ✅ SUCCESS: Intent 'incident.report' handled successfully
```

---

## 💬 Interactive Testing (Frontend)

### 1. Open Chat Interface

Navigate to `http://localhost:3000`

### 2. Send Free-Form Messages

Try these messages and observe intelligent behavior:

**Scenario 1: Incident Report**
```
User: "my kitchen sink is leaking badly"
Bot: [Creates incident card] "I've detected a plumbing issue..."
User: "yes it's urgent"
Bot: [Continues discovery] "Is the water still actively leaking?"
User: "yes"
Bot: [More questions] "Have you tried turning off the water supply?"
```

**Scenario 2: Context Continuity**
```
User: "there's a broken pipe"
Bot: [Creates INC-123] "Let me gather more details..."
[User leaves for 5 minutes]
User: "so what happens next?"
Bot: "For incident INC-123, I can create a work order..."
```

**Scenario 3: Policy Enforcement**
```
Tenant: "I approve this job"
Bot: "I appreciate your initiative, but job approvals need to be
     handled by your landlord. I've notified them!"
```

**Scenario 4: Persona-Specific Help**
```
Tenant: "help"
Bot: "As a tenant, here's what I can assist you with:
     • Report property issues and maintenance needs
     • Track incident status
     • Get DIY suggestions..."

Landlord: "help"
Bot: "As a landlord, here's what I can assist you with:
     • Review and approve work orders
     • View contractor bids
     • Manage property incidents..."
```

---

## 🎯 Key Features to Test

### ✅ Context Persistence

```
# Send multiple messages - context should persist
1. "my sink is broken"           → Creates INC-123
2. "it's in the kitchen"         → Adds to INC-123 context
3. "it started yesterday"        → More INC-123 details
4. "what's the status?"          → Bot knows it's about INC-123
```

### ✅ Intent Detection Accuracy

```
Test these intents:
- "there's a leak" → incident.report
- "show me bids" → bids.request
- "approve that" → approval.decision
- "hello" → greeting
- "what's the job status?" → job.inquiry
```

### ✅ Policy Boundaries

```
# Tenant tries forbidden action
Tenant: "I'll approve the contractor"
→ Bot: Friendly decline message

# Landlord approves large cost
Landlord: "approve $800 job"
→ Bot: "That amount requires additional review..."
```

### ✅ Graceful Degradation

```
# Disable OpenAI (set invalid key)
OPENAI_API_KEY=invalid

# Send message
"my pipe is broken"

# System falls back to rule-based detection
→ Still works! Confidence: 0.6 (instead of 0.95)
```

---

## 🐛 Troubleshooting

### Issue: Context not persisting

**Symptoms:** Each message treated as new conversation

**Solutions:**
1. Check DynamoDB table exists:
   ```bash
   aws dynamodb list-tables --endpoint-url http://localhost:8000
   ```

2. Verify context creation:
   ```bash
   python -c "
   from app.services.context_manager import get_context_manager
   cm = get_context_manager()
   ctx = cm.get_context('test', 'test')
   print(ctx['context_id'])
   "
   ```

3. Check logs for errors:
   ```bash
   grep -i "context" backend.log
   ```

### Issue: Intent detection always returns "unclear"

**Symptoms:** Low confidence (<0.5), falls back to unclear

**Solutions:**
1. Verify OpenAI API key:
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

2. Check model availability:
   ```python
   import openai
   openai.api_key = "sk-..."
   models = openai.Model.list()
   print([m.id for m in models.data if 'gpt-4' in m.id])
   ```

3. Test AI service directly:
   ```python
   from app.services.ai_service import get_ai_response
   response = get_ai_response("test message", persona="tenant")
   print(response)
   ```

### Issue: Policy always blocks actions

**Symptoms:** All actions return policy violations

**Solutions:**
1. Check persona detection:
   ```python
   from app.services.stream_bot import get_bot
   bot = get_bot()
   persona = bot.get_channel_persona("channel-id")
   print(f"Detected: {persona}")
   ```

2. Verify policy configuration:
   ```python
   from app.services.policy_validator import get_policy_validator
   pv = get_policy_validator()
   caps = pv.get_persona_capabilities("tenant")
   print(caps)
   ```

### Issue: Webhook returns 401

**Symptoms:** "Invalid webhook signature"

**Solutions:**
1. Disable signature verification for testing:
   ```bash
   export AUTH_DISABLED=true
   ```

2. Check webhook secret matches Stream Chat:
   - Go to Stream Chat dashboard
   - Copy webhook secret
   - Update `STREAM_WEBHOOK_SECRET` in `.env`

---

## 📊 Monitoring & Logs

### Enable Debug Logging

```python
# In app/main.py
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(name)s: %(message)s'
)
```

### Key Log Patterns

```bash
# Intent detection
grep "\[ai-reasoning\] Intent detected" logs.txt

# Context operations
grep "\[context-manager\]" logs.txt

# Policy violations
grep "\[policy-validator\]" logs.txt

# Webhook processing
grep "\[ai-webhook\]" logs.txt
```

### Useful Metrics

```bash
# Count intents processed
grep -c "Intent detected" logs.txt

# Intent distribution
grep "Intent detected" logs.txt | cut -d: -f3 | sort | uniq -c

# Average confidence
grep "confidence:" logs.txt | grep -oP '\d+\.\d+' | awk '{sum+=$1; count++} END {print sum/count}'
```

---

## 🚢 Production Deployment

### Environment Setup

1. **Set production environment variables:**
   ```bash
   export STAGE=prod
   export DYNAMO_ENDPOINT_URL=  # Empty for AWS
   export AUTH_DISABLED=false
   ```

2. **Create production DynamoDB table:**
   ```bash
   python scripts/init_context_table.py --stage prod
   ```

3. **Configure Stream Chat webhook:**
   - URL: `https://your-domain.com/ai/stream-webhook`
   - Events: `message.new`, `reaction.new`
   - Secret: Set `STREAM_WEBHOOK_SECRET`

### Security Checklist

- [ ] Enable webhook signature verification (`AUTH_DISABLED=false`)
- [ ] Use HTTPS for all endpoints
- [ ] Rotate OpenAI API key monthly
- [ ] Set up DynamoDB backup
- [ ] Enable CloudWatch logging
- [ ] Configure rate limiting
- [ ] Set up alerts for high error rates

---

## 📚 Next Steps

1. **Explore API Reference:** See `API_REFERENCE.md` for complete API docs

2. **Read Architecture Docs:** See `TRANSFORMATION_DOCUMENTATION.md` for details

3. **Customize Flows:** Edit `backend/app/config/flow_definitions.json`

4. **Add New Personas:** Update `policy_validator.py` policies

5. **Extend Intents:** Add new intent handlers in `ai_webhooks.py`

---

## 🆘 Getting Help

### Documentation
- `TRANSFORMATION_DOCUMENTATION.md` - Complete architectural overview
- `API_REFERENCE.md` - Complete API documentation
- `QUICKSTART.md` - This guide

### Code Examples
- `backend/app/services/context_manager.py` - Context management
- `backend/app/services/ai_reasoning.py` - Intent detection
- `backend/app/routes/ai_webhooks.py` - Webhook handlers

### Community
- GitHub Issues: Report bugs or request features
- Contact: [your-email@example.com]

---

## ✅ Verification Checklist

Before considering setup complete, verify:

- [ ] Backend starts without errors
- [ ] Frontend loads successfully
- [ ] DynamoDB table exists and is accessible
- [ ] OpenAI API key works (test intent detection)
- [ ] Stream Chat connection established
- [ ] Webhook receives and processes messages
- [ ] Context persists between messages
- [ ] Intent detection accuracy >80%
- [ ] Policy validation blocks forbidden actions
- [ ] Logs show detailed processing information

---

**Setup Time:** ~10 minutes
**First Message:** ~2 minutes after setup
**Ready for Production:** After testing all personas

---

🎉 **Congratulations!** You now have an intelligent, context-aware, persona-driven AI assistant running!

**Try it:**
```
User: "there's a leak in my kitchen"
Bot: "I've detected a plumbing issue and created incident INC-123..."
```

The system is now **smart as f***!** 🚀
