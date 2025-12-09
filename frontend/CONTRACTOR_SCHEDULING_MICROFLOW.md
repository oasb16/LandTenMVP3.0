# Contractor Scheduling Microflow

## Overview

This microflow enables contractors to propose multiple visit time slots to property owners (tenants/landlords) directly within the chat UI. The property owner can then select and approve the time slot that works best for them.

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONTRACTOR SCHEDULING FLOW                   │
└─────────────────────────────────────────────────────────────────┘

1. CONTRACTOR VIEW (scheduling_panel)
   ┌─────────────────────────────────────────┐
   │  Propose Visit Schedule                  │
   │  ────────────────────────────            │
   │  Job: Fix leaking kitchen faucet        │
   │  Address: 123 Main St                   │
   │                                          │
   │  ┌────────────────────────────────┐     │
   │  │ Option 1                       │     │
   │  │ Date: 2025-12-12               │     │
   │  │ Time: 09:00 AM - 11:00 AM      │     │
   │  │ Notes: Prefer morning          │     │
   │  └────────────────────────────────┘     │
   │                                          │
   │  ┌────────────────────────────────┐     │
   │  │ Option 2                       │     │
   │  │ Date: 2025-12-13               │     │
   │  │ Time: 02:00 PM - 04:00 PM      │     │
   │  └────────────────────────────────┘     │
   │                                          │
   │  [+ Add Another Time Slot]              │
   │                                          │
   │  [Cancel]  [Propose Schedule (2 options)]│
   └─────────────────────────────────────────┘
                      │
                      │ Intent: propose_schedule
                      │ Payload: { job_id, proposed_slots[] }
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND PROCESSING                          │
│  - Store proposed time slots                                    │
│  - Notify property owner                                        │
│  - Transition to schedule_approval stage                        │
└─────────────────────────────────────────────────────────────────┘
                      │
                      │ Event: ai_state
                      │ ui_mode: schedule_approval_panel
                      ▼
2. PROPERTY OWNER VIEW (schedule_approval_panel)
   ┌─────────────────────────────────────────┐
   │  Approve Visit Schedule                  │
   │  ────────────────────────────            │
   │  Job: Fix leaking kitchen faucet        │
   │  Contractor: John Smith                 │
   │                                          │
   │  Proposed Time Slots (2 options)        │
   │                                          │
   │  ┌────────────────────────────────┐     │
   │  │ Thu  12  Dec                   │  ✓  │
   │  │ 09:00 AM - 11:00 AM           │     │
   │  │ In 3 days                      │     │
   │  │ Note: Prefer morning           │     │
   │  └────────────────────────────────┘     │
   │                                          │
   │  ┌────────────────────────────────┐     │
   │  │ Fri  13  Dec                   │  ○  │
   │  │ 02:00 PM - 04:00 PM           │     │
   │  │ In 4 days                      │     │
   │  └────────────────────────────────┘     │
   │                                          │
   │  [Request Different Times]              │
   │  [Approve Selected Time]                │
   └─────────────────────────────────────────┘
                      │
                      │ Intent: approve_schedule
                      │ Payload: { job_id, selected_slot }
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND PROCESSING                          │
│  - Update job status to SCHEDULED                               │
│  - Store confirmed schedule                                     │
│  - Notify contractor of approval                                │
│  - Add to calendars                                             │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. SchedulingPanel (Contractor View)

**File:** `/frontend/src/app/ai-support/panels/SchedulingPanel.tsx`

**Purpose:** Allows contractors to propose 2-5 time slot options for property visits.

**Features:**
- Add/remove multiple time slot options
- Date picker with validation (no past dates)
- Time range selection (start/end time)
- Optional notes for each slot
- Duplicate detection
- Form validation
- Responsive design with animations

**Props:**
```typescript
interface SchedulingPanelProps {
  jobId: string;
  jobTitle: string;
  propertyAddress?: string;
  onSubmit: (intent: string, payload: any) => Promise<void>;
  onCancel?: () => void;
}
```

**Intent Sent:**
```typescript
{
  intent: "propose_schedule",
  payload: {
    job_id: "job_123",
    proposed_slots: [
      {
        date: "2025-12-12",
        start_time: "09:00",
        end_time: "11:00",
        notes: "Prefer morning slots"
      },
      // ... more slots
    ]
  }
}
```

### 2. ScheduleApprovalPanel (Property Owner View)

**File:** `/frontend/src/app/ai-support/panels/ScheduleApprovalPanel.tsx`

**Purpose:** Allows tenants/landlords to select and approve one of the proposed time slots.

**Features:**
- Visual calendar-style time slot display
- Single selection mode
- Relative date display ("Today", "Tomorrow", "In 3 days")
- Contractor information display
- Request reschedule option
- Confirmation workflow

