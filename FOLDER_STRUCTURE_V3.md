# LandTen V3 Folder Structure

## Complete File Map

```
LandTenMVP3.0/
│
├── system_prompts/
│   └── orchestrator_prompt.txt          ✅ NEW - Universal LLM system prompt
│
├── backend/
│   └── app/
│       │
│       ├── functions/                    ✅ NEW - Function registry module
│       │   ├── __init__.py
│       │   └── function_registry.py     ✅ All callable tools with implementations
│       │
│       ├── models/
│       │   ├── user.py
│       │   └── orchestrator_schemas.py  ✅ NEW - Pydantic v2 schemas
│       │
│       ├── services/
│       │   ├── orchestrator.py          ✅ NEW - LLM orchestrator engine
│       │   ├── meta_context_manager.py  ✅ NEW - Enhanced context management
│       │   │
│       │   ├── ai_reasoning_v2.py       ⛔ DEPRECATED
│       │   ├── intent_classifier.py     ⛔ DEPRECATED
│       │   ├── flow_engine.py           ⛔ DEPRECATED
│       │   ├── flow_engine_v2.py        ⛔ DEPRECATED
│       │   ├── flow_stage_mapper.py     ⛔ DEPRECATED
│       │   ├── flow_state_machine.py    ⛔ DEPRECATED
│       │   │
│       │   ├── stream_bot.py            ✅ KEEP - Stream Chat integration
│       │   ├── dynamo_service.py        ✅ KEEP - DynamoDB operations
│       │   ├── card_builder.py          ✅ KEEP - Stream Chat cards
│       │   ├── incident_flow.py         ✅ KEEP - Incident utilities
│       │   ├── policy_validator.py      ✅ KEEP - Persona policies
│       │   ├── approval_workflow.py     ✅ KEEP - Approval logic
│       │   ├── bid_generator.py         ✅ KEEP - Bid generation
│       │   └── context_manager.py       ⛔ DEPRECATED (replaced by meta_context_manager)
│       │
│       ├── routes/
│       │   ├── ai_webhooks_v3.py        ✅ NEW - Orchestrator-based routing
│       │   ├── ai_webhooks.py           ⛔ DEPRECATED (old routing)
│       │   │
│       │   ├── chat.py                  ✅ KEEP
│       │   ├── incident.py              ✅ KEEP
│       │   ├── job.py                   ✅ KEEP
│       │   ├── contractor.py            ✅ KEEP
│       │   └── ... (other routes)       ✅ KEEP
│       │
│       ├── config/
│       │   ├── flows/                   ⛔ DEPRECATED (no longer used)
│       │   │   ├── communication.json
│       │   │   └── maintenance.json
│       │   ├── flow_definitions.json    ⛔ DEPRECATED
│       │   └── settings.py              ✅ KEEP
│       │
│       ├── repos/                       ✅ KEEP ALL
│       │   ├── incident_repo.py
│       │   ├── job_repo.py
│       │   └── ... (all repos)
│       │
│       ├── deps/                        ✅ KEEP ALL
│       │   ├── dynamo.py
│       │   ├── stream_signing.py
│       │   └── ...
│       │
│       ├── utils/                       ✅ KEEP ALL
│       │   ├── logging.py
│       │   └── ...
│       │
│       └── main.py                      ✅ KEEP
│
├── ARCHITECTURE_V3.md                   ✅ NEW - Complete architecture docs
├── FOLDER_STRUCTURE_V3.md               ✅ NEW - This file
└── README.md                            (existing)
```

## New Files Summary

### Critical New Files

1. **`system_prompts/orchestrator_prompt.txt`**
   - Single source of truth for LLM behavior
   - Replaces all hardcoded intent classification logic
   - Defines function selection rules
   - Specifies JSON output schema

2. **`backend/app/services/orchestrator.py`**
   - LLM orchestrator engine
   - Handles Anthropic API calls
   - Formats context for LLM
   - Parses structured responses

3. **`backend/app/services/meta_context_manager.py`**
   - Enhanced context management
   - Pydantic v2 based
   - Simplified API
   - Better error handling

4. **`backend/app/functions/function_registry.py`**
   - All callable tools
   - Function implementations
   - JSON schemas for LLM
   - Execution layer

5. **`backend/app/models/orchestrator_schemas.py`**
   - All Pydantic v2 models
   - Type-safe schemas
   - Validation logic

6. **`backend/app/routes/ai_webhooks_v3.py`**
   - New routing layer
   - No hardcoded logic
   - Pure orchestrator-based

### Documentation Files

7. **`ARCHITECTURE_V3.md`**
   - Complete architecture guide
   - Flow examples
   - Migration guide
   - Testing instructions

8. **`FOLDER_STRUCTURE_V3.md`**
   - This file
   - File organization
   - What to keep/deprecate

## Files to Deprecate

### Do NOT Delete (backward compatibility)

Keep these files but mark as deprecated:

```
backend/app/services/
├── ai_reasoning_v2.py          # Old intent classification
├── intent_classifier.py        # Multi-layer classifier
├── flow_engine.py              # Simple flow engine
├── flow_engine_v2.py           # Advanced flow engine
├── flow_stage_mapper.py        # Stage mapping
├── flow_state_machine.py       # State machine
└── context_manager.py          # Old context manager

backend/app/routes/
└── ai_webhooks.py              # Old routing layer

backend/app/config/flows/
├── communication.json          # Flow definitions
└── maintenance.json            # Flow definitions

backend/app/config/
└── flow_definitions.json       # Flow definitions
```

### Why Keep Them?

1. **Backward compatibility** - Some routes might still import them
2. **Gradual migration** - Allow testing before full cutover
3. **Reference** - Useful for understanding old logic

### How to Migrate

