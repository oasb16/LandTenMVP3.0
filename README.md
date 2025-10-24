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
