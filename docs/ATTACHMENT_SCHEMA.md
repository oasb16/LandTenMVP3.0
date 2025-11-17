# Stream Chat Attachment Schema Reference

**Last Updated:** October 27, 2025

## Overview

This document defines the standardized attachment schemas used between backend (`card_builder.py`) and frontend (`MessageCards.tsx`) for interactive message cards.

---

## Supported Card Types

All card types are sent as Stream Chat message attachments with a `type` field that determines rendering:

### 1. Incident Card

**Type:** `"incident"`

**Purpose:** Display detected maintenance incident with action buttons

**Schema:**
```json
{
  "type": "incident",
  "title": "Kitchen Sink Leak",
  "text": "User reported: My kitchen sink is leaking water everywhere",
  "color": "#f59e0b",
  "fields": [
    {"title": "Severity", "value": "Medium", "short": true},
    {"title": "Category", "value": "Plumbing", "short": true},
    {"title": "Reported By", "value": "Jane Doe", "short": true},
    {"title": "Status", "value": "Detected", "short": true}
  ],
  "actions": [
    {
      "name": "start_discovery",
      "text": "Start Discovery",
      "style": "primary",
      "type": "button",
      "value": "action:start_discovery:INC-1234567890"
    },
    {
      "name": "dismiss",
      "text": "Dismiss",
      "style": "default",
      "type": "button",
      "value": "action:dismiss:INC-1234567890"
    }
  ]
}
```

**Color Mapping:**
- `low`: `#10b981` (green)
- `medium`: `#f59e0b` (orange)
- `high`: `#ef4444` (red)
- `emergency`: `#dc2626` (dark red)

---

### 2. Discovery Card

**Type:** `"discovery"`

**Purpose:** Track progress through issue discovery Q&A flow

**Schema:**
```json
{
  "type": "discovery",
  "title": "Issue Discovery",
  "text": "Gathering details about the incident",
  "color": "#3b82f6",
  "fields": [
    {"title": "Progress", "value": "2/4 questions answered", "short": false},
    {"title": "Current Question", "value": "Can you upload photos?", "short": false},
    {"title": "Images Uploaded", "value": "0", "short": true}
  ],
  "actions": [
    {
      "name": "upload_photos",
      "text": "Upload Photos",
      "style": "primary",
      "type": "button",
      "value": "action:upload_photos:INC-1234567890"
    }
  ]
}
```

**Color:** Always `#3b82f6` (blue)

---

### 3. Job/Work Order Card

**Type:** `"job"`

**Purpose:** Display created work order details

**Schema:**
```json
{
  "type": "job",
  "title": "Plumbing Repair",
  "text": "Work order created for incident",
  "color": "#8b5cf6",
  "fields": [
    {"title": "Job ID", "value": "JOB-1234567890", "short": true},
    {"title": "Incident ID", "value": "INC-1234567890", "short": true},
    {"title": "Category", "value": "Plumbing", "short": true},
    {"title": "Estimated Cost", "value": "$150-200", "short": true},
    {"title": "Urgency", "value": "High", "short": true},
    {"title": "Status", "value": "Created", "short": true}
  ],
  "actions": [
    {
      "name": "view_bids",
      "text": "View Contractor Bids",
      "style": "primary",
      "type": "button",
      "value": "action:view_bids:INC-1234567890:JOB-1234567890"
    },
    {
      "name": "approve_job",
      "text": "Approve & Find Contractors",
      "style": "primary",
      "type": "button",
      "value": "action:approve_job:JOB-1234567890"
    }
  ]
}
```

**Color:** Always `#8b5cf6` (purple)

---

### 4. Bids Card

**Type:** `"bids"`

**Purpose:** Display contractor bids with comparison

