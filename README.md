# LandTenMVP3.0

Monorepo for a modern SaaS platform using a managed mix architecture.

## Structure
- `frontend/` - Next.js/React app
- `backend/` - FastAPI app
- `functions/` - Serverless functions (AI, chat, etc.)
- `infra/` - Infrastructure as code
- `scripts/` - Utility scripts
- `docs/` - Documentation

## Realtime Messaging & Agent Overview

- **Stream Chat** powers the in-app inbox. The backend exposes `/chat/stream/*` routes to issue user tokens, create/list channels, and post agent replies. The frontend proxies through `/app/api/chat/*` to avoid leaking service secrets to the browser.
- **Agent persona**: set `OPENAI_API_KEY` (and optional `OPENAI_MODEL`, `AGENT_SYSTEM_PROMPT`) to let the LandTen agent answer conversations when users mention `@agent`. Without a key, the agent still responds with a lightweight deterministic fallback.
- **Env knobs**: configure `STREAM_AGENT_USER_ID`, `STREAM_AGENT_NAME`, and `STREAM_AGENT_AUTOJOIN` to control the virtual helper. `STREAM_ALLOWED_ROLES` should include the agent role so Stream permissions stay valid.
- **Multi-thread inbox**: the chat pane now supports Messenger-style conversation switching, unread badges, and quick notifications when new messages land in the background. Use the “New Conversation” button to spin up direct or group chats; the agent auto-joins by default.
- **Webhooks + Incident Flow**: Configure `STREAM_WEBHOOK_SECRET` and point Stream's webhook at `/chat/stream/webhook`. The bot drives the guided discovery → DIY → incident creation pipeline described in the incident-management doc, persisting incidents to DynamoDB and surfacing landlord approval recommendations directly in chat.

## Setup for OpenAI Responses API

LandTen has migrated to OpenAI's Responses API for improved conversational AI architecture. This replaces the previous dual-agent flow (TenantAgent + Orchestrator) with a single unified prompt.

### Prerequisites

1. **OpenAI API Key**: Ensure `OPENAI_API_KEY` is set in your environment
2. **DynamoDB Table**: Create `landten_conversation_mappings` table (or set custom name via `CONVERSATION_MAPPING_TABLE`)

### Configuration Steps

1. **Create Unified Prompt in OpenAI Dashboard**
   - Navigate to [OpenAI Platform Prompts](https://platform.openai.com/prompts)
   - Click "Create prompt"
   - Paste the content from `prompts/landten-unified-prompt-v1.md`
   - Save the prompt and copy the prompt ID (starts with `prompt_`)

2. **Set Environment Variable**
   ```bash
   export LANDTEN_PROMPT_ID=prompt_xxxxx  # Replace with your actual prompt ID
   ```

   Or add to your `.env` file:
   ```bash
   LANDTEN_PROMPT_ID=prompt_xxxxx
   ```

3. **Create DynamoDB Table** (if not exists)
   ```bash
   aws dynamodb create-table \
     --table-name landten_conversation_mappings \
     --attribute-definitions AttributeName=channel_id,AttributeType=S \
     --key-schema AttributeName=channel_id,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST
   ```

4. **Verify Setup**
   - Start the backend: `cd backend && uvicorn app.main:app --reload`
   - Send a test message through the webhook
   - Check logs for `ResponseHandler initialized with prompt: prompt_xxxxx`

### Architecture Changes

- **Before**: User → TenantAgent (empathy) → Orchestrator (functions) → Execute
- **After**: User → Single Response (empathy + functions) → Execute

### Benefits

- ✅ **Improved Fluidity**: Single unified response flow
- ✅ **Better State Management**: Native Conversations API replaces custom meta_context
- ✅ **Easier Debugging**: Prompt versions managed in OpenAI dashboard
- ✅ **Performance**: Reduced latency and better caching
- ✅ **Future-Ready**: Access to MCP, deep research, and new OpenAI features

### Troubleshooting

**Error: `LANDTEN_PROMPT_ID environment variable not set`**
- Ensure you've created the prompt in OpenAI dashboard and set the environment variable
- Check that the prompt ID starts with `prompt_`

**Conversations not persisting:**
- Verify `CONVERSATION_MAPPING_TABLE` DynamoDB table exists
- Check AWS credentials and permissions

**For more details**, see `prompts/README.md` for prompt management guide.
