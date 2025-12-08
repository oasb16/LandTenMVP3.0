# Archived Code - Responses API Migration

This directory contains deprecated code from the pre-Responses API architecture.

## Why These Files Are Archived

As of December 2025, LandTen migrated from a dual-agent architecture to OpenAI's Responses API. This migration replaced the custom orchestrator and tenant agent with a single unified prompt.

### Architecture Change

**Old Architecture (Archived)**:
```
User Message → TenantAgent (empathy) → Orchestrator (function calling) → Execute Functions
```

**New Architecture (Current)**:
```
User Message → ResponseHandler (unified empathy + functions) → Execute Functions
```

## Archived Files

### Services

- **`orchestrator.py`**: Custom LLM orchestrator that managed function calling and state transitions
  - Replaced by: `ResponseHandler` using OpenAI Responses API
  - Key functionality now handled natively by OpenAI's conversation management

### Agents

- **`base_agent.py`**: Base agent class and TenantAgent for empathetic responses
  - Replaced by: Unified prompt in OpenAI dashboard (`prompts/landten-unified-prompt-v1.md`)
  - Empathy is now part of the single prompt, not a separate agent

### System Prompts

- **`orchestrator_prompt.txt`**: Prompt for orchestrator agent
- **`tenant_prompt.txt`**: Prompt for tenant-facing empathetic agent
  - Both merged into: `prompts/landten-unified-prompt-v1.md`

## Migration Benefits

The new architecture provides:

- ✅ **Better Fluidity**: Single response flow eliminates dual-agent delays
- ✅ **Native State Management**: Conversations API replaces custom meta_context
- ✅ **Easier Maintenance**: Prompts managed in OpenAI dashboard with versioning
- ✅ **Performance**: Improved caching and reduced latency
- ✅ **Future-Ready**: Access to MCP, deep research, and new OpenAI features

## Why Keep These Files?

These files are archived (not deleted) for:

1. **Reference**: Understanding the previous architecture during migration
2. **Rollback**: Quick restoration if critical issues arise
3. **Documentation**: Preserving institutional knowledge
4. **Comparison**: Analyzing improvements in the new architecture

## Migration Timeline

- **Phase 1-3**: Built new ResponseHandler and ConversationManager services
- **Phase 4**: Integrated ResponseHandler into webhook route (old code commented)
- **Phase 5**: Updated environment configuration and documentation
- **Phase 6**: Archived deprecated code (this phase)
- **Phase 7**: Final cleanup and deployment

## DO NOT USE

⚠️ **These files are deprecated and should not be imported or used in new code.**

If you need to reference the old architecture, consult these archived files. For current implementation, see:

- `backend/app/services/response_handler.py`
- `backend/app/services/conversation_manager.py`
- `prompts/landten-unified-prompt-v1.md`

## Related Files Still In Use

Some files from the old architecture are still needed:

- `function_registry.py`: Tool definitions (still used by ResponseHandler)
- `dynamo_service.py`: Incident and user management (still needed)
- `discovery_manager.py`: Question generation (still used in discovery flow)
- `meta_context_manager.py`: Backward compatibility (marked deprecated, will be removed later)

---

*Archived on: December 8, 2025*
*Migration Branch: claude/assistants-to-responses-migration-01AiwKigtzutWutk9zbHpHpQ*
