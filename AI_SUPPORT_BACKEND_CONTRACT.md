# AI Support Experience - Backend Contract

> **Complete API specification for the AI Support Experience orchestrator**

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Event Protocol](#event-protocol)
4. [Backend Endpoints](#backend-endpoints)
5. [JSON Schemas](#json-schemas)
6. [State Machine](#state-machine)
7. [Error Handling](#error-handling)
8. [Example Flows](#example-flows)

---

## Overview

The AI Support Experience is an Amazon-style guided support flow that uses:

- **Frontend**: Next.js + Stream Chat React
- **Backend**: Python FastAPI orchestrator + LLM
- **Communication**: Stream Chat custom events
- **State Management**: Backend-driven UI state machine

### Key Principles

1. **Backend controls UI state** - Frontend renders based on `ui_mode` events
2. **Event-driven architecture** - All communication via Stream Chat events
3. **Stateless frontend** - No complex frontend state management
4. **Persona-aware** - Different flows for tenant/landlord/contractor

---

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Frontend  │◄───────►│  Stream Chat │◄───────►│   Backend   │
│   (Next.js) │  Events │   (WebSocket)│  Webhook│ (Orchestrator)│
└─────────────┘         └──────────────┘         └─────────────┘
       │                                                  │
       │                                                  │
       ▼                                                  ▼
  UI Panels                                        LLM + Logic
  - CTA Panel                                      - Intent Router
  - Item Picker                                    - State Machine
  - Reason Selector                                - DynamoDB
  - Resolution Panel                               - Context Builder
```

### Event Flow

1. **User Action** → Frontend sends `ai_intent` event to Stream
2. **Stream Webhook** → Backend receives event via webhook
3. **Backend Processing** → Orchestrator processes intent + updates state
4. **State Update** → Backend sends `ai_state` event back via Stream
5. **UI Update** → Frontend renders appropriate panel

---

## Event Protocol

### Frontend → Backend: `ai_intent`

Custom Stream Chat event that represents user actions.

```typescript
{
  type: "ai_intent",
  intent: IntentType,
  payload: Record<string, unknown>,
  user_id: string,
  channel_id: string,
  created_at: string
}
```

**Intent Types:**

- `session_init` - Initialize new support session
- `user_message` - Free-form text message
- `item_selected` - User selected an item from gallery
- `reason_selected` - User selected a reason/issue
- `resolution_action` - User chose a resolution action
- `escalate_human` - Request human support

### Backend → Frontend: `ai_state`

Custom Stream Chat event that controls UI state.

```typescript
{
  type: "ai_state",
  ui_mode: UIMode,
  payload: Record<string, unknown>,
  metadata?: {
    session_id?: string,
    incident_id?: string,
    timestamp?: string
  }
}
```

**UI Modes:**

- `idle` - No active panel
- `cta_panel` - Initial "How can we help?" panel
- `gallery` - Item picker (properties, units, etc.)
- `selector` - Reason picker (issue selection)
- `diagnosis` - AI analyzing the issue
- `resolution` - Final resolution options
- `escalation` - Human escalation form
- `complete` - Session complete

---

## Backend Endpoints

### 1. Initialize Session

**Endpoint:** `POST /ai-support/init`

**Purpose:** Creates a new AI support session and returns initial state.

**Request:**
```json
{
  "user_id": "user@example.com",
  "persona": "tenant" | "landlord" | "contractor",
  "mode": "guided"
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "session_12345",
  "channel_id": "ai-support-user@example.com-1234567890",
  "initial_state": {
    "type": "ai_state",
    "ui_mode": "cta_panel",
    "payload": {
      "title": "How can we help?",
      "options": [
        {
          "id": "maintenance",
          "label": "Report Maintenance Issue",
          "description": "Something needs fixing",
          "icon": "🔧"
        },
        {
          "id": "payment",
          "label": "Payment Question",
          "description": "Billing or rent related",
          "icon": "💳"
        }
      ]
    }
  }
}
```

### 2. Process Intent

**Endpoint:** `POST /ai-support/intent`

**Purpose:** Processes user intent and triggers state transition.

**Request:**
```json
{
  "user_id": "user@example.com",
  "channel_id": "ai-support-user@example.com-1234567890",
  "session_id": "session_12345",
  "intent": "item_selected",
  "payload": {
    "item_id": "property_123",
    "item_data": {
      "id": "property_123",
      "title": "123 Main St, Apt 4B",
      "subtitle": "Downtown Location",
      "image": "https://..."
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "acknowledged": true
}
```

**Note:** Backend sends `ai_state` event via Stream webhook after processing.

### 3. Stream Webhook Handler

**Endpoint:** `POST /webhooks/stream`

**Purpose:** Receives all Stream Chat events including custom `ai_intent` events.

**Stream Event Structure:**
```json
{
  "type": "message.new" | "custom.ai_intent",
  "channel_id": "messaging:ai-support-...",
  "user": {
    "id": "user@example.com"
  },
  "custom": {
    "intent": "item_selected",
    "payload": { ... }
  }
}
```

**Processing Flow:**
1. Validate Stream signature
2. Extract intent and payload
3. Route to appropriate handler
4. Update session state in DynamoDB
5. Send `ai_state` event back via Stream API

---

## JSON Schemas

### CTA Panel Payload

```json
{
  "title": "How can we help?",
  "subtitle": "Select a category to get started",
  "options": [
    {
      "id": "maintenance",
      "label": "Report Maintenance Issue",
      "description": "Something needs fixing",
      "icon": "🔧",
      "persona_specific": false
    }
  ]
}
```

### Gallery Payload

```json
{
  "title": "Which item is this about?",
  "subtitle": "Select the property or unit",
  "items": [
    {
      "id": "property_123",
      "title": "123 Main St, Apt 4B",
      "subtitle": "Downtown Location",
      "description": "2 bed, 1 bath",
      "image": "https://example.com/image.jpg",
      "metadata": {
        "property_id": "prop_123",
        "unit_id": "unit_456"
      }
    }
  ],
  "allow_skip": false
}
```

### Reason Selector Payload

```json
{
  "title": "What seems to be the issue?",
  "subtitle": "Select the most relevant option",
  "reasons": [
    {
      "id": "leak",
      "label": "Water leak",
      "description": "Dripping or flooding",
      "severity": "high"
    },
    {
      "id": "appliance",
      "label": "Appliance broken",
      "description": "Fridge, stove, washer, etc.",
      "severity": "medium"
    }
  ],
  "selected_item": {
    "id": "property_123",
    "title": "123 Main St, Apt 4B"
  }
}
```

### Diagnosis Payload

```json
{
  "status": "analyzing" | "complete" | "error",
  "message": "Analyzing your issue...",
  "progress": 75
}
```

### Resolution Payload

```json
{
  "summary": "Based on your description, this appears to be a plumbing issue requiring immediate attention.",
  "diagnosis": "Water leak in kitchen sink - likely caused by worn seal",
  "severity": "high",
  "actions": [
    {
      "id": "schedule_contractor",
      "label": "Schedule Emergency Plumber",
      "description": "We'll dispatch a certified plumber within 2 hours",
      "type": "primary",
      "icon": "🔧",
      "requires_confirmation": false
    },
    {
      "id": "escalate_human",
      "label": "Speak to Support Agent",
      "description": "Connect with a human for more help",
      "type": "secondary",
      "icon": "💬",
      "requires_confirmation": false
    }
  ],
  "estimated_time": "2-4 hours",
  "estimated_cost": "$150-$300"
}
```

### Escalation Payload

```json
{
  "reason": "User requested human agent",
  "context": {
    "session_id": "session_12345",
    "incident_id": "incident_789",
    "selected_item": "property_123",
    "selected_reason": "leak"
  },
  "message_placeholder": "Describe your issue in detail..."
}
```

---

## State Machine

### State Transitions

```
session_init → cta_panel
    ↓
user_message (category selected) → gallery
    ↓
item_selected → selector
    ↓
reason_selected → diagnosis
    ↓
(AI processing) → resolution
    ↓
resolution_action → complete | escalation
    ↓
escalate_human → escalation
```

### Persona-Specific Flows

#### Tenant Flow
```
session_init → cta_panel (maintenance, payment, community)
  → gallery (properties/units tenant has access to)
  → selector (maintenance issues)
  → diagnosis
  → resolution (schedule contractor, DIY guide, escalate)
```

#### Landlord Flow
```
session_init → cta_panel (tenant issues, property mgmt, financials)
  → gallery (all owned properties)
  → selector (tenant complaints, maintenance, payments)
  → diagnosis
  → resolution (assign contractor, contact tenant, view report)
```

#### Contractor Flow
```
session_init → cta_panel (view jobs, update status, billing)
  → gallery (assigned properties)
  → selector (job-related issues)
  → diagnosis
  → resolution (update job, upload photos, submit invoice)
```

---

## Error Handling

### Frontend Error Handling

```typescript
try {
  await sendIntent("item_selected", payload);
} catch (error) {
  // Show error toast/notification
  // Optionally retry or fallback to text input
}
```

### Backend Error Responses

**Via Stream Event:**
```json
{
  "type": "custom.error",
  "message": "Failed to process request",
  "code": "PROCESSING_ERROR",
  "retry_after": 5000
}
```

### Common Error Codes

- `INVALID_INTENT` - Unknown intent type
- `MISSING_PAYLOAD` - Required payload fields missing
- `SESSION_NOT_FOUND` - Session ID doesn't exist
- `PROCESSING_ERROR` - LLM or logic error
- `RATE_LIMIT` - Too many requests
- `UNAUTHORIZED` - Invalid user or permissions

---

## Example Flows

### Complete Maintenance Request Flow

**1. Session Init**

Frontend → Backend:
```json
{
  "type": "ai_intent",
  "intent": "session_init",
  "payload": {
    "persona": "tenant",
    "mode": "guided"
  }
}
```

Backend → Frontend:
```json
{
  "type": "ai_state",
  "ui_mode": "cta_panel",
  "payload": {
    "options": [
      { "id": "maintenance", "label": "Report Maintenance Issue", "icon": "🔧" },
      { "id": "payment", "label": "Payment Question", "icon": "💳" },
      { "id": "community", "label": "Community Question", "icon": "👥" }
    ]
  }
}
```

**2. User Selects Maintenance**

Frontend → Backend:
```json
{
  "type": "ai_intent",
  "intent": "user_message",
  "payload": {
    "category": "maintenance"
  }
}
```

Backend → Frontend:
```json
{
  "type": "ai_state",
  "ui_mode": "gallery",
  "payload": {
    "title": "Which property is this about?",
    "items": [
      {
        "id": "prop_123",
        "title": "123 Main St, Apt 4B",
        "image": "https://...",
        "subtitle": "Downtown Location"
      }
    ]
  }
}
```

**3. User Selects Property**

Frontend → Backend:
```json
{
  "type": "ai_intent",
  "intent": "item_selected",
  "payload": {
    "item_id": "prop_123",
    "item_data": { ... }
  }
}
```

Backend → Frontend:
```json
{
  "type": "ai_state",
  "ui_mode": "selector",
  "payload": {
    "title": "What seems to be the issue?",
    "reasons": [
      { "id": "leak", "label": "Water leak", "severity": "high" },
      { "id": "heating", "label": "Heating/AC", "severity": "medium" },
      { "id": "appliance", "label": "Appliance broken", "severity": "medium" }
    ],
    "selected_item": {
      "id": "prop_123",
      "title": "123 Main St, Apt 4B"
    }
  }
}
```

**4. User Selects Reason**

Frontend → Backend:
```json
{
  "type": "ai_intent",
  "intent": "reason_selected",
  "payload": {
    "reason_id": "leak",
    "reason_label": "Water leak"
  }
}
```

Backend → Frontend (Diagnosis):
```json
{
  "type": "ai_state",
  "ui_mode": "diagnosis",
  "payload": {
    "status": "analyzing",
    "message": "Analyzing your issue..."
  }
}
```

**5. Backend Completes Diagnosis**

Backend → Frontend (Resolution):
```json
{
  "type": "ai_state",
  "ui_mode": "resolution",
  "payload": {
    "summary": "Water leak detected in your unit. This requires immediate attention.",
    "diagnosis": "Plumbing issue - likely kitchen or bathroom",
    "severity": "high",
    "actions": [
      {
        "id": "schedule_emergency",
        "label": "Schedule Emergency Plumber",
        "description": "Available within 2 hours",
        "type": "primary"
      },
      {
        "id": "temporary_fix",
        "label": "View Temporary Fix Guide",
        "description": "Stop the leak yourself",
        "type": "secondary"
      }
    ],
    "estimated_time": "2-4 hours",
    "estimated_cost": "$150-$300"
  }
}
```

**6. User Selects Resolution Action**

Frontend → Backend:
```json
{
  "type": "ai_intent",
  "intent": "resolution_action",
  "payload": {
    "action_id": "schedule_emergency"
  }
}
```

Backend → Frontend:
```json
{
  "type": "ai_state",
  "ui_mode": "complete",
  "payload": {
    "message": "Emergency plumber scheduled for today at 2:00 PM",
    "confirmation_number": "MAINT-12345"
  }
}
```

---

## Implementation Checklist

### Backend Requirements

- [ ] Implement `/ai-support/init` endpoint
- [ ] Implement `/ai-support/intent` endpoint
- [ ] Set up Stream webhook handler at `/webhooks/stream`
- [ ] Implement intent routing logic
- [ ] Create state machine for UI transitions
- [ ] Add DynamoDB session storage
- [ ] Integrate LLM for diagnosis and recommendations
- [ ] Implement persona-specific logic
- [ ] Add error handling and retry logic
- [ ] Set up logging and monitoring

### Stream Chat Configuration

- [ ] Create custom event types: `ai_intent`, `ai_state`
- [ ] Configure webhook URL
- [ ] Set up webhook signature verification
- [ ] Enable custom events in channel settings
- [ ] Configure channel permissions

### Testing

- [ ] Test session initialization
- [ ] Test all intent types
- [ ] Test state transitions
- [ ] Test error scenarios
- [ ] Test persona-specific flows
- [ ] Test concurrent sessions
- [ ] Load testing
- [ ] Mobile responsiveness

---

## Security Considerations

1. **Authentication**: All requests must validate user session
2. **Authorization**: Check user has access to selected items
3. **Rate Limiting**: Prevent abuse of AI endpoints
4. **Input Validation**: Sanitize all user inputs
5. **Stream Signature**: Verify webhook signatures
6. **Session Management**: Expire old sessions
7. **PII Protection**: Handle sensitive data appropriately

---

## Performance Optimization

1. **Caching**: Cache user properties/units for gallery
2. **Lazy Loading**: Load images on demand
3. **WebSocket**: Use Stream's real-time updates efficiently
4. **Debouncing**: Prevent rapid-fire intent sends
5. **Optimistic Updates**: Show UI changes before backend confirms
6. **Connection Pooling**: Reuse HTTP connections to backend

---

## Monitoring & Analytics

### Key Metrics

- Session completion rate
- Average time to resolution
- Most common issue types
- Escalation rate
- User satisfaction scores
- Response times (frontend → backend → frontend)

### Logging Points

- Session initialization
- Each intent transition
- LLM calls and responses
- Errors and retries
- Resolution outcomes
- Escalations to human support

---

## Future Enhancements

1. **Multi-language Support**: Internationalization
2. **Voice Input**: Voice-to-text for accessibility
3. **Image Upload**: Allow users to upload photos of issues
4. **Scheduling Integration**: Calendar picker for contractor visits
5. **Payment Integration**: In-chat payment for services
6. **AI Follow-ups**: Automated check-ins after resolution
7. **Smart Suggestions**: Learn from historical data
8. **Rich Media**: Video tutorials, animated guides

---

## Support

For questions or issues with the AI Support Experience:

- **Frontend Issues**: Check `/frontend/src/app/ai-support/`
- **Backend Issues**: Check `/backend/ai_support/`
- **Stream Chat**: Review Stream dashboard for event logs
- **Documentation**: This file + type definitions in `/types/ai-support.ts`

---

**Version**: 1.0
**Last Updated**: 2025-01-28
**Maintainer**: LandTen Development Team
