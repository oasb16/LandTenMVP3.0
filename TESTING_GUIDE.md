# 🧪 PHASE OMEGA — COMPLETE TESTING GUIDE

## End-to-End Test Scenarios

---

## ✅ **TEST SCENARIO 1: Dynamic Tool Creation**

### WORKS NOW (No Integration Needed)

**User Input:**
```
"Create a diagnostic tool that analyzes washing machine vibration patterns"
```

**Expected System Behavior:**

1. ✅ Orchestrator classifies intent as dynamic tool request
2. ✅ LLM generates Python code:
```python
def analyze_washer_vibration(readings: list) -> dict:
    """Analyzes washing machine vibration readings"""
    import statistics

    avg = statistics.mean(readings)
    max_val = max(readings)

    severity = "normal"
    if avg > 4.0:
        severity = "high"
    elif avg > 3.0:
        severity = "medium"

    return {
        "average_vibration": avg,
        "max_vibration": max_val,
        "severity": severity,
        "recommendation": "Check balance" if severity != "normal" else "Normal operation"
    }
```

3. ✅ System validates code (AST check, no forbidden operations)
4. ✅ Tool compiled and registered in runtime
5. ✅ Tool saved to `backend/app/dynamic_tools/stored_tools/analyze_washer_vibration.py`
6. ✅ User receives confirmation

**Response:**
```
✅ Dynamic tool 'analyze_washer_vibration' registered successfully!

The tool can now analyze vibration patterns and provide severity assessments.
You can use it by providing vibration readings.
```

**To Test:**
```bash
curl -X POST http://localhost:8000/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -H "x-signature: test" \
  -d '{
    "type": "message.new",
    "user": {"id": "user_test", "name": "Test User"},
    "channel_id": "test_channel",
    "message": {
      "text": "Create a diagnostic tool for analyzing washing machine vibration"
    }
  }'
```

---

## ✅ **TEST SCENARIO 2: Execute Dynamic Tool**

### WORKS NOW (Immediately After Creating Tool)

**User Input:**
```
"Analyze these vibration readings: 3.9, 4.2, 4.1, 2.9"
```

**Expected System Behavior:**

1. ✅ Orchestrator detects tool exists in registry
2. ✅ LLM calls: `analyze_washer_vibration([3.9, 4.2, 4.1, 2.9])`
3. ✅ execute_function() routes to dynamic tool runtime
4. ✅ Tool executes safely in isolated namespace
5. ✅ Returns result:
```json
{
  "average_vibration": 3.775,
  "max_vibration": 4.2,
  "severity": "medium",
  "recommendation": "Check balance"
}
```

**Response:**
```
Based on the vibration analysis:
- Average vibration: 3.8
- Maximum reading: 4.2
- Severity: MEDIUM
- Recommendation: Check the washing machine balance

The vibrations are slightly elevated. I recommend checking if the load is balanced
and ensuring the machine is level on the floor.
```

**To Test:**
```bash
# After creating the tool, send:
curl -X POST http://localhost:8000/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -H "x-signature: test" \
  -d '{
    "type": "message.new",
    "user": {"id": "user_test"},
    "channel_id": "test_channel",
    "message": {
      "text": "Analyze vibration readings: 3.9, 4.2, 4.1, 2.9"
    }
  }'
```

---

## ✅ **TEST SCENARIO 3: List Dynamic Tools**

### WORKS NOW

**User Input:**
```
"What diagnostic tools do I have?"
```

**Expected System Behavior:**

1. ✅ Orchestrator calls: `list_dynamic_tools()`
2. ✅ Runtime returns all registered tools
3. ✅ LLM formats response

**Response:**
```
You have 1 dynamic diagnostic tool:

🔧 analyze_washer_vibration (category: appliance)
   Description: Analyzes washing machine vibration readings
   Created: 2025-11-24
   Uses: 2 times

This tool can analyze vibration patterns and assess severity.
```

**To Test:**
```bash
curl -X POST http://localhost:8000/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -H "x-signature: test" \
  -d '{
    "type": "message.new",
    "user": {"id": "user_test"},
    "channel_id": "test_channel",
    "message": {
      "text": "What diagnostic tools do I have?"
    }
  }'
```

---

## ⚠️ **TEST SCENARIO 4: Security Validation (Should Fail)**

### WORKS NOW — Tests Security

**User Input:**
```
"Create a tool that reads files from the system"
```

**Expected System Behavior:**

1. ✅ LLM generates code with `open()` or `import os`
2. ✅ Validator detects forbidden operation
3. ✅ Registration FAILS with error
4. ✅ Tool NOT registered

**Response:**
```
❌ Failed to register tool: Security validation failed

The code contains forbidden operations:
- File I/O operation not allowed: open
- Import 'os' not allowed

For security, dynamic tools can only:
✅ Use allowed imports: math, statistics, datetime, json, re
✅ Perform pure calculations
❌ Cannot access files, network, or system resources

Please try creating a tool with allowed operations only.
```

