# LandTenMVP Function/Class/Module Overview

## Frontend
- **App (Next.js):** Next 15 app router powering dashboards and chat surfaces.
- **Firebase / NextAuth:** Manages identity and persona metadata for dashboards.
- **Stream Chat UI:** `StreamChatPane` wraps Stream's React SDK, delivers multi-conversation inbox, unread badges, and agent triggers. New conversation modal issues `/api/chat/thread` calls, and agent mentions post to `/api/chat/agent`.
- **Local API proxy:** `/app/api/chat/*` routes keep browser secrets out of the client, forwarding to FastAPI with session context.

## Backend
- **FastAPI App:** Serves REST for chat, incident, job, media, and new Stream helpers.
- **Stream Chat router:** `app/routes/chat_stream.py` issues auth tokens, creates/list channels, and posts agent replies. It also ensures a dedicated `STREAM_AGENT_*` user is present in every room.
- **Agent service:** `app/services/ai_service.py` now integrates with OpenAI (when configured) and falls back to offline responses.
- **Repositories:** DynamoDB-backed chat/job/incident repos remain available for persistence beyond Stream.
- **Middleware:** Logging + rate limiting in `app/main.py`; CORS stays minimal for Next.js.

## Cloud/Infra
- **AWS CLI Scripts:** Automate ECR repo creation, EC2 launch, security group management, Docker image push/pull.
- **.env Files:** Store secrets and config for frontend/backend.

## Key Implementation Rationale
- Decoupled frontend/backend for scalability and deploy flexibility.
- Stream Chat drives multi-thread messaging, unread counters, and notifications while FastAPI owns identity + channel orchestration.
- AI agent piggybacks on OpenAI (or deterministic fallback) so every conversation can summon assistance with `@agent`.
- DynamoDB remains the system of record for structured ops data (jobs/incidents), complementing Stream's chat history.
