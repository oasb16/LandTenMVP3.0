# Stream Chat Authentication Architecture

> **Unified authentication for Classic Dashboard and AI Support Experience**

## Overview

Both **Classic Dashboard** and **AI Support Experience** use the **same Stream Chat authentication pattern**:

1. **Server-side token generation** using backend API credentials
2. **Per-user token distribution** via `/api/chat/token` Next.js API route
3. **User-specific identity** derived from `session.user.email`
4. **No client-side env vars** required

This ensures:
- ✅ Each user has their own Stream identity
- ✅ Tokens are generated dynamically and expire safely
- ✅ API secrets never exposed to frontend
- ✅ Both features share same token generation logic
- ✅ Single source of configuration

---

## Architecture Flow

```
┌──────────────┐
│  Frontend    │
│ Component    │
└──────┬───────┘
       │
       │ 1. fetch("/api/chat/token")
       ▼
┌──────────────┐
│ Next.js API  │
│   Route      │  2. Extract session.user.email & persona
│ /api/chat/   │
│   token      │
└──────┬───────┘
       │
       │ 3. GET /chat/stream/token?user_id={email}&persona={persona}
       ▼
┌──────────────┐
│   Backend    │
│  FastAPI     │  4. Sanitize user_id, create Stream user
│   Route      │  5. Generate token: client.create_token(user_id)
└──────┬───────┘
       │
       │ 6. Return { api_key, token, user_id, display_user_id, persona }
       ▼
┌──────────────┐
│  Frontend    │
│ Component    │  7. StreamChat.getInstance(api_key)
│              │  8. connectUser({ id, name }, token)
└──────────────┘
```

---

## Environment Variables

### Backend Only (`backend/.env`)

```bash
# Required for Stream Chat authentication
STREAM_CHAT_API_KEY=your_stream_api_key
STREAM_CHAT_API_SECRET=your_stream_api_secret

# Optional configuration
STREAM_DEFAULT_CHANNEL=landten-default
STREAM_AGENT_USER_ID=landten-agent
STREAM_AGENT_NAME=LandTen Agent
STREAM_AGENT_ROLE=agent
STREAM_AGENT_PERSONA=assistant
STREAM_AGENT_AUTOJOIN=true
STREAM_WEBHOOK_SECRET=your_webhook_secret
STREAM_WEBHOOK_URL=https://your-backend.ngrok-free.dev/chat/stream/webhook
```

### Frontend (`frontend/.env`)

```bash
# NO Stream Chat environment variables required!
# Tokens are fetched dynamically from /api/chat/token endpoint.
```

---

## Code Examples

### Frontend - Classic Dashboard

From `frontend/src/hooks/chat/StreamChatContext.tsx`:

```typescript
// Fetch token from backend
const tokenRes = await fetch("/api/chat/token");
const tokenData = await tokenRes.json();
const { api_key, token, user_id, display_user_id } = tokenData;

// Create client
const streamClient = StreamChat.getInstance(api_key, { timeout: 6000 });

// Connect user
await streamClient.connectUser(
  {
    id: user_id,
    name: display_user_id ?? session.user.email ?? user_id,
  },
  token
);
```

### Frontend - AI Support Experience

From `frontend/src/app/ai-support/components/AIChatContainer.tsx`:

```typescript
// Fetch token from backend (same as Classic Dashboard)
const tokenRes = await fetch("/api/chat/token");
const tokenData = await tokenRes.json();
const { api_key, token, user_id, display_user_id } = tokenData;

// Create client (same pattern)
const streamClient = StreamChat.getInstance(api_key, { timeout: 8000 });

// Connect user (same pattern)
await streamClient.connectUser(
  {
    id: user_id,
    name: display_user_id ?? session.user.email ?? user_id,
  },
  token
);
```

### Next.js API Route

From `frontend/src/app/api/chat/token/route.ts`:

```typescript
export async function GET() {
  const session = await auth();
  if (!session?.user?.email) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const user_id = session.user.email;
  const persona = session.user.persona;

  // Proxy to backend
  const url = `${backendBase}/chat/stream/token?user_id=${encodeURIComponent(user_id)}&persona=${encodeURIComponent(persona)}`;
  const res = await fetch(url);

  return NextResponse.json(await res.json());
}
```

### Backend Route

From `backend/app/routes/chat_stream.py`:

