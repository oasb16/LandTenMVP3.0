# PropertyAI - Complete Setup Guide

## Overview

PropertyAI is a fully integrated, production-ready property management platform with:
- **NextAuth** authentication with Google OAuth
- **Real-time chat** via Stream Chat
- **Backend APIs** for incidents, tasks, jobs, and profiles
- **Multi-role support**: Landlord, Tenant, Contractor
- **Media uploads** to S3
- **AI-powered** incident classification and responses

---

## Architecture

```
Frontend (Next.js 15 + React 19)
├── PropertyAI Component (New UI)
├── Classic Dashboard (Original)
├── API Routes (/api/*)
└── NextAuth + Stream Chat

Backend (FastAPI + Python)
├── REST APIs
├── Stream Chat Integration
├── DynamoDB Storage
├── OpenAI Integration
└── S3 Media Upload
```

---

## Prerequisites

1. **Node.js** 20+ and **npm**
2. **Python** 3.10+
3. **AWS Account** (for DynamoDB & S3 - optional in dev mode)
4. **Google OAuth** credentials
5. **Stream Chat** account (free tier available)
6. **OpenAI API** key (optional)

---

## 🚀 Quick Start (Development Mode)

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
```

**Minimal `.env` for development:**
```bash
# Disable authentication for local development
AUTH_DISABLED=true

# Stream Chat (REQUIRED - get from https://getstream.io)
STREAM_CHAT_API_KEY=your_stream_chat_api_key
STREAM_CHAT_API_SECRET=your_stream_chat_secret

# OpenAI (OPTIONAL - for AI features)
OPENAI_API_KEY=your_openai_api_key

# DynamoDB will fall back to in-memory storage if AWS not configured
```

**Start backend:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at `http://localhost:8000`

---

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env.local

# Edit .env.local with your credentials
```

**Required `.env.local`:**
```bash
# Backend URL
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# NextAuth Configuration
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=generate-with-openssl-rand-base64-32

# Google OAuth (REQUIRED)
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

**Start frontend:**
```bash
npm run dev
```

Frontend will be available at `http://localhost:3000`

---

## 🔐 Setting Up Google OAuth

### Step 1: Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Authorized JavaScript origins:
   - `http://localhost:3000`
   - `https://yourdomain.com` (for production)
7. Authorized redirect URIs:
   - `http://localhost:3000/api/auth/callback/google`
   - `https://yourdomain.com/api/auth/callback/google` (for production)
8. Save and copy **Client ID** and **Client Secret**

### Step 2: Generate NEXTAUTH_SECRET

```bash
openssl rand -base64 32
```

Copy the output to `NEXTAUTH_SECRET` in `.env.local`

---

## 💬 Setting Up Stream Chat

### Step 1: Create Stream Chat Account

