# LandTen Backend Architecture V3 - LLM-Driven Orchestrator

## Overview

The LandTen backend has been completely rewritten into a **universal LLM-driven orchestrator architecture**. All hardcoded business logic, classifiers, and flow engines have been removed and replaced with a single intelligent LLM orchestrator that makes all decisions.

## Core Principles

1. **Stateless Backend** - The backend is a thin execution layer
2. **LLM as Intelligence** - All decision-making flows through the LLM
3. **Function-Calling Architecture** - LLM selects and invokes functions as needed
4. **Meta-Context Driven** - Conversation state persists in DynamoDB and drives decisions
5. **No Hardcoded Rules** - Intent classification, flow logic, and responses are all LLM-generated

## Architecture Diagram

```
User Message
     ↓
[Stream Chat Webhook]
     ↓
[ai_webhooks_v3.py] ──────→ Load Meta-Context from DynamoDB
     ↓
[LLM Orchestrator] ←────── Meta-Context + User Message + Function List
     ↓
[Claude API] ──────────────→ Structured JSON Output:
     ↓                       {
     ↓                         "intent": "...",
     ↓                         "reasoning": "...",
     ↓                         "context_updates": {...},
     ↓                         "function_call": {...},
     ↓                         "response_to_user": "..."
     ↓                       }
     ↓
[Function Executor] ←────── Execute selected function
     ↓
[Meta-Context Update] ─────→ Save updated context to DynamoDB
     ↓
[Response to User] ────────→ Stream Chat message
```

## Directory Structure

```
backend/app/
├── functions/
│   ├── __init__.py
│   └── function_registry.py        # All callable tools with schemas
├── models/
│   └── orchestrator_schemas.py     # Pydantic v2 schemas
├── routes/
│   ├── ai_webhooks.py              # OLD (deprecated)
│   └── ai_webhooks_v3.py           # NEW orchestrator-based routing
├── services/
│   ├── meta_context_manager.py     # Enhanced context management
│   ├── orchestrator.py             # LLM orchestrator engine
│   ├── ai_reasoning_v2.py          # DEPRECATED
│   ├── intent_classifier.py        # DEPRECATED
│   ├── flow_engine.py              # DEPRECATED
│   └── flow_engine_v2.py           # DEPRECATED
└── config/
    └── flows/                       # DEPRECATED

system_prompts/
└── orchestrator_prompt.txt          # Universal LLM system prompt
```

## Key Components

### 1. System Prompt (`system_prompts/orchestrator_prompt.txt`)

The **single source of truth** for LLM behavior. Defines:

- How to interpret user messages
- How to use meta-context
- How to select functions
- Stage flow logic
- Persona-based authorization
- JSON output schema

**Critical:** This prompt replaces all hardcoded business logic.

### 2. Meta-Context Manager (`services/meta_context_manager.py`)

Manages conversation state in DynamoDB.

**Meta-Context Schema:**
```python
{
  "user_id": str,
  "channel_id": str,
  "persona": "tenant|landlord|contractor",
  "stage": "idle|discovery|job-ready|approval-pending|job-active|completed",
  "active_incident_id": str | null,
  "active_job_id": str | null,
  "discovery": {
    "question_index": int,
    "questions": [str],
    "answers": {str: str}
  },
  "last_intent": str,
  "last_user_message": str,
  "conversation_history": [{role, text, timestamp}],
  "entities": {},
  "metadata": {}
}
```

**Key Methods:**
- `load_context()` - Load from DynamoDB
- `save_context()` - Save to DynamoDB
- `update_context()` - Partial updates
- `merge_context_updates()` - Apply LLM updates

### 3. LLM Orchestrator (`services/orchestrator.py`)

The intelligence engine.

**Responsibilities:**
- Load system prompt
- Format meta-context for LLM
- Call Anthropic Claude API with function definitions
- Parse structured JSON output
- Handle multi-turn function calling

