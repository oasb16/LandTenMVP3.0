# 01 - Architecture Overview

## System Description

LandTenMVP3.0 is an intelligent property management platform that automates the entire incident-to-payment workflow using AI-driven orchestration. The system connects three distinct personas (Tenants, Landlords, Contractors) through real-time communication, intelligent routing, and automated workflow management.

---

## Core Architectural Principles

### 1. Multi-Persona Architecture
- **Single Unified Platform** - One codebase serves all three user types
- **Role-Based Access Control** - Persona-specific permissions and workflows
- **Shared Communication Layer** - All personas communicate through Stream Chat
- **Persona-Aware AI** - AI agent adapts behavior based on user persona

### 2. Event-Driven Workflow
- **Message-Triggered Processing** - User messages trigger AI analysis
- **Webhook-Based Integration** - Stream Chat webhooks drive backend processing
- **Asynchronous Processing** - Non-blocking message handling
- **State Machine Flows** - Deterministic workflow progression

### 3. AI-First Design
- **Intent Detection** - Every message analyzed for user intent
- **Entity Extraction** - Structured data extracted from natural language
- **Contextual Memory** - Conversation history maintained per channel
- **Adaptive Responses** - AI generates persona-appropriate responses

### 4. Real-Time Collaboration
- **Live Chat** - Instant messaging between all parties
- **Multi-Party Channels** - Tenants, landlords, and contractors in same conversation
- **Presence Indicators** - Typing indicators and online status
- **Push Notifications** - Real-time alerts via Pusher

---

## Technology Stack

### Frontend Layer
| Technology | Version | Purpose |
|-----------|---------|---------|
| **Next.js** | 15.5.4 | React framework with App Router |
| **React** | 18.3.1 | UI component library |
| **TypeScript** | 5.x | Type-safe JavaScript |
| **Tailwind CSS** | 4.0 | Utility-first styling |
| **Stream Chat React** | 13.9.0 | Real-time chat UI components |
| **NextAuth** | 5.0.0-beta.26 | Authentication framework |
| **Framer Motion** | 12.0.3 | Animation library |
| **Lucide React** | 0.548.0 | Icon library |

### Backend Layer
| Technology | Purpose |
|-----------|---------|
| **FastAPI** | High-performance Python web framework |
| **Pydantic** | Data validation and settings management |
| **Boto3** | AWS SDK for Python (DynamoDB, S3) |
| **Mangum** | ASGI adapter for AWS Lambda deployment |
| **Stream Chat SDK** | Server-side Stream Chat integration |
| **OpenAI Python SDK** | AI/LLM integration |
| **Stripe Python SDK** | Payment processing |

### Infrastructure & Services
| Service | Purpose | Status |
|---------|---------|--------|
| **AWS DynamoDB** | NoSQL database for all entities | ✅ Production |
| **AWS S3** | Media storage (photos, documents) | ✅ Production |
| **Stream Chat** | Real-time messaging platform | ✅ Production |
| **OpenAI API** | GPT-4o-mini for AI reasoning | ✅ Production |
| **Google OAuth** | User authentication | ✅ Production |
| **Stripe** | Payment processing | 🟡 Partial |
| **Pusher** | Push notifications | 🟡 Optional |
| **Heroku** | Backend hosting | ✅ Production |

---

## System Components

### 1. Frontend Application (Next.js)
**Location:** `/frontend`
**Entry Point:** `src/app/layout.tsx`

**Responsibilities:**
- User interface rendering
- Authentication flow (Google OAuth via NextAuth)
- Persona selection and switching
- Stream Chat client initialization
- Message composition and display
- Interactive card rendering (AI responses)
- File upload to S3
- Payment form UI

**Key Routes:**
- `/` - Landing page
- `/auth/signin` - Google OAuth entry
- `/dashboard` - Persona selector
- `/dashboard/[persona]` - Main dashboard (tenant/landlord/contractor)
- `/property-ai` - PropertyAI chat interface

### 2. Backend API (FastAPI)
**Location:** `/backend`
**Entry Point:** `app/main.py`

**Responsibilities:**
- RESTful API endpoints for all entities
- Stream Chat webhook processing
- AI intent detection and response generation
- DynamoDB data persistence
- S3 presigned URL generation
- Stripe payment processing
- User profile management
- Session token generation

