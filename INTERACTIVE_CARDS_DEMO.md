# Interactive Cards Demo Guide

**LandTen MVP 3.0 - Incident Management Workflow**

This guide shows you how to demo the new interactive message cards system that transforms LandTen Chat into a fully guided incident management workflow.

---

## 🎯 Overview

The system now supports **interactive message cards** that guide users through the complete incident lifecycle:

**Detection → Discovery → Work Order → Bids → Approval → Completion**

Cards appear directly in chat with action buttons, replacing the need for static forms and external workflows.

---

## 🚀 Quick Start

### 1. Start the Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

**Verify it's running:**
```bash
curl http://localhost:8000/ai/bot-status
```

You should see AI bot configuration with `status: "active"`.

### 2. Start the Frontend

```bash
cd frontend
npm run dev
```

Open http://localhost:3000/property-ai

### 3. Sign In

- Sign in with your Google account
- You'll be taken to the PropertyAI dashboard

---

## 📝 Demo Scenario: Tenant Reports a Leak

### Step 1: Trigger Incident Detection

**As Tenant**, in the Chat tab, type:

```
My kitchen sink is leaking badly
```

**What Happens:**
1. AI bot (PropertyHelper) detects the incident keywords ("leaking")
2. **Incident Detection Card** appears with:
   - Issue title and description
   - Severity badge (automatically classified as MEDIUM or HIGH)
   - Two action buttons:
     - "Start Discovery" (primary button)
     - "Dismiss"

**Card Example:**
```
┌─────────────────────────────────────┐
│ 🔴 Kitchen Sink Leak                │
├─────────────────────────────────────┤
│ My kitchen sink is leaking badly    │
│                                     │
│ Severity: 🔴 HIGH                   │
│ Status: Detected                    │
│ Reported By: Sarah Johnson          │
├─────────────────────────────────────┤
│ [Start Discovery] [Dismiss]         │
└─────────────────────────────────────┘
```

---

### Step 2: Start Discovery

Click the **"Start Discovery"** button on the card.

**What Happens:**
1. AI asks the first discovery question
2. **Discovery Progress Card** appears showing:
   - Progress bar (0/4 questions)
   - Current question
   - Number of photos uploaded

**Example:**
```
┌─────────────────────────────────────┐
│ 🔍 Issue Discovery in Progress      │
├─────────────────────────────────────┤
│ ██░░░░░░░░ 25% Complete             │
│                                     │
│ Where is the issue located?         │
│                                     │
│ Progress: 1/4 questions answered    │
│ Photos: 0 uploaded                  │
├─────────────────────────────────────┤
│ [📸 Upload Photos]                  │
└─────────────────────────────────────┘
```

**Respond to Questions:**
```
It's under the kitchen sink in the cabinet
```

AI will ask follow-up questions:
- How severe is the leak? (dripping, steady, flooding)
- When did you first notice it?
- Can you upload photos?

---

### Step 3: Create Work Order

After discovery is complete, click **"Create Work Order"**.

**What Happens:**
1. AI creates a work order from the incident
2. **Work Order Card** appears with:
   - Job ID and category (e.g., "Plumbing")
   - Estimated cost range
   - Urgency level
   - Status (Created)
   - Action buttons for landlord

**Example:**
```
┌─────────────────────────────────────┐
│ 🔧 Work Order: Plumbing Repair      │
├─────────────────────────────────────┤
│ A work order has been created       │
│                                     │
│ Category: Plumbing                  │
│ Status: 📝 Created                  │
│ Estimated Cost: $150-200            │
│ Urgency: ⚡ Urgent                  │
├─────────────────────────────────────┤
│ [✅ Approve Job]                    │
│ [View Contractor Bids]              │
└─────────────────────────────────────┘
```

---

### Step 4: View Contractor Bids

Click **"View Contractor Bids"** (works for both tenant and landlord).