**Key Method:**
```python
async def run(
    user_message: str,
    meta_context: MetaContext,
    available_functions: List[FunctionDefinition],
    function_result: Optional[FunctionResult] = None,
) -> OrchestratorOutput
```

**LLM Output Schema:**
```json
{
  "intent": "incident.report",
  "reasoning": "User is reporting a plumbing leak...",
  "context_updates": {
    "stage": "discovery",
    "active_incident_id": "inc_123",
    "entities": {"category": "plumbing"}
  },
  "function_call": {
    "name": "create_incident",
    "arguments": {
      "title": "Sink leak",
      "category": "plumbing",
      "severity": "high",
      "urgency": "urgent"
    }
  },
  "response_to_user": null
}
```

### 4. Function Registry (`functions/function_registry.py`)

All available tools the LLM can invoke.

**Function Categories:**

**Incident Management:**
- `create_incident` - Create new maintenance incident
- `update_incident` - Update incident details
- `get_incident` - Retrieve incident
- `close_incident` - Mark as resolved

**Discovery:**
- `start_discovery` - Begin diagnostic questions
- `record_discovery_answer` - Save answer
- `get_discovery_status` - Check progress

**Work Orders:**
- `create_work_order` - Create job from incident
- `update_work_order` - Update job status
- `get_work_order` - Retrieve job details
- `assign_contractor` - Assign contractor

**Bids & Approval:**
- `generate_bids` - Get contractor bids
- `get_bids` - Retrieve bids
- `accept_bid` - Accept contractor bid
- `request_landlord_approval` - Submit for approval
- `process_approval_decision` - Process approval/rejection

**Information:**
- `get_user_incidents` - List user's incidents
- `get_user_jobs` - List user's jobs
- `get_property_info` - Get property details

Each function has:
- JSON schema for parameters
- Pydantic model for validation
- Async implementation
- Error handling

### 5. Routing Layer (`routes/ai_webhooks_v3.py`)

Ultra-simplified routing with no hardcoded logic.

**Message Flow:**

```python
async def handle_new_message(payload):
    1. Extract user_id, channel_id, message_text
    2. Load meta_context from DynamoDB
    3. Get available_functions list
    4. Call orchestrator.run(message, context, functions)
    5. Apply context_updates
    6. Execute function_call if requested
    7. Update context with function result
    8. Check for multi-turn (next_action)
    9. Send response_to_user to Stream Chat
    10. Append to conversation_history
```

**No classifiers. No flow engines. No intent mapping. Just orchestrator.**

### 6. Pydantic Schemas (`models/orchestrator_schemas.py`)

All data structures use Pydantic v2 for validation.

**Key Schemas:**
- `MetaContext` - Complete conversation state
- `OrchestratorOutput` - LLM response structure
- `FunctionDefinition` - Tool schema
- `FunctionResult` - Execution result
- `ContextUpdates` - Updates to apply
- All function parameter models

## Flow Examples

### Example 1: New Incident Report

**User:** "My sink is leaking"

**Step 1: Load Context**
```json
{
  "persona": "tenant",
  "stage": "idle",
  "active_incident_id": null
}
```

**Step 2: LLM Orchestrator Decides**
```json
{
  "intent": "incident.report",
  "reasoning": "User reports water leak, plumbing emergency",
  "context_updates": {
    "stage": "discovery",
    "last_intent": "incident.report"
  },
  "function_call": {
    "name": "create_incident",
    "arguments": {
      "title": "Sink leak",
      "description": "My sink is leaking",
      "category": "plumbing",
      "severity": "high",
      "urgency": "urgent"
    }
  },
  "response_to_user": null
}
```

**Step 3: Execute Function**
- Creates incident `inc_abc123`
- Sends incident card to Stream Chat
- Saves to DynamoDB

**Step 4: Multi-Turn Action**
- LLM set `context_updates.next_action = "start_discovery"`
- Orchestrator called again with function result
- LLM calls `start_discovery(incident_id="inc_abc123")`
- First discovery question sent