**Key Routes:**
- `/ai/stream-webhook` - AI webhook handler
- `/chat/token` - Stream Chat token generation
- `/incident/*` - Incident CRUD operations
- `/job/*` - Job/work order management
- `/profile/*` - User profile management
- `/property/*` - Property management
- `/contractor/*` - Contractor operations & payments

### 3. AI Reasoning Engine
**Location:** `/backend/app/services/ai_reasoning.py`

**Responsibilities:**
- Message intent classification
- Entity extraction from natural language
- Context-aware response generation
- Flow state determination
- Policy validation enforcement
- Interactive card generation

**Core Functions:**
- `infer_intent()` - Classifies user message into intent enum
- `extract_entities()` - Extracts structured data (category, severity, etc.)
- `predict_next_actions()` - Determines valid next steps

### 4. Context Manager
**Location:** `/backend/app/services/context_manager.py`

**Responsibilities:**
- Persistent conversation memory per user/channel
- Entity tracking across messages
- Intent history maintenance
- TTL-based context expiration (24 hours default)

**Storage:** DynamoDB table with PK=user#id, SK=channel#id

### 5. Flow Engine
**Location:** `/backend/app/services/flow_engine.py`

**Responsibilities:**
- Workflow state machine orchestration
- Stage transition validation
- Multi-step flow coordination
- Policy-based routing

**Flow Graph:**
```
incident.report → [discovery.response, incident.followup, diy.suggestion]
discovery.response → [job.request, incident.followup]
job.request → [approval.decision, bids.request]
approval.decision → [completion.confirmation]
```

### 6. Database Layer (DynamoDB)
**Location:** `/backend/app/services/dynamo_service.py`, `/backend/app/repos/`

**Tables:**
- `landten_incidents` - Incident records
- `landten_jobs` - Work orders
- `landten_job_bids` - Contractor bids
- `landten_users` - User profiles
- `landten_property` - Property records
- `context_manager` - Conversation state
- `chat_messages` - Message history
- `mttr_events` - SLA tracking
- `ai_training_feedback` - AI model feedback

---

## Data Flow Architecture

### Message Flow (User → AI → Response)
```
1. User types message in StreamChatPane
   ↓
2. Frontend sends via Stream Chat SDK
   ↓
3. Stream Chat triggers webhook → /ai/stream-webhook
   ↓
4. Backend:
   a. Verifies webhook signature
   b. Fetches/creates context from DynamoDB
   c. Calls AIReasoning.infer_intent()
   d. Validates against persona policies
   e. Determines next workflow stage
   f. Generates AI response via OpenAI
   g. Builds interactive card
   h. Posts response to Stream Chat
   ↓
5. Frontend receives response via Stream subscription
   ↓
6. AIResponseParser renders JSON structure
   ↓
7. User sees AI response with action cards
```

### Incident Creation Flow
```
1. Tenant reports issue: "Water leak under kitchen sink"
   ↓
2. AI detects intent: INCIDENT_REPORT
   ↓
3. AI extracts entities:
   - category: plumbing
   - severity: medium
   - urgency: immediate
   ↓
4. Backend creates incident in DynamoDB:
   - incident_id: INC-1732123456
   - status: detected
   - tenant_id: user@example.com
   ↓
5. AI sends discovery card with questions
   ↓
6. User answers discovery questions
   ↓
7. System determines if DIY or contractor needed
   ↓
8. If contractor needed → create job → generate bids
```

### Authentication Flow
```
1. User visits /auth/signin
   ↓
2. Clicks "Sign in with Google"
   ↓
3. Google OAuth flow (NextAuth handles redirect)
   ↓
4. JWT callback triggered:
   a. Check if user has persona
   b. If not, fetch from backend: GET /profile/{email}
   c. If profile doesn't exist, create default (tenant)
   d. Store persona in JWT token
   ↓
5. Session callback exposes persona to browser
   ↓
6. Redirect to /dashboard
   ↓
7. User selects/confirms persona
   ↓
8. Redirect to /dashboard/{persona}
```

---

## Deployment Architecture

### Current Setup (Development)
```
Frontend (Next.js)
  ↓
  Deployed to: Heroku (via scripts/heroku_start.sh)
  URL: https://thysanurous-cecilia-nonstretchable.ngrok-free.dev

Backend (FastAPI)
  ↓
  Deployed to: Heroku
  URL: https://demiurgic-stevie-polymorphous.ngrok-free.dev

Stream Chat Webhook
  ↓
  Points to: Backend /ai/stream-webhook
  Auto-registered on backend startup
```

