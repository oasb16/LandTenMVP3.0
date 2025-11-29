# Stream Chat Token Setup Guide

> **How to generate the production token for AI Support Experience**

## Overview

The AI Support Experience uses a **fixed production user ID** (`prod-user`) with a pre-generated Stream Chat token. This simplifies authentication and allows the frontend to connect directly without backend token generation.

---

## 🔑 Token Generation

### Required Setup

1. **Stream Chat Account**: https://getstream.io/dashboard/
2. **API Credentials**: You'll need your Stream API Key and Secret
3. **Python Environment**: With `stream-chat` package installed

### Step 1: Install Stream Chat SDK

If you haven't already, install the Stream Chat Python SDK in your backend environment:

```bash
pip install stream-chat
```

### Step 2: Generate Token for "prod-user"

Create a Python script or run this in your backend:

```python
from stream_chat import StreamChat

# Your Stream credentials (from dashboard)
api_key = "YOUR_STREAM_API_KEY"
api_secret = "YOUR_STREAM_API_SECRET"

# Initialize Stream server client
server_client = StreamChat(api_key=api_key, api_secret=api_secret)

# Generate token for fixed production user
token = server_client.create_token("prod-user")

print("=" * 60)
print("STREAM CHAT TOKEN GENERATED")
print("=" * 60)
print(f"User ID: prod-user")
print(f"Token: {token}")
print("=" * 60)
print("\nAdd this to your frontend/.env.local:")
print(f"NEXT_PUBLIC_STREAM_USER_TOKEN={token}")
print("=" * 60)
```

### Step 3: Run the Script

```bash
python generate_stream_token.py
```

**Example Output:**
```
============================================================
STREAM CHAT TOKEN GENERATED
============================================================
User ID: prod-user
Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoicHJvZC11c2VyIn0.xxxxxxxxxxxxx
============================================================

Add this to your frontend/.env.local:
NEXT_PUBLIC_STREAM_USER_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoicHJvZC11c2VyIn0.xxxxxxxxxxxxx
============================================================
```

---

## 📝 Environment Configuration

### frontend/.env.local

Add both required variables:

```bash
# Stream Chat API Key (from dashboard)
NEXT_PUBLIC_STREAM_KEY=your_stream_api_key_here

# Stream Chat User Token (generated above)
NEXT_PUBLIC_STREAM_USER_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoicHJvZC11c2VyIn0.xxxxxxxxxxxxx
```

### Finding Your Stream API Key