**Step 5: Update Context**
```json
{
  "stage": "discovery",
  "active_incident_id": "inc_abc123",
  "discovery": {
    "question_index": 0,
    "questions": ["Is the water still flowing?", ...]
  }
}
```

### Example 2: Discovery Response

**User:** "Yes it's still leaking"

**Context:**
```json
{
  "stage": "discovery",
  "active_incident_id": "inc_abc123",
  "discovery": {"question_index": 0, "questions": [...]}
}
```

**LLM Decides:**
```json
{
  "intent": "discovery.response",
  "context_updates": {
    "discovery": {"question_index": 1}
  },
  "function_call": {
    "name": "record_discovery_answer",
    "arguments": {
      "incident_id": "inc_abc123",
      "question_index": 0,
      "answer": "Yes it's still leaking"
    }
  }
}
```

**Function Executes:**
- Records answer
- Updates discovery card
- Sends next question (index 1)

### Example 3: Meta Question During Discovery

**User:** "How long will this take?"

**Context:**
```json
{
  "stage": "discovery",
  "discovery": {"question_index": 2}
}
```

**LLM Decides:**
```json
{
  "intent": "meta.info",
  "context_updates": {},
  "function_call": {"name": null},
  "response_to_user": "Once we finish these questions and create a work order, repairs typically take 1-3 days. Now, question 3: When did you first notice the leak?"
}
```

**No function executed. Stage preserved. User gets answer + next question.**

## Stage Flow Logic

All stage transitions are **LLM-controlled**, but follow this guidance:

```
idle ──[incident.report]──→ discovery
discovery ──[all questions answered]──→ job-ready
job-ready ──[job.request]──→ approval-pending
approval-pending ──[approval.decision:approved]──→ job-active
approval-pending ──[approval.decision:rejected]──→ idle
job-active ──[job completed]──→ completed
completed ──[acknowledgment]──→ idle
```

The LLM decides when to transition based on:
- User message
- Current stage
- Meta-context state
- Function results

## Persona Authorization

Enforced by **LLM**, guided by system prompt:

**Tenant:**
- ✅ Report incidents
- ✅ Answer discovery questions
- ✅ Request work orders
- ✅ View status
- ❌ Approve jobs
- ❌ View bids
- ❌ Assign contractors

**Landlord:**
- ✅ Everything tenant can do
- ✅ Approve/reject jobs
- ✅ View bids
- ✅ Assign contractors
- ✅ Manage costs

**Contractor:**
- ✅ View assigned jobs
- ✅ Submit bids
- ✅ Update job status
- ❌ Create incidents
- ❌ Approve jobs

**If unauthorized action attempted:** LLM responds with explanation, no function called.

## DynamoDB Tables

### Chat Contexts Table
```
Table: {prefix}_{stage}_chat_contexts
PK: user#{user_id}
SK: channel#{channel_id}
TTL: 24 hours
```

### Incidents Table
```
Table: landten_incidents
PK: incident_id
Fields: user_id, property_id, title, description, category, severity, urgency, status, channel_id
```

### Jobs Table
```
Table: landten_jobs
PK: job_id
Fields: incident_id, property_id, landlord_id, contractor_id, title, category, estimated_cost, status
```

### Bids Table
```
Table: landten_job_bids
PK: bid_id
Fields: job_id, contractor_id, quote, eta, rating, status
```

## Configuration

### Environment Variables

```bash
# LLM Configuration
ANTHROPIC_API_KEY=sk-ant-...
ORCHESTRATOR_MODEL=claude-3-5-sonnet-20241022
ORCHESTRATOR_TEMPERATURE=0.3

# Stream Chat
STREAM_CHAT_API_KEY=...
STREAM_CHAT_API_SECRET=...
STREAM_WEBHOOK_SECRET=...

# DynamoDB
AWS_REGION=us-east-1
TABLE_PREFIX=landten
STAGE=dev

# Context TTL
CONTEXT_TTL_HOURS=24
```

