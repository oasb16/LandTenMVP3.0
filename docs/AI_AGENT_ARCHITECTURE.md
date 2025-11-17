# PropertyAI - AI Agent Architecture

## Overview

PropertyAI uses Stream Chat AI bot capabilities to provide intelligent assistance across three personas: Tenants, Landlords, and Contractors. Each persona has a dedicated AI agent that manages workflows, automates tasks, and provides contextual guidance.

---

## System Architecture

### High-Level Flow

```
User (Tenant/Landlord/Contractor)
    ↓
Stream Chat Channel with AI Agent
    ↓
PropertyAI Backend (FastAPI)
    ↓
AI Processing Layer (OpenAI GPT-4)
    ↓
Business Logic (Incidents, Jobs, Contractors)
    ↓
Database (DynamoDB)
```

### Key Components

1. **Stream Chat AI Bots** - Real-time conversational AI in chat channels
2. **Backend AI Service** - Python service handling AI requests and business logic
3. **Frontend AI Components** - React components for AI interactions
4. **Calendar Integration** - Scheduling system for jobs and appointments
5. **Payment Processing** - Automated receipt and payment handling

---

## AI Agent Personas

### 1. Tenant AI Agent ("PropertyHelper")

**Purpose:** Help tenants report issues, troubleshoot problems, and communicate with landlords efficiently.

**Capabilities:**
- **Issue Troubleshooting**
  - Ask clarifying questions about the problem
  - Suggest DIY fixes for minor issues
  - Determine if professional help is needed

- **Severity Analysis**
  - Analyze issue gravity (Low/Medium/High/Emergency)
  - Recommend urgency level
  - Suggest timeline for resolution

- **Incident Creation Workflow**
  ```
  1. Tenant describes issue in chat
  2. AI asks clarifying questions (location, severity, photos)
  3. AI suggests severity level
  4. AI requests approval: "Should I create an incident?"
  5. On approval, AI creates incident via API
  6. AI confirms creation and provides tracking number
  ```

- **Proactive Assistance**
  - Monthly maintenance reminders
  - Lease renewal notifications
  - Utility payment tracking
  - Community guidelines

**Example Conversation:**
```
Tenant: "My kitchen sink is leaking"
AI: "I can help with that! A few questions:
     1. Is it actively dripping now, or only when running water?
     2. Where is the leak coming from (faucet, pipe under sink, etc.)?
     3. Can you send a photo?"
Tenant: [uploads photo] "It's dripping from under the sink constantly"
AI: "This looks like a pipe joint issue - requires professional repair.
     I'd classify this as MEDIUM urgency (not emergency, but needs attention soon).
     Shall I create an incident for your landlord?"
Tenant: "Yes please"
AI: "✅ Incident #INC-1234 created and sent to your landlord.
     Expected response time: 24-48 hours.
     I'll notify you when they respond."
```

---

### 2. Landlord AI Agent ("PropertyManager")

**Purpose:** Automate property management tasks, match jobs with contractors, and handle approval workflows.

**Capabilities:**

- **Incident Management**
  - Auto-receive incidents from tenants
  - Categorize by property and unit
  - Map incidents to specific properties in portfolio
  - Track incident status and history

- **Job Creation & Pricing**
  - Convert incidents to contractor jobs
  - Suggest pricing based on job type and market rates
  - Generate job descriptions
  - Set deadlines and priorities

- **Contractor Matching Algorithm**
  ```python
  Match contractors based on:
  1. Skills match (plumber for plumbing, electrician for electrical)
  2. Rating/reviews (prefer 4.5+ stars)
  3. Proximity to property (within 10-mile radius preferred)
  4. Availability (can start within required timeframe)
  5. Price competitiveness (compare 3+ bids)
  ```

- **Approval Workflows**
  - Present matched contractors to landlord
  - Get approval before assigning job
  - Handle bid comparisons
  - Manage change orders

- **Financial Tracking**
  - Track job costs per property
  - Monthly expense reports
  - Budget alerts
  - Tax documentation