**Props:**
```typescript
interface ScheduleApprovalPanelProps {
  jobId: string;
  jobTitle: string;
  propertyAddress?: string;
  contractorName: string;
  contractorAvatar?: string;
  proposedSlots: ProposedTimeSlot[];
  onSubmit: (intent: string, payload: any) => Promise<void>;
  onRequestChange?: () => void;
}
```

**Intent Sent:**
```typescript
{
  intent: "approve_schedule",
  payload: {
    job_id: "job_123",
    selected_slot: {
      date: "2025-12-12",
      start_time: "09:00",
      end_time: "11:00"
    }
  }
}
```

## Type Definitions

**File:** `/frontend/src/types/ai-support.ts`

### New Stages
```typescript
| "job_scheduling"       // Propose visit schedule
| "schedule_approval"    // Approve contractor schedule
```

### New UI Modes
```typescript
| "scheduling_panel"      // Contractor propose visit schedule
| "schedule_approval_panel" // Tenant/landlord approve schedule
```

### New Intents
```typescript
| "propose_schedule"      // Propose visit schedule options
| "approve_schedule"      // Approve selected schedule
| "request_reschedule"    // Request different schedule times
```

### Payload Types
```typescript
interface SchedulingPanelPayload {
  job_id: string;
  job_title: string;
  property_address?: string;
  min_slots?: number;
  max_slots?: number;
}

interface ProposedTimeSlot {
  id: string;
  date: string;
  start_time: string;
  end_time: string;
  notes?: string;
}

interface ScheduleApprovalPanelPayload {
  job_id: string;
  job_title: string;
  property_address?: string;
  contractor_name: string;
  contractor_avatar?: string;
  proposed_slots: ProposedTimeSlot[];
}
```

## Integration with AIDynamicPanel

**File:** `/frontend/src/app/ai-support/components/AIDynamicPanel.tsx`

Both panels are registered in the dynamic panel router:

```typescript
{uiMode === "scheduling_panel" && (
  <SchedulingPanel
    jobId={payload.job_id}
    jobTitle={payload.job_title}
    propertyAddress={payload.property_address}
    onSubmit={sendIntent}
    onCancel={() => sendIntent("ai_continue", {})}
  />
)}

{uiMode === "schedule_approval_panel" && (
  <ScheduleApprovalPanel
    jobId={payload.job_id}
    jobTitle={payload.job_title}
    propertyAddress={payload.property_address}
    contractorName={payload.contractor_name}
    contractorAvatar={payload.contractor_avatar}
    proposedSlots={payload.proposed_slots}
    onSubmit={sendIntent}
    onRequestChange={() => sendIntent("request_reschedule", { job_id: payload.job_id })}
  />
)}
```

## Backend Integration Requirements

To fully integrate this microflow, the backend needs to:

### 1. Handle `propose_schedule` Intent

```python
@handle_intent("propose_schedule")
async def handle_propose_schedule(intent_data):
    job_id = intent_data["job_id"]
    proposed_slots = intent_data["proposed_slots"]

    # Store proposed time slots
    await db.store_proposed_schedule(job_id, proposed_slots)

    # Get job and property owner details
    job = await db.get_job(job_id)
    contractor = await db.get_contractor(job.contractor_id)

    # Notify property owner
    await notify_property_owner(job.property_owner_id, {
        "type": "schedule_proposed",
        "job_id": job_id,
        "contractor_name": contractor.name
    })

    # Transition to approval panel for property owner
    return {
        "type": "ai_state",
        "stage": "schedule_approval",
        "ui_mode": "schedule_approval_panel",
        "payload": {
            "job_id": job_id,
            "job_title": job.title,
            "property_address": job.property.address,
            "contractor_name": contractor.name,
            "contractor_avatar": contractor.avatar_url,
            "proposed_slots": proposed_slots
        }
    }
```

### 2. Handle `approve_schedule` Intent

```python
@handle_intent("approve_schedule")
async def handle_approve_schedule(intent_data):
    job_id = intent_data["job_id"]
    selected_slot = intent_data["selected_slot"]

    # Update job status to SCHEDULED
    await db.update_job_status(job_id, "SCHEDULED")

    # Store confirmed schedule
    await db.store_confirmed_schedule(job_id, selected_slot)

    # Notify contractor
    await notify_contractor(job.contractor_id, {
        "type": "schedule_approved",
        "job_id": job_id,
        "scheduled_date": selected_slot["date"],
        "scheduled_time": f"{selected_slot['start_time']} - {selected_slot['end_time']}"
    })

    # Add to calendars (optional)
    await calendar_service.create_event(job_id, selected_slot)

    # Return success state
    return {
        "type": "ai_state",
        "stage": "status_tracking",
        "ui_mode": "status_tracker",
        "payload": {
            "entity_type": "job",
            "entity_id": job_id,
            "title": job.title,
            "current_status": "SCHEDULED",
            "timeline": await db.get_job_timeline(job_id),
            "next_actions": [
                {"id": "start_work", "label": "Start Work"}
            ]
        }
    }
```