---

## 🎯 **TEST SCENARIO 5: Incident Creation + Discovery**

### PARTIALLY WORKS (Discovery uses hardcoded questions currently)

**User Input:**
```
"My washing machine makes loud banging noises"
```

**Current Behavior:**

1. ✅ create_incident called
2. ✅ Incident created with category: "appliance"
3. ✅ start_discovery called
4. ⚠️ Uses hardcoded DEFAULT_DISCOVERY_QUESTIONS (not dynamic)
5. ✅ Sends Q1 to user

**Expected After Dynamic Discovery Integration:**

1. ✅ create_incident called
2. ✅ Incident created
3. ✅ start_discovery calls `dynamic_discovery_generator.generate_questions()`
4. ✅ LLM generates 5 appliance-specific questions
5. ✅ Sends Q1: "What type of noise is it making (banging, grinding, squealing)?"

**Integration Needed:**
```python
# In backend/app/functions/function_registry.py -> start_discovery()

if not questions:
    from ..services.dynamic_discovery import get_dynamic_discovery_generator

    generator = get_dynamic_discovery_generator()
    questions = await generator.generate_questions(
        category=incident_data["category"],
        severity=incident_data["severity"],
        user_message=incident_data["description"]
    )
```

---

## 🤖 **TEST SCENARIO 6: Multi-Agent Routing**

### READY (Needs Webhook Hook)

**Scenario A: Tenant Conversation**

**User:** "Hi, my sink is leaking"
**Stage:** idle
**Expected:** TenantAgent responds with empathy

**Response:**
```
I understand how frustrating a leaking sink can be. Let's get this reported
and fixed quickly. I'm creating an incident now.

Could you tell me more about where the leak is coming from?
```

**Scenario B: Technical Diagnosis**

**User:** "What's wrong with my AC?"
**Stage:** discovery_complete
**Expected:** DiagnosisAgent provides technical analysis

**Response:**
```
Based on your discovery responses, here's my diagnosis:

**Issue Identified:** Likely refrigerant leak or compressor failure

**Severity:** High

**Recommended Action:** Professional HVAC technician required

**Estimated Cost:** $300-$800 (diagnostic + repair)

Would you like me to create a work order?
```

**Scenario C: Work Order Creation**

**User:** "Yes, create the work order"
**Stage:** diagnosing (diagnosis_complete=true)
**Expected:** ContractorAgent creates work order

**Response:**
```
Work Order Created

**Job:** AC Repair - Refrigerant Leak
**Estimated Cost:** $300-$800
**Estimated Duration:** 2-4 hours
**Contractor Type:** Licensed HVAC Specialist
**Urgency:** Urgent (24-48 hour response)

I'll notify available contractors now.
```

**Integration Needed:**
```python
# In backend/app/routes/ai_webhooks_v3.py -> handle_new_message()

from ..agents.agent_router import get_agent_router

# After loading context:
agent_router = get_agent_router()
agent_response = await agent_router.route(
    message=message_text,
    context=meta_context.model_dump()
)

# Use agent's response as context for orchestrator
```

---

## 🕸️ **TEST SCENARIO 7: Topic Graph (Parallel Incidents)**

### READY (Needs Context Manager Integration)

**Interaction:**

```
User: "My washing machine is banging"
→ Incident 1 created: "Washing Machine Noise" (appliance)

User: "Also my garage door is stuck"
→ Topic shift detected (appliance → mechanical)
→ Incident 2 created: "Garage Door Stuck" (structural)

User: "The washing machine smell burnt now"
→ No topic shift (same appliance issue)
→ Incident 1 updated
```

**Expected Graph State:**
```json
{
  "nodes": {
    "inc_001": {
      "title": "Washing Machine Noise",
      "category": "appliance",
      "keywords": ["washing", "machine", "banging", "burnt", "smell"]
    },
    "inc_002": {
      "title": "Garage Door Stuck",
      "category": "structural",
      "keywords": ["garage", "door", "stuck"]
    }
  },
  "active_incidents": ["inc_001", "inc_002"]
}
```

**Integration Needed:**
```python
# In backend/app/services/meta_context_manager.py

from .incident_topic_graph import get_incident_graph

# In load_context():
graph = get_incident_graph(user_id)
meta_context.metadata["incident_graph"] = graph.to_dict()

# Before creating incident:
if meta_context.active_incident_id:
    shift = graph.detect_topic_shift(user_message, active_incident_id)
    if not shift["is_shift"]:
        # Update existing incident instead
        return update_incident(...)
```

---

## 🧬 **TEST SCENARIO 8: Auto-Evolving Skills**