**Example Conversation:**
```
AI: "🔔 New incident from Tenant Sarah at 123 Oakwood Ave, Unit 2A:
     'Kitchen sink leak - pipe joint issue'
     Severity: MEDIUM | Photos attached
     Suggested action: Hire plumber"
Landlord: "Find me a plumber"
AI: "Searching for qualified plumbers near 123 Oakwood Ave...

     Found 3 matches:

     1. ⭐ Joe's Plumbing (4.8★, 2.3 mi away)
        - Available: Tomorrow 9 AM
        - Estimated cost: $150-200
        - Specialization: Residential leaks

     2. ⭐ Quick Fix Plumbing (4.6★, 5.1 mi away)
        - Available: Today 2 PM
        - Estimated cost: $180-250
        - Specialization: Emergency repairs

     3. ⭐ Dave's Plumbing (4.9★, 8.2 mi away)
        - Available: Next week Mon
        - Estimated cost: $140-180
        - Specialization: Sink/drain specialist

     Which contractor would you like to hire?"
Landlord: "Go with #1"
AI: "✅ Job assigned to Joe's Plumbing
     📅 Scheduled: Tomorrow 9 AM
     💰 Budget approved: $200 max
     🔔 I'll notify the tenant and track completion."
```

---

### 3. Contractor AI Agent ("JobAssistant")

**Purpose:** Help contractors manage jobs, schedules, bids, and get paid efficiently.

**Capabilities:**

- **Job Discovery & Bidding**
  - Show available jobs matching skills
  - Help create competitive bids
  - Highlight job urgency and requirements
  - Track bid status (pending/accepted/rejected)

- **Schedule Management**
  - Calendar view of upcoming jobs
  - Send reminders 24h and 1h before job
  - Handle rescheduling requests
  - Track job completion deadlines

- **Skills & Profile Management**
  - Update skills and certifications
  - Manage service area (zip codes)
  - Set availability windows
  - Update pricing structure

- **Job Completion Workflow**
  ```
  1. Contractor arrives → AI sends "Job started" notification to landlord
  2. Contractor uploads before photos
  3. Contractor completes work
  4. Contractor uploads after photos
  5. AI analyzes photo quality and work completeness
  6. Contractor submits time and materials
  7. AI generates receipt and pay slip
  8. AI requests landlord approval for payment
  9. On approval, AI processes payment (via Stripe/PayPal)
  10. AI sends invoice and tax document to contractor
  ```

- **Payment Processing**
  - Auto-generate receipts
  - Track payment status
  - Send reminders for overdue payments
  - Provide tax documentation (1099 forms)

- **Performance Analytics**
  - Job completion rate
  - Average rating from landlords
  - Response time metrics
  - Revenue tracking

**Example Conversation:**
```
AI: "🔔 New job available:

     📍 Location: 123 Oakwood Ave (2.3 mi from you)
     🔧 Type: Kitchen sink leak repair
     ⏰ Urgency: Medium (24-48h response needed)
     💰 Budget: $200
     📸 Photos: [3 attached]

     This matches your skills: ✅ Plumbing, ✅ Residential

     Would you like to bid on this job?"
Contractor: "Yes, I can do it tomorrow at 9 AM for $175"
AI: "✅ Bid submitted to landlord
     Your bid: $175 (tomorrow 9 AM)
     Competing bids: 2 other contractors
     I'll notify you when landlord responds."

[Next day, after job is assigned]

AI: "⏰ Reminder: Job at 123 Oakwood Ave starts in 1 hour (9 AM)

     Details:
     - Contact: Sarah Johnson (tenant)
     - Phone: (555) 123-4567
     - Access: Unit 2A, 2nd floor
     - Issue: Kitchen sink leak (pipe joint)

     Please upload 'before' photos when you arrive."

[Contractor arrives and uploads photos]

AI: "✅ Before photos received
     Timer started: $175 job, estimated 1-2 hours

     Need help with anything?"

[2 hours later, contractor uploads after photos]

Contractor: "Job done, used 1 pipe joint ($8) and 1 hour labor"
AI: "Great! Analyzing completion...

     ✅ Before/after photos look good
     ✅ Work appears complete
     ✅ Time: 1 hour (within estimate)

     Receipt generated:
     - Labor: $167 (1 hr @ $167/hr)
     - Materials: $8 (pipe joint)
     - Total: $175

     Sending to landlord for approval. Payment typically processes within 24 hours.

     Thanks for the great work! 🎉"

[Next day]

AI: "💰 Payment approved and processed!
     Amount: $175
     Method: Direct deposit
     ETA: 2-3 business days

     📄 Invoice #INV-5678 sent to your email
     📋 Added to your tax records for 2025

     ⭐ Landlord rated your work: 5.0 stars
     'Quick and professional - highly recommend!'"
```

