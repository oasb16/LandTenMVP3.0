# LandTenMVP3.0 - Complete System Mapping Documentation

**Version:** 1.0.0
**Phase:** Phase 1 - Discovery & Observability
**Last Updated:** 2025-11-20

---

## Purpose

This documentation provides a comprehensive architectural understanding of the entire LandTenMVP3.0 system, establishing the foundation for all future development phases.

---

## Documentation Structure

This system map is organized into focused modules for maintainability and clarity:

### Core Architecture
- **[01 - Architecture Overview](./01_ARCHITECTURE_OVERVIEW.md)** - High-level system design, tech stack, and component overview
- **[02 - Frontend Architecture](./02_FRONTEND_ARCHITECTURE.md)** - Next.js app structure, routing, components, and UI flows
- **[03 - Backend Architecture](./03_BACKEND_ARCHITECTURE.md)** - FastAPI routes, services, repositories, and business logic
- **[04 - AI Agent Pipeline](./04_AI_AGENT_PIPELINE.md)** - AI reasoning, intent detection, and response generation

### Data & Integration
- **[05 - Data Models & Schema](./05_DATA_MODELS.md)** - DynamoDB tables, entities, and relationships
- **[06 - Authentication & Session](./06_AUTHENTICATION.md)** - NextAuth, persona system, and security
- **[07 - Chat System](./07_CHAT_SYSTEM.md)** - Stream Chat integration, channels, and message flows

### Analysis & Planning
- **[08 - Current Implementation State](./08_IMPLEMENTATION_STATE.md)** - What's implemented vs conceptual
- **[09 - Gap Analysis](./09_GAP_ANALYSIS.md)** - Missing features, technical debt, and improvement areas
- **[10 - Development Roadmap](./10_ROADMAP.md)** - 7-phase development plan

### Workflows & Processes
- **[11 - Complete Workflows](./11_WORKFLOWS.md)** - End-to-end flows from tenant report to payment
- **[12 - Message Lifecycle](./12_MESSAGE_LIFECYCLE.md)** - How messages flow through the system

---

## Quick Reference

### System Overview

**LandTenMVP3.0** is a multi-persona property management platform with AI-driven incident detection, workflow automation, and real-time collaboration.

**Three Personas:**
- **Tenant** - Reports issues, tracks repairs
- **Landlord** - Approves jobs, manages properties, coordinates contractors
- **Contractor** - Receives bids, performs work, submits invoices

**Key Technologies:**
- Frontend: Next.js 15 + React 18 + TypeScript + Tailwind CSS
- Backend: Python FastAPI + AWS DynamoDB + AWS S3
- AI: OpenAI GPT-4o-mini with intent detection & entity extraction
- Real-time: Stream Chat SDK + Pusher (optional)
- Payments: Stripe
- Auth: NextAuth v5 (Google OAuth)

---

## System Flow (High-Level)

```
User Authentication (Google OAuth)
  ↓
Persona Selection (Tenant/Landlord/Contractor)
  ↓
Dashboard with Stream Chat Integration
  ↓
AI Agent analyzes messages → Detects incidents
  ↓
Backend creates incident records in DynamoDB
  ↓
Discovery flow → Job creation → Contractor bidding
  ↓
Scheduling → Work execution → Payment
  ↓
Job closeout & metrics tracking
```

---

## Key File Locations

### Frontend
```
frontend/src/
├── app/
│   ├── api/auth/[...nextauth]/     # NextAuth configuration
│   ├── dashboard/[persona]/        # Main persona dashboards
│   └── property-ai/                # PropertyAI chat interface
├── components/
│   ├── StreamChatPane.tsx          # Main chat UI (347 lines)
│   ├── PropertyAI.tsx              # Advanced AI interface (1080 lines)
│   └── ai/                         # AI-specific UI components
├── lib/
│   ├── auth.ts                     # NextAuth config & callbacks
│   └── api.ts                      # Backend API service layer
└── hooks/
    └── chat/StreamChatContext.tsx  # Global chat state management
```