**Schema:**
```json
{
  "type": "bids",
  "title": "Contractor Bids",
  "text": "3 qualified contractors available",
  "color": "#06b6d4",
  "bids": [
    {
      "bid_id": "BID-1234567890-0",
      "name": "Joe's Plumbing",
      "quote": 175,
      "eta": "Tomorrow, 9:00 AM",
      "rating": 4.8,
      "distance": "2 miles",
      "recommended": true
    },
    {
      "bid_id": "BID-1234567890-1",
      "name": "Quick Fix",
      "quote": 200,
      "eta": "Today, 2:00 PM",
      "rating": 4.6,
      "distance": "3 miles"
    },
    {
      "bid_id": "BID-1234567890-2",
      "name": "Dave's Services",
      "quote": 150,
      "eta": "Next Week",
      "rating": 4.9,
      "distance": "4 miles"
    }
  ],
  "actions": [
    {
      "name": "approve_contractor",
      "text": "Hire Joe's Plumbing",
      "style": "primary",
      "type": "button",
      "value": "action:approve_contractor:JOB-1234567890:Joe's Plumbing:175:INC-1234567890"
    }
  ]
}
```

**Color:** Always `#06b6d4` (cyan)

**Bid Object Fields:**
- `bid_id` (string): Unique bid identifier
- `name` (string): Contractor name
- `quote` (number): Price quote in dollars
- `eta` (string): Estimated time of arrival/start
- `rating` (number): Contractor rating (0-5)
- `distance` (string): Distance from property
- `recommended` (boolean, optional): Mark as recommended

---

### 5. Approval Card

**Type:** `"approval"`

**Purpose:** Confirm contractor hiring and scheduling

**Schema:**
```json
{
  "type": "approval",
  "title": "Contractor Approved",
  "text": "Joe's Plumbing has been hired",
  "color": "#10b981",
  "fields": [
    {"title": "Contractor", "value": "Joe's Plumbing", "short": true},
    {"title": "Final Cost", "value": "$175", "short": true},
    {"title": "Scheduled", "value": "Tomorrow, 9:00 AM", "short": true},
    {"title": "Status", "value": "Approved", "short": true}
  ],
  "actions": []
}
```

**Color:** Always `#10b981` (green)

---

### 6. Completion Card

**Type:** `"completion"`

**Purpose:** Mark job as completed and request feedback

**Schema:**
```json
{
  "type": "completion",
  "title": "Job Completed",
  "text": "Plumbing repair has been completed",
  "color": "#10b981",
  "fields": [
    {"title": "Completed By", "value": "Joe's Plumbing", "short": true},
    {"title": "Final Cost", "value": "$175", "short": true},
    {"title": "Date", "value": "Oct 27, 2025", "short": true},
    {"title": "Status", "value": "Completed", "short": true}
  ],
  "actions": [
    {
      "name": "rate_contractor",
      "text": "Rate Service",
      "style": "primary",
      "type": "button",
      "value": "action:rate_contractor:JOB-1234567890"
    }
  ]
}
```

**Color:** Always `#10b981` (green)

---

## Common Schema Elements

### Fields Array

All cards can have a `fields` array for displaying key-value pairs:

```typescript
interface CardField {
  title: string;        // Field label
  value: string;        // Field value
  short: boolean;       // Display in half-width column (true) or full-width (false)
}
```

**Layout:**
- `short: true`: Displayed in 2-column grid (50% width each)
- `short: false`: Displayed full-width (100%)

### Actions Array

All cards can have an `actions` array for interactive buttons:

```typescript
interface CardAction {
  name: string;         // Action identifier
  text: string;         // Button text
  style: string;        // "primary" | "default" | "danger"
  type: string;         // Always "button"
  value: string;        // Action value (format: "action:name:param1:param2:...")
}
```

**Action Value Format:**
- Prefix: `action:`
- Action name: `start_discovery`, `view_bids`, etc.
- Parameters: Colon-separated (`:`)
- Example: `action:approve_contractor:JOB-123:ContractorName:175:INC-456`