### System Prompt Location

```
system_prompts/orchestrator_prompt.txt
```

Modify this file to change LLM behavior without code changes.

## Migration from V2

### Deprecated Services

**DO NOT USE:**
- ❌ `ai_reasoning_v2.py`
- ❌ `intent_classifier.py`
- ❌ `flow_engine.py`
- ❌ `flow_engine_v2.py`
- ❌ `flow_stage_mapper.py`
- ❌ `flow_state_machine.py`

**Use Instead:**
- ✅ `orchestrator.py`
- ✅ `meta_context_manager.py`
- ✅ `function_registry.py`

### Deprecated Routes

**DO NOT USE:**
- ❌ `ai_webhooks.py` (old routing)

**Use Instead:**
- ✅ `ai_webhooks_v3.py` (orchestrator-based)

### Context Manager Changes

**Old:** `services/context_manager.py`
**New:** `services/meta_context_manager.py`

**Key Differences:**
- Pydantic v2 schemas
- Simplified API
- Better type safety
- Meta-context focused

## Testing

### Test LLM Orchestrator

```python
from app.services.orchestrator import get_orchestrator
from app.models.orchestrator_schemas import MetaContext
from app.functions.function_registry import get_function_definitions

orchestrator = get_orchestrator()
meta_context = MetaContext(
    user_id="test_user",
    channel_id="test_channel",
    persona="tenant",
    stage="idle"
)

result = await orchestrator.run(
    user_message="My faucet is broken",
    meta_context=meta_context,
    available_functions=get_function_definitions()
)

print(result.intent)
print(result.function_call.name)
```

### Test Function Execution

```python
from app.functions.function_registry import execute_function

result = await execute_function(
    function_name="create_incident",
    arguments={
        "title": "Test incident",
        "description": "Test",
        "category": "plumbing",
        "severity": "low",
        "urgency": "routine"
    },
    context={"user_id": "test", "channel_id": "test"}
)

print(result.success)
print(result.data)
```

## Performance Considerations

### LLM Latency
- Typical response: 1-3 seconds
- Uses Claude 3.5 Sonnet (fast model)
- Stream response when possible

### Function Execution
- Most functions: <100ms
- DynamoDB operations: <50ms
- Stream Chat API: 100-300ms

### Total Request Time
- Simple message: 1-2 seconds
- With function call: 1.5-3 seconds
- Multi-turn: 3-5 seconds

### Optimization Strategies
1. Use haiku model for simple intents (future)
2. Cache function results when possible
3. Parallel function execution (future)
4. Streaming LLM responses (future)

## Monitoring & Logging

All logs use structured logging:

```python
logger.info(f"Orchestrator result: intent={intent}, function={func}")
logger.debug(f"Context updates: {updates}")
logger.error(f"Function error: {error}", exc_info=True)
```

**Key Metrics to Monitor:**
- LLM latency (p50, p95, p99)
- Function execution time
- Error rate per function
- Intent distribution
- Stage transition flow

## Future Enhancements

1. **Streaming Responses** - Stream LLM output as it generates
2. **Tool Result Parsing** - Let LLM parse function results and decide next action
3. **Multi-Agent Orchestration** - Specialized agents for complex tasks
4. **Adaptive Prompting** - Persona-specific system prompts
5. **Feedback Loop** - Use reactions to improve responses
6. **Cost Optimization** - Use smaller models for simple intents
7. **Caching Layer** - Cache common LLM responses

## Support

For issues or questions:
- Check system prompt first
- Review orchestrator logs
- Test function execution independently
- Validate meta-context state

## Summary

The V3 architecture is **radically simpler** than V2:

- **1 system prompt file** (instead of 6+ services)
- **1 orchestrator engine** (instead of classifiers + flow engines)
- **1 routing handler** (instead of intent-specific handlers)
- **Meta-context driven** (clear state management)
- **Function calling** (extensible tool system)

**Everything flows through the LLM. No hardcoded logic. Pure intelligence.**
