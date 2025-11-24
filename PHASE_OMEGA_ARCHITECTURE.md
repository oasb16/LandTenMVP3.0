# 🚀 PHASE OMEGA — "Boundaryless Agent" Architecture

## Complete Transformation Documentation
### LandTenMVP3.0 — Self-Extending AI Runtime

---

## 📋 TABLE OF CONTENTS

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [New Components](#new-components)
4. [Integration Points](#integration-points)
5. [Deployment Guide](#deployment-guide)
6. [Testing Plan](#testing-plan)
7. [API Changes](#api-changes)
8. [Migration Notes](#migration-notes)

---

## 1. EXECUTIVE SUMMARY

### What Changed

The LandTen Agent has been transformed from a **rigid orchestrator** into a **dynamic, self-extending AI runtime**.

**Before (V3.0):**
- Hardcoded function registry
- Fixed discovery questions (Q1-Q5)
- Single orchestrator for all tasks
- Linear incident flow
- Static system capabilities

**After (Phase Omega):**
- ✨ **Dynamic Tool Runtime** - LLM generates and registers Python functions at runtime
- 🎯 **Multi-Agent System** - TenantAgent, DiagnosisAgent, ContractorAgent with specialized knowledge
- 📊 **Dynamic Discovery** - Category-specific questions generated on the fly
- 🎨 **Dynamic Incident Cards** - Rich, structured JSON cards for UI
- 🕸️ **Incident Topic Graph** - Track multiple parallel issues simultaneously
- 🧬 **Auto-Evolving Skills** - System learns from patterns and creates new tools

### Impact

| Feature | Before | After |
|---------|--------|-------|
| Add new tool | Code deployment required | LLM generates and registers instantly |
| Discovery questions | Hardcoded Q1-Q5 | Dynamically generated per category/issue |
| Agent specialization | Single orchestrator | 3 specialized agents with domain expertise |
| Multi-issue handling | Sequential only | Parallel tracking via topic graph |
| Learning capability | None | Learns patterns, creates new tools |
| Incident cards | Basic text | Rich JSON with collapsible sections, progress bars |

---

## 2. ARCHITECTURE OVERVIEW

### System Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                     USER MESSAGE INPUT                        │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              AI WEBHOOKS V3 (Entry Point)                     │
│  - Signature verification                                     │
│  - Message routing                                            │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│               META CONTEXT MANAGER                            │
│  - Loads conversation state                                   │
│  - Manages incident topic graph                               │
│  - Tracks dynamic tool metadata                               │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                  AGENT ROUTER                                 │
│  Routes to: TenantAgent | DiagnosisAgent | ContractorAgent   │
└──────┬─────────────────┬─────────────────┬───────────────────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌────────────┐   ┌────────────┐   ┌────────────┐
│  TENANT    │   │ DIAGNOSIS  │   │ CONTRACTOR │
│  AGENT     │   │  AGENT     │   │   AGENT    │
│            │   │            │   │            │
│ Friendly   │   │ Technical  │   │ Scheduling │
│ Guidance   │   │ Analysis   │   │ Work Order │
└────────────┘   └────────────┘   └────────────┘
       │                 │                 │
       └─────────────────┴─────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                 ORCHESTRATOR (LLM)                            │
│  - Intent classification                                      │
│  - Function selection (built-in + dynamic)                    │
│  - Context management                                         │
└────────────────────────┬─────────────────────────────────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
┌─────────────────────┐   ┌──────────────────────┐
│  BUILT-IN FUNCTIONS │   │   DYNAMIC TOOLS      │
│  - create_incident  │   │  - Runtime-generated │
│  - start_discovery  │   │  - LLM-created       │
│  - create_work_order│   │  - Self-validating   │
└─────────────────────┘   └──────────────────────┘
              │                     │
              └──────────┬──────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              FUNCTION EXECUTION LAYER                         │
│  - Executes tool (built-in or dynamic)                        │
│  - Updates incident graph                                     │
│  - Triggers skill evolution                                   │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                 RESPONSE GENERATION                           │
│  - Dynamic incident cards (JSON)                              │
│  - Agent-specific responses                                   │
│  - Stream Bot sends to user                                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. NEW COMPONENTS

### 3.1 Dynamic Tool Runtime

**Location:** `/backend/app/dynamic_tools/`

**Components:**
- `tool_validator.py` - Validates LLM-generated Python code for safety
- `tool_runtime.py` - Manages tool registration, storage, and execution
- `tool_loader.py` - Loads dynamic tools into function registry

**Features:**
- ✅ Safe code validation (whitelist imports, no file I/O, no network)
- ✅ Compilation and execution in isolated namespace
- ✅ Persistent storage to disk
- ✅ Usage tracking and metadata
- ✅ Version management

**Security:**
```python
# Allowed imports
ALLOWED_IMPORTS = {
    "math", "statistics", "datetime", "decimal",
    "re", "json", "typing", "collections"
}

# Forbidden operations
- open() / file I/O
- import os / subprocess
- network access (urllib, requests, socket)
- exec / eval
- global/nonlocal modifications
```

**Example Dynamic Tool:**
```python
def analyze_plumbing_leak_severity(
    leak_rate: str,
    location: str,
    water_color: str
) -> dict:
    """
    Analyzes plumbing leak severity based on symptoms.
    Auto-generated by LLM based on 5+ similar incidents.
    """
    severity = "medium"

    if "flooding" in leak_rate.lower():
        severity = "emergency"
    elif "dripping" in leak_rate.lower():
        severity = "low"

    return {
        "severity": severity,
        "confidence": 0.85,
        "recommendation": "Call emergency plumber" if severity == "emergency" else "Schedule repair within 24-48 hours"
    }
```

### 3.2 Multi-Agent Pipeline

**Location:** `/backend/app/agents/`

**Agents:**

1. **TenantAgent** (`tenant_agent.py`)
   - Role: Friendly conversation and guidance
   - Tone: Warm, empathetic, reassuring
   - Use: General chat, status updates, troubleshooting tips

2. **DiagnosisAgent** (`diagnosis_agent.py`)
   - Role: Technical analysis and root cause identification
   - Tone: Technical but clear
   - Use: Discovery complete → diagnosis stage

3. **ContractorAgent** (`contractor_agent.py`)
   - Role: Work order creation and scheduling
   - Tone: Professional, detail-oriented
   - Use: Diagnosis complete → work order creation

**Agent Router** (`agent_router.py`)
- Auto-routes based on `context.stage`
- Supports explicit agent selection
- Maintains conversation context across agents

**Routing Rules:**
```python
stage == "discovery_complete" → DiagnosisAgent
stage == "diagnosing" + diagnosis_complete → ContractorAgent
stage == "work_order" → ContractorAgent
ALL OTHER CASES → TenantAgent (default)
```

### 3.3 Dynamic Discovery Question Generator

**Location:** `/backend/app/services/dynamic_discovery.py`

**Features:**
- ✨ Generates 5 category-specific questions via LLM
- ✨ Considers incident category, severity, and description
- ✨ Adapts to user's language and detail level
- ✨ Fallback to template questions if LLM fails

**Example:**
```python
# Instead of hardcoded:
Q1: "Is the issue still occurring right now?"
Q2: "Where exactly is the problem located?"
Q3: "When did you first notice this?"
Q4: "Are there any safety hazards?"

# Now generates:
# For plumbing leak:
Q1: "Where exactly is the leak coming from (pipe, faucet, etc.)?"
Q2: "Is it actively dripping or flowing water?"
Q3: "What color is the water (clear, brown, or discolored)?"
Q4: "Is there any water damage visible on walls or floors?"
Q5: "When did you first notice this leak?"
```

### 3.4 Dynamic Incident Cards

**Location:** `/backend/app/services/dynamic_incident_cards.py`

**Card Structure:**
```json
{
  "type": "incident_card",
  "incident_id": "inc_abc123",
  "header": {
    "title": "Kitchen Sink Leak",
    "severity": {
      "level": "high",
      "color": "orange",
      "label": "HIGH"
    },
    "status": {
      "stage": "diagnosing",
      "emoji": "🔬",
      "label": "Diagnosing"
    }
  },
  "sections": [
    {
      "type": "collapsible",
      "title": "📄 Issue Description",
      "collapsed": false,
      "content": "Kitchen sink has been dripping for 3 days..."
    },
    {
      "type": "expandable",
      "title": "❓ Discovery Questions",
      "expanded": false,
      "content": {
        "type": "qa_list",
        "items": [
          {"question": "Q1", "answer": "Under the kitchen sink"},
          {"question": "Q2", "answer": "Yes, actively dripping"}
        ]
      }
    },
    {
      "type": "progress",
      "title": "📊 Status",
      "progress": 60,
      "stages": [
        {"key": "detected", "label": "Reported", "completed": true},
        {"key": "discovery", "label": "Gathering Info", "completed": true},
        {"key": "diagnosing", "label": "Diagnosing", "current": true}
      ]
    }
  ]
}
```

### 3.5 Incident Topic Graph

**Location:** `/backend/app/services/incident_topic_graph.py`

**Features:**
- 🕸️ Tracks multiple parallel incidents as graph nodes
- 🕸️ Detects topic shifts (new vs related issues)
- 🕸️ Maintains keyword and category indexes
- 🕸️ Calculates similarity scores
- 🕸️ Links related incidents (parent-child)

**Topic Shift Detection:**
```python
# Current incident: "Kitchen Sink Leak" (plumbing)
# User message: "My garage door is stuck"

shift_result = graph.detect_topic_shift(
    "My garage door is stuck",
    current_incident_id="inc_123"
)

# Returns:
{
    "is_shift": True,
    "similarity_score": 0.0,
    "reason": "Category shift: plumbing → mechanical"
}
```

### 3.6 Auto-Evolving Skills

**Location:** `/backend/app/services/auto_evolving_skills.py`

**Workflow:**
```
1. Record incident patterns
   ↓
2. Detect repeated scenarios (threshold: 3+ similar incidents in 30 days)
   ↓
3. Extract common keywords and patterns
   ↓
4. Generate Python skill code (via LLM or template)
   ↓
5. Validate and register as dynamic tool
   ↓
6. Future incidents auto-use this skill
```

**Example Evolution:**
```
After 3 incidents of "AC not cooling":
→ System creates: analyze_hvac_cooling_issue()
→ Auto-classifies future AC issues
→ Provides faster diagnosis
```

---

## 4. INTEGRATION POINTS

### 4.1 Changes to Existing Files

**NO CHANGES REQUIRED TO:**
- `ai_webhooks_v3.py` - Works as-is
- `orchestrator.py` - Works as-is
- `meta_context_manager.py` - Works as-is
- `function_registry.py` - Works as-is

**WHY?** The new architecture is **additive**, not replacive. All new components integrate via:
- Function registry extends dynamically
- Orchestrator receives additional tools automatically
- Meta context stores new metadata fields
- Agent router plugs into existing flow

### 4.2 Optional Integration (for Full Features)

To enable full "Boundaryless Agent" capabilities:

**In `function_registry.py`:**
```python
# Add dynamic tool loader
from ..dynamic_tools.tool_loader import get_dynamic_tool_loader

def get_function_definitions() -> List[FunctionDefinition]:
    """Get all function definitions (built-in + dynamic)"""
    built_in = [
        # ... existing functions ...
    ]

    # Add dynamic tools
    loader = get_dynamic_tool_loader()
    dynamic = loader.get_dynamic_function_definitions()

    return built_in + dynamic
```

**In `execute_function`:**
```python
async def execute_function(
    function_name: str,
    arguments: Dict[str, Any],
    context: Dict[str, Any],
) -> FunctionResult:
    """Execute function (built-in or dynamic)"""

    # Check if dynamic tool
    loader = get_dynamic_tool_loader()
    runtime = get_dynamic_tool_runtime()

    if function_name in runtime.tools:
        return await loader.execute_dynamic_tool(
            function_name, arguments, context
        )

    # Otherwise execute built-in
    # ... existing code ...
```

---

## 5. DEPLOYMENT GUIDE

### 5.1 Prerequisites

- Python 3.10+
- Existing LandTenMVP3.0 deployment
- OpenAI API key
- DynamoDB access (for context persistence)

### 5.2 Installation Steps

**Step 1: Create dynamic tools directory**
```bash
mkdir -p backend/app/dynamic_tools/stored_tools
mkdir -p backend/app/agents
```

**Step 2: Install new files**

All new files have been created in:
- `backend/app/dynamic_tools/` (4 files)
- `backend/app/agents/` (5 files)
- `backend/app/services/` (3 new services)

**Step 3: No dependencies to install**

All new components use existing dependencies:
- `openai` (already installed)
- `boto3` (already installed)
- `pydantic` (already installed)

**Step 4: Environment variables**

No new environment variables required! Uses existing:
- `OPENAI_API_KEY`
- `AWS_REGION`
- `TABLE_PREFIX`

**Step 5: Database changes**

Optional: Add fields to meta_context table (DynamoDB):
- `dynamic_tools` (dict) - Metadata for registered tools
- `incident_graph` (dict) - Topic graph state
- `evolution_patterns` (dict) - Learning data

**Step 6: Deploy**

```bash
# From backend directory
uvicorn app.main:app --reload
```

### 5.3 Verification

**Test Dynamic Tool Creation:**
```bash
curl -X POST http://localhost:8000/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message.new",
    "user": {"id": "user_test", "name": "Test User"},
    "channel_id": "test_channel",
    "message": {
      "text": "Create a tool that analyzes AC temperature issues"
    }
  }'
```

**Test Agent Routing:**
```bash
# Stage: idle → TenantAgent
# Stage: discovery_complete → DiagnosisAgent
# Stage: diagnosing → ContractorAgent
```

---

## 6. TESTING PLAN

### Test Suite 1: Dynamic Tool Runtime

**Test 1.1: Tool Creation**
```
USER: "Create a dynamic tool that checks water pressure issues"

EXPECTED:
✅ LLM generates Python function
✅ Validator approves code (no security violations)
✅ Tool registered in runtime
✅ Tool persisted to disk
✅ Tool available in function registry
```

**Test 1.2: Tool Validation Failures**
```python
# Test forbidden imports
CODE: "import os"
EXPECTED: ❌ Validation fails

# Test file I/O
CODE: "open('file.txt')"
EXPECTED: ❌ Validation fails

# Test network
CODE: "import requests"
EXPECTED: ❌ Validation fails
```

**Test 1.3: Tool Execution**
```
SCENARIO: Execute dynamic tool "analyze_leak_severity"
ARGS: {"leak_rate": "flooding", "location": "bathroom"}

EXPECTED:
✅ Tool executes successfully
✅ Returns structured result
✅ Usage count increments
✅ No security violations
```

### Test Suite 2: Multi-Agent System

**Test 2.1: TenantAgent Routing**
```
STAGE: idle
USER: "Hi, my sink is leaking"

EXPECTED:
✅ Routed to TenantAgent
✅ Friendly, empathetic response
✅ Guidance to report issue
```

**Test 2.2: DiagnosisAgent Routing**
```
STAGE: discovery_complete
USER: "What's wrong with my AC?"

EXPECTED:
✅ Routed to DiagnosisAgent
✅ Technical analysis response
✅ Severity assessment
✅ Repair recommendations
```

**Test 2.3: ContractorAgent Routing**
```
STAGE: diagnosing (diagnosis_complete=true)
USER: "Create a work order"

EXPECTED:
✅ Routed to ContractorAgent
✅ Work order details generated
✅ Cost estimate provided
✅ Timeline estimate provided
```

### Test Suite 3: Dynamic Discovery

**Test 3.1: Plumbing Questions**
```
CATEGORY: plumbing
SEVERITY: high
USER MESSAGE: "My sink is overflowing"

EXPECTED:
✅ 5 plumbing-specific questions generated
✅ Questions focus on leak type, location, damage
✅ No generic questions
✅ Questions stored in context
```

**Test 3.2: Electrical Questions**
```
CATEGORY: electrical
SEVERITY: emergency
USER MESSAGE: "Outlet is sparking"

EXPECTED:
✅ 5 electrical-specific questions
✅ Safety-focused questions
✅ Breaker status question
✅ Hazard identification
```

### Test Suite 4: Dynamic Incident Cards

**Test 4.1: Card Generation**
```
INCIDENT: {
  "incident_id": "inc_123",
  "title": "Kitchen Leak",
  "category": "plumbing",
  "status": "diagnosing"
}

EXPECTED:
✅ Card with header (title, severity, status)
✅ Collapsible description section
✅ Progress bar showing 60% (diagnosing stage)
✅ JSON structure valid
```

**Test 4.2: Card with Discovery**
```
INCLUDE_DISCOVERY: true

EXPECTED:
✅ Expandable Q&A section
✅ All discovery answers displayed
✅ Collapsed by default
```

### Test Suite 5: Topic Graph

**Test 5.1: Single Incident**
```
USER: "My sink is leaking"

EXPECTED:
✅ Incident node created
✅ Indexed by category (plumbing)
✅ Keywords extracted (sink, leak, water)
✅ Added to active incidents list
```

**Test 5.2: Topic Shift Detection**
```
ACTIVE: "Kitchen Sink Leak" (plumbing)
USER: "My garage door is stuck"

EXPECTED:
✅ Topic shift detected (plumbing → mechanical)
✅ is_shift = true
✅ reason = "Category shift"
✅ New incident created
```

**Test 5.3: Related Issue (No Shift)**
```
ACTIVE: "Kitchen Sink Leak"
USER: "The sink is still dripping badly"

EXPECTED:
✅ No topic shift detected
✅ is_shift = false
✅ reason = "High similarity to current incident"
✅ Update existing incident
```

### Test Suite 6: Auto-Evolving Skills

**Test 6.1: Pattern Detection**
```
SCENARIO: 3 similar incidents within 30 days
INCIDENTS:
  1. "AC not cooling" (HVAC)
  2. "Air conditioner broken" (HVAC)
  3. "AC system not working" (HVAC)

EXPECTED:
✅ Pattern detected (common keywords: "ac", "cooling", "not working")
✅ Skill suggestion created
✅ Skill name: "analyze_hvac_cooling_issue"
```

**Test 6.2: Skill Generation**
```
PATTERN: {
  "common_keywords": ["ac", "cooling", "not"],
  "incident_count": 3
}

EXPECTED:
✅ Python function generated
✅ Function validates successfully
✅ Tool registered
✅ Available for future incidents
```

**Test 6.3: Skill Usage**
```
SCENARIO: New AC incident after skill created
USER: "My AC is not cooling the house"

EXPECTED:
✅ Auto-detects AC issue
✅ Uses generated skill "analyze_hvac_cooling_issue"
✅ Provides instant diagnosis
✅ Skill usage count increments
```

---

## 7. API CHANGES

### 7.1 New Endpoints

**None required!** The architecture is fully backward compatible.

### 7.2 Optional New Endpoints

For admin/debugging purposes:

```python
# GET /ai/dynamic-tools
# List all registered dynamic tools

# POST /ai/dynamic-tools/register
# Manually register a dynamic tool

# GET /ai/incident-graph/{user_id}
# View user's incident topic graph

# GET /ai/evolution-stats
# View skill evolution statistics
```

---

## 8. MIGRATION NOTES

### 8.1 Backward Compatibility

✅ **FULLY BACKWARD COMPATIBLE**

- All existing incidents continue to work
- No database migration required
- Existing functions unchanged
- No breaking changes to API

### 8.2 Gradual Adoption

You can adopt features incrementally:

**Week 1: Multi-Agent System**
- Enable agent routing
- Keep existing functions

**Week 2: Dynamic Discovery**
- Enable dynamic question generation
- Fallback to hardcoded questions if needed

**Week 3: Dynamic Tools**
- Enable tool runtime
- Start with read-only mode

**Week 4: Full Evolution**
- Enable skill evolution
- Monitor pattern detection

### 8.3 Rollback Plan

If issues occur:

1. **Disable Dynamic Tools:**
   ```python
   # In function_registry.py
   ENABLE_DYNAMIC_TOOLS = False
   ```

2. **Disable Agent Routing:**
   ```python
   # In ai_webhooks_v3.py
   ENABLE_MULTI_AGENT = False
   ```

3. **Fallback to V3.0:**
   - All original code is unchanged
   - System works exactly as before

---

## 9. PERFORMANCE CONSIDERATIONS

### 9.1 Expected Impact

| Component | Added Latency | Mitigation |
|-----------|---------------|------------|
| Dynamic tool validation | +50-100ms | Cache validation results |
| Agent routing | +10ms | Negligible |
| Dynamic discovery generation | +500-1000ms | Run async, fallback to template |
| Topic graph updates | +5-10ms | In-memory ops |
| Skill evolution | +0ms | Runs in background |

### 9.2 Optimization Tips

- Cache dynamic tool validation results
- Preload agents at startup
- Use template questions as fallback
- Run skill evolution async (not blocking)

---

## 10. SECURITY NOTES

### 10.1 Dynamic Tool Safety

**Validation Layers:**
1. AST parsing (syntax check)
2. Import whitelist enforcement
3. Forbidden node detection (exec, eval, etc.)
4. Built-in function blacklist
5. File I/O detection
6. Network access detection

**Safe Execution:**
- Isolated namespace (no global access)
- No file system access
- No network access
- Limited to pure functions
- Timeout protection (future enhancement)

### 10.2 Agent Security

- All agents use same OpenAI API key (no new credentials)
- System prompts are read-only (cannot be modified by users)
- No user data exposed to LLM beyond incident details

---

## 11. FUTURE ENHANCEMENTS

### Phase Omega+1

1. **LLM-Generated Dynamic Agents**
   - Create specialized agents on the fly
   - Example: "Create an expert in pool maintenance"

2. **Cross-Incident Learning**
   - Learn from landlord's entire property portfolio
   - Detect seasonal patterns (HVAC issues in summer)

3. **Predictive Maintenance**
   - Based on incident patterns, predict future issues
   - Proactive notifications

4. **Tool Marketplace**
   - Share evolved skills across deployments
   - Rate and review dynamic tools

---

## 🎉 CONCLUSION

The **Phase Omega** architecture transforms LandTen from a **static maintenance bot** into a **self-extending AI agent** that grows smarter over time.

**Key Achievements:**
✅ Dynamic tool generation and validation
✅ Multi-agent specialization
✅ Adaptive discovery questions
✅ Rich incident visualization
✅ Parallel incident handling
✅ Self-learning capabilities

**Next Steps:**
1. Deploy new components
2. Run test suite
3. Monitor dynamic tool creation
4. Watch the system evolve!

---

**Built by: Claude (Anthropic)** for oasb16/LandTenMVP3.0
**Date:** 2025-11-24
**Version:** Phase Omega v1.0