**Button Styles:**
- `primary`: Blue gradient (#3b82f6 → #2563eb)
- `default`: Gray (#6b7280)
- `danger`: Red gradient (#ef4444 → #dc2626)

---

## Frontend Rendering

**File:** `frontend/src/components/ai/MessageCards.tsx`

**Card Components:**
- `IncidentCard` - Renders `type: "incident"`
- `DiscoveryCard` - Renders `type: "discovery"`
- `JobCard` - Renders `type: "job"`
- `BidsCard` - Renders `type: "bids"`
- `ApprovalCard` - Renders `type: "approval"`
- `CompletionCard` - Renders `type: "completion"`

**Unknown Types:**
- Return `null` (no rendering)
- No error thrown
- Graceful degradation

---

## Backend Generation

**File:** `backend/app/services/card_builder.py`

**Card Builders:**
- `CardBuilder.incident_card(...)` - Creates incident attachment
- `CardBuilder.discovery_card(...)` - Creates discovery attachment
- `CardBuilder.work_order_card(...)` - Creates job attachment (type: "job")
- `CardBuilder.bids_card(...)` - Creates bids attachment
- `CardBuilder.approval_card(...)` - Creates approval attachment
- `CardBuilder.completion_card(...)` - Creates completion attachment

**Sending Cards:**
```python
from app.services.card_builder import CardBuilder, send_card_message

# Create card
card = CardBuilder.incident_card(
    incident_id="INC-123",
    title="Kitchen Leak",
    description="Sink is leaking",
    severity="medium"
)

# Send to Stream Chat channel
send_card_message(
    stream_client=client,
    channel_id="tenant-123",
    bot_id="ai-tenant-bot",
    card=card,
    message_text="I detected a maintenance issue"
)
```

---

## Action Handling

**Frontend → Backend Flow:**

1. **User clicks button** in `MessageCards.tsx`
2. **Calls** `onActionClick(action.value)`
3. **Sends message** with text: `action.value` (e.g., `"action:view_bids:INC-123:JOB-456"`)
4. **Webhook receives** `message.new` event
5. **Backend detects** action prefix in `stream_bot.py`:
   ```python
   if message_text.startswith("action:") or "@agent action:" in message_text:
       return self.handle_action(action_value, user_id, channel_id, persona)
   ```
6. **Routes to handler** based on action name:
   ```python
   action_name = parts[1]  # "view_bids"
   params = parts[2:]      # ["INC-123", "JOB-456"]
   ```
7. **Handler executes** business logic (create job, persist to DB, etc.)
8. **Sends response card** back to channel

---

## Validation Rules

### Required Fields

**All Cards:**
- ✅ `type` (string) - Must match one of 6 supported types
- ✅ `title` (string) - Card heading
- ✅ `color` (string) - Hex color code

**Optional Fields:**
- `text` (string) - Card description
- `fields` (array) - Key-value pairs
- `actions` (array) - Interactive buttons
- `bids` (array) - Only for bids card

### Field Limits

- `title`: Max 100 characters
- `text`: Max 500 characters
- `fields`: Max 10 items
- `actions`: Max 5 buttons
- `bids`: Max 10 contractors

---

## Testing

**Verify Schema Compatibility:**

1. **Backend sends valid JSON:**
   ```bash
   curl -X POST http://localhost:8000/ai/send-action \
     -d '{"channel_id":"test","persona":"tenant","text":"Test",...}'
   ```

2. **Frontend receives and renders:**
   - Check browser DevTools → Network → Stream Chat API response
   - Verify attachment object matches schema
   - Confirm card renders without errors

3. **Actions trigger correctly:**
   - Click button
   - Check console for action value
   - Verify webhook receives action message
   - Confirm handler executes

---

## Migration Notes

**Breaking Changes:**
- None (initial version)

**Future Enhancements:**
- Add `metadata` object for extensibility
- Support `image_url` for card thumbnails
- Add `footer` text for timestamps
- Support nested cards (card arrays)

---

**Schema Version:** 1.0
**Status:** Stable
**Last Validated:** October 27, 2025