**What Happens:**
1. AI generates contractor bids from the system
2. **Bids Comparison Card** appears with:
   - Top 3 qualified contractors
   - Ratings, prices, ETAs, distances
   - Recommended contractor highlighted
   - Action buttons to hire each contractor

**Example:**
```
┌─────────────────────────────────────┐
│ 💼 Contractor Bids                  │
├─────────────────────────────────────┤
│ Found 3 qualified contractors.      │
│ Review and select one to proceed.   │
│                                     │
│ 🏆 RECOMMENDED                      │
│ RapidFix                            │
│ $150 • Next business day            │
│ ⭐⭐⭐⭐⭐ • 2 miles                │
│                                     │
│ Prime Contractors                   │
│ $195 • 48 hours                     │
│ ⭐⭐⭐⭐ • 3 miles                  │
│                                     │
│ SafeHome Pros                       │
│ $240 • Same week                    │
│ ⭐⭐⭐⭐ • 4 miles                  │
├─────────────────────────────────────┤
│ [Hire RapidFix]                     │
│ [Hire Prime Contractors]            │
│ [Hire SafeHome Pros]                │
└─────────────────────────────────────┘
```

---

### Step 5: Approve Contractor

Click **"Hire RapidFix"** (or any contractor).

**What Happens:**
1. **Approval Card** appears showing:
   - Selected contractor name
   - Final cost
   - Scheduled date/time
   - Status: Approved

**Example:**
```
┌─────────────────────────────────────┐
│ ✅ Approval Approved                │
├─────────────────────────────────────┤
│ Contractor RapidFix is ready to     │
│ start work.                         │
│                                     │
│ Contractor: RapidFix                │
│ Total Cost: $150                    │
│ Scheduled Date: Tomorrow, 9:00 AM   │
├─────────────────────────────────────┤
│ Incident INC-123 • Job JOB-456     │
└─────────────────────────────────────┘
```

AI also sends confirmation message:
```
The contractor will arrive tomorrow at 9:00 AM.
You'll receive a notification when they're on their way.
```

---

## 🎨 Card Types Reference

### 1. Incident Card
**Purpose:** Detect and present potential maintenance issues
**Trigger:** AI detects incident keywords in chat
**Actions:**
- Start Discovery
- Dismiss

**Border Color:** Red/Amber/Yellow (by severity)

---

### 2. Discovery Card
**Purpose:** Show progress through discovery questions
**Trigger:** User clicks "Start Discovery"
**Actions:**
- Upload Photos
- Create Work Order (when complete)