### Environment Configuration
- Frontend env vars managed via `.env.local`
- Backend env vars via Heroku config vars or `.env`
- Secrets managed via environment variables (not committed)
- CORS configured to allow frontend → backend communication

---

## Security Architecture

### Authentication
- **Google OAuth 2.0** via NextAuth
- **Session tokens** stored in httpOnly cookies
- **CSRF protection** enabled
- **Secure cookie flags** (httpOnly, sameSite, secure)

### Authorization
- **Persona-based policies** enforced by PolicyValidator
- **Action whitelist/blacklist** per persona
- **Cost threshold enforcement** for job approvals
- **Channel membership validation** for Stream Chat

### API Security
- **Stream webhook signature verification** (HMAC SHA256)
- **Firebase token verification** (optional, dev mode bypass)
- **Rate limiting** (120 req/min per IP)
- **CORS restrictions** (configurable origins)

### Data Security
- **DynamoDB encryption at rest** (AWS managed)
- **S3 presigned URLs** (1-hour expiration)
- **Stripe tokenization** for payment methods
- **No sensitive data in logs** (sanitized)

---

## Scalability Considerations

### Current Limitations
- **Synchronous webhook processing** - Could cause backlog under high load
- **No caching layer** - DynamoDB queried on every request
- **Single-region deployment** - No geographic redundancy
- **No connection pooling** - DynamoDB clients recreated per request
- **Limited rate limiting** - Simple IP-based limiting

### Future Improvements
- Implement message queue (SQS) for webhook processing
- Add Redis caching layer for frequent queries
- Multi-region DynamoDB deployment
- Connection pooling for DynamoDB and Stream Chat
- Advanced rate limiting with user-based quotas
- Horizontal scaling via container orchestration

---

## Monitoring & Observability (Current State)

### Existing Logging
- **FastAPI middleware** - Logs request method, path, status, duration
- **Error logging** - Exceptions logged to stdout
- **Stream webhook logs** - Basic event logging

### Missing Observability (Phase 1 Goal)
- ❌ Structured logging with context
- ❌ Request tracing across services
- ❌ Performance metrics
- ❌ Business metrics (incidents created, jobs completed, MTTR)
- ❌ AI model performance tracking
- ❌ Error rate monitoring
- ❌ User journey tracking

**Phase 1 will add comprehensive structured logging and DEBUG_MODE.**

---

## Integration Points

### External Services
1. **Google OAuth** - User authentication
2. **Stream Chat** - Real-time messaging infrastructure
3. **OpenAI API** - LLM for intent detection and response generation
4. **AWS DynamoDB** - Primary data store
5. **AWS S3** - Media storage
6. **Stripe** - Payment processing
7. **Pusher** - Push notifications (optional)

### Internal Service Communication
- **Frontend → Backend** - RESTful HTTP/HTTPS
- **Backend → Stream Chat** - REST API + webhook callbacks
- **Backend → OpenAI** - REST API
- **Backend → DynamoDB** - Boto3 SDK
- **Backend → S3** - Boto3 SDK
- **Backend → Stripe** - Stripe Python SDK

---

## Development Workflow

### Local Development
```bash
# Frontend
cd frontend
npm install
npm run dev  # http://localhost:3000

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload  # http://localhost:8000
```

### Environment Variables
- Frontend: `.env.local` (gitignored)
- Backend: `.env` (gitignored)
- Example files: `.env.example` (committed)

### Git Workflow
- Feature branches: `claude/{feature-name}-{session-id}`
- Main branch: `main` (protected)
- CI/CD: GitHub Actions (if configured)

---

## Next Steps

Continue to:
- **[02_FRONTEND_ARCHITECTURE.md](./02_FRONTEND_ARCHITECTURE.md)** - Detailed frontend structure
- **[03_BACKEND_ARCHITECTURE.md](./03_BACKEND_ARCHITECTURE.md)** - Detailed backend routes
- **[08_IMPLEMENTATION_STATE.md](./08_IMPLEMENTATION_STATE.md)** - What's implemented vs conceptual

Return to: **[SYSTEM_FULL_MAP.md](./SYSTEM_FULL_MAP.md)**