In `backend/app/main.py`, add both routes:

```python
from app.routes import ai_webhooks        # OLD
from app.routes import ai_webhooks_v3     # NEW

# Register both
app.include_router(ai_webhooks.router, tags=["ai-v2"])
app.include_router(ai_webhooks_v3.router, tags=["ai-v3"])
```

Then gradually migrate endpoints:
- `/ai/stream-webhook` → handled by v3
- `/ai/init-channel` → handled by v3
- `/ai/bot-status` → handled by v3

## Files to Keep (No Changes)

### DynamoDB Layer
```
backend/app/services/
└── dynamo_service.py           ✅ KEEP - Database operations
```

### Stream Chat Integration
```
backend/app/services/
├── stream_bot.py               ✅ KEEP - Bot messaging
└── card_builder.py             ✅ KEEP - Card UI
```

### Utility Services
```
backend/app/services/
├── incident_flow.py            ✅ KEEP - Incident utilities (classify_issue, etc.)
├── policy_validator.py         ✅ KEEP - Persona authorization
├── approval_workflow.py        ✅ KEEP - Approval logic
├── bid_generator.py            ✅ KEEP - Mock bid generation
├── mttr_calculator.py          ✅ KEEP - Metrics
└── notification_service.py     ✅ KEEP - Notifications
```

### Repositories
```
backend/app/repos/
├── incident_repo.py            ✅ KEEP
├── job_repo.py                 ✅ KEEP
├── contractor_repo.py          ✅ KEEP
└── ... (all other repos)       ✅ KEEP
```

### Dependencies
```
backend/app/deps/
├── dynamo.py                   ✅ KEEP
├── stream_signing.py           ✅ KEEP
├── pusher_client.py            ✅ KEEP
└── auth.py                     ✅ KEEP
```

### Other Routes
```
backend/app/routes/
├── chat.py                     ✅ KEEP
├── incident.py                 ✅ KEEP
├── job.py                      ✅ KEEP
├── contractor.py               ✅ KEEP
├── property.py                 ✅ KEEP
└── ... (all other routes)      ✅ KEEP
```

## Integration Points

### How V3 Uses Existing Services

```python
# V3 orchestrator uses these existing services:

from app.services.dynamo_service import get_dynamo_service
# ✅ Used by function_registry.py for database operations

from app.services.stream_bot import get_stream_bot
# ✅ Used by function_registry.py for sending cards/messages

from app.services.card_builder import incident_card, work_order_card
# ✅ Used by stream_bot.py to build card UI

from app.services.incident_flow import classify_issue, generate_contractor_bids
# ✅ Used by function_registry.py for incident classification

from app.services.policy_validator import get_policy_validator
# ⚠️  Optional - LLM handles authorization, but can be used as safety check
```

## Testing Strategy

### Test New Architecture

```bash
# Test orchestrator
pytest tests/test_orchestrator.py

# Test function registry
pytest tests/test_function_registry.py

# Test meta-context manager
pytest tests/test_meta_context_manager.py

# Test end-to-end
pytest tests/test_ai_webhooks_v3.py
```

### Gradual Rollout

1. **Phase 1:** Deploy V3 alongside V2
2. **Phase 2:** Route 10% of traffic to V3
3. **Phase 3:** Monitor metrics, increase to 50%
4. **Phase 4:** Full cutover to V3
5. **Phase 5:** Deprecate V2 files

## Environment Setup

### Required Environment Variables

```bash
# New for V3
ANTHROPIC_API_KEY=sk-ant-...
ORCHESTRATOR_MODEL=claude-3-5-sonnet-20241022
ORCHESTRATOR_TEMPERATURE=0.3

# Existing (still needed)
STREAM_CHAT_API_KEY=...
STREAM_CHAT_API_SECRET=...
AWS_REGION=us-east-1
TABLE_PREFIX=landten
STAGE=dev
```

## File Dependencies

### Critical Dependencies

```
ai_webhooks_v3.py
├── depends on → orchestrator.py
├── depends on → meta_context_manager.py
├── depends on → function_registry.py
└── depends on → stream_bot.py

orchestrator.py
├── depends on → orchestrator_prompt.txt (system prompt file)
├── depends on → orchestrator_schemas.py
└── depends on → anthropic library

function_registry.py
├── depends on → dynamo_service.py
├── depends on → stream_bot.py
├── depends on → incident_flow.py
└── depends on → orchestrator_schemas.py

meta_context_manager.py
├── depends on → orchestrator_schemas.py
├── depends on → boto3 (DynamoDB)
└── depends on → settings.py
```

## Summary

### ✅ New Architecture Files (7 files)

1. `system_prompts/orchestrator_prompt.txt`
2. `backend/app/services/orchestrator.py`
3. `backend/app/services/meta_context_manager.py`
4. `backend/app/functions/__init__.py`
5. `backend/app/functions/function_registry.py`
6. `backend/app/models/orchestrator_schemas.py`
7. `backend/app/routes/ai_webhooks_v3.py`

### ⛔ Deprecated Files (9 files)

1. `backend/app/services/ai_reasoning_v2.py`
2. `backend/app/services/intent_classifier.py`
3. `backend/app/services/flow_engine.py`
4. `backend/app/services/flow_engine_v2.py`
5. `backend/app/services/flow_stage_mapper.py`
6. `backend/app/services/flow_state_machine.py`
7. `backend/app/services/context_manager.py`
8. `backend/app/routes/ai_webhooks.py`
9. `backend/app/config/flows/*.json`

### ✅ Keep Unchanged (20+ files)

All other existing files (repos, utils, deps, other routes, etc.)

---

**Total New Code:** ~3,500 lines
**Total Deprecated Code:** ~5,000 lines
**Net Reduction:** 1,500 lines (30% simpler!)
