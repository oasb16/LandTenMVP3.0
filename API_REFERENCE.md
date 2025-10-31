# PropertyAI Intelligent System - API Reference

Complete API documentation for the intelligent context-aware ecosystem.

---

## Table of Contents

1. [Context Manager API](#context-manager-api)
2. [AI Reasoning API](#ai-reasoning-api)
3. [Policy Validator API](#policy-validator-api)
4. [Webhook Handler API](#webhook-handler-api)
5. [Flow Definitions Schema](#flow-definitions-schema)
6. [Usage Examples](#usage-examples)

---

## Context Manager API

**Module:** `app.services.context_manager`

### Singleton Access

```python
from app.services.context_manager import get_context_manager

context_manager = get_context_manager()
```

### Methods

#### `get_context(user_id: str, channel_id: str, create_if_missing: bool = True) → Optional[Dict]`

Retrieve conversation context for a user in a channel.

**Parameters:**
- `user_id` (str): The user's unique identifier
- `channel_id` (str): The channel identifier
- `create_if_missing` (bool): Auto-create context if none exists (default: True)

**Returns:**
- `Dict`: Context dictionary (see schema below)
- `None`: If not found and `create_if_missing=False`

**Example:**
```python
context = context_manager.get_context("user-123", "channel-abc")

print(context["flow_type"])        # "incident"
print(context["active_incident_id"]) # "INC-789"
print(len(context["conversation_history"])) # 5
```

**Context Schema:**
```python
{
    "context_id": str,              # "user_id:channel_id"
    "user_id": str,
    "channel_id": str,
    "persona": Optional[str],       # "tenant" | "landlord" | "contractor"
    "flow_type": str,               # "incident" | "job" | "bid" | "discovery" | "general"
    "flow_state": str,              # "idle" | "in_progress" | "completed"
    "active_incident_id": Optional[str],
    "active_job_id": Optional[str],
    "last_intent": Optional[str],
    "last_message": Optional[str],
    "last_message_at": Optional[str],
    "entities": Dict[str, Any],     # Extracted entities
    "discovery_progress": Dict,
    "policy_state": Dict,
    "conversation_history": List[Dict],
    "metadata": Dict,
    "created_at": str,              # ISO 8601 timestamp
    "updated_at": str,
    "expires_at": str               # TTL timestamp
}
```

---

#### `update_context(user_id: str, channel_id: str, updates: Dict, append_to_history: Optional[Dict] = None) → bool`

Update context with new information.

**Parameters:**
- `user_id` (str): User identifier
- `channel_id` (str): Channel identifier
- `updates` (Dict): Fields to update (merged with existing context)
- `append_to_history` (Optional[Dict]): Message to append to history

**Returns:**
- `bool`: True if successful, False otherwise

**Example:**
```python
# Update context fields
success = context_manager.update_context(
    user_id="user-123",
    channel_id="channel-abc",
    updates={
        "flow_type": "incident",
        "entities": {"category": "plumbing", "severity": "high"}
    }
)

# Update and append message
success = context_manager.update_context(
    user_id="user-123",
    channel_id="channel-abc",
    updates={"last_intent": "incident.report"},
    append_to_history={
        "role": "user",
        "content": "there's a leak in my kitchen"
    }
)
```

---

#### `append_message(user_id: str, channel_id: str, role: str, content: str) → bool`

Append a message to conversation history.

**Parameters:**
- `user_id` (str): User identifier
- `channel_id` (str): Channel identifier
- `role` (str): "user" or "assistant"
- `content` (str): Message content

**Returns:**
- `bool`: True if successful

**Example:**
```python
# User message
context_manager.append_message(
    user_id="user-123",
    channel_id="channel-abc",
    role="user",
    content="Is this urgent?"
)

# Assistant response
context_manager.append_message(
    user_id="user-123",
    channel_id="channel-abc",
    role="assistant",
    content="Based on your description, this seems to be a medium severity issue."
)
```

---

#### `set_persona(user_id: str, channel_id: str, persona: str) → bool`

Set the persona for a context.

**Parameters:**
- `persona` (str): "tenant" | "landlord" | "contractor"

---

#### `set_flow(user_id: str, channel_id: str, flow_type: str, flow_state: str = "in_progress") → bool`

Set the active flow type and state.

**Parameters:**
- `flow_type` (str): "incident" | "job" | "bid" | "discovery" | "general"
- `flow_state` (str): "idle" | "in_progress" | "completed"

---

#### `set_active_incident(user_id: str, channel_id: str, incident_id: str) → bool`

Set the active incident ID and switch flow to "incident".

---

#### `set_active_job(user_id: str, channel_id: str, job_id: str) → bool`

Set the active job ID and switch flow to "job".

---

#### `get_conversation_history(user_id: str, channel_id: str, limit: Optional[int] = None) → List[Dict]`

Get conversation history for a context.

**Parameters:**
- `limit` (Optional[int]): Max number of messages to return (most recent)

**Returns:**
- `List[Dict]`: List of messages with format:
  ```python
  [
      {"role": "user", "content": "...", "timestamp": "2025-10-31T12:00:00Z"},
      {"role": "assistant", "content": "...", "timestamp": "2025-10-31T12:00:05Z"}
  ]
  ```

---

#### `clear_context(user_id: str, channel_id: str) → bool`

Clear/reset a context (starts fresh).

---

#### `get_active_flows(user_id: str, channel_id: str) → Dict`

Get summary of active flows.

**Returns:**
```python
{
    "has_active_incident": bool,
    "has_active_job": bool,
    "active_incident_id": Optional[str],
    "active_job_id": Optional[str],
    "flow_type": str,
    "flow_state": str,
    "last_intent": Optional[str],
    "discovery_in_progress": bool
}
```

---

## AI Reasoning API

**Module:** `app.services.ai_reasoning`

### Singleton Access

```python
from app.services.ai_reasoning import get_ai_reasoning

ai_reasoning = get_ai_reasoning()
```

### Methods

#### `infer_intent(message: str, context: Dict, persona: str) → Dict`

Infer user intent from a message using LLM reasoning.

**Parameters:**
- `message` (str): User's message text
- `context` (Dict): Current conversation context
- `persona` (str): User's persona

**Returns:**
```python
{
    "intent": str,          # Intent enum value (e.g., "incident.report")
    "confidence": float,    # 0.0 - 1.0
    "entities": Dict,       # Extracted entities
    "next_actions": List[str],  # Suggested actions
    "card_type": str,       # Card type to show
    "reasoning": str        # Explanation of classification
}
```

**Supported Intents:**
- `incident.report` - New property issue
- `incident.followup` - More info about existing incident
- `discovery.response` - Answering discovery questions
- `discovery.continue` - Continue discovery
- `job.request` - Request work order
- `job.inquiry` - Ask about job
- `job.status` - Job status check
- `bids.request` - View contractor bids
- `bids.compare` - Compare bids
- `approval.request` - Request approval
- `approval.decision` - Approve/reject
- `general.chat` - General conversation
- `greeting` - Hello messages
- `help` - Help requests
- `unclear` - Ambiguous intent

**Example:**
```python
result = ai_reasoning.infer_intent(
    message="my kitchen sink is leaking badly",
    context=current_context,
    persona="tenant"
)

print(result)
# {
#     "intent": "incident.report",
#     "confidence": 0.95,
#     "entities": {
#         "category": "plumbing",
#         "location": "kitchen",
#         "severity": "high",
#         "symptoms": ["leak", "water"]
#     },
#     "next_actions": ["create_incident", "start_discovery"],
#     "card_type": "incident",
#     "reasoning": "User reporting urgent plumbing issue"
# }
```

**Fallback Behavior:**
- If LLM fails, falls back to rule-based keyword matching
- Ensures 99.9% availability
- Fallback confidence typically 0.6-0.7

---

#### `extract_entities(message: str, intent: str, persona: str) → Dict`

Extract structured entities from a message.

**Parameters:**
- `message` (str): User's message
- `intent` (str): Detected intent
- `persona` (str): User's persona

**Returns:**
```python
{
    "category": Optional[str],      # "plumbing" | "electrical" | "hvac" | ...
    "severity": Optional[str],      # "low" | "medium" | "high" | "emergency"
    "urgency": Optional[str],       # "routine" | "urgent" | "immediate"
    "location": Optional[str],      # "kitchen" | "bathroom" | ...
    "symptoms": Optional[List[str]],
    "cost_estimate": Optional[float],
    "timeline": Optional[str],
    "contractor_name": Optional[str],
    ...
}
```

**Example:**
```python
entities = ai_reasoning.extract_entities(
    message="The bathroom ceiling is dripping water, it started yesterday",
    intent="incident.report",
    persona="tenant"
)

print(entities)
# {
#     "category": "plumbing",
#     "location": "bathroom",
#     "symptoms": ["dripping", "water"],
#     "duration": "1 day"
# }
```

---

#### `generate_response_plan(intent: str, entities: Dict, context: Dict, persona: str) → Dict`

Generate a comprehensive response plan based on intent.

**Returns:**
```python
{
    "response_type": str,       # "card" | "message" | "hybrid"
    "card_type": str,           # Card type if applicable
    "message_text": str,        # Message to send
    "actions": List[Dict],      # Action buttons
    "metadata": Dict,           # Metadata to attach
    "should_update_context": bool,
    "context_updates": Dict     # Fields to update in context
}
```

---

## Policy Validator API

**Module:** `app.services.policy_validator`

### Singleton Access

```python
from app.services.policy_validator import get_policy_validator

policy_validator = get_policy_validator()
```

### Methods

#### `validate_intent(intent: str, persona: str) → Tuple[bool, Optional[str]]`

Validate if a persona is allowed to perform an intent.

**Parameters:**
- `intent` (str): Intent to validate
- `persona` (str): User's persona

**Returns:**
- `Tuple[bool, Optional[str]]`: (is_valid, error_message)

**Example:**
```python
is_valid, error = policy_validator.validate_intent(
    intent="approval.decision",
    persona="tenant"
)

if not is_valid:
    print(error)
    # "I appreciate your initiative, but job approvals need to be
    #  handled by your landlord. I've notified them of your request!"
```

---

#### `validate_action(action: str, persona: str) → Tuple[bool, Optional[str]]`

Validate if a persona is allowed to perform an action.

**Parameters:**
- `action` (str): Action name (e.g., "approve_job", "create_incident")
- `persona` (str): User's persona

**Example:**
```python
is_valid, error = policy_validator.validate_action(
    action="approve_contractor",
    persona="contractor"
)

# Returns: (False, "That action requires landlord permissions...")
```

---

#### `validate_cost_approval(cost: float, persona: str) → Tuple[bool, str]`

Validate if a persona can approve a cost amount.

**Parameters:**
- `cost` (float): Cost amount in dollars
- `persona` (str): User's persona

**Returns:**
- `Tuple[bool, str]`: (can_auto_approve, approval_type)
  - `approval_type`: "auto-approve" | "recommended-review" | "manual-approval"

**Example:**
```python
can_approve, approval_type = policy_validator.validate_cost_approval(
    cost=450.00,
    persona="landlord"
)

# Landlord max_auto_approve = $500
# Returns: (True, "auto-approve")

can_approve, approval_type = policy_validator.validate_cost_approval(
    cost=750.00,
    persona="landlord"
)

# Returns: (False, "recommended-review")
```

---

#### `can_access_data(persona: str, data_type: str, resource_owner: Optional[str], user_id: Optional[str]) → bool`

Check if a persona can access specific data.

**Parameters:**
- `persona` (str): User's persona
- `data_type` (str): "incidents" | "jobs" | "bids" | "costs"
- `resource_owner` (Optional[str]): Owner of the resource
- `user_id` (Optional[str]): Current user ID

**Example:**
```python
# Can tenant view their own incident?
can_view = policy_validator.can_access_data(
    persona="tenant",
    data_type="incidents",
    resource_owner="tenant-123",
    user_id="tenant-123"
)
# Returns: True

# Can tenant view all incidents?
can_view = policy_validator.can_access_data(
    persona="tenant",
    data_type="incidents",
    resource_owner="other-tenant",
    user_id="tenant-123"
)
# Returns: False

# Can landlord view all incidents?
can_view = policy_validator.can_access_data(
    persona="landlord",
    data_type="incidents",
    resource_owner="any",
    user_id="landlord-456"
)
# Returns: True
```

---

#### `get_message_guidelines(persona: str) → Dict`

Get message generation guidelines for a persona.

**Returns:**
```python
{
    "tone": str,                      # Message tone
    "can_provide_diy_tips": bool,
    "can_provide_cost_estimates": bool,
    "must_include_safety_warnings": bool
}
```

**Example:**
```python
guidelines = policy_validator.get_message_guidelines("tenant")

print(guidelines)
# {
#     "tone": "friendly, helpful, empathetic",
#     "can_provide_diy_tips": True,
#     "can_provide_cost_estimates": False,
#     "must_include_safety_warnings": True
# }
```

---

#### `get_persona_capabilities(persona: str) → Dict`

Get a summary of what a persona can and cannot do.

**Returns:**
```python
{
    "persona": str,
    "allowed_intents": List[str],
    "forbidden_actions": List[str],
    "can_create_incident": bool,
    "can_approve_work": bool,
    "can_view_bids": bool,
    "max_auto_approve_amount": float,
    "data_access": Dict,
    "message_guidelines": Dict
}
```

---

## Webhook Handler API

**Module:** `app.routes.ai_webhooks`

### Endpoints

#### `POST /ai/stream-webhook`

Main webhook endpoint for Stream Chat events.

**Request Headers:**
- `x-signature`: HMAC SHA256 signature for verification

**Request Body:**
```json
{
  "type": "message.new",
  "channel_id": "channel-123",
  "user": {
    "id": "user-456",
    "name": "John Doe"
  },
  "message": {
    "text": "there's a leak in my bathroom",
    "metadata": {
      "agentEnabled": true
    }
  }
}
```

**Response:**
```json
{
  "status": "processed",
  "intent": "incident.report",
  "confidence": 0.95,
  "channel_id": "channel-123",
  "result": {
    "response_text": "I've detected an issue...",
    "incident_id": "INC-789",
    "action": "incident_created"
  }
}
```

**Event Types Handled:**
- `message.new` - New user message
- `message.updated` - Message edited
- `reaction.new` - User reaction to message
- `health.check` - Health check ping

---

#### `POST /ai/init-channel`

Initialize a channel with AI bot.

**Request:**
```json
{
  "channel_id": "tenant-general",
  "persona": "tenant"
}
```

**Response:**
```json
{
  "status": "success",
  "channel_id": "tenant-general",
  "bot_id": "ai-tenant-bot",
  "persona": "tenant",
  "message": "AI bot ensured and ready for tenant persona"
}
```

---

#### `GET /ai/bot-status`

Get AI bot status and configuration.

**Response:**
```json
{
  "status": "active",
  "service": "PropertyAI Bot System",
  "version": "1.0",
  "bots": {
    "tenant": {
      "id": "ai-tenant-bot",
      "name": "PropertyHelper",
      "description": "AI assistant for tenants"
    },
    "landlord": { ... },
    "contractor": { ... }
  },
  "configuration": {
    "webhook_secret_configured": true,
    "stream_api_key_configured": true,
    "stream_api_secret_configured": true
  }
}
```

---

## Flow Definitions Schema

**File:** `backend/app/config/flow_definitions.json`

### Structure

```json
{
  "flows": {
    "flow_name": {
      "name": "Display Name",
      "description": "Flow description",
      "personas": ["tenant", "landlord"],
      "entry_intents": ["intent.type"],
      "states": {
        "state_name": {
          "description": "State description",
          "actions": ["action1", "action2"],
          "next_states": ["state2", "state3"],
          "card_type": "incident",
          "metadata": { ... }
        }
      }
    }
  },
  "card_templates": { ... },
  "routing_hints": { ... }
}
```

### Example Flow

```json
{
  "incident_report": {
    "name": "Incident Report Flow",
    "personas": ["tenant", "landlord"],
    "entry_intents": ["incident.report"],
    "states": {
      "detection": {
        "actions": ["create_incident_record", "send_incident_card"],
        "next_states": ["discovery", "dismissed"],
        "card_type": "incident"
      },
      "discovery": {
        "actions": ["start_discovery", "ask_questions"],
        "next_states": ["work_order", "resolved"],
        "card_type": "discovery",
        "metadata": {
          "min_questions": 3,
          "adaptive": true
        }
      }
    }
  }
}
```

---

## Usage Examples

### Complete Conversation Flow

```python
from app.services.context_manager import get_context_manager
from app.services.ai_reasoning import get_ai_reasoning
from app.services.policy_validator import get_policy_validator
from app.services.stream_bot import get_bot

# Initialize services
context_manager = get_context_manager()
ai_reasoning = get_ai_reasoning()
policy_validator = get_policy_validator()
bot = get_bot()

# User info
user_id = "tenant-123"
channel_id = "general-chat"
persona = "tenant"

# Step 1: Get or create context
context = context_manager.get_context(user_id, channel_id)

# Step 2: User sends message
message = "my kitchen sink is leaking"

# Step 3: Infer intent
intent_result = ai_reasoning.infer_intent(message, context, persona)

intent = intent_result["intent"]  # "incident.report"
entities = intent_result["entities"]  # {category: "plumbing", ...}

# Step 4: Validate against policy
is_valid, error = policy_validator.validate_intent(intent, persona)

if not is_valid:
    bot.send_message(channel_id, bot.get_bot_id(persona), error)
else:
    # Step 5: Update context
    context_manager.update_context(
        user_id, channel_id,
        {"last_intent": intent, "entities": entities}
    )
    context_manager.append_message(user_id, channel_id, "user", message)

    # Step 6: Handle intent (create incident, send card, etc.)
    # ... handler logic ...

    # Step 7: Append bot response
    context_manager.append_message(
        user_id, channel_id,
        "assistant",
        "I've detected a plumbing issue and created an incident."
    )
```

### Testing Intent Detection

```python
# Test various messages
test_messages = [
    "there's water everywhere in my bathroom",
    "can you show me the contractor bids?",
    "I approve that job",
    "what's the status of my repair?",
    "hello"
]

for msg in test_messages:
    result = ai_reasoning.infer_intent(msg, {}, "tenant")
    print(f"Message: {msg}")
    print(f"Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
    print(f"Entities: {result['entities']}")
    print()
```

### Policy Validation Examples

```python
# Test tenant trying to approve job
is_valid, error = policy_validator.validate_action("approve_job", "tenant")
# Returns: (False, "I appreciate your initiative, but job approvals...")

# Test landlord approving $400 job
can_approve, type_ = policy_validator.validate_cost_approval(400, "landlord")
# Returns: (True, "auto-approve")

# Test contractor viewing bids
can_view = policy_validator.can_access_data("contractor", "bids", None, None)
# Returns: False (contractors can't see other bids)
```

---

## Error Handling

### Context Manager

```python
try:
    context = context_manager.get_context(user_id, channel_id)
except Exception as e:
    logger.error(f"Context retrieval failed: {e}")
    # Fallback: create minimal context
    context = {"persona": "tenant", "flow_type": "general"}
```

### AI Reasoning

```python
try:
    result = ai_reasoning.infer_intent(message, context, persona)
except Exception as e:
    logger.error(f"Intent inference failed: {e}")
    # Fallback: use rule-based detection
    result = {
        "intent": "general.chat",
        "confidence": 0.5,
        "entities": {},
        "card_type": "none"
    }
```

---

## Configuration

### Environment Variables

```bash
# AI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini              # Default: gpt-4o-mini
OPENAI_TEMPERATURE=0.3                 # Default: 0.3

# Context Configuration
CONTEXT_TTL_HOURS=24                   # Default: 24
CONTEXT_MAX_HISTORY=20                 # Default: 20

# DynamoDB
TABLE_PREFIX=landtenmvp                # Default: landtenmvp
STAGE=dev                              # Default: dev
AWS_REGION=us-east-1                   # Default: us-east-1
DYNAMO_ENDPOINT_URL=http://localhost:8000  # Optional (local dev)
```

---

## Performance Considerations

### Context Retrieval
- **Latency:** ~50ms (DynamoDB single-item read)
- **Cost:** ~$0.25 per million reads

### Intent Detection
- **Latency:** ~500-1500ms (OpenAI API call)
- **Cost:** ~$0.15 per 1M tokens (gpt-4o-mini)
- **Fallback:** <10ms (rule-based, if LLM fails)

### Recommendations
- Cache contexts in memory for high-frequency users
- Batch context updates where possible
- Use fallback intent detection for cost-sensitive deployments

---

## Security

### Authentication
- Webhook signature verification (HMAC SHA256)
- Stream Chat user tokens
- Persona-based authorization

### Data Protection
- Context data encrypted at rest (DynamoDB)
- Conversation history limited to 20 messages
- Automatic TTL expiration (24 hours)
- No PII logged

---

## Support & Troubleshooting

### Common Issues

**1. Context not persisting**
- Check DynamoDB table exists: `landtenmvp_dev_chat_contexts`
- Verify AWS credentials configured
- Check TTL hasn't expired

**2. Intent detection failing**
- Verify `OPENAI_API_KEY` is set
- Check OpenAI API quota
- Fallback to rule-based should activate automatically

**3. Policy violations**
- Check persona is correctly set in context
- Verify policy rules in `policy_validator.py`
- Check logs for violation messages

### Debug Logging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Logs will show:
```
[ai-webhook] ========== Incoming Message ==========
[ai-webhook] Context retrieved: flow_type=incident
[ai-webhook] Intent detected: incident.report (confidence: 0.95)
[ai-webhook] ✅ SUCCESS: Intent handled
```

---

**Last Updated:** October 31, 2025
**Version:** 1.0.0
**Status:** Production Ready ✅