---

## Technical Implementation

### Backend Components

#### 1. Stream Chat Bot Configuration (`backend/app/services/stream_bot.py`)

```python
from stream_chat import StreamChat

class PropertyAIBot:
    def __init__(self):
        self.client = StreamChat(
            api_key=settings.STREAM_CHAT_API_KEY,
            api_secret=settings.STREAM_CHAT_API_SECRET
        )

    async def create_bot_user(self, persona: str):
        """Create AI bot user for specific persona"""
        bot_id = f"ai-{persona}-bot"
        bot_name = {
            "tenant": "PropertyHelper",
            "landlord": "PropertyManager",
            "contractor": "JobAssistant"
        }[persona]

        self.client.upsert_user({
            "id": bot_id,
            "name": bot_name,
            "role": "admin",
            "is_bot": True,
            "persona": persona
        })
        return bot_id

    async def add_bot_to_channel(self, channel_id: str, bot_id: str):
        """Add bot to channel with AI capabilities"""
        channel = self.client.channel("messaging", channel_id)
        channel.add_members([bot_id], {"is_moderator": True})
```

#### 2. AI Processing Service (`backend/app/services/ai_processor.py`)

```python
from openai import AsyncOpenAI

class AIProcessor:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def process_tenant_message(self, message: str, context: dict):
        """Process tenant message and determine action"""
        system_prompt = """
        You are PropertyHelper, an AI assistant for tenants.
        Help troubleshoot issues, assess severity, and create incidents.
        Be friendly, professional, and proactive.
        """

        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            functions=[
                {
                    "name": "create_incident",
                    "description": "Create maintenance incident",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "severity": {"type": "string", "enum": ["low", "medium", "high", "emergency"]},
                            "category": {"type": "string"}
                        }
                    }
                }
            ]
        )
        return response

    async def match_contractors(self, job: dict):
        """Match contractors using AI-powered ranking"""
        # Implementation for contractor matching algorithm
        pass
```

#### 3. Webhook Handler (`backend/app/routes/ai_webhooks.py`)

```python
@router.post("/ai/stream-webhook")
async def handle_stream_webhook(request: Request):
    """Handle Stream Chat webhooks for AI bot interactions"""
    payload = await request.json()

    if payload["type"] == "message.new":
        message = payload["message"]
        channel_id = payload["channel_id"]
        user_id = payload["user"]["id"]

        # Don't respond to bot's own messages
        if message["user"]["is_bot"]:
            return {"status": "ignored"}

        # Determine persona from channel
        persona = await get_channel_persona(channel_id)

        # Process message through AI
        if persona == "tenant":
            response = await ai_processor.process_tenant_message(
                message["text"],
                context={"user_id": user_id, "channel_id": channel_id}
            )
        elif persona == "landlord":
            response = await ai_processor.process_landlord_message(...)
        elif persona == "contractor":
            response = await ai_processor.process_contractor_message(...)

        # Send AI response back to channel
        await stream_bot.send_message(channel_id, response)

    return {"status": "processed"}
```

### Frontend Components

#### 1. AI Chat Interface (`frontend/src/components/ai/AIStreamChat.tsx`)

```typescript
import { useAIState } from '@stream-io/ai-sdk-react';

export function AIStreamChat({ persona }: { persona: string }) {
  const { aiState, sendMessage } = useAIState({
    botId: `ai-${persona}-bot`,
    channelType: 'messaging',
    channelId: `${persona}-${userId}`
  });

  return (
    <div className="ai-chat-container">
      <StreamChatPane
        persona={persona}
        aiEnabled={true}
        aiIndicator={aiState.thinking}
      />
      {aiState.suggestedActions && (
        <SuggestedActions actions={aiState.suggestedActions} />
      )}
    </div>
  );
}
```

#### 2. Calendar Component (`frontend/src/components/ai/CalendarScheduler.tsx`)