### Backend
```
backend/app/
├── main.py                         # FastAPI app + webhook registration
├── routes/
│   ├── ai_webhooks.py              # AI webhook handler (500+ lines)
│   ├── chat_stream.py              # Stream token generation
│   ├── incident.py                 # Incident CRUD
│   ├── job.py                      # Job/work order management
│   └── profile.py                  # User profile management
├── services/
│   ├── ai_reasoning.py             # Intent detection engine
│   ├── flow_engine.py              # Workflow state machine
│   ├── context_manager.py          # Conversation memory
│   ├── incident_flow.py            # Incident classification logic
│   ├── policy_validator.py         # Persona-based authorization
│   └── dynamo_service.py           # DynamoDB ORM (550+ lines)
└── repos/                          # Data access layer
    ├── incident_repo.py
    ├── job_repo.py
    └── profile_repo.py
```

---

## Critical Integrations

| Service | Purpose | Status |
|---------|---------|--------|
| **Google OAuth** | User authentication | ✅ Implemented |
| **Stream Chat** | Real-time messaging & channels | ✅ Implemented |
| **OpenAI API** | AI reasoning & intent detection | ✅ Implemented |
| **AWS DynamoDB** | Primary database | ✅ Implemented |
| **AWS S3** | Media storage | ✅ Implemented |
| **Stripe** | Payment processing | 🟡 Partially implemented |
| **Pusher** | Real-time notifications | 🟡 Optional/configured |
| **Firebase** | Alternative auth | 🟡 Configured but not primary |

---

## Development Phases

The system follows a 7-phase development roadmap:

1. **Phase 1 (Current)** - Full Discovery, System Mapping, Observability
2. **Phase 2** - Enhanced Incident Detection & Classification
3. **Phase 3** - Job Creation & Contractor Integration
4. **Phase 4** - Bidding & Selection System
5. **Phase 5** - Scheduling & Multi-party Coordination
6. **Phase 6** - Payment & Financial Workflows
7. **Phase 7** - Analytics, Reporting & Optimization

See **[10_ROADMAP.md](./10_ROADMAP.md)** for detailed phase descriptions.

---

## For Developers

### Getting Started
1. Read **[01_ARCHITECTURE_OVERVIEW.md](./01_ARCHITECTURE_OVERVIEW.md)** for system context
2. Review **[08_IMPLEMENTATION_STATE.md](./08_IMPLEMENTATION_STATE.md)** to understand what's complete
3. Check **[09_GAP_ANALYSIS.md](./09_GAP_ANALYSIS.md)** for known issues and missing features
4. Reference specific modules as needed during development

### Making Changes
- **Frontend changes:** Review [02_FRONTEND_ARCHITECTURE.md](./02_FRONTEND_ARCHITECTURE.md)
- **Backend changes:** Review [03_BACKEND_ARCHITECTURE.md](./03_BACKEND_ARCHITECTURE.md)
- **AI modifications:** Review [04_AI_AGENT_PIPELINE.md](./04_AI_AGENT_PIPELINE.md)
- **Database updates:** Review [05_DATA_MODELS.md](./05_DATA_MODELS.md)
- **Auth/session changes:** Review [06_AUTHENTICATION.md](./06_AUTHENTICATION.md)

### Understanding Workflows
- **How incidents are created:** [11_WORKFLOWS.md](./11_WORKFLOWS.md) → Incident Report Flow
- **How messages are processed:** [12_MESSAGE_LIFECYCLE.md](./12_MESSAGE_LIFECYCLE.md)
- **How personas interact:** [06_AUTHENTICATION.md](./06_AUTHENTICATION.md) → Persona System

---

## Contact & Contribution

This documentation is maintained as part of Phase 1 system discovery. As the system evolves:
- Update relevant module docs when making changes
- Keep gap analysis current
- Document new workflows as they're implemented
- Maintain implementation state accuracy

---

**Next:** Begin with [01_ARCHITECTURE_OVERVIEW.md](./01_ARCHITECTURE_OVERVIEW.md)
