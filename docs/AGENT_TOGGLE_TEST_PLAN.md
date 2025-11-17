# Agent Toggle Feature - Test Plan

**Created:** October 27, 2025
**Feature:** AI Agent ON/OFF Toggle for Stream Chat

---

## Overview

The Agent Toggle feature allows users to control whether messages are processed by the AI agent (PropertyAIBot) for incident detection and automated responses.

**Key Changes:**
- Added `AgentToggleButton` component with visual state indicator
- Enhanced `StreamChatPane` with agent enable/disable logic
- Modified backend `/chat/stream/agent_reply` to trigger PropertyAIBot incident detection
- Agent state persists in localStorage

---

## Feature Components

### 1. AgentToggleButton Component

**Location:** `frontend/src/components/ai/AgentToggleButton.tsx`

**Features:**
- Toggle switch with ON/OFF states
- Visual indicators:
  - **ON:** Green background (emerald-600), robot emoji 🤖, switch right
  - **OFF:** Gray background (slate-700), chat emoji 💬, switch left
- State persisted in localStorage (`landten_agent_enabled`)
- Tooltip on hover explaining current state

**Usage:**
```tsx
<AgentToggleButton
  initialState={agentEnabled}
  onChange={handleAgentToggle}
/>
```

### 2. StreamChatPane Enhancements

**Location:** `frontend/src/components/StreamChatPane.tsx`

**Changes:**
- Added `agentEnabled` state (default: `true`)
- Integrated AgentToggleButton in sidebar
- Enhanced `handleSendMessage()`:
  - **Agent ON:** All messages trigger AI processing
  - **Agent OFF:** Only messages with `@agent` trigger processing
- New conversation form reflects agent state
- Channel list refresh on new conversation creation

**Message Processing Logic:**
```typescript
const hasAgentTrigger = text.includes("@agent")
const shouldProcessAgent = agentEnabled || hasAgentTrigger

if (shouldProcessAgent) {
  // Call /api/chat/agent → PropertyAIBot
} else {
  // Direct message, no AI processing
}
```

### 3. Backend Integration

**Location:** `backend/app/routes/chat_stream.py`

**Changes to `/chat/stream/agent_reply`:**
1. Generate AI response via `get_ai_response()`
2. Post response to Stream Chat
3. **NEW:** Trigger `PropertyAIBot.handle_message_event()` for incident detection
4. Persist incidents to DynamoDB if detected

**Flow:**
```
User Message → /api/chat/agent →
├─ Generate AI response
├─ Post to Stream Chat
└─ PropertyAIBot.handle_message_event()
    ├─ detect_incident_in_message()
    └─ If incident detected:
        ├─ IncidentDB.create_incident()
        └─ send_incident_card()
```

---

## Test Scenarios

### Test 1: Agent ON - Incident Detection

**Objective:** Verify incident detection works when agent is ON

**Steps:**
1. Open Stream Chat interface
2. Verify "Agent: ON" button shows 🤖 with green background
3. Send message: `"My kitchen sink is leaking water everywhere"`
4. Wait 2-3 seconds

**Expected Results:**
- ✅ Message appears in chat immediately
- ✅ AI response appears within 3 seconds
- ✅ Incident card appears with:
  - Title: "Kitchen Sink Leak" or similar
  - Severity: Medium or High
  - Category: Plumbing
  - Actions: "Start Discovery", "Dismiss"
- ✅ Console logs show:
  ```
  [StreamChatPane] Sending message, agent enabled: true
  [StreamChatPane] Triggering agent processing for: My kitchen sink is leaking...
  [agent_reply] Triggering PropertyAIBot incident detection...
  [PropertyAIBot] Creating incident: INC-XXXXXXXXXX
  [PropertyAIBot] Incident persisted to DynamoDB: INC-XXXXXXXXXX
  ```

**DynamoDB Verification:**
```bash
aws dynamodb scan --table-name landten_incidents --region us-east-1 \
  --filter-expression "contains(description, :text)" \
  --expression-attribute-values '{":text":{"S":"kitchen sink is leaking"}}' \
  | jq
```

**Success Criteria:**
- Incident card rendered correctly
- DynamoDB record created with correct fields
- User can click "Start Discovery" button

---

### Test 2: Agent OFF - No Incident Detection

**Objective:** Verify messages bypass AI when agent is OFF

**Steps:**
1. Click "Agent: ON" button to toggle it OFF
2. Verify button shows 💬 with gray background (slate-700)
3. Verify localStorage has `landten_agent_enabled = "false"`
4. Send message: `"The bathroom faucet is broken"`
5. Wait 2-3 seconds

**Expected Results:**
- ✅ Message appears in chat immediately
- ✅ NO AI response generated
- ✅ NO incident card appears
- ✅ Console logs show:
  ```
  [StreamChatPane] Sending message, agent enabled: false
  [StreamChatPane] Agent OFF - message sent without AI processing
  ```
- ✅ NO DynamoDB record created