```typescript
import { Calendar } from '@stream-io/calendar-sdk';

export function CalendarScheduler({ contractorId, jobId }) {
  const [availability, setAvailability] = useState([]);

  useEffect(() => {
    // Fetch contractor availability
    fetchAvailability(contractorId).then(setAvailability);
  }, [contractorId]);

  return (
    <Calendar
      availability={availability}
      onSchedule={(slot) => scheduleJob(jobId, slot)}
      minNotice="2h"
      workingHours={{ start: "8:00", end: "18:00" }}
    />
  );
}
```

#### 3. AI Action Buttons (`frontend/src/components/ai/AIActionButton.tsx`)

```typescript
export function AIActionButton({
  action,
  onConfirm
}: {
  action: AIAction,
  onConfirm: () => void
}) {
  return (
    <button
      onClick={onConfirm}
      className="ai-action-btn"
    >
      {action.icon} {action.label}
    </button>
  );
}

// Example usage:
<AIActionButton
  action={{
    type: "create_incident",
    label: "Create Incident",
    icon: "🔧"
  }}
  onConfirm={() => createIncident(aiSuggestedData)}
/>
```

---

## Workflow Examples

### Complete Tenant Workflow

```
1. Tenant opens chat → AI greets: "Hi! How can I help today?"

2. Tenant: "Heater not working"

3. AI: "Let me help troubleshoot:
   - Have you checked the thermostat settings?
   - Is the circuit breaker on?
   - When did it stop working?"

4. Tenant: "Thermostat is set to 72°F, breaker is on, stopped yesterday"

5. AI: "This requires professional HVAC service (HIGH urgency - it's winter).

   I recommend:
   - Severity: HIGH
   - Category: HVAC
   - Urgency: 24-hour response needed

   Shall I create an incident for your landlord?"

6. Tenant: "Yes"

7. AI: "✅ Incident #INC-5678 created
   📸 Can you send a photo of your thermostat?
   🔔 Landlord will be notified immediately"

8. [Tenant uploads photo]

9. AI: "Photo received and added to incident.
   I'll keep you updated on landlord's response.

   In the meantime, you might want to use a space heater if you have one."

10. [Landlord assigns job to contractor]

11. AI: "🎉 Update: HVAC technician scheduled
    👷 Contractor: Quick Fix HVAC
    📅 Time: Today 2 PM

    They'll call 30 min before arrival."
```

### Complete Landlord Workflow

```
1. AI: "🔔 URGENT: New incident from Tenant Mike

   Property: 456 Maple St, Unit 1B
   Issue: Heater not working
   Severity: HIGH (winter heating emergency)
   Photos: [thermostat showing 58°F]

   Recommended action: Hire HVAC contractor within 24h"

2. Landlord: "Find HVAC contractors"

3. AI: "Searching HVAC contractors near 456 Maple St...

   🎯 TOP MATCH: Quick Fix HVAC
   ⭐ Rating: 4.9/5 (127 reviews)
   📍 Distance: 3.2 miles
   ⏰ Available: Today 2 PM or tomorrow 8 AM
   💰 Estimate: $120-180 (diagnostic + repair)
   🔧 Specialization: Residential heating systems

   Other options:
   2. Budget HVAC (4.5★, $100-150, tomorrow)
   3. Premium Heat (4.8★, $200-300, today 4 PM)

   Hire Quick Fix HVAC?"

4. Landlord: "Yes, schedule for today 2 PM"

5. AI: "✅ Job #JOB-9012 created
   👷 Contractor: Quick Fix HVAC
   📅 Scheduled: Today 2 PM
   💰 Budget: $180 max

   Notifications sent to:
   - Tenant (Mike)
   - Contractor (Quick Fix HVAC)

   I'll update you on job progress."

6. [Later that day]

7. AI: "📍 Job started: Quick Fix HVAC arrived at 456 Maple St
   ⏱️ Started: 2:07 PM"

8. AI: "✅ Job completed: 3:42 PM

   Contractor report:
   - Issue: Faulty thermostat wiring
   - Fix: Rewired thermostat, tested system
   - Cost: $165 (labor + materials)
   - Photos: [before/after images]

   Tenant confirmed: Heat is working ✅

   Approve payment of $165?"

9. Landlord: "Approved"

10. AI: "💰 Payment processed
    📄 Invoice #INV-9012 saved
    📊 Added to property expenses: $165

    This month's maintenance: $487 (Budget: $800)

    Job closed. ✅"
```