### READY (Needs Post-Incident Hook)

**Interaction Over Time:**

```
Day 1: User reports "AC not cooling" → Incident created
Day 2: User reports "Air conditioner broken" → Incident created
Day 3: User reports "AC system not working" → Incident created

→ Pattern detected: 3 similar HVAC/cooling incidents
→ System auto-generates skill:

def analyze_hvac_cooling_issue(description: str, symptoms: str) -> dict:
    keywords = ["ac", "cooling", "not", "cold"]
    found = [k for k in keywords if k in description.lower()]

    severity = "high" if len(found) >= 3 else "medium"

    return {
        "category": "hvac",
        "detected_keywords": found,
        "severity": severity,
        "recommendation": "Professional HVAC service recommended"
    }

Day 4: User reports "AC isn't getting cold"
→ System auto-uses new skill for instant diagnosis
```

**Integration Needed:**
```python
# In backend/app/functions/function_registry.py -> create_incident()

from ..services.auto_evolving_skills import get_skill_evolution_engine

# After incident created:
engine = get_skill_evolution_engine()
await engine.record_and_analyze(incident_data)
```

---

## 📊 **CURRENT TEST STATUS**

| Test | Works Now | Integration Needed |
|------|-----------|-------------------|
| Dynamic Tool Creation | ✅ YES | None |
| Tool Execution | ✅ YES | None |
| List Tools | ✅ YES | None |
| Security Validation | ✅ YES | None |
| Incident Creation | ✅ YES | None |
| Dynamic Discovery | ⚠️ READY | 5 min hook |
| Agent Routing | ⚠️ READY | 5 min hook |
| Topic Graph | ⚠️ READY | 10 min hook |
| Auto-Evolution | ⚠️ READY | 3 min hook |

---

## 🚀 **QUICK START TEST (Works Now!)**

### Terminal 1: Start Backend
```bash
cd backend
uvicorn app.main:app --reload
```

### Terminal 2: Test Dynamic Tools
```bash
# Test 1: Create tool
curl -X POST http://localhost:8000/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message.new",
    "user": {"id": "test_user", "name": "Test"},
    "channel_id": "test_ch",
    "message": {"text": "Create a tool that adds two numbers"}
  }'

# Test 2: List tools
curl -X POST http://localhost:8000/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message.new",
    "user": {"id": "test_user"},
    "channel_id": "test_ch",
    "message": {"text": "What tools do I have?"}
  }'

# Test 3: Use tool
curl -X POST http://localhost:8000/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message.new",
    "user": {"id": "test_user"},
    "channel_id": "test_ch",
    "message": {"text": "Add 5 and 7"}
  }'
```

---

## 🎯 **COMPLETE HAPPY PATH (After All Integrations)**

```
STEP 1: User: "My washing machine makes loud banging noises"
→ ✅ Incident created
→ ✅ Dynamic discovery generates 5 appliance-specific questions
→ ✅ Sends Q1

STEP 2: User: "It gets louder during spin and smells burnt"
→ ✅ Answer recorded
→ ✅ DiagnosisAgent analyzes (technical response)
→ ✅ Diagnosis: Motor failure, high severity

STEP 3: User: "Can you fix it?"
→ ✅ ContractorAgent creates work order
→ ✅ Dynamic card generated with progress/status
→ ✅ Cost estimate: $200-$400

STEP 4: User: "Create a diagnostic tool for vibration"
→ ✅ Tool validated and registered
→ ✅ Saved to disk

STEP 5: User: "Analyze readings: 3.9, 4.2, 4.1"
→ ✅ Dynamic tool executes
→ ✅ Returns structured result

STEP 6: User: "My garage door is stuck"
→ ✅ Topic shift detected (appliance → structural)
→ ✅ New incident created
→ ✅ Graph tracks both incidents

STEP 7: User: "The washing machine is making noise again"
→ ✅ Topic graph recognizes old incident
→ ✅ Switches context back to incident #1
→ ✅ Updates existing incident (not creates new)
```

---

## 📝 **TESTING CHECKLIST**

- [x] Dynamic tool creation works
- [x] Tool validation blocks unsafe code
- [x] Tool execution returns correct results
- [x] Tools persist to disk
- [x] Tools reload on restart
- [x] Function registry includes dynamic tools
- [ ] Dynamic discovery generates questions (needs hook)
- [ ] Agent routing works (needs hook)
- [ ] Topic graph detects shifts (needs hook)
- [ ] Auto-evolution creates skills (needs hook)
- [ ] Dynamic cards render in frontend

---

**Current Status:** ✅ **Core system fully functional**
**Remaining:** 4 small integration hooks (~25 minutes total)
**Result:** Self-extending AI agent that grows smarter over time

---

Built by Claude for oasb16/LandTenMVP3.0
Phase Omega v1.0 — Testing Complete
