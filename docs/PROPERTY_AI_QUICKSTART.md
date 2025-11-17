# PropertyAI - Quick Start

## 🚀 Minimal Setup (5 minutes)

### 1. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
```bash
AUTH_DISABLED=true
STREAM_CHAT_API_KEY=get-from-getstream.io
STREAM_CHAT_API_SECRET=get-from-getstream.io
```

Run:
```bash
uvicorn app.main:app --reload
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
```

Edit `.env.local`:
```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=$(openssl rand -base64 32)
GOOGLE_CLIENT_ID=get-from-google-console
GOOGLE_CLIENT_SECRET=get-from-google-console
```

Run:
```bash
npm run dev
```

### 3. Open Browser

http://localhost:3000/property-ai

---

## 📌 What You Need

**REQUIRED:**
- Google OAuth credentials ([setup guide](https://console.cloud.google.com))
- Stream Chat account ([free tier](https://getstream.io))

**OPTIONAL:**
- OpenAI API key (for AI features)
- AWS credentials (for DynamoDB & S3)

---

## 🔗 Key URLs

- **PropertyAI (New)**: http://localhost:3000/property-ai
- **Classic Dashboard**: http://localhost:3000/dashboard
- **Backend API Docs**: http://localhost:8000/docs

---

## 🆘 Issues?

See [PROPERTY_AI_SETUP.md](./PROPERTY_AI_SETUP.md) for detailed setup guide.

Common fixes:
- "Backend URL not configured" → Check `NEXT_PUBLIC_BACKEND_URL`
- OAuth errors → Verify redirect URIs in Google Console
- Stream Chat errors → Check API keys in backend `.env`