**Success Criteria:**
- Message sent to Stream Chat as regular message
- No AI processing triggered
- No incident detection occurs
- Other users in channel can see message

---

### Test 3: Agent OFF but @agent Trigger

**Objective:** Verify @agent trigger overrides OFF state

**Steps:**
1. Ensure agent is OFF (gray button, 💬)
2. Send message: `"@agent my toilet is clogged"`
3. Wait 2-3 seconds

**Expected Results:**
- ✅ Message appears in chat
- ✅ AI response generated (because of @agent trigger)
- ✅ Incident card appears
- ✅ Console logs show:
  ```
  [StreamChatPane] Sending message, agent enabled: false
  [StreamChatPane] Triggering agent processing for: @agent my toilet is clogged
  [agent_reply] Triggering PropertyAIBot incident detection...
  ```

**Success Criteria:**
- @agent trigger forces AI processing even when toggle is OFF
- Incident detected and card displayed
- DynamoDB record created

---

### Test 4: State Persistence Across Sessions

**Objective:** Verify agent state persists after page reload

**Steps:**
1. Toggle agent to OFF
2. Verify localStorage: `localStorage.getItem('landten_agent_enabled')` returns `"false"`
3. Refresh the page (F5 or Cmd+R)
4. Wait for Stream Chat to connect

**Expected Results:**
- ✅ Agent button still shows OFF (gray, 💬)
- ✅ `agentEnabled` state restored from localStorage
- ✅ Messages continue to bypass AI processing

**Steps to Toggle Back:**
1. Click agent button to turn ON
2. Verify localStorage now has `"true"`
3. Send incident message
4. Verify incident detected

---

### Test 5: New Conversation with Agent State

**Objective:** Verify new conversations respect agent state

**Test 5a: Agent ON**
1. Ensure agent is ON
2. Click "New Conversation"
3. Enter participant email
4. Verify form text: "All participants plus the LandTen agent will join"
5. Create conversation
6. Verify new channel appears in ChannelList immediately
7. Send incident message in new channel
8. Verify incident detected

**Test 5b: Agent OFF**
1. Toggle agent OFF
2. Click "New Conversation"
3. Enter participant email
4. Verify form text: "Participants will join this conversation. Agent is OFF."
5. Create conversation
6. Verify agent NOT added to channel members
7. Send message
8. Verify no AI processing

---

### Test 6: Layout and Responsiveness

**Objective:** Verify UI layout works correctly

**Desktop (> 768px):**
- ✅ Sidebar: 280px width, fixed on left
- ✅ Chat area: Flex-grows to fill remaining space
- ✅ Agent toggle button visible at top of sidebar
- ✅ Message list scrolls independently
- ✅ ChannelList scrolls independently

**Mobile/Tablet (< 768px):**
- ✅ Layout switches to column (sidebar above chat)
- ✅ Sidebar max-height: 250px
- ✅ Chat area takes remaining vertical space
- ✅ Both sections scroll independently
- ✅ Agent toggle still accessible

**Stream Chat Container:**
- ✅ `.str-chat__container` height: 100%, flex column
- ✅ `.str-chat__main-panel` height: 100%, no overflow issues
- ✅ `.str-chat__list` flex: 1, scrolls correctly
- ✅ Messages stack vertically without layout breaks

---

### Test 7: Action Button Interactions

**Objective:** Verify incident card buttons work correctly

**Steps:**
1. Agent ON
2. Send: `"My pipe is leaking"`
3. Wait for incident card
4. Click "Start Discovery" button
5. Verify discovery card appears with progress tracker
6. Answer discovery questions
7. Verify flow proceeds: Discovery → Work Order → Bids

**Expected Results:**
- ✅ All action buttons clickable
- ✅ Loading spinner appears on clicked button
- ✅ All buttons disabled during processing
- ✅ Action triggers correct backend handler
- ✅ New cards appear after actions complete

---

### Test 8: Multiple Messages Rapid Fire

**Objective:** Verify system handles multiple messages correctly

**Steps:**
1. Agent ON
2. Send 3 messages rapidly:
   - "My sink is leaking"
   - "The faucet is broken"
   - "Water everywhere"
3. Wait for all responses

**Expected Results:**
- ✅ All 3 messages appear in chat
- ✅ AI responds to each message
- ✅ Multiple incident cards may appear (one per incident)
- ✅ No race conditions or duplicate cards
- ✅ DynamoDB has records for all detected incidents

---

### Test 9: Backend Error Handling

**Objective:** Verify system gracefully handles backend errors

**Test 9a: PropertyAIBot throws exception**
1. Temporarily break PropertyAIBot (e.g., invalid DynamoDB credentials)
2. Agent ON, send incident message
3. Verify:
   - ✅ AI response still posted
   - ✅ Error logged: `[agent_reply] WARNING: PropertyAIBot incident detection failed`
   - ✅ Request doesn't fail (returns 200)
   - ✅ Frontend doesn't show error