**Border Color:** Blue (#3b82f6)

**Features:**
- Animated progress bar
- Question counter (e.g., "2/4 answered")
- Photo upload count

---

### 3. Work Order Card
**Purpose:** Show job details and status
**Trigger:** Discovery complete or manual creation
**Actions:**
- Approve Job (landlord)
- View Contractor Bids

**Border Color:** Purple (#8b5cf6)

**Features:**
- Category badges (Plumbing, Electrical, etc.)
- Cost estimates
- Urgency indicators
- Status tracking

---

### 4. Bids Card
**Purpose:** Compare contractor options
**Trigger:** User clicks "View Contractor Bids"
**Actions:**
- Hire [Contractor Name] (one per contractor)

**Border Color:** Green (#059669)

**Features:**
- Top 3 contractors displayed
- Recommended badge for best match
- Rating stars
- Price and ETA comparison
- Distance from property

---

### 5. Approval Card
**Purpose:** Confirm contractor selection
**Trigger:** User clicks "Hire [Contractor]"
**Actions:**
- Approve (landlord final approval)
- Reject

**Border Color:** Amber (#f59e0b) when pending, Green when approved

**Features:**
- Contractor details
- Final cost
- Scheduled date/time
- Status badges

---

### 6. Completion Card
**Purpose:** Show job completion details
**Trigger:** Contractor marks job as complete (future feature)
**Actions:**
- Rate Contractor

**Border Color:** Green (#10b981)

**Features:**
- Before/after photos
- Final cost breakdown
- Completion date
- Tenant satisfaction indicator

---

## 🧪 Testing Different Scenarios

### Scenario 1: Emergency Incident

**Trigger Message:**
```
URGENT! Water is flooding from the ceiling in my bedroom!
```

**Expected Behavior:**
- Incident card with EMERGENCY severity (red)
- Expedited workflow
- Immediate contractor availability check

---

### Scenario 2: Minor Routine Issue

**Trigger Message:**
```
The bathroom faucet drips a little
```

**Expected Behavior:**
- Incident card with LOW severity (blue)
- Normal priority workflow
- DIY suggestions offered

---

### Scenario 3: Electrical Issue

**Trigger Message:**
```
One of my outlets stopped working and smells like burning
```

**Expected Behavior:**
- Incident card with HIGH severity
- Category: Electrical
- Safety warnings in AI response
- Contractor matching prioritizes electricians

---

### Scenario 4: Dismiss False Alarm

**Trigger Message:**
```
My refrigerator is making a weird noise
```

**Then:** Click "Dismiss" button

**Expected Behavior:**
- AI acknowledges dismissal
- No work order created
- Conversation continues normally

---

## 🎯 Action Value Format

When a button is clicked, it sends a message with this format:

```
@agent action:action_name:param1:param2:param3
```

### Examples:

```
action:start_discovery:INC-1730000000
action:create_work_order:INC-1730000000
action:view_bids:INC-1730000000
action:approve_contractor:JOB-123:RapidFix:150:INC-1730000000
action:dismiss:INC-1730000000
```

The backend `handle_action()` method parses this and routes to appropriate handlers.

---

## 🔍 Backend Workflow Logic

### Incident Detection Flow

```
User Message
    ↓
detect_incident_in_message()
    ↓
classify_issue() - determines category/severity
    ↓
send_incident_card()
    ↓
Incident Card displayed in chat
```

### Action Handler Flow

```
User Clicks Button
    ↓
handleActionClick() (frontend)
    ↓
Send "@agent action:..." message
    ↓
handle_message_event() (backend webhook)
    ↓
handle_action()
    ↓
Route to specific handler (_handle_start_discovery, etc.)
    ↓
Send appropriate card or response
```

### Discovery Flow

```
Start Discovery
    ↓
Ask Question 1
    ↓
User Responds
    ↓
Update Discovery Progress Card
    ↓
Ask Question 2
    ↓
... (repeat for all questions)
    ↓
Complete Discovery
    ↓
Show "Create Work Order" button
```

---

## 🎨 Styling and Themes

### Card Colors by Type

- **Incident:** Dynamic (based on severity)
  - Low: `#10b981` (green)
  - Medium: `#f59e0b` (amber)
  - High: `#ef4444` (red)
  - Emergency: `#dc2626` (dark red)
- **Discovery:** `#3b82f6` (blue)
- **Job:** `#8b5cf6` (purple)
- **Bids:** `#059669` (emerald)
- **Approval:** `#f59e0b` (amber) → `#10b981` (green when approved)
- **Completion:** `#10b981` (green)

### Dark Mode Support

All cards automatically adapt to Stream Chat's dark theme:
- Background changes to dark gray
- Text inverts to light colors
- Buttons maintain proper contrast

### Mobile Responsive

Cards automatically adapt to mobile screens:
- Fields stack vertically on small screens
- Buttons expand to full width
- Images scale appropriately

---

## 🐛 Troubleshooting

### Cards Not Appearing

**Problem:** Message sent but no card displays

**Solution:**
1. Check browser console for errors
2. Verify backend is running: `curl http://localhost:8000/health`
3. Check webhook is processing: Look for `[stream-bot]` logs in backend
4. Verify Stream Chat API keys are set in `.env`

---

### Action Buttons Not Working

**Problem:** Clicking button doesn't do anything

**Solution:**
1. Open browser DevTools Network tab
2. Look for message being sent to Stream Chat
3. Check backend logs for `[stream-bot] Handling action:` messages
4. Verify `handleActionClick` is called in frontend console

---

### Incident Not Detected

**Problem:** Typing incident message doesn't trigger card

**Solution:**
1. Make sure message contains incident keywords (leak, broken, damage, etc.)
2. Check persona is set to "tenant" (landlords don't get auto-detection)
3. Verify AI bot is added to channel
4. Check backend logs for incident detection

---

### Styling Issues

**Problem:** Cards look broken or unstyled

**Solution:**
1. Verify `message-cards.css` is imported in `page.tsx`
2. Check browser DevTools for CSS errors
3. Clear browser cache and reload
4. Verify CSS file is in `/frontend/app/message-cards.css`

---

## 📊 Testing Checklist

### Basic Flow
- [ ] Tenant sends incident message
- [ ] Incident card appears
- [ ] Click "Start Discovery" works
- [ ] Discovery questions progress
- [ ] Create work order generates card
- [ ] View bids shows contractors
- [ ] Hire contractor shows approval

### Edge Cases
- [ ] Dismiss incident works correctly
- [ ] Multiple incidents in same channel
- [ ] Switching between channels preserves cards
- [ ] Mobile responsive layout works
- [ ] Dark mode renders correctly

### Error Handling
- [ ] Invalid action doesn't crash
- [ ] Network errors show gracefully
- [ ] Missing data shows fallback UI

---

## 🚀 Next Steps

### Planned Enhancements

1. **Photo Upload Integration**
   - Allow users to attach images to incidents
   - Show photos in incident cards
   - Store in S3 or media service

2. **Real-time Updates**
   - Update cards when status changes
   - Show typing indicators during AI processing
   - Live contractor availability

3. **Landlord Dashboard Integration**
   - Send cards to landlord's channel
   - Cross-channel notifications
   - Approval workflows

4. **Contractor Bidding**
   - Contractors receive job notifications
   - Submit bids via cards
   - Real-time bid comparison

5. **Payment Processing**
   - Stripe integration for payments
   - Receipt generation
   - Invoice cards

6. **Calendar Integration**
   - Calendly-style scheduling
   - Contractor availability
   - Automated reminders

---

## 📚 Code References

### Backend Files
- `backend/app/services/card_builder.py` - Card creation logic
- `backend/app/services/stream_bot.py` - AI bot and action handlers
- `backend/app/routes/ai_webhooks.py` - Webhook endpoints

### Frontend Files
- `frontend/src/components/ai/MessageCards.tsx` - Card rendering
- `frontend/src/components/ai/CustomMessageUI.tsx` - Message wrapper
- `frontend/src/components/StreamChatPane.tsx` - Chat integration
- `frontend/app/message-cards.css` - Card styles

---

## 🎉 Success Metrics

**The system is working correctly when:**

✅ Incident detection happens automatically
✅ Cards appear within 1 second of trigger
✅ Action buttons respond immediately
✅ Workflow progresses through all stages
✅ UI is clean and conversational
✅ Mobile layout works smoothly
✅ Dark mode renders properly

---

## 💡 Tips for Best Demo

1. **Prepare Your Test Messages:**
   - Write incident messages beforehand
   - Use clear, specific language
   - Include severity keywords ("urgent", "emergency", "minor")

2. **Show the Flow:**
   - Start with incident detection
   - Walk through discovery step-by-step
   - Highlight contractor matching intelligence
   - End with approval confirmation

3. **Highlight Key Features:**
   - Interactive cards vs static forms
   - AI-driven guidance
   - Conversational workflow
   - Real-time updates

4. **Point Out Details:**
   - Severity color coding
   - Progress indicators
   - Recommended contractor badges
   - Status tracking

---

**Happy Testing! 🎉**

If you encounter issues or have questions, check the troubleshooting section or review the code references above.
