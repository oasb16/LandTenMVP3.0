# Changelog

All notable changes to LandTen MVP 3.0 will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2025-12-08] Responses API Migration

### Breaking Changes

- **Migrated from dual-agent architecture to OpenAI Responses API**
  - Old: TenantAgent (empathy) → Orchestrator (function calling) → Execute
  - New: Single ResponseHandler (unified empathy + functions) → Execute

- **State management moved from DynamoDB meta_context to OpenAI Conversations API**
  - `meta_context` custom storage replaced by native Conversations API
  - Lightweight `conversation_mappings` table now only stores channel_id → conversation_id

- **Requires new environment variable: `LANDTEN_PROMPT_ID`**
  - Must create unified prompt in OpenAI dashboard
  - Set prompt ID in environment configuration
  - See README.md "Setup for OpenAI Responses API" for instructions

### Added

- **ResponseHandler** (`backend/app/services/response_handler.py`)
  - Single-flow message processing using Responses API
  - Replaces dual-agent architecture
  - Handles empathy + function calling in one unified call
  - Explicit tool loop management (max 5 iterations)

- **ConversationManager** (`backend/app/services/conversation_manager.py`)
  - Integration with OpenAI Conversations API
  - Maps Slack channels to OpenAI Conversations
  - Native state storage replacing custom meta_context
  - Lightweight DynamoDB mapping table

- **Unified Prompt** (`prompts/landten-unified-prompt-v1.md`)
  - Merged TenantAgent + Orchestrator prompts
  - Single comprehensive prompt for all interactions
  - Managed in OpenAI dashboard with versioning
  - A/B testable and easily updatable

- **Conversation Mapping DynamoDB Methods**
  - `save_conversation_mapping()`: Store channel → conversation mapping
  - `get_conversation_mapping()`: Retrieve conversation ID
  - `delete_conversation_mapping()`: Remove mapping

- **Enhanced Configuration**
  - `LANDTEN_PROMPT_ID`: OpenAI prompt identifier
  - `CONVERSATION_MAPPING_TABLE`: DynamoDB table name
  - `REQUIRE_PROMPT_ID`: Optional strict validation flag

- **Comprehensive Documentation**
  - Updated README.md with Responses API setup guide
  - Created `backend/app/archived/README.md` explaining deprecated code
  - Configuration steps and troubleshooting guide

### Changed

- **Webhook Route** (`backend/app/routes/ai_webhooks_v3.py`)
  - Now uses ResponseHandler for all message processing
  - Old dual-agent flow commented out for easy rollback
  - Cleaner, more maintainable code structure

- **Health Check Endpoint** (`backend/app/routes/health_check.py`)
  - Now checks ResponseHandler instead of Orchestrator
  - Reports prompt_id in health status

- **Environment Configuration**
  - Updated `.env.example` with new Responses API variables
  - Added `settings.py` configuration for LANDTEN_PROMPT_ID
  - Optional validation with clear error messages

### Deprecated

- **orchestrator.py** (moved to `backend/app/archived/`)
  - Custom LLM orchestrator no longer needed
  - Replaced by OpenAI's native Responses API
  - Archived for reference and potential rollback

- **base_agent.py** (moved to `backend/app/archived/`)
  - TenantAgent functionality merged into unified prompt
  - No longer need separate empathy agent
  - Archived for reference

- **orchestrator_prompt.txt** (moved to `backend/app/archived/`)
  - Merged into unified prompt in OpenAI dashboard
  - Archived for historical reference

- **meta_context_manager.py** (marked deprecated, will be removed)
  - Still used for backward compatibility
  - Will be fully replaced by ConversationManager
  - Added deprecation warning in docstring

- **Agent Files** (marked deprecated)
  - `tenant_agent.py`, `diagnosis_agent.py`, `contractor_agent.py`
  - Now import from archived location
  - Added deprecation warnings

### Migration Steps

1. **Create Unified Prompt**
   - Navigate to [OpenAI Platform Prompts](https://platform.openai.com/prompts)
   - Create new prompt using content from `prompts/landten-unified-prompt-v1.md`
   - Copy prompt ID (starts with `prompt_`)

2. **Set Environment Variables**
   ```bash
   export LANDTEN_PROMPT_ID=prompt_xxxxx
   export CONVERSATION_MAPPING_TABLE=landten_conversation_mappings
   ```

3. **Create DynamoDB Table**
   ```bash
   aws dynamodb create-table \
     --table-name landten_conversation_mappings \
     --attribute-definitions AttributeName=channel_id,AttributeType=S \
     --key-schema AttributeName=channel_id,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST
   ```

4. **Deploy Updated Code**
   - Push changes to production
   - Restart services
   - Monitor logs for successful initialization

5. **Validate Deployment**
   - Send test messages through webhook
   - Verify empathetic responses
   - Test discovery flow and incident creation
   - Confirm conversation state persistence

### Performance Improvements

- ⚡ **Reduced Latency**: Single API call instead of dual-agent flow
- 📦 **Better Caching**: OpenAI prompt caching reduces token usage
- 🎯 **Fewer Round Trips**: Native conversation storage eliminates DynamoDB calls for state
- 🚀 **Scalability**: Leverages OpenAI's infrastructure for state management

### Benefits

- ✅ **Improved Fluidity**: Single unified response flow eliminates delays
- ✅ **Better State Management**: Native Conversations API replaces custom solution
- ✅ **Easier Debugging**: Prompt versions managed in dashboard with A/B testing
- ✅ **Future-Ready**: Access to MCP, deep research, and new OpenAI features
- ✅ **Simpler Architecture**: Less custom code to maintain

### Rollback Plan

If issues occur after deployment:

1. Uncomment old dual-agent code in `ai_webhooks_v3.py` (lines 378-842)
2. Comment out new ResponseHandler code (lines 307-377)
3. Restart services
4. Report issues to development team

### Known Limitations

- Requires OpenAI Responses API access (currently in beta/limited availability)
- Prompt changes require updating via OpenAI dashboard (not code)
- Conversation history stored in OpenAI (not self-hosted)

### Security & Privacy

- Conversation data stored in OpenAI's infrastructure
- Follow OpenAI's data retention and privacy policies
- Channel mappings still stored in DynamoDB for control
- No sensitive data beyond conversation context sent to OpenAI

---

## Migration Timeline

- **Phase 1**: Created unified prompt content (Dec 8, 2025)
- **Phase 2**: Built ConversationManager service (Dec 8, 2025)
- **Phase 3**: Built ResponseHandler service (Dec 8, 2025)
- **Phase 4**: Integrated ResponseHandler into webhook route (Dec 8, 2025)
- **Phase 5**: Updated DynamoDB schema and environment config (Dec 8, 2025)
- **Phase 6**: Archived deprecated dual-agent code (Dec 8, 2025)
- **Phase 7**: Final documentation and deployment prep (Dec 8, 2025)

---

For detailed technical documentation, see:
- `README.md` - Setup guide for OpenAI Responses API
- `DEPLOYMENT.md` - Deployment checklist and procedures
- `MIGRATION_SUMMARY.md` - Architecture changes and technical details
- `backend/app/archived/README.md` - Information about deprecated code