### Complete Contractor Workflow

```
1. AI: "☀️ Good morning! You have 3 new job opportunities:

   1. 🔥 URGENT: Heater repair (3.2 mi, $120-180)
   2. Leaky faucet (5.1 mi, $80-120)
   3. Electrical outlet repair (8.7 mi, $100-150)

   Interested in any?"

2. Contractor: "Tell me more about #1"

3. AI: "🔥 Job Details:

   Property: 456 Maple St, Unit 1B
   Issue: Heater not working (tenant reports 58°F inside)
   Urgency: HIGH (needs repair today if possible)
   Photos: [thermostat display]
   Budget: $120-180

   Property Manager: John Smith (4.8★ as client)
   Tenant: Mike (home all day)

   Your match score: 95%
   - ✅ HVAC specialist
   - ✅ Within 5 miles
   - ✅ Available today
   - ✅ High rating (4.9★)

   Available times:
   - Today: 2 PM, 4 PM
   - Tomorrow: 8 AM, 10 AM, 2 PM

   Submit a bid?"

4. Contractor: "Bid $150, available today 2 PM"

5. AI: "✅ Bid submitted
   Your bid: $150 (today 2 PM)
   Status: Pending landlord approval

   I'll notify you ASAP."

6. [5 minutes later]

7. AI: "🎉 BID ACCEPTED!

   Job: Heater repair at 456 Maple St
   Time: Today 2 PM
   Pay: $150

   Contact info:
   - Tenant: Mike Johnson
   - Phone: (555) 234-5678
   - Access code: #1234

   ⏰ I'll remind you 1 hour before.

   Added to your calendar 📅"

8. [1 PM - reminder]

9. AI: "⏰ Reminder: Job in 1 hour

   📍 456 Maple St, Unit 1B
   🕐 2:00 PM
   👤 Mike Johnson (555) 234-5678

   Don't forget to upload before photos when you arrive!"

10. [Contractor arrives at 2 PM]

11. Contractor: [uploads before photos]

12. AI: "✅ Before photos received
    ⏱️ Timer started

    Let me know when you're done!"

13. [Job completed at 3:42 PM]

14. Contractor: "Done. Rewired thermostat. Used $15 in parts, 1.5 hours labor"

15. AI: "Great work! Upload after photos to complete the job."

16. Contractor: [uploads after photos]

17. AI: "📸 Analyzing completion...

    ✅ Looks good! System appears to be working
    ⏱️ Time: 1h 35min
    💰 Cost breakdown:
    - Labor: $135 (1.5h)
    - Parts: $15
    - Total: $150

    Generating receipt... done!

    📄 Receipt #REC-9012 sent to landlord
    Payment pending approval (typically < 24h)

    🌟 Great job today!"

18. [Next day]

19. AI: "💰 PAYMENT RECEIVED

    Amount: $150
    Method: Direct deposit
    Account: •••• 1234

    📊 This week's earnings: $847
    📈 This month: $3,215

    📄 Invoice saved for tax records

    ⭐ Client rating: 5.0/5
    Review: 'Fast and professional. Highly recommend!'

    Your new rating: 4.9★ (132 jobs)

    Keep up the excellent work! 🎉"
```

---

## Data Models

### AI Context Storage

```python
class AIContext(BaseModel):
    user_id: str
    persona: str  # tenant, landlord, contractor
    conversation_id: str
    messages: List[Message]
    current_intent: Optional[str]  # "troubleshoot", "create_incident", "find_contractor", etc.
    extracted_data: Dict[str, Any]  # Parsed entities from conversation
    suggested_actions: List[Action]
    created_at: datetime
    updated_at: datetime

class Action(BaseModel):
    type: str  # "create_incident", "schedule_job", "process_payment"
    label: str  # Display text for button
    data: Dict[str, Any]  # Pre-filled data from AI
    requires_approval: bool
```

### Job Matching Score

```python
class ContractorMatch(BaseModel):
    contractor_id: str
    contractor_name: str
    match_score: float  # 0-100
    rating: float
    distance_miles: float
    estimated_cost: str
    availability: List[datetime]
    skills_match: List[str]
    reasons: List[str]  # Why this is a good match
```