1. Go to https://getstream.io/dashboard/
2. Sign in to your account
3. Select your app (or create a new one)
4. Navigate to **"Dashboard"** → **"App Settings"** → **"Keys"**
5. Copy the **"Key"** (this is your API Key)
6. Copy the **"Secret"** (you'll need this to generate tokens)

---

## 🔧 Complete Setup Script

Save this as `backend/generate_stream_token.py`:

```python
#!/usr/bin/env python3
"""
Generate Stream Chat token for prod-user

Usage:
    python generate_stream_token.py
"""

import os
from stream_chat import StreamChat

def generate_token():
    # Get credentials from environment or prompt
    api_key = os.getenv("STREAM_API_KEY")
    api_secret = os.getenv("STREAM_API_SECRET")

    if not api_key:
        api_key = input("Enter your Stream API Key: ").strip()

    if not api_secret:
        api_secret = input("Enter your Stream API Secret: ").strip()

    if not api_key or not api_secret:
        print("❌ Error: Both API Key and Secret are required")
        return

    try:
        # Initialize Stream server client
        server_client = StreamChat(api_key=api_key, api_secret=api_secret)

        # Generate token for prod-user
        token = server_client.create_token("prod-user")

        print("\n" + "=" * 60)
        print("✅ STREAM CHAT TOKEN GENERATED SUCCESSFULLY")
        print("=" * 60)
        print(f"User ID: prod-user")
        print(f"Token: {token}")
        print("=" * 60)
        print("\nAdd these to your frontend/.env.local:")
        print(f"NEXT_PUBLIC_STREAM_KEY={api_key}")
        print(f"NEXT_PUBLIC_STREAM_USER_TOKEN={token}")
        print("=" * 60)
        print("\n✅ Setup complete! Your AI Support Experience is ready.")

    except Exception as e:
        print(f"\n❌ Error generating token: {e}")
        print("Please check your API credentials and try again.")

if __name__ == "__main__":
    generate_token()
```

Make it executable:

```bash
chmod +x backend/generate_stream_token.py
```

Run it:

```bash
# Option 1: With environment variables
export STREAM_API_KEY="your_key"
export STREAM_API_SECRET="your_secret"
python backend/generate_stream_token.py

# Option 2: Interactive (will prompt for credentials)
python backend/generate_stream_token.py
```

---

## 🔒 Security Notes

### Token Expiration

By default, `create_token()` generates a token that **does not expire**. This is suitable for:
- Development environments
- Fixed production users
- Long-running applications

If you need expiring tokens, you can specify expiration:

```python
import time

# Token expires in 30 days
expiration = int(time.time()) + (30 * 24 * 60 * 60)
token = server_client.create_token("prod-user", expiration)
```

### Token Security

- ✅ **Safe to use in frontend**: Stream tokens are designed to be used client-side
- ✅ **User-specific**: Token is tied to "prod-user" ID only
- ✅ **Cannot be reused for other users**: Token validation checks user ID match
- ⚠️ **Keep API Secret secure**: Never expose your Stream API Secret in frontend code

### Environment Variables

- ✅ `NEXT_PUBLIC_STREAM_KEY` - Safe to expose (public API key)
- ✅ `NEXT_PUBLIC_STREAM_USER_TOKEN` - Safe to expose (user-specific token)
- ❌ `STREAM_API_SECRET` - **NEVER** expose in frontend (server-side only)

---

## 🧪 Testing

### Verify Setup

1. Start your frontend:
   ```bash
   cd frontend
   npm run dev
   ```

2. Navigate to `/ai-support`

3. Check browser console for:
   ```
   [AI Support Container] Connecting as prod-user
   [AI Support Container] ✅ Stream client connected successfully
   ```

4. If you see errors:
   - Check `NEXT_PUBLIC_STREAM_KEY` is set correctly
   - Check `NEXT_PUBLIC_STREAM_USER_TOKEN` is set correctly
   - Verify token was generated for "prod-user"
   - Check Stream dashboard for connection logs

### Test Token Validity

You can verify your token using the Stream API:

```python
from stream_chat import StreamChat

api_key = "your_key"
api_secret = "your_secret"
token = "your_generated_token"

server_client = StreamChat(api_key=api_key, api_secret=api_secret)

# Verify token (will raise exception if invalid)
try:
    user_id = server_client.verify_webhook(token)
    print(f"✅ Token is valid for user: {user_id}")
except Exception as e:
    print(f"❌ Token is invalid: {e}")
```

---

## 🔄 Token Rotation

If you need to rotate the token:

1. Generate a new token using the same script
2. Update `NEXT_PUBLIC_STREAM_USER_TOKEN` in `.env.local`
3. Restart your frontend development server
4. Existing sessions will reconnect automatically

---

## ❓ Troubleshooting

### "Missing required environment variables"

**Problem**: Frontend shows error about missing env vars

**Solution**:
1. Check `frontend/.env.local` exists
2. Verify both variables are set:
   - `NEXT_PUBLIC_STREAM_KEY`
   - `NEXT_PUBLIC_STREAM_USER_TOKEN`
3. Restart dev server after adding env vars

### "Failed to initialize Stream client"

**Problem**: Connection fails even with env vars set

**Solution**:
1. Verify API key is correct (check Stream dashboard)
2. Verify token was generated for "prod-user" (not another user ID)
3. Check token is valid (use verification script above)
4. Check network connectivity to Stream servers
5. Check browser console for detailed error messages

### "Token expired"

**Problem**: Token works initially but fails after some time

**Solution**:
1. Generate a new token without expiration
2. Or set a longer expiration time when generating
3. Update `.env.local` with new token
4. Restart frontend server

---

## 📚 Additional Resources

- **Stream Chat Docs**: https://getstream.io/chat/docs/
- **Token Generation**: https://getstream.io/chat/docs/token_generation/
- **JavaScript Client**: https://getstream.io/chat/docs/sdk/javascript/
- **Security Best Practices**: https://getstream.io/chat/docs/security_and_auth/

---

## ✅ Quick Start Checklist

- [ ] Install `stream-chat` Python package
- [ ] Get Stream API Key and Secret from dashboard
- [ ] Run token generation script
- [ ] Copy token to `frontend/.env.local`
- [ ] Set `NEXT_PUBLIC_STREAM_KEY` in `.env.local`
- [ ] Set `NEXT_PUBLIC_STREAM_USER_TOKEN` in `.env.local`
- [ ] Restart frontend dev server
- [ ] Test by visiting `/ai-support`
- [ ] Verify console shows successful connection

---

**Generated**: 2025-01-28
**User ID**: `prod-user` (fixed)
**Token Type**: Non-expiring (recommended for production)
**Security Level**: Client-safe