```python
@router.get("/chat/stream/token")
def get_stream_token(user_id: str, persona: str, token: str = Depends(verify_firebase_token)):
    client = _get_stream_client()  # Uses STREAM_CHAT_API_KEY/SECRET

    # Sanitize user_id for Stream
    sanitized_user_id = _slugify(user_id, allow_at=True)

    # Check token cache
    cached_token = _token_cache.get(sanitized_user_id, persona)
    if cached_token:
        return {
            "api_key": api_key,
            "token": cached_token,
            "user_id": sanitized_user_id,
            "display_user_id": user_id,
            "persona": persona,
        }

    # Upsert Stream user
    client.upsert_user({
        "id": sanitized_user_id,
        "role": persona if persona in allowed_roles else "user",
        "email": user_id,
        "persona": persona,
    })

    # Generate token
    token_value = client.create_token(sanitized_user_id)
    _token_cache.set(sanitized_user_id, persona, token_value)

    return {
        "api_key": api_key,
        "token": token_value,
        "user_id": sanitized_user_id,
        "display_user_id": user_id,
        "persona": persona,
    }
```

---

## Security Features

### 1. Server-Side Token Generation
- API secrets never exposed to client
- Tokens generated on-demand per user
- Token caching with 5-minute TTL

### 2. Rate Limiting
- 5-second minimum interval between token requests per user
- Prevents token spam/abuse

### 3. User Authentication
- Requires valid NextAuth session
- Firebase token verification on backend

### 4. Token Expiration
- Tokens auto-expire after 5 minutes
- Frontend cache expires after 4 minutes (safe margin)
- New tokens auto-fetched when needed

---

## Benefits

### 1. Unified Implementation
- ✅ Both features use identical authentication
- ✅ Single source of truth for Stream configuration
- ✅ No duplicate env vars

### 2. Security
- ✅ API secrets protected on backend
- ✅ Per-user token isolation
- ✅ Auto-expiring tokens

### 3. Scalability
- ✅ Token caching reduces backend load
- ✅ Rate limiting prevents abuse
- ✅ Singleton client pattern in frontend

### 4. User Experience
- ✅ Real user identities (not fixed "prod-user")
- ✅ Proper message attribution
- ✅ User-specific channels and history

---

## Migration from Old Pattern

### ❌ Old Pattern (Fixed "prod-user")

```typescript
// WRONG: All users share same identity
const apiKey = process.env.NEXT_PUBLIC_STREAM_KEY;
const userToken = process.env.NEXT_PUBLIC_STREAM_USER_TOKEN;

await streamClient.connectUser(
  { id: "prod-user", name: "Production User" },
  userToken
);
```

**Problems:**
- All users appear as "prod-user"
- Static token expires
- API key exposed to client
- No user-specific identity

### ✅ New Pattern (Dynamic Per-User)

```typescript
// CORRECT: Each user has own identity
const tokenRes = await fetch("/api/chat/token");
const { api_key, token, user_id, display_user_id } = await tokenRes.json();

await streamClient.connectUser(
  { id: user_id, name: display_user_id },
  token
);
```

**Benefits:**
- Each user has unique identity
- Tokens auto-refresh
- API secrets protected
- User-specific channels

---

## Troubleshooting

### "Unauthorized" Error

**Cause:** No active NextAuth session

**Solution:** Ensure user is logged in before accessing Stream features

### "Stream credentials incomplete"

**Cause:** Backend env vars not configured

**Solution:** Set `STREAM_CHAT_API_KEY` and `STREAM_CHAT_API_SECRET` in `backend/.env`

### "Too many token requests"

**Cause:** Rate limiting triggered

**Solution:** Wait 5 seconds between token requests. Frontend should cache tokens.

### Token Expires Quickly

**Cause:** Normal behavior - tokens expire after 5 minutes

**Solution:** Frontend auto-refreshes tokens. No action needed.

---

## Testing

### 1. Verify Backend Configuration

```bash
# Check backend env vars
cat backend/.env | grep STREAM

# Should show:
# STREAM_CHAT_API_KEY=...
# STREAM_CHAT_API_SECRET=...
```

### 2. Test Token Endpoint

```bash
# Get NextAuth session token first, then:
curl -H "Authorization: Bearer YOUR_SESSION_TOKEN" \
  http://localhost:3000/api/chat/token

# Should return:
# {
#   "api_key": "...",
#   "token": "...",
#   "user_id": "sanitized-email",
#   "display_user_id": "user@example.com",
#   "persona": "tenant"
# }
```

### 3. Verify User Identity

```javascript
// In browser console on /ai-support or /dashboard
console.log(streamClient.userID);
// Should show sanitized email, NOT "prod-user"
```

---

## Summary

✅ **Classic Dashboard** and **AI Support** now use **identical Stream authentication**

✅ **Per-user tokens** generated dynamically via backend API

✅ **No client-side env vars** required - all secrets protected on backend

✅ **Unified configuration** - single source of truth

✅ **Production-ready** - secure, scalable, user-specific identity