**Test 9b: Stream Chat API error**
1. Send message with agent ON
2. Stream Chat API temporarily down
3. Verify:
   - ✅ Error message displayed to user
   - ✅ Message retry or helpful error text

---

### Test 10: End-to-End Workflow

**Objective:** Complete incident flow from detection to contractor approval

**Full Flow:**
1. **Tenant sends incident:**
   - Agent ON
   - Send: "My kitchen sink is leaking badly"
   - Verify incident card appears
   - Verify DynamoDB: `landten_incidents` has record

2. **Start discovery:**
   - Click "Start Discovery"
   - Answer 4 questions:
     - Location: "kitchen sink under the counter"
     - Severity: "steady leak, puddle forming"
     - Noticed: "this morning around 8am"
     - Media: "uploading photo now"
   - Verify discovery card updates with progress

3. **Create work order:**
   - System detects DIY won't resolve
   - Work order card appears automatically
   - Verify DynamoDB: `landten_jobs` has record
   - Incident status updated to "work_order"

4. **View contractor bids:**
   - Click "View Contractor Bids"
   - Verify bids card with 3 contractors
   - Verify DynamoDB: `landten_job_bids` has 3 records

5. **Approve contractor:**
   - Click "Hire Joe's Plumbing" (or top bid)
   - Verify approval card appears
   - Verify DynamoDB:
     - Job updated with contractor_id
     - Job status = "approved"
     - Incident status = "scheduled"

**Success Criteria:**
- ✅ Complete flow executes without errors
- ✅ All cards render correctly
- ✅ All DynamoDB records created and linked
- ✅ Status transitions tracked properly
- ✅ User sees clear progression

---

## Console Log Checklist

**When Agent ON:**
```
[StreamChatPane] Sending message, agent enabled: true
[StreamChatPane] Triggering agent processing for: My kitchen sink is leaking...
[StreamChatPane] Agent processing initiated
[agent_reply] Processing request for channel: landten-default
[agent_reply] Prompt: My kitchen sink is leaking...
[agent_reply] AI response posted to channel landten-default
[agent_reply] Triggering PropertyAIBot incident detection...
[PropertyAIBot] Creating incident: INC-1730012345
[PropertyAIBot] Incident persisted to DynamoDB: INC-1730012345
[agent_reply] PropertyAIBot processed message - incident detection completed
```

**When Agent OFF (no @agent):**
```
[StreamChatPane] Sending message, agent enabled: false
[StreamChatPane] Agent OFF - message sent without AI processing
```

**When Agent OFF but with @agent:**
```
[StreamChatPane] Sending message, agent enabled: false
[StreamChatPane] Triggering agent processing for: @agent my toilet is clogged
[agent_reply] Processing request for channel: landten-default
...
```

---

## Troubleshooting

### Issue: Agent button doesn't toggle

**Check:**
- Browser console for React errors
- localStorage permissions
- Component re-render triggers

**Fix:**
- Clear localStorage: `localStorage.removeItem('landten_agent_enabled')`
- Refresh page
- Check AgentToggleButton onChange callback

---

### Issue: Incident card doesn't appear

**Check:**
1. Agent state: Is it ON?
2. Console logs: Did PropertyAIBot trigger?
3. DynamoDB: Is record created?
4. Keywords: Does message contain incident keywords?

**Debug:**
```bash
# Check if incident detected
grep "PropertyAIBot" backend_logs.txt

# Check DynamoDB
aws dynamodb scan --table-name landten_incidents --region us-east-1

# Check frontend
# Open browser DevTools → Network → Filter "agent"
# Check /api/chat/agent request/response
```

---

### Issue: Layout broken or scroll not working

**Check:**
- `.str-chat__container` height: should be 100%
- `.str-chat__main-panel` overflow: should be hidden
- `.str-chat__list` flex: should be 1

**Fix:**
- Clear browser cache
- Verify StreamChatPane.tsx styles applied
- Check for conflicting global CSS

---

## Success Checklist

After testing, verify:

- [ ] Agent toggle button visible and functional
- [ ] ON state: Green, 🤖, incident detection works
- [ ] OFF state: Gray, 💬, no AI processing
- [ ] @agent trigger works in both states
- [ ] State persists across page reloads
- [ ] New conversations reflect agent state
- [ ] Layout responsive on mobile/desktop
- [ ] Message scrolling works correctly
- [ ] Action buttons trigger correct workflows
- [ ] DynamoDB records created correctly
- [ ] Console logs clear and helpful
- [ ] No React errors or warnings
- [ ] End-to-end workflow completes successfully

---

## Next Steps

After tests pass:

1. ✅ Commit frontend and backend changes
2. ✅ Push to git repository
3. Deploy to staging environment
4. Run smoke tests in staging
5. Monitor error logs for 24 hours
6. Deploy to production if stable
7. Update user documentation
8. Train support team on agent toggle feature

---

**Document Status:** Ready for testing
**Last Updated:** October 27, 2025
**Maintainer:** Claude Code / PropertyAI Team