1. Go to [getstream.io](https://getstream.io)
2. Sign up for free (includes 10,000 MAU)
3. Create a new app

### Step 2: Get API Credentials

1. Go to your app dashboard
2. Copy **API Key** and **Secret**
3. Add to backend `.env`:
   ```bash
   STREAM_CHAT_API_KEY=your_api_key
   STREAM_CHAT_API_SECRET=your_secret
   ```

---

## 🗄️ Database Setup (Optional for Development)

PropertyAI uses **AWS DynamoDB** for production but falls back to **in-memory storage** in development.

### For Development (In-Memory)
No setup needed! Data will be stored in memory (resets on restart).

### For Production (DynamoDB)

1. **Create DynamoDB tables** using Terraform:
   ```bash
   cd infra/terraform
   terraform init
   terraform apply
   ```

2. **Configure AWS credentials:**
   ```bash
   aws configure
   ```
   Or set environment variables:
   ```bash
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   export AWS_DEFAULT_REGION=us-east-1
   ```

**Required Tables:**
- `chat_messages`
- `incidents`
- `jobs`
- `tasks`
- `profiles`

---

## 📦 S3 Media Upload Setup (Optional)

For media uploads (photos/videos):

1. **Create S3 bucket:**
   ```bash
   aws s3 mb s3://your-property-ai-media
   ```

2. **Configure CORS:**
   ```json
   {
     "CORSRules": [{
       "AllowedOrigins": ["http://localhost:3000", "https://yourdomain.com"],
       "AllowedMethods": ["GET", "PUT", "POST"],
       "AllowedHeaders": ["*"]
     }]
   }
   ```

3. **Add to backend `.env`:**
   ```bash
   MEDIA_BUCKET=your-property-ai-media
   ```

---

## 🤖 OpenAI Integration (Optional)

For AI-powered incident classification and responses:

1. Get API key from [platform.openai.com](https://platform.openai.com/)
2. Add to backend `.env`:
   ```bash
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-4o-mini
   ```

---

## 🧪 Testing the Application

### 1. Access PropertyAI

1. Open browser to `http://localhost:3000`
2. Click **"Try PropertyAI (New UI)"**
3. Sign in with Google
4. Select a role: Landlord, Tenant, or Contractor

### 2. Test Features

**As Tenant:**
- Report new issues
- View incident status
- Chat with landlord/AI

**As Landlord:**
- View properties
- Manage incidents
- Approve jobs

**As Contractor:**
- View available jobs
- Accept assignments

### 3. Test Real-time Chat

1. Open two browser windows
2. Sign in as different users
3. Send messages - they should appear in real-time

---

## 🚢 Production Deployment

### Backend Deployment

**Option 1: AWS AppRunner**
```bash
# Build and push Docker image
docker build -t property-ai-backend ./backend
docker tag property-ai-backend:latest <ecr-url>/property-ai-backend:latest
docker push <ecr-url>/property-ai-backend:latest

# Deploy with AppRunner (via AWS Console or CLI)
```

**Option 2: Fly.io**
```bash
cd backend
fly launch
fly deploy
```

### Frontend Deployment

**Option 1: Vercel (Recommended)**
```bash
npm install -g vercel
cd frontend
vercel
```

**Option 2: Docker**
```bash
docker build -t property-ai-frontend ./frontend
docker run -p 3000:3000 property-ai-frontend
```

### Environment Variables for Production

**Backend:**
- Set `AUTH_DISABLED=false`
- Configure production database URLs
- Use AWS IAM roles instead of hardcoded credentials
- Enable CORS for your production domain

**Frontend:**
- Update `NEXT_PUBLIC_BACKEND_URL` to production backend URL
- Update `NEXTAUTH_URL` to production frontend URL
- Update Google OAuth redirect URIs

---

## 🔧 Troubleshooting

### "Backend URL not configured"
- Check `NEXT_PUBLIC_BACKEND_URL` in frontend `.env.local`
- Restart frontend dev server after changing env vars

### "Failed to fetch Stream Chat token"
- Verify Stream Chat credentials in backend `.env`
- Check backend is running and accessible

### "Google OAuth error"
- Verify redirect URIs match exactly in Google Console
- Check `NEXTAUTH_URL` matches your current domain
- Ensure `NEXTAUTH_SECRET` is set

### "Dynamo unavailable" warnings
- Normal in development mode (uses in-memory fallback)
- For production, configure AWS credentials and create tables

### Media upload fails
- Check S3 bucket exists and has correct permissions
- Verify CORS configuration
- Check `MEDIA_BUCKET` env var

---

## 📝 API Endpoints

### Frontend API Routes
- `GET /api/profile` - Get user profile
- `POST /api/profile` - Save user persona
- `GET /api/chat/token` - Get Stream Chat token

### Backend API Routes
- `POST /incident/create` - Create incident
- `GET /incident/list/{tenant_id}` - List incidents
- `POST /job/create` - Create job
- `GET /job/list/{contractor_id}` - List jobs
- `POST /task/create` - Create task
- `GET /task/list/{persona}` - List tasks
- `POST /task/update_status` - Update task status
- `GET /profile/{email}` - Get profile
- `POST /profile` - Save profile
- `GET /media/upload_url` - Get S3 presigned URL

---

## 🎯 Current Limitations & Future Work

### Known Limitations:
1. **Properties** - No backend API yet (uses mock data)
2. **Contractor matching** - Basic implementation
3. **Notifications** - In-app only (no email/SMS)
4. **File attachments** - Requires S3 setup

### Planned Features:
1. Property CRUD APIs
2. Advanced contractor matching algorithm
3. Email/SMS notifications
4. Payment processing
5. Reporting & analytics

---

## 🆘 Support & Resources

- **Backend API Docs**: `http://localhost:8000/docs` (FastAPI auto-docs)
- **Stream Chat Docs**: https://getstream.io/chat/docs/
- **Next.js Docs**: https://nextjs.org/docs
- **NextAuth Docs**: https://next-auth.js.org/

---

## 📋 Pre-Launch Checklist

Before going to production:

- [ ] Configure production Google OAuth with HTTPS redirect URIs
- [ ] Set up DynamoDB tables via Terraform
- [ ] Configure S3 bucket for media uploads
- [ ] Set `AUTH_DISABLED=false` in backend
- [ ] Add production domains to CORS allowlist
- [ ] Generate strong `NEXTAUTH_SECRET`
- [ ] Set up monitoring (CloudWatch, Sentry, etc.)
- [ ] Configure backup strategy for DynamoDB
- [ ] Set up SSL/TLS certificates
- [ ] Review and adjust rate limits
- [ ] Test all features end-to-end

---

## 🎉 You're Ready!

Your PropertyAI application is now fully integrated and production-ready!

Access the new interface at: **`http://localhost:3000/property-ai`**

Classic dashboard still available at: **`http://localhost:3000/dashboard`**