### 3. Handle `request_reschedule` Intent

```python
@handle_intent("request_reschedule")
async def handle_request_reschedule(intent_data):
    job_id = intent_data["job_id"]

    # Notify contractor to propose new times
    await notify_contractor(job.contractor_id, {
        "type": "reschedule_requested",
        "job_id": job_id
    })

    # Return to chat mode for negotiation
    return {
        "type": "ai_state",
        "stage": "job_scheduling",
        "ui_mode": "chat",
        "payload": {
            "agent_prompt": "I've notified the contractor that you need different time slots. They'll propose new options shortly."
        }
    }
```

## Usage Example

### Typical Flow Sequence

1. **Job Acceptance**: Contractor accepts a job
   - Backend sends `ai_state` with `ui_mode: "job_acceptance"`
   - Contractor clicks "Accept Job"

2. **Scheduling Initiated**: Backend transitions to scheduling
   - Backend sends `ai_state` with `ui_mode: "scheduling_panel"`
   - Contractor sees SchedulingPanel

3. **Contractor Proposes Times**:
   - Contractor fills in 2-3 time slot options
   - Clicks "Propose Schedule"
   - Frontend sends `propose_schedule` intent

4. **Property Owner Notified**:
   - Backend sends `ai_state` to property owner's session
   - Property owner sees ScheduleApprovalPanel

5. **Property Owner Approves**:
   - Property owner selects preferred time slot
   - Clicks "Approve Selected Time"
   - Frontend sends `approve_schedule` intent

6. **Confirmation**:
   - Job status updated to SCHEDULED
   - Both parties notified
   - Calendar events created

## Design Patterns Used

### 1. Framer Motion Animations
- Smooth entrance/exit transitions
- Stagger animations for time slot cards
- Loading state animations

### 2. Form Validation
- Real-time validation with error messages
- Date validation (no past dates)
- Time validation (end > start)
- Duplicate detection

### 3. Responsive Design
- Mobile-first approach
- Flexbox/Grid layouts
- Tailwind CSS utilities

### 4. Accessibility
- Semantic HTML
- Keyboard navigation support
- Focus states
- ARIA labels (can be added)

### 5. State Management
- Local component state with useState
- Error handling with try/catch
- Loading states during submission

## Styling

### Color Scheme
- **Contractor Panel**: Blue accent (`bg-blue-600`)
- **Approval Panel**: Emerald accent (`bg-emerald-600`)
- **Background**: Slate dark mode (`bg-slate-950`)
- **Cards**: Slate-900 with slate-800 borders
- **Text**: Slate-100 (primary), Slate-400 (secondary)

### Icons (Lucide React)
- Calendar: Date/scheduling indicator
- Clock: Time indicator
- Plus: Add time slot
- X: Remove time slot
- CheckCircle2: Selection indicator
- ThumbsUp: Approve action
- AlertCircle: Info/warnings
- User: Contractor avatar fallback
- MapPin: Property address

## Testing Recommendations

### Unit Tests
- Form validation logic
- Date/time formatting functions
- Duplicate detection

### Integration Tests
- Intent sending and receiving
- Panel transitions
- Error handling

### E2E Tests
- Full scheduling flow
- Reschedule request flow
- Edge cases (all slots in past, etc.)

## Future Enhancements

1. **Calendar Integration**
   - Google Calendar / Outlook sync
   - ICS file export

2. **Time Zone Support**
   - Automatic time zone detection
   - Display in user's local time

3. **Recurring Visits**
   - Weekly/monthly maintenance schedules
   - Recurring time slot templates

4. **Buffer Time**
   - Travel time consideration
   - Minimum gap between appointments

5. **Conflict Detection**
   - Check contractor's existing schedule
   - Warn about overlapping appointments

6. **Reminder Notifications**
   - Email/SMS reminders
   - 24-hour advance notice

## Files Modified/Created

### Created
- ✅ `/frontend/src/app/ai-support/panels/SchedulingPanel.tsx` (395 lines)
- ✅ `/frontend/src/app/ai-support/panels/ScheduleApprovalPanel.tsx` (388 lines)

### Modified
- ✅ `/frontend/src/types/ai-support.ts` (added scheduling types)
- ✅ `/frontend/src/app/ai-support/components/AIDynamicPanel.tsx` (added panel routing)

## Summary

This microflow provides a seamless, chat-integrated scheduling experience that:
- ✅ Reduces back-and-forth messaging
- ✅ Provides visual time slot selection
- ✅ Validates dates and times
- ✅ Maintains consistency with existing design patterns
- ✅ Supports the full contractor workflow
- ✅ Is mobile-responsive and accessible

The implementation follows the existing Amazon-style guided flow pattern and integrates smoothly with the event-driven architecture using Stream Chat.