---

## Configuration

### Environment Variables (Backend)

```bash
# AI Service
OPENAI_API_KEY=sk-...
AI_MODEL=gpt-4
AI_TEMPERATURE=0.7

# Stream Chat
STREAM_CHAT_API_KEY=...
STREAM_CHAT_API_SECRET=...
STREAM_WEBHOOK_SECRET=...

# Payment Processing
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...

# Calendar Integration
CALENDLY_API_KEY=...
```

### Stream Chat Dashboard Setup

1. Enable AI/ML features in Stream dashboard
2. Configure webhook URL: `https://your-backend.com/ai/stream-webhook`
3. Select events: `message.new`, `message.updated`, `reaction.new`
4. Set webhook secret for security

---

## Security Considerations

1. **AI Response Validation**
   - All AI-generated actions require explicit user approval
   - Validate AI output before executing database operations
   - Implement rate limiting on AI requests

2. **Payment Security**
   - Never let AI directly process payments without approval
   - Use Stripe for PCI compliance
   - Log all payment-related AI suggestions

3. **Privacy**
   - Don't expose personal info (phone, email) unless necessary
   - Respect tenant privacy in landlord conversations
   - Anonymize data in AI training logs

4. **Error Handling**
   - Graceful fallback when AI service is down
   - Human escalation for complex issues
   - Clear error messages to users

---

## Performance Optimization

1. **Caching**
   - Cache contractor availability calendars
   - Cache property details for quick lookups
   - Cache AI responses for common questions

2. **Async Processing**
   - Process AI requests asynchronously
   - Use background jobs for contractor matching
   - Queue webhook processing

3. **Cost Management**
   - Set budget limits on OpenAI API usage
   - Use cheaper models (GPT-3.5) for simple tasks
   - Implement token limits per conversation

---

## Rollout Plan

### Phase 1: Foundation (Week 1)
- Set up Stream Chat bot users
- Implement webhook handler
- Create basic AI response system
- Test with simple tenant Q&A

### Phase 2: Tenant Workflow (Week 2)
- Implement incident creation workflow
- Add severity analysis
- Test troubleshooting flow
- Deploy to beta users

### Phase 3: Landlord Workflow (Week 3)
- Implement contractor matching
- Add job creation automation
- Test approval workflows
- Integrate calendar scheduling

### Phase 4: Contractor Workflow (Week 4)
- Implement bidding system
- Add job completion tracking
- Integrate payment processing
- Test end-to-end flow

### Phase 5: Polish & Launch (Week 5)
- Performance optimization
- Error handling improvements
- User documentation
- Public launch

---

## Success Metrics

1. **User Engagement**
   - % of incidents created via AI (target: >60%)
   - Average messages per incident (target: <10)
   - User satisfaction rating (target: >4.5/5)

2. **Efficiency**
   - Time to schedule contractor (target: <2 hours)
   - Job completion rate (target: >95%)
   - Payment processing time (target: <24h)

3. **Cost**
   - AI cost per interaction (target: <$0.10)
   - Total AI spend per month (monitor)
   - ROI from automation savings

---

## Future Enhancements

1. **Voice Integration**
   - Voice commands for hands-free reporting
   - Voice reminders for contractors
   - Call transcription for record-keeping

2. **Predictive Maintenance**
   - AI predicts issues before they occur
   - Seasonal maintenance reminders
   - Equipment lifecycle tracking

3. **Smart Pricing**
   - Dynamic pricing based on market rates
   - Bulk discount for multiple jobs
   - Seasonal pricing adjustments

4. **Advanced Analytics**
   - Property health scores
   - Contractor performance trends
   - Cost optimization recommendations

---

## Resources

- **Stream Chat AI Docs**: https://getstream.io/chat/docs/python/chat_bots/
- **Stream AI UI Components**: https://getstream.io/chat/docs/sdk/react/components/ai/ui-components/
- **OpenAI Function Calling**: https://platform.openai.com/docs/guides/function-calling
- **Stripe Payments**: https://stripe.com/docs/payments
- **Calendly API**: https://developer.calendly.com/

---

This architecture provides a comprehensive AI-powered property management experience that reduces manual work, speeds up incident resolution, and improves satisfaction for all user personas.
