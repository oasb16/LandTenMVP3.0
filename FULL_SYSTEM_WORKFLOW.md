# LandTen MVP 3.0 - System Flow Documentation
 
**Last Updated:** 2025-11-20
**Version:** 3.0
**Purpose:** Comprehensive system architecture, data flows, and observability reference
 
---
 
## Table of Contents
 
1. [System Overview](#1-system-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Complete Business Flow](#3-complete-business-flow)
4. [Data Models & DynamoDB Schema](#4-data-models--dynamodb-schema)
5. [API Routes Reference](#5-api-routes-reference)
6. [AI & Chat Routing System](#6-ai--chat-routing-system)
7. [Persona System](#7-persona-system)
8. [Background Services](#8-background-services)
9. [External Integrations](#9-external-integrations)
10. [Observability & Logging](#10-observability--logging)
11. [Error Handling Strategy](#11-error-handling-strategy)
12. [Performance Considerations](#12-performance-considerations)
 
---
 
## 1. System Overview
 
### 1.1 Platform Architecture
 
LandTen MVP 3.0 is a **property maintenance orchestration platform** combining:
 
- **FastAPI Backend** (Python 3.11+) - Business logic, AI reasoning, data persistence
- **Next.js 15 Frontend** (React/TypeScript) - User interface, authentication, real-time chat
- **Stream Chat** - Real-time messaging infrastructure
- **AWS DynamoDB** - NoSQL database for scalable data storage
- **OpenAI GPT-4** - Natural language understanding and intent classification
- **Stripe Connect** - Payment processing and contractor payouts
- **Google OAuth** - Authentication via NextAuth.js
 
### 1.2 Core Value Proposition
 
**Problem:** Property maintenance is fragmented, slow, and lacks transparency for tenants, landlords, and contractors.
 
**Solution:** Conversational AI-driven platform that:
- Detects and classifies maintenance issues automatically
- Routes requests through policy-bounded workflows
- Generates contractor bids and manages approvals
- Tracks end-to-end incident resolution with MTTR metrics
- Provides persona-specific experiences (tenant, landlord, contractor)
 
### 1.3 Key Metrics
 
- **MTTR (Mean Time to Repair):** 8 hours (immediate) to 48 hours (routine)
- **Auto-approval Threshold:** $500 (landlord configurable)
- **Discovery Questions:** 4 standard questions per incident
- **Contractor Bids:** 3-5 generated per job
- **Session TTL:** 24 hours (DynamoDB context expiration)
 
---
 
## 2. Architecture Diagram
 
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js 15)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │  Dashboard   │  │ PropertyAI   │  │    Stream Chat UI            │  │
│  │  (Persona    │  │   Chat       │  │  (CustomMessageUI, Cards)    │  │
│  │  Selector)   │  │  Interface   │  │                              │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┬───────────────┘  │
│         │                 │                          │                  │
│         └─────────────────┴──────────────────────────┘                  │
│                            │                                            │
│                   ┌────────▼────────────┐                               │
│                   │  NextAuth.js (OAuth)│                               │
│                   └────────┬────────────┘                               │
└────────────────────────────┼─────────────────────────────────────────────┘
                            │
                   ┌────────▼──────────┐
                   │   API Gateway     │
                   │  (FastAPI CORS)   │
                   └────────┬──────────┘
                            │
   ┌────────────────────────┼─────────────────────────────┐
   │                        │                             │
┌───▼────────────┐  ┌────────▼───────────┐  ┌─────────────▼──────────┐
│  Stream Chat   │  │  AI Reasoning      │  │   Business Routes      │
│   Webhooks     │  │   Engine           │  │  (Incident, Job, Bid)  │
│ /ai/stream-    │  │  - Intent          │  │                        │
│  webhook       │  │    Detection       │  │  - /incident/*         │
│                │  │  - Entity          │  │  - /job/*              │
│                │  │    Extraction      │  │  - /contractor/*       │
│                │  │  - Response Plan   │  │                        │
└───┬────────────┘  └────────┬───────────┘  └─────────────┬──────────┘
   │                        │                             │
   │         ┌──────────────▼──────────────┐             │
   │         │   Policy Validator          │             │
   │         │  (Persona-based Auth)       │             │
   │         └──────────────┬──────────────┘             │
   │                        │                             │
   │         ┌──────────────▼──────────────┐             │
   │         │   Flow Engine v2            │             │
   │         │  (State Transitions)        │◄────────────┘
   │         └──────────────┬──────────────┘
   │                        │
   │         ┌──────────────▼──────────────┐
   │         │   Context Manager           │
   │         │  (Session Persistence)      │
   │         └──────────────┬──────────────┘
   │                        │
   └────────────────────────┼─────────────────────────────┐
                            │                             │
                   ┌────────▼─────────┐         ┌────────▼────────┐
                   │   Repository      │         │  Card Builder   │
                   │     Layer         │         │  (Interactive   │
                   │  - IncidentRepo   │         │   Messages)     │
                   │  - JobRepo        │         │                 │
                   │  - JobBidRepo     │         └─────────────────┘
                   │  - ContractorRepo │
                   └────────┬──────────┘
                            │
                   ┌────────▼──────────┐
                   │   AWS DynamoDB    │
                   │  - incidents      │
                   │  - jobs           │
                   │  - job_bids       │
                   │  - profiles       │
                   │  - chat_contexts  │
                   └───────────────────┘
 
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                            │
│  ┌───────────┐  ┌──────────┐  ┌────────────┐  ┌─────────────┐  │
│  │  OpenAI   │  │  Stripe  │  │  Google    │  │ Stream Chat │  │
│  │  GPT-4    │  │  Connect │  │  OAuth     │  │   Service   │  │
│  └───────────┘  └──────────┘  └────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```
 
---
 
## 3. Complete Business Flow
 
### 3.1 End-to-End: Tenant → Incident → Job → Contractor → Payment
 
```
┌──────────────────────────────────────────────────────────────────────┐
│ PHASE 1: INCIDENT DETECTION & CLASSIFICATION                        │
└──────────────────────────────────────────────────────────────────────┘
 
[TENANT] Reports issue via chat
   │
   ├─► Stream Chat: message.new webhook
   │
   ├─► POST /ai/stream-webhook
   │   │
   │   ├─► Verify HMAC signature
   │   │
   │   ├─► Extract: user_id, channel_id, message_text
   │   │
   │   ├─► Context Manager: get_context(user_id, channel_id)
   │   │   └─► Load from DynamoDB or create new context
   │   │
   │   ├─► AI Reasoning: infer_intent(message, context, persona)
   │   │   │
   │   │   ├─► OpenAI GPT-4o-mini classification
   │   │   │   └─► Returns: intent, entities, confidence, reasoning
   │   │   │
   │   │   └─► Fallback: rule-based classification (keywords)
   │   │
   │   ├─► Policy Validator: validate_intent(intent, persona)
   │   │   └─► Check if tenant can perform this action
   │   │
   │   └─► Intent: "incident.report" detected
   │
   ├─► Incident Flow: classify_issue(message_text)
   │   │
   │   ├─► Extract category: plumbing, electrical, hvac, etc.
   │   ├─► Extract severity: low, medium, high, emergency
   │   ├─► Extract urgency: routine, urgent, immediate
   │   │
   │   └─► Threshold decision:
   │       │
   │       ├─► IF severity in {medium, high, emergency} + maintenance category
   │       │   └─► is_actionable = True → Create formal incident
   │       │
   │       └─► ELSE severity == low
   │           └─► is_actionable = False → Conversational response only
   │
   └─► IF is_actionable:
       │
       ├─► Generate contractor bids (cost estimation)
       │   └─► Returns: [{"name": "RapidFix", "quote": 150, "eta": "Next day"}...]
       │
       ├─► Create Incident Record (DynamoDB)
       │   │
       │   ├─► incident_id = INC-{timestamp}
       │   ├─► Fields: category, severity, urgency, description, estimated_cost
       │   └─► IncidentRepo.create_incident()
       │
       ├─► Send Incident Card (Stream Chat)
       │   │
       │   ├─► CardBuilder.incident_card()
       │   │   └─► Color-coded by severity (red=emergency, yellow=high, etc.)
       │   │
       │   └─► Bot sends card to channel
       │
       ├─► Update Context Manager
       │   │
       │   ├─► set_active_incident(incident_id)
       │   ├─► advance_flow_state("incident.active")
       │   └─► Store: question_index=0, answers={}
       │
       └─► Send Confirmation Message
           └─► "I've created incident {incident_id} and notified your landlord"
 
┌──────────────────────────────────────────────────────────────────────┐
│ PHASE 2: DISCOVERY (INFORMATION GATHERING)                          │
└──────────────────────────────────────────────────────────────────────┘
 
Bot asks Discovery Question 1/4
   │
   └─► "Is the water still flowing right now?"
 
[TENANT] Responds
   │
   ├─► Intent: "discovery.response"
   │
   ├─► Store answer in context.flow_state.answers["q0"]
   │
   ├─► Send Discovery Progress Card
   │   └─► Shows: "2/4 questions answered"
   │
   ├─► Ask next question (q1)
   │   └─► "Where exactly is the issue located?"
   │
   └─► Repeat until all 4 questions answered
 
After Discovery Complete:
   │
   ├─► Bot: "This looks like a high-severity leak. Should I create a work order?"
   │
   └─► Flow state: "job-ready"
 
┌──────────────────────────────────────────────────────────────────────┐
│ PHASE 3: JOB CREATION & APPROVAL                                    │
└──────────────────────────────────────────────────────────────────────┘
 
[TENANT] "Yes, create a work order"
   │
   ├─► Intent: "job.request"
   │
   ├─► Create Job Record (DynamoDB)
   │   │
   │   ├─► job_id = JOB-{timestamp}
   │   ├─► Fields: incident_id, category, estimated_cost, urgency, status="created"
   │   └─► JobRepo.create_job()
   │
   ├─► Send Work Order Card
   │   │
   │   ├─► CardBuilder.work_order_card()
   │   │   └─► Shows: category, estimated cost, urgency, status
   │   │
   │   └─► Bot sends to channel
   │
   ├─► Update Context
   │   │
   │   ├─► set_active_job(job_id)
   │   └─► advance_flow_state("job")
   │
   └─► Notify Landlord
       └─► Create landlord channel notification (if configured)
 
IF estimated_cost > $500:
   │
   ├─► Requires Landlord Approval
   │   │
   │   ├─► Send Approval Card to Landlord
   │   │   │
   │   │   ├─► Shows: job details, estimated cost, contractor bids
   │   │   └─► Buttons: [Approve] [Reject]
   │   │
   │   └─► Wait for landlord response
   │
   └─► [LANDLORD] Clicks "Approve"
       │
       ├─► Intent: "approval.decision"
       ├─► Update job.status = "approved"
       └─► Continue to Phase 4
 
ELSE IF estimated_cost <= $500:
   │
   └─► Auto-approve
       │
       ├─► Update job.status = "approved"
       └─► Continue to Phase 4
 
┌──────────────────────────────────────────────────────────────────────┐
│ PHASE 4: CONTRACTOR BIDS & SELECTION                                │
└──────────────────────────────────────────────────────────────────────┘
 
Generate Contractor Bids
   │
   ├─► generate_contractor_bids(category)
   │   │
   │   └─► Returns: 3 mock bids (RapidFix, Prime Contractors, SafeHome Pros)
   │
   ├─► Create Bid Records (DynamoDB)
   │   │
   │   ├─► FOR EACH bid:
   │   │   │
   │   │   ├─► bid_id = BID-{timestamp}-{index}
   │   │   ├─► Fields: job_id, contractor_id, quote, eta, rating, status="pending"
   │   │   └─► JobBidRepo.create_bid()
   │   │
   │   └─► Store all bids in database
   │
   └─► Send Bids Card to Landlord
       │
       ├─► CardBuilder.bids_card()
       │   │
       │   └─► Shows: comparison table (price, ETA, rating, distance)
       │
       └─► Landlord selects best contractor
 
[LANDLORD] Selects Contractor "RapidFix"
   │
   ├─► Update job.contractor_id = "contractor-123"
   │
   ├─► Update job.status = "approved"
   │
   ├─► Update bid.status = "accepted" (for RapidFix)
   │
   ├─► Update bid.status = "rejected" (for others)
   │
   └─► Notify all parties:
       │
       ├─► Tenant: "Your job has been assigned to RapidFix"
       ├─► Contractor: "You've been assigned job {job_id}"
       └─► Landlord: "Job {job_id} assigned successfully"
 
┌──────────────────────────────────────────────────────────────────────┐
│ PHASE 5: JOB EXECUTION & SCHEDULING                                 │
└──────────────────────────────────────────────────────────────────────┘
 
Create Schedule Entry
   │
   ├─► ScheduleRepo.create_schedule({
   │       contractor_id: "contractor-123",
   │       job_id: job_id,
   │       scheduled_date: "2025-11-21T10:00:00Z"
   │   })
   │
   └─► Contractor views schedule in dashboard
 
[CONTRACTOR] Arrives on-site
   │
   ├─► Updates job.status = "in_progress"
   │
   └─► Tenant/Landlord receive status update
 
[CONTRACTOR] Completes work
   │
   ├─► Uploads completion photos
   │   └─► Media stored in S3 (or similar)
   │
   ├─► Updates job.status = "completed"
   │   └─► job.completion_date = now()
   │
   └─► Send Completion Card
       │
       ├─► CardBuilder.completion_card()
       │   └─► Shows: before/after photos, final cost, completion date
       │
       └─► Sent to tenant and landlord
 
┌──────────────────────────────────────────────────────────────────────┐
│ PHASE 6: PAYMENT & CLOSEOUT                                         │
└──────────────────────────────────────────────────────────────────────┘
 
[LANDLORD] Initiates Payment
   │
   ├─► POST /contractor/payment/initiate
   │   {
   │       "job_id": "JOB-123",
   │       "contractor_id": "contractor-123",
   │       "amount": 150.00,
   │       "currency": "USD"
   │   }
   │
   ├─► Stripe Service: create_payout()
   │   │
   │   ├─► Validate contractor has Stripe Connect account
   │   │   └─► contractor.stripe_account_id exists
   │   │
   │   ├─► Create Stripe Transfer
   │   │   │
   │   │   ├─► stripe.Transfer.create({
   │   │   │       amount: 15000,  # cents
   │   │   │       currency: "usd",
   │   │   │       destination: contractor.stripe_account_id
   │   │   │   })
   │   │   │
   │   │   └─► Returns: transfer_id
   │   │
   │   └─► Update job.final_cost = 150.00
   │
   ├─► Update job.status = "paid"
   │
   ├─► Update incident.status = "resolved"
   │   └─► incident.resolved_at = now()
   │
   └─► Calculate MTTR
       │
       ├─► mttr_hours = (resolved_at - created_at) / 3600
       │
       ├─► Record MTTR event (DynamoDB)
       │   └─► mttr_events table: {incident_id, mttr_hours, category, severity}
       │
       └─► Send completion notifications
           │
           ├─► Tenant: "Your issue has been resolved. Payment processed."
           ├─► Contractor: "Payment of $150.00 has been sent to your account"
           └─► Landlord: "Job {job_id} completed and paid"
 
┌──────────────────────────────────────────────────────────────────────┐
│ END-TO-END FLOW COMPLETE                                            │
│ Total time: 8-48 hours (depending on urgency)                       │
└──────────────────────────────────────────────────────────────────────┘
```
 
---
 
## 4. Data Models & DynamoDB Schema
 
### 4.1 Incidents Table
 
**Table Name:** `landten_incidents`
**Primary Key:** `user_id` (PK), `incident_id` (SK)
 
```python
{
   # Keys
   "user_id": str,              # Partition key (tenant_id or thread_id)
   "incident_id": str,          # Sort key (INC-{timestamp})
 
   # Core Fields
   "tenant_id": str,            # Tenant identifier (email)
   "tenant_email": str,         # Tenant email address
   "landlord_id": str,          # Landlord identifier (optional)
   "property_id": str,          # Property identifier (optional)
   "thread_id": str,            # Stream Chat channel ID
   "channel_id": str,           # Alias for thread_id
 
   # Classification
   "category": str,             # plumbing | electrical | hvac | appliance | structural | pest | other
   "severity": str,             # low | medium | high | emergency
   "urgency": str,              # routine | urgent | immediate
 
   # Description
   "title": str,                # Short summary (optional)
   "summary": str,              # Detailed description from tenant
   "description": str,          # Alias for summary
 
   # Discovery & DIY
   "diy_attempted": bool,       # Whether tenant tried DIY fix
   "diy_result": str,           # Outcome of DIY attempt (optional)
   "discovery_data": dict,      # Discovery question responses
   "media": list,               # URLs to photos/videos
 
   # Status & Workflow
   "status": str,               # detected | discovery | work_order | in_progress | completed | resolved
   "created_at": str,           # ISO timestamp (UTC)
   "updated_at": str,           # ISO timestamp (UTC)
   "first_response_at": str,    # When AI first responded (optional)
   "resolved_at": str,          # When incident closed (optional)
 
   # Cost & Approval
   "estimated_cost": float,     # Estimated repair cost ($)
   "approval_threshold": str,   # auto-approve | recommended-review | manual-approval
 
   # MTTR Tracking
   "mttr_target_hours": int,    # Target resolution time (8 or 48 hours)
   "mttr_actual_hours": float,  # Actual resolution time (calculated)
 
   # Assignment
   "assigned_contractor": str,  # Contractor ID (optional)
   "assigned_job_id": str,      # Associated job ID (optional)
 
   # Metadata
   "status_metric_flags": dict, # Internal tracking flags
   "metadata": dict             # Additional custom fields
}
```
 
**Example:**
 
```json
{
   "user_id": "tenant-alice@example.com",
   "incident_id": "INC-1732147920",
   "tenant_id": "tenant-alice@example.com",
   "tenant_email": "alice@example.com",
   "category": "plumbing",
   "severity": "high",
   "urgency": "immediate",
   "summary": "Water leaking from kitchen sink, flooding floor",
   "diy_attempted": false,
   "status": "work_order",
   "created_at": "2025-11-20T14:32:00Z",
   "estimated_cost": 150.0,
   "approval_threshold": "auto-approve",
   "mttr_target_hours": 8
}
```
 
---
 
### 4.2 Jobs Table
 
**Table Name:** `landten_jobs`
**Primary Key:** `job_id` (PK)
 
```python
{
   # Key
   "job_id": str,               # Partition key (JOB-{timestamp})
 
   # Relationships
   "incident_id": str,          # Associated incident
   "property_id": str,          # Property where work needed
   "landlord_id": str,          # Landlord who owns property
   "contractor_id": str,        # Assigned contractor (optional until assigned)
 
   # Job Details
   "title": str,                # Job title/summary
   "description": str,          # Detailed work description
   "category": str,             # plumbing | electrical | hvac | etc.
 
   # Scheduling
   "urgency": str,              # routine | urgent | immediate
   "scheduled_date": str,       # ISO timestamp when work scheduled (optional)
   "completion_date": str,      # ISO timestamp when completed (optional)
 
   # Status
   "status": str,               # created | approved | scheduled | in_progress | completed | paid
   "created_at": str,           # ISO timestamp
   "updated_at": str,           # ISO timestamp
 
   # Cost
   "estimated_cost": str,       # "$150 - $250" or "150.00"
   "final_cost": float,         # Actual cost after completion (optional)
 
   # Communication
   "channel_id": str,           # Stream Chat channel for updates
 
   # Metadata
   "metadata": dict             # Additional custom fields
}
```
 
**Example:**
 
```json
{
   "job_id": "JOB-1732148000",
   "incident_id": "INC-1732147920",
   "landlord_id": "landlord-bob@example.com",
   "contractor_id": "contractor-123",
   "title": "Emergency Plumbing Response",
   "category": "plumbing",
   "estimated_cost": "$150 - $250",
   "urgency": "immediate",
   "status": "approved",
   "created_at": "2025-11-20T14:40:00Z",
   "channel_id": "tenant-alice"
}
```
 
---
 
### 4.3 Job Bids Table
 
**Table Name:** `landten_job_bids`
**Primary Key:** `bid_id` (PK)
 
```python
{
   # Key
   "bid_id": str,               # Partition key (BID-{timestamp}-{index})
 
   # Relationships
   "job_id": str,               # Associated job
   "contractor_id": str,        # Contractor submitting bid
 
   # Contractor Info
   "contractor_name": str,      # Display name
   "contractor_email": str,     # Contact email (optional)
   "contractor_phone": str,     # Contact phone (optional)
 
   # Bid Details
   "quote": Decimal,            # Quoted price ($)
   "eta": str,                  # Estimated time to arrival (e.g., "Next business day")
   "availability": str,         # Available time slots (optional)
 
   # Quality Indicators
   "rating": Decimal,           # Contractor rating (0.0 - 5.0)
   "reviews_count": int,        # Number of reviews (optional)
   "distance": str,             # Distance from property (e.g., "2.3 mi")
 
   # Status
   "status": str,               # pending | accepted | rejected
   "created_at": str,           # ISO timestamp
   "updated_at": str,           # ISO timestamp
 
   # Metadata
   "metadata": dict             # Additional custom fields
}
```
 
**Example:**
 
```json
{
   "bid_id": "BID-1732148100-0",
   "job_id": "JOB-1732148000",
   "contractor_id": "contractor-123",
   "contractor_name": "RapidFix Plumbing",
   "quote": 150.00,
   "eta": "Next business day",
   "rating": 4.8,
   "distance": "2.3 mi",
   "status": "accepted",
   "created_at": "2025-11-20T14:41:40Z"
}
```
 
---
 
### 4.4 Profiles Table
 
**Table Name:** `landten_profiles`
**Primary Key:** `user_id` (PK)
 
```python
{
   # Key
   "user_id": str,              # Partition key (email)
 
   # User Info
   "email": str,                # Email address (unique)
   "name": str,                 # Display name
   "phone": str,                # Phone number (optional)
   "avatar_url": str,           # Profile picture URL (optional)
 
   # Persona
   "persona": str,              # tenant | landlord | contractor
   "role": str,                 # Alias for persona
 
   # Activity
   "created_at": str,           # ISO timestamp
   "updated_at": str,           # ISO timestamp
   "last_seen": str,            # Last activity timestamp
 
   # Metadata
   "metadata": dict             # Additional custom fields
}
```
 
---
 
### 4.5 Chat Contexts Table
 
**Table Name:** `landten_chat_contexts`
**Primary Key:** `context_id` (PK)
 
```python
{
   # Key
   "context_id": str,           # Partition key (user_id:channel_id)
 
   # Session Info
   "user_id": str,              # User identifier
   "channel_id": str,           # Stream Chat channel ID
   "persona": str,              # tenant | landlord | contractor
 
   # Flow State
   "flow_type": str,            # incident | job | bid | discovery | general
   "flow_state": str,           # idle | in_progress | completed
   "active_stage": str,         # Current flow stage
 
   # Active Entities
   "active_incident_id": str,   # Current incident (optional)
   "active_job_id": str,        # Current job (optional)
   "active_bid_id": str,        # Current bid (optional)
 
   # Intent Tracking
   "last_intent": str,          # Last detected intent
   "intent_confidence": float,  # Confidence score (0.0 - 1.0)
 
   # Entities & Discovery
   "entities": dict,            # Extracted entities from conversation
   "discovery_progress": dict,  # Discovery flow state
 
   # Conversation History
   "conversation_history": list, # Last 20 messages [{role, content, timestamp}]
 
   # Timestamps
   "created_at": str,           # ISO timestamp
   "updated_at": str,           # ISO timestamp
   "expires_at": int,           # TTL (Unix timestamp, 24 hours from creation)
 
   # Metadata
   "metadata": dict             # Additional custom fields
}
```
 
**TTL Behavior:**
- Context expires 24 hours after `created_at`
- DynamoDB TTL attribute: `expires_at` (Unix timestamp)
- After expiration, context is automatically deleted
- New context created on next message
 
---
 
### 4.6 Supporting Tables
 
#### Contractors Table
**Table Name:** `landten_contractors`
**Primary Key:** `contractor_id` (PK)
 
```python
{
   "contractor_id": str,
   "name": str,
   "email": str,
   "phone": str,
   "category": list,            # ["plumbing", "electrical"]
   "rating": Decimal,
   "reviews_count": int,
   "stripe_account_id": str,    # Stripe Connect account
   "created_at": str,
   "status": str                # active | inactive | suspended
}
```
 
#### Schedules Table
**Table Name:** `landten_schedules`
**Primary Key:** `contractor_id` (PK), `schedule_id` (SK)
 
```python
{
   "contractor_id": str,
   "schedule_id": str,
   "job_id": str,
   "scheduled_date": str,
   "duration_minutes": int,
   "status": str                # scheduled | completed | cancelled
}
```
 
#### MTTR Events Table
**Table Name:** `landten_mttr_events`
**Primary Key:** `event_id` (PK)
 
```python
{
   "event_id": str,
   "incident_id": str,
   "category": str,
   "severity": str,
   "mttr_hours": float,
   "target_hours": int,
   "met_target": bool,
   "created_at": str
}
```
 
---
 
## 5. API Routes Reference
 
### 5.1 AI & Webhooks
 
| Method | Route | Purpose | Auth |
|--------|-------|---------|------|
| **POST** | `/ai/stream-webhook` | Stream Chat webhook handler | HMAC Signature |
| **POST** | `/ai/init-channel` | Initialize AI bot in channel | None (internal) |
| **POST** | `/ai/send-action` | Send action buttons message | None (internal) |
| **GET** | `/ai/bot-status` | Get bot status and config | None |
 
**POST /ai/stream-webhook**
 
Handles Stream Chat events:
- `message.new` - New user message
- `message.updated` - Edited message
- `reaction.new` - Message reaction
- `health.check` - Health check ping
 
Request:
```json
{
   "type": "message.new",
   "message": {
       "id": "msg-123",
       "text": "My sink is leaking",
       "user": {"id": "alice@example.com", "name": "Alice"}
   },
   "channel_id": "tenant-alice",
   "user": {"id": "alice@example.com"}
}
```
 
Response:
```json
{
   "status": "processed",
   "intent": "incident.report",
   "channel_id": "tenant-alice",
   "card_sent": true,
   "incident_id": "INC-1732147920",
   "flow_state": "incident.active"
}
```
 
---
 
### 5.2 Incidents
 
| Method | Route | Purpose | Auth |
|--------|-------|---------|------|
| **POST** | `/incident/create` | Create incident record | Firebase Token |
| **GET** | `/incident/list/{tenant_id}` | List tenant incidents | Firebase Token |
 
**POST /incident/create**
 
Request:
```json
{
   "id": "INC-1732147920",
   "tenant_id": "alice@example.com",
   "description": "Water leaking from kitchen sink",
   "status": "detected"
}
```
 
Response:
```json
{
   "status": "created",
   "incident": {
       "id": "INC-1732147920",
       "tenant_id": "alice@example.com",
       "description": "Water leaking from kitchen sink",
       "status": "detected",
       "created_at": "2025-11-20T14:32:00Z"
   }
}
```
 
---
 
### 5.3 Jobs
 
| Method | Route | Purpose | Auth |
|--------|-------|---------|------|
| **POST** | `/job/create` | Create job/work order | Firebase Token |
| **GET** | `/job/list/{contractor_id}` | List contractor jobs | Firebase Token |
 
**POST /job/create**
 
Request:
```json
{
   "id": "JOB-1732148000",
   "incident_id": "INC-1732147920",
   "contractor_id": "contractor-123",
   "status": "created"
}
```
 
---
 
### 5.4 Contractors
 
| Method | Route | Purpose | Auth |
|--------|-------|---------|------|
| **POST** | `/contractor/payment/initiate` | Initiate Stripe payment | Firebase Token |
| **POST** | `/contractor/bank-account` | Add bank account | Firebase Token |
| **GET** | `/contractor/{contractor_id}` | Get contractor profile | Firebase Token |
 
**POST /contractor/payment/initiate**
 
Request:
```json
{
   "job_id": "JOB-1732148000",
   "contractor_id": "contractor-123",
   "amount": 150.00,
   "currency": "USD"
}
```
 
Response:
```json
{
   "status": "success",
   "transfer_id": "tr_1234567890",
   "amount": 150.00,
   "contractor_id": "contractor-123"
}
```
 
---
 
### 5.5 Chat & Messaging
 
| Method | Route | Purpose | Auth |
|--------|-------|---------|------|
| **POST** | `/chat/stream` | Start chat stream | Session |
| **POST** | `/chat/message` | Send message | Session |
| **GET** | `/chat/token` | Get Stream Chat token | Session |
 
**GET /chat/token**
 
Request Query Params:
- `user_id` - User identifier
- `persona` - tenant | landlord | contractor
 
Response:
```json
{
   "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
   "user_id": "alice@example.com",
   "expires_at": "2025-11-21T14:32:00Z"
}
```
 
---
 
### 5.6 Profiles
 
| Method | Route | Purpose | Auth |
|--------|-------|---------|------|
| **GET** | `/profile/{user_id}` | Get user profile | Firebase Token |
| **POST** | `/profile` | Create/update profile | Firebase Token |
 
---
 
### 5.7 Frontend API Routes (Next.js)
 
| Method | Route | Purpose | Auth |
|--------|-------|---------|------|
| **GET/POST** | `/api/auth/[...nextauth]` | NextAuth handlers | Public |
| **GET** | `/api/profile` | Get current user profile | Session |
| **GET** | `/api/chat/token` | Get Stream Chat token | Session |
| **GET** | `/api/test-backend` | Backend health check | None |
 
---
 
## 6. AI & Chat Routing System
 
### 6.1 Intent Classification
 
**Service:** `ai_reasoning.py::infer_intent()`
 
**Input:**
```python
{
   "message": "My sink is leaking badly",
   "context": {
       "conversation_history": [...],
       "active_incident": None,
       "persona": "tenant"
   },
   "persona": "tenant"
}
```
 
**Process:**
 
1. **OpenAI Classification (Primary)**
  - Model: GPT-4o-mini
  - Temperature: 0.3
  - System Prompt: Intent classification with persona context
  - Structured Output: {intent, entities, confidence, reasoning}
 
2. **Rule-based Fallback (Secondary)**
  - Keyword matching (leak → incident.report)
  - Pattern detection (status check → job.status)
  - Context-aware rules (active incident + "yes" → approval.decision)
 
**Output:**
```python
{
   "intent": "incident.report",
   "entities": {
       "category": "plumbing",
       "severity": "high",
       "symptoms": ["leak", "water"],
       "location": "kitchen sink"
   },
   "confidence": 0.92,
   "reasoning": "User reported active leak requiring immediate attention"
}
```
 
**Supported Intents:**
 
| Intent | Description | Triggers |
|--------|-------------|----------|
| `incident.report` | New maintenance issue | "leak", "broken", "not working" |
| `incident.followup` | Follow-up on existing incident | With active_incident |
| `discovery.response` | Answer discovery question | During discovery flow |
| `discovery.continue` | Continue discovery | "next", "continue" |
| `job.request` | Create work order | "create job", "work order" |
| `job.inquiry` | Ask about job | "job status", "when scheduled" |
| `job.status` | Check job status | "status", "progress" |
| `bids.request` | View contractor bids | "show bids", "contractors" |
| `bids.compare` | Compare bids | "which contractor", "best price" |
| `approval.request` | Request approval | "approve", "review" |
| `approval.decision` | Approve/reject | "yes approve", "reject" |
| `general.chat` | General conversation | Fallback |
| `greeting` | Hello/hi | "hello", "hi" |
| `help` | Help request | "help", "what can you do" |
 
---
 
### 6.2 Policy Validation
 
**Service:** `policy_validator.py::validate_intent()`
 
**Purpose:** Enforce persona-based permissions
 
**Policies:**
 
```python
PERSONA_POLICIES = {
   "tenant": {
       "allowed_intents": [
           "incident.report",
           "incident.followup",
           "discovery.response",
           "job.inquiry",
           "job.status",
           "general.chat",
           "greeting",
           "help"
       ],
       "forbidden_intents": [
           "approval.decision",
           "bids.compare",
           "job.request"  # Can request but not create directly
       ],
       "max_auto_approve": 0,  # Cannot approve any costs
       "can_view_bids": False,
       "can_approve_jobs": False
   },
 
   "landlord": {
       "allowed_intents": ["*"],  # All intents allowed
       "max_auto_approve": 500,   # Can auto-approve up to $500
       "can_view_bids": True,
       "can_approve_jobs": True,
       "can_initiate_payment": True
   },
 
   "contractor": {
       "allowed_intents": [
           "job.inquiry",
           "job.status",
           "bids.request",
           "general.chat"
       ],
       "forbidden_intents": [
           "incident.report",
           "approval.decision"
       ],
       "can_view_bids": True,      # Only their own bids
       "can_update_job_status": True,
       "can_submit_invoice": True
   }
}
```
 
**Validation Flow:**
 
```python
def validate_intent(intent: str, persona: str) -> Tuple[bool, Optional[str]]:
   """
   Returns:
       (allowed: bool, violation_message: Optional[str])
   """
   policy = PERSONA_POLICIES.get(persona)
 
   if intent in policy["forbidden_intents"]:
       return False, f"As a {persona}, you cannot perform this action."
 
   if intent not in policy["allowed_intents"] and "*" not in policy["allowed_intents"]:
       return False, f"This action requires {get_required_persona(intent)} permissions."
 
   return True, None
```
 
---
 
### 6.3 Flow Engine (State Machine)
 
**Service:** `flow_engine_v2.py::process_transition()`
 
**Purpose:** Manage conversation flow state transitions
 
**Flow Definitions:** `/backend/app/config/flow_definitions.json`
 
**State Transition Example:**
 
```python
# Current state: "idle"
# User intent: "incident.report"
# Persona: "tenant"
 
transition = process_transition(
   user_id="alice@example.com",
   channel_id="tenant-alice",
   persona="tenant",
   intent="incident.report",
   message="My sink is leaking",
   context={}
)
 
# Returns:
{
   "allowed": True,
   "next_stage": "incident.active",
   "actions": ["create_incident", "start_discovery"],
   "violation_message": None
}
```
 
**Flow States:**
 
```
idle
 │
 ├─► incident.active (incident detected)
 │   └─► discovery (gathering details)
 │       └─► job-ready (discovery complete)
 │           └─► job (work order created)
 │               └─► approval (pending landlord approval)
 │                   └─► scheduled (contractor assigned)
 │                       └─► in_progress (work started)
 │                           └─► completed (work finished)
 │                               └─► paid (payment processed)
 │                                   └─► resolved (incident closed)
 │
 └─► general (conversational mode)
```
 
---
 
### 6.4 Context Manager
 
**Service:** `context_manager.py`
 
**Purpose:** Persist conversation state across messages
 
**Key Operations:**
 
```python
# Get or create context
context = context_manager.get_context(
   user_id="alice@example.com",
   channel_id="tenant-alice",
   create_if_missing=True
)
 
# Update context
context_manager.update_context(
   user_id="alice@example.com",
   channel_id="tenant-alice",
   updates={
       "active_incident": "INC-1732147920",
       "entities": {"category": "plumbing"},
       "last_intent": "incident.report"
   }
)
 
# Append message to history
context_manager.append_message(
   user_id="alice@example.com",
   channel_id="tenant-alice",
   role="user",
   content="My sink is leaking"
)
 
# Advance flow state
context_manager.advance_flow_state(
   user_id="alice@example.com",
   channel_id="tenant-alice",
   stage="discovery",
   state_data={"question_index": 0, "answers": {}}
)
```
 
**Context Structure:**
 
```python
{
   "context_id": "alice@example.com:tenant-alice",
   "user_id": "alice@example.com",
   "channel_id": "tenant-alice",
   "persona": "tenant",
 
   # Flow tracking
   "flow_type": "incident",
   "flow_state": "discovery",
   "active_stage": "discovery",
 
   # Active entities
   "active_incident": "INC-1732147920",
   "active_job": None,
 
   # Intent history
   "last_intent": "discovery.response",
   "intent_confidence": 0.89,
 
   # Discovery progress
   "discovery_progress": {
       "question_index": 2,
       "answers": {
           "q0": "Yes, water is flowing",
           "q1": "Kitchen sink under the cabinet"
       }
   },
 
   # Conversation history (last 20 messages)
   "conversation_history": [
       {"role": "user", "content": "My sink is leaking", "timestamp": "2025-11-20T14:32:00Z"},
       {"role": "assistant", "content": "I've created incident INC-1732147920", "timestamp": "2025-11-20T14:32:05Z"},
       {"role": "assistant", "content": "Is the water still flowing?", "timestamp": "2025-11-20T14:32:06Z"},
       {"role": "user", "content": "Yes, water is flowing", "timestamp": "2025-11-20T14:33:00Z"}
   ],
 
   # TTL
   "created_at": "2025-11-20T14:32:00Z",
   "updated_at": "2025-11-20T14:33:00Z",
   "expires_at": 1732233120  # Unix timestamp (24 hours from creation)
}
```
 
---
 
## 7. Persona System
 
### 7.1 Tenant Persona
 
**Capabilities:**
- Report maintenance incidents
- Answer discovery questions
- Upload photos/videos
- View job status
- Receive notifications
 
**Restrictions:**
- Cannot approve jobs
- Cannot view contractor bids
- Cannot see cost breakdowns
- Cannot modify jobs
 
**Conversation Tone:**
- Friendly, empathetic
- Simple language
- Reassuring
- Focused on issue resolution
 
**Example Interactions:**
 
```
Tenant: "My sink is leaking really bad"
Bot: "I understand - a leaking sink can be stressful. I've created incident
    INC-1732147920 and will help you get this fixed quickly. Is the water
    still flowing right now?"
 
Tenant: "Yes, it's getting worse"
Bot: "Thanks for letting me know. Where exactly is the leak located?"
```
 
---
 
### 7.2 Landlord Persona
 
**Capabilities:**
- View all incidents
- Approve/reject work orders
- Compare contractor bids
- Initiate payments
- Auto-approve jobs < $500
- View cost analytics
- Manage properties
 
**Restrictions:**
- (Minimal - has most permissions)
 
**Conversation Tone:**
- Professional, efficient
- Business-focused
- Data-driven
- Cost-conscious
 
**Example Interactions:**
 
```
Landlord: "Show me pending approvals"
Bot: "You have 2 pending approvals:
    1. Job JOB-1732148000 - Plumbing repair, $150 (auto-approved)
    2. Job JOB-1732148100 - HVAC repair, $650 (requires approval)
 
    Would you like to review the contractor bids for Job JOB-1732148100?"
 
Landlord: "Yes, show me the bids"
Bot: [Sends bids comparison card with 3 contractors]
```
 
---
 
### 7.3 Contractor Persona
 
**Capabilities:**
- View assigned jobs
- Submit/update bids
- Update job status
- Submit completion photos
- Submit invoices
- Manage bank account (Stripe)
 
**Restrictions:**
- Cannot create incidents
- Cannot approve jobs
- Cannot view other contractors' bids
- Limited property data access
 
**Conversation Tone:**
- Professional, task-focused
- Clear, concise
- Job-oriented
- Status-update driven
 
**Example Interactions:**
 
```
Contractor: "What jobs do I have today?"
Bot: "You have 2 jobs scheduled for today:
    1. Job JOB-1732148000 - Plumbing repair at 123 Main St, 10:00 AM
    2. Job JOB-1732148200 - Electrical fix at 456 Oak Ave, 2:00 PM
 
    Would you like details on either job?"
 
Contractor: "Update JOB-1732148000 to completed"
Bot: "Great! I've marked Job JOB-1732148000 as completed. Please upload
    completion photos to finalize the job."
```
 
---
 
## 8. Background Services
 
### 8.1 Current Services
 
**Note:** Currently, there are no explicit background tasks or cron jobs in the codebase.
 
**Handled by Infrastructure:**
- **DynamoDB TTL:** Automatic context expiration (24 hours)
- **Stream Chat:** Real-time message delivery
- **Stripe Webhooks:** Payment event processing (future)
 
### 8.2 Future Services (Recommended)
 
1. **Channel Snapshot Aggregation**
  - Frequency: Every 6 hours
  - Purpose: Aggregate conversation metrics
  - Table: `channel_snapshots`
 
2. **MTTR Metric Calculation**
  - Trigger: On incident resolution
  - Purpose: Calculate mean time to repair
  - Table: `mttr_events`
 
3. **Expired Context Cleanup**
  - Frequency: Daily
  - Purpose: Verify TTL expiration (backup to DynamoDB TTL)
  - Table: `landten_chat_contexts`
 
4. **Payment Reconciliation**
  - Frequency: Daily
  - Purpose: Match Stripe transfers with job payments
  - Tables: `landten_jobs`, Stripe API
 
---
 
## 9. External Integrations
 
### 9.1 Stream Chat
 
**Purpose:** Real-time messaging infrastructure
 
**SDK:** `stream-chat-python`
 
**Configuration:**
```python
STREAM_CHAT_API_KEY = os.getenv("STREAM_CHAT_API_KEY")
STREAM_CHAT_API_SECRET = os.getenv("STREAM_CHAT_API_SECRET")
STREAM_WEBHOOK_SECRET = os.getenv("STREAM_WEBHOOK_SECRET")
```
 
**Bot Configuration:**
```python
BOTS = {
   "tenant": {
       "id": "ai-tenant-bot",
       "name": "PropertyHelper",
       "description": "Your friendly maintenance assistant"
   },
   "landlord": {
       "id": "ai-landlord-bot",
       "name": "LandlordAssistant",
       "description": "Property management AI"
   },
   "contractor": {
       "id": "ai-contractor-bot",
       "name": "ContractorBot",
       "description": "Job coordination assistant"
   }
}
```
 
**Webhook Events:**
- `message.new` - New message from user
- `message.updated` - Message edited
- `reaction.new` - Reaction added to message
- `health.check` - Stream health check
 
**Security:**
- HMAC SHA256 signature verification
- Header: `x-signature`
- Payload: Raw request body
 
---
 
### 9.2 OpenAI
 
**Purpose:** Natural language understanding and intent classification
 
**SDK:** `openai`
 
**Configuration:**
```python
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
```
 
**Usage:**
 
```python
response = openai.ChatCompletion.create(
   model="gpt-4o-mini",
   temperature=0.3,
   messages=[
       {"role": "system", "content": "You are an intent classifier..."},
       {"role": "user", "content": user_message}
   ]
)
 
intent = response.choices[0].message.content
```
 
**Rate Limits:**
- Requests per minute: 500 (varies by tier)
- Tokens per minute: 100,000 (varies by tier)
 
**Fallback Strategy:**
- If OpenAI fails, use rule-based classification
- If confidence < 0.5, escalate to human or ask clarifying question
 
---
 
### 9.3 Stripe
 
**Purpose:** Payment processing and contractor payouts
 
**SDK:** `stripe`
 
**Configuration:**
```python
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY")
```
 
**Stripe Connect Flow:**
 
1. **Contractor Onboarding**
  ```python
  account = stripe.Account.create(
      type="express",
      country="US",
      email=contractor_email,
      capabilities={
          "transfers": {"requested": True}
      }
  )
  ```
 
2. **Add Bank Account**
  ```python
  bank_account = stripe.Account.create_external_account(
      account_id,
      external_account={
          "object": "bank_account",
          "country": "US",
          "currency": "usd",
          "account_number": "000123456789",
          "routing_number": "110000000"
      }
  )
  ```
 
3. **Create Payout**
  ```python
  transfer = stripe.Transfer.create(
      amount=15000,  # $150.00 in cents
      currency="usd",
      destination=contractor.stripe_account_id,
      transfer_group=job_id
  )
  ```
 
**Webhook Events (Future):**
- `transfer.created` - Transfer initiated
- `transfer.paid` - Transfer completed
- `account.updated` - Contractor account updated
 
---
 
### 9.4 Google OAuth
 
**Purpose:** User authentication
 
**SDK:** NextAuth.js with Google Provider
 
**Configuration:**
```javascript
GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET
NEXTAUTH_SECRET = process.env.NEXTAUTH_SECRET
NEXTAUTH_URL = process.env.NEXTAUTH_URL
```
 
**OAuth Flow:**
 
1. User clicks "Sign in with Google"
2. Redirects to Google OAuth consent screen
3. User approves
4. Google redirects back with authorization code
5. NextAuth exchanges code for tokens
6. NextAuth creates session
7. Backend creates/updates profile in DynamoDB
 
**Session Management:**
- Session duration: 30 days
- Cookie: `__Host-next-auth.session-token`
- JWT token includes: user_id, email, persona
 
---
 
### 9.5 AWS DynamoDB
 
**Purpose:** NoSQL database for all application data
 
**SDK:** `boto3`
 
**Configuration:**
```python
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
```
 
**Table Naming Convention:**
```python
def table_name(base_name: str) -> str:
   prefix = os.getenv("DYNAMODB_TABLE_PREFIX", "landten_")
   return f"{prefix}{base_name}"
 
# Examples:
# "incidents" → "landten_incidents"
# "jobs" → "landten_jobs"
```
 
**Billing:**
- On-Demand capacity mode (pay per request)
- Estimated cost: $0.25 per million writes, $0.25 per million reads
 
---
 
## 10. Observability & Logging
 
### 10.1 Logging Strategy
 
**Current Logging:**
 
```python
# Console logging with structured prefixes
print(f"[ai-webhook] Processing message from {user_id}")
print(f"[incident-flow] ✅ Incident {incident_id} created")
print(f"[context-manager] ❌ Failed to update context: {error}")
```
 
**Log Levels (Implicit):**
- `[service] Message` - INFO
- `[service] ⚠️  Warning` - WARNING
- `[service] ❌ ERROR` - ERROR
- `[service] ✅ Success` - SUCCESS
 
**Key Logging Points:**
 
1. **Webhook Entry:**
  ```python
  [ai-webhook] ========== Incoming webhook request ==========
  [ai-webhook] Received 2048 bytes of payload
  [ai-webhook] Event type: message.new
  ```
 
2. **Intent Detection:**
  ```python
  [ai-webhook] Detected intent: incident.report (confidence: 0.92)
  [ai-reasoning] OpenAI classification successful
  ```
 
3. **Incident Creation:**
  ```python
  [incident-flow] 🔍 Classifying issue
  [incident-flow] ✅ Classified as: plumbing | Severity: high | Urgency: immediate
  [incident-flow] ⚖️  Threshold decision: actionable=True
  [incident-flow] 📋 Created incident card: INC-1732147920
  [incident-flow] 💾 Incident persisted to DynamoDB
  ```
 
4. **Job Creation:**
  ```python
  [workorder-flow] ✅ Created work order JOB-1732148000 for incident INC-1732147920
  ```
 
5. **Context Updates:**
  ```python
  [context-manager] ✅ Active incident set: INC-1732147920
  [context-manager] ✅ Flow state advanced to incident.active
  ```
 
6. **Errors:**
  ```python
  [ai-webhook] ❌ ERROR: Exception while handling message: {exception}
  [incident-flow] ❌ Failed to persist incident to DynamoDB: {error}
  ```
 
---
 
### 10.2 Enhanced Logging (Phase 1 Additions)
 
**Structured Logging Format:**
 
```python
import logging
import json
from datetime import datetime
 
class StructuredLogger:
   """Enhanced logger with structured output for better observability"""
 
   def __init__(self, service_name: str):
       self.service = service_name
       self.logger = logging.getLogger(service_name)
 
   def log(self, level: str, event: str, **kwargs):
       """Log structured event with metadata"""
       log_entry = {
           "timestamp": datetime.utcnow().isoformat(),
           "service": self.service,
           "level": level,
           "event": event,
           **kwargs
       }
 
       if level == "ERROR":
           self.logger.error(json.dumps(log_entry))
       elif level == "WARNING":
           self.logger.warning(json.dumps(log_entry))
       else:
           self.logger.info(json.dumps(log_entry))
 
   def trace_incident_creation(self, incident_id: str, **metadata):
       """Trace incident creation flow"""
       self.log("INFO", "incident_created",
               incident_id=incident_id,
               **metadata)
 
   def trace_job_creation(self, job_id: str, incident_id: str, **metadata):
       """Trace job creation flow"""
       self.log("INFO", "job_created",
               job_id=job_id,
               incident_id=incident_id,
               **metadata)
 
   def trace_bid_creation(self, bid_id: str, job_id: str, **metadata):
       """Trace bid creation flow"""
       self.log("INFO", "bid_created",
               bid_id=bid_id,
               job_id=job_id,
               **metadata)
```
 
**Usage:**
 
```python
logger = StructuredLogger("incident-flow")
 
logger.trace_incident_creation(
   incident_id="INC-1732147920",
   category="plumbing",
   severity="high",
   urgency="immediate",
   tenant_id="alice@example.com",
   estimated_cost=150.0
)
```
 
**Output:**
 
```json
{
   "timestamp": "2025-11-20T14:32:05.123Z",
   "service": "incident-flow",
   "level": "INFO",
   "event": "incident_created",
   "incident_id": "INC-1732147920",
   "category": "plumbing",
   "severity": "high",
   "urgency": "immediate",
   "tenant_id": "alice@example.com",
   "estimated_cost": 150.0
}
```
 
---
 
### 10.3 Metrics & Analytics
 
**Current Metrics Tables:**
 
1. **MTTR Events** (`landten_mttr_events`)
  - Tracks incident resolution time
  - Compares actual vs. target MTTR
  - Aggregated by category and severity
 
2. **Channel Snapshots** (`channel_snapshots`)
  - Conversation engagement metrics
  - Message volume
  - Response times
 
**Recommended Metrics (Future):**
 
1. **Intent Accuracy**
  - Track AI intent classification accuracy
  - Compare with user corrections
  - Table: `ai_training_feedback`
 
2. **Flow Completion Rate**
  - Track % of incidents that reach resolution
  - Identify drop-off points
  - Table: `flow_analytics`
 
3. **Cost Metrics**
  - Average job cost by category
  - Auto-approval rate
  - Payment processing time
 
---
 
## 11. Error Handling Strategy
 
### 11.1 Graceful Degradation
 
**Principle:** System should continue to function even when external services fail.
 
**Examples:**
 
1. **DynamoDB Unavailable:**
  ```python
  try:
      IncidentRepo().create_incident(payload)
  except Exception:
      # Fallback: in-memory storage
      _IN_MEMORY_INCIDENTS.append(payload)
      return {
          "status": "created",
          "incident": payload,
          "warning": "Dynamo unavailable; stored in-memory"
      }
  ```
 
2. **OpenAI API Failure:**
  ```python
  try:
      intent = openai_classify(message)
  except Exception:
      # Fallback: rule-based classification
      intent = rule_based_classify(message)
  ```
 
3. **Stream Chat Failure:**
  ```python
  try:
      bot.send_message(channel_id, text)
  except Exception:
      # Fallback: store message for retry
      message_queue.append((channel_id, text))
  ```
 
---
 
### 11.2 Error Response Format
 
**Consistent Error Structure:**
 
```python
{
   "status": "error",
   "error": "DynamoDB connection timeout",
   "error_code": "DB_TIMEOUT",
   "hint": "Check AWS credentials and network connectivity",
   "timestamp": "2025-11-20T14:32:05Z",
   "request_id": "req-1732147920"
}
```
 
**HTTP Status Codes:**
 
| Code | Meaning | Usage |
|------|---------|-------|
| 400 | Bad Request | Invalid input, missing required fields |
| 401 | Unauthorized | Invalid signature, missing auth token |
| 403 | Forbidden | Policy violation, insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | External service down (temporary) |
 
---
 
### 11.3 Retry Strategy
 
**Exponential Backoff:**
 
```python
def retry_with_backoff(func, max_retries=3, base_delay=1.0):
   """Retry function with exponential backoff"""
   for attempt in range(max_retries):
       try:
           return func()
       except Exception as e:
           if attempt == max_retries - 1:
               raise
 
           delay = base_delay * (2 ** attempt)  # 1s, 2s, 4s
           time.sleep(delay)
```
 
**Use Cases:**
- DynamoDB throttling
- OpenAI rate limits
- Stripe API transient errors
 
---
 
## 12. Performance Considerations
 
### 12.1 Database Optimization
 
**DynamoDB Best Practices:**
 
1. **Efficient Queries:**
  - Use partition key + sort key queries (not scans)
  - Add GSI for common access patterns
  - Limit result set size
 
2. **Batch Operations:**
  ```python
  # Instead of multiple put_item calls
  with table.batch_writer() as batch:
      for item in items:
          batch.put_item(Item=item)
  ```
 
3. **Conditional Writes:**
  ```python
  # Prevent overwrites
  table.put_item(
      Item=item,
      ConditionExpression="attribute_not_exists(incident_id)"
  )
  ```
 
---
 
### 12.2 API Response Time Targets
 
| Endpoint | Target | Max Acceptable |
|----------|--------|----------------|
| `/ai/stream-webhook` | < 500ms | 2s |
| `/incident/create` | < 200ms | 1s |
| `/job/create` | < 200ms | 1s |
| `/chat/token` | < 100ms | 500ms |
| OpenAI classification | < 2s | 5s |
 
**Optimization Strategies:**
- Cache OpenAI responses for similar messages (future)
- Use DynamoDB on-demand mode (auto-scaling)
- Async processing for non-critical tasks
- Connection pooling for AWS SDK
 
---
 
### 12.3 Scalability Considerations
 
**Current Limitations:**
- Single-region deployment (us-east-1)
- Synchronous webhook processing
- No message queuing for retries
 
**Future Improvements:**
1. **Message Queue (SQS):**
  - Decouple webhook receipt from processing
  - Enable retry with dead-letter queue
 
2. **Lambda Functions:**
  - Serverless processing for webhooks
  - Auto-scaling based on traffic
 
3. **Multi-Region:**
  - Global DynamoDB tables
  - CloudFront for frontend
  - Regional Stream Chat endpoints
 
---
 
## Appendix A: Environment Variables Reference
 
### Backend (.env)
 
```bash
# Auth
AUTH_DISABLED=true  # Disable auth for development
 
# Stream Chat
STREAM_CHAT_API_KEY=your_stream_api_key
STREAM_CHAT_API_SECRET=your_stream_api_secret
STREAM_WEBHOOK_SECRET=your_webhook_secret
 
# OpenAI
OPENAI_API_KEY=sk-your_openai_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.3
 
# DynamoDB
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
DYNAMODB_TABLE_PREFIX=landten_
 
# Stripe
STRIPE_SECRET_KEY=sk_test_your_stripe_key
 
# Thresholds
INCIDENT_THRESHOLD_LOW=200
INCIDENT_THRESHOLD_MEDIUM=500
INCIDENT_THRESHOLD_HIGH=1000
```
 
### Frontend (.env.local)
 
```bash
# NextAuth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your_nextauth_secret
BACKEND_INTERNAL_URL=http://localhost:8080
NEXT_PUBLIC_BACKEND_URL=http://localhost:8080
 
# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
 
# Stripe
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_key
 
# Stream Chat (Frontend)
NEXT_PUBLIC_STREAM_API_KEY=your_stream_api_key
```
 
---
 
## Appendix B: Glossary
 
| Term | Definition |
|------|------------|
| **Incident** | A reported maintenance issue requiring attention |
| **Discovery** | Question-answer flow to gather incident details |
| **Work Order** | Same as "job" - a formal request for contractor services |
| **Job** | A work assignment created from an incident |
| **Bid** | A contractor's quote for a job (price, ETA, rating) |
| **Persona** | User role (tenant, landlord, contractor) |
| **Intent** | Classified purpose of user message (e.g., incident.report) |
| **Entity** | Extracted data from message (category, severity, location) |
| **Flow State** | Current stage in conversation workflow |
| **Context** | Persistent session data (conversation history, active entities) |
| **MTTR** | Mean Time to Repair - metric for incident resolution speed |
| **TTL** | Time To Live - automatic expiration of context records |
| **Bot** | AI assistant (tenant-bot, landlord-bot, contractor-bot) |
 
---
 
## Appendix C: Quick Reference - Common Tasks
 
### How to trace an incident end-to-end:
 
1. Check webhook logs: `[ai-webhook]` entries
2. Find incident creation: `[incident-flow] 📋 Created incident card: {incident_id}`
3. Track discovery: `[incident-flow] 🔍 Discovery flow initiated`
4. Find job creation: `[workorder-flow] ✅ Created work order {job_id}`
5. Check context updates: `[context-manager] ✅ Active incident set`
 
### How to debug intent classification:
 
1. Look for: `[ai-webhook] Detected intent: {intent} (confidence: {score})`
2. Check: `[ai-reasoning] OpenAI classification successful` or fallback
3. Verify: `[ai-webhook] Policy validation passed for {persona}`
 
### How to trace payment flow:
 
1. Job marked complete: `job.status = "completed"`
2. Payment initiated: `POST /contractor/payment/initiate`
3. Stripe transfer: `[stripe-service] Transfer created: {transfer_id}`
4. Job updated: `job.status = "paid"`
 
---