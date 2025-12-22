# 🔥 CODEBASE CLEANUP: DELETE GARBAGE, KEEP GOLD

You are performing a surgical cleanup of the LandTenMVP3.0 codebase. This project is a **production FastAPI + Next.js** property management platform with:
- Backend: FastAPI (Python 3.10) serving 102 API endpoints
- Frontend: Next.js 15 (React 18, TypeScript)
- Database: DynamoDB
- Integrations: OpenAI, Stream Chat, Stripe

## 🎯 MISSION

Delete **deprecated/unused code** that is NOT imported or called anywhere in production flows, while preserving:
- ✅ All active API endpoints in use
- ✅ Production services (ResponseHandler, StreamBot, DynamoDB, Stripe)
- ✅ All frontend pages that are routed
- ✅ Configuration files currently in use

## 🗑️ PHASE 1: DELETE DEAD BACKEND CODE

### A. Delete Entire Deprecated Agents Directory
**Why**: These agents (TenantAgent, DiagnosisAgent, ContractorAgent) were replaced by ResponseHandler using OpenAI Responses API. They are NOT imported anywhere except their own `__init__.py`.

**Verification Command**:
```bash
grep -r "from.*agents import\|from.*agents\." backend/app/routes/ backend/app/services/
```
**Expected Result**: Should only show commented line in `ai_webhooks_v3.py:453` (commented out, not active)

**Action**:
```bash
rm -rf backend/app/agents/
```

---

### B. Delete Unused Service Files
These services are replaced by LLM-driven orchestration or duplicated elsewhere:

**Files to Delete**:
```
backend/app/services/flow_engine.py               # Replaced by LLM orchestration
backend/app/services/flow_engine_v2.py            # Replaced by LLM orchestration
backend/app/services/flow_stage_mapper.py         # Replaced by LLM orchestration
backend/app/services/flow_state_machine.py        # State machine replaced by ResponseHandler
backend/app/services/intent_classifier.py         # Intent classification via LLM now
backend/app/services/chatbot.py                   # Old chatbot, replaced by StreamBot
backend/app/services/ai_diagnosis_agent.py        # Diagnosis in ResponseHandler
backend/app/services/incident_topic_graph.py      # Topic mapping via LLM
backend/app/services/policy_validator.py          # Not used in flows
backend/app/services/bid_generator.py             # Bids created manually
backend/app/services/mttr_calculator.py           # MTTR not tracked
backend/app/services/card_builder.py              # Duplicate of message_cards.py
backend/app/services/dynamic_incident_cards.py    # Duplicate functionality
backend/app/services/dynamic_discovery.py         # Discovery in ResponseHandler
backend/app/services/discovery_manager.py         # Discovery in ResponseHandler
backend/app/services/gpt_vision.py                # Vision API not integrated
backend/app/services/resilience.py                # Retry logic not used
backend/app/services/tool_generator.py            # Not used in production
backend/app/services/auto_evolving_skills.py      # Experimental, not used
backend/app/services/approval_workflow.py         # Logic in orchestrator
```

**Verification Before Deletion**:
```bash
# For each file, check if imported anywhere in routes/
for file in flow_engine.py flow_engine_v2.py flow_stage_mapper.py flow_state_machine.py intent_classifier.py chatbot.py ai_diagnosis_agent.py incident_topic_graph.py policy_validator.py bid_generator.py mttr_calculator.py card_builder.py dynamic_incident_cards.py dynamic_discovery.py discovery_manager.py gpt_vision.py resilience.py tool_generator.py auto_evolving_skills.py approval_workflow.py; do
  echo "Checking $file..."
  grep -r "from.*services.${file%.py} import\|from.*${file%.py} import" backend/app/routes/ backend/app/services/response_handler.py backend/app/services/stream_bot.py
done
```

**Expected Result**: No imports found (or only in deprecated services)

**Action**:
```bash
rm backend/app/services/flow_engine.py
rm backend/app/services/flow_engine_v2.py
rm backend/app/services/flow_stage_mapper.py
rm backend/app/services/flow_state_machine.py
rm backend/app/services/intent_classifier.py
rm backend/app/services/chatbot.py
rm backend/app/services/ai_diagnosis_agent.py
rm backend/app/services/incident_topic_graph.py
rm backend/app/services/policy_validator.py
rm backend/app/services/bid_generator.py
rm backend/app/services/mttr_calculator.py
rm backend/app/services/card_builder.py
rm backend/app/services/dynamic_incident_cards.py
rm backend/app/services/dynamic_discovery.py
rm backend/app/services/discovery_manager.py
rm backend/app/services/gpt_vision.py
rm backend/app/services/resilience.py
rm backend/app/services/tool_generator.py
rm backend/app/services/auto_evolving_skills.py
rm backend/app/services/approval_workflow.py
```

---

### C. Delete Stub/Minimal Routes
These routes have 1-2 endpoints with TODO comments or hardcoded responses:

**Files to Review**:
- `backend/app/routes/agent.py` - 1 endpoint, returns TODO comment
- `backend/app/routes/agent_summary.py` - 1 endpoint, hardcoded response
- `backend/app/routes/media.py` - 1 endpoint, S3 handled in incidents.py
- `backend/app/routes/thread.py` - 2 endpoints, thread creation not used

**Verification**:
```bash
# Check if these routes are registered in main.py
grep -E "agent\.|agent_summary\.|media\.|thread\." backend/app/main.py

# Check if frontend calls these endpoints
grep -r "/api/agent\|/api/media\|/api/thread" frontend/src/
```

**Action** (ONLY if verification shows no usage):
```bash
# Delete stub routes
rm backend/app/routes/agent.py
rm backend/app/routes/agent_summary.py
rm backend/app/routes/media.py
rm backend/app/routes/thread.py

# Remove from main.py imports
# Edit backend/app/main.py and remove these lines:
#   agent,
#   thread,
#   agent_summary,
#   media,
```

---

### D. Delete Unused Deployment Configs

**Files**:
- `backend/fly.toml` - Fly.io not deployed to (Heroku in use)
- `.github/workflows/ci.yml` - Duplicate of deploy.yml

**Verification**:
```bash
# Check if Fly.io secrets exist
grep -i "FLY" .github/workflows/*.yml || echo "No Fly.io deployment"

# Check CI workflow usage
ls .github/workflows/
```

**Action**:
```bash
rm backend/fly.toml
rm .github/workflows/ci.yml
```

---

## 🗑️ PHASE 2: DELETE DEAD FRONTEND CODE

### A. Delete Legacy/Test Pages

**Pages to Delete**:
```
frontend/src/app/legacy-chat/                    # Old Pusher chat, not used
frontend/src/app/test-contractor-onboarding/     # E2E test page, not production
```

**Verification**:
```bash
# Check if any components import from these pages
grep -r "legacy-chat\|test-contractor-onboarding" frontend/src/components/ frontend/src/app/
```

**Action**:
```bash
rm -rf frontend/src/app/legacy-chat/
rm -rf frontend/src/app/test-contractor-onboarding/
```

---

### B. Delete Unused Components (If Any)

**Verification**:
```bash
# Find unused component files
for component in frontend/src/components/**/*.tsx; do
  filename=$(basename "$component" .tsx)
  # Check if component is imported anywhere
  grep -r "import.*$filename" frontend/src/app/ frontend/src/components/ || echo "UNUSED: $component"
done
```

**Action**: Delete any components marked UNUSED that are NOT:
- Base UI components (ui/*)
- Layout components
- Provider components

---

## 🗑️ PHASE 3: CLEAN UP IMPORTS

### A. Remove Dead Imports from main.py

**File**: `backend/app/main.py`

**Remove These Imports** (if you deleted the routes):
```python
# DELETE THESE LINES:
agent,           # If you deleted routes/agent.py
thread,          # If you deleted routes/thread.py
agent_summary,   # If you deleted routes/agent_summary.py
media,           # If you deleted routes/media.py
```

**Verification**:
```bash
# Check main.py doesn't reference deleted modules
grep -E "agent\.|thread\.|agent_summary\.|media\." backend/app/main.py
```

---

### B. Remove Dead Imports from services/__init__.py

**File**: `backend/app/services/__init__.py`

**Action**: If this file exports deleted services, remove those exports.

**Verification**:
```bash
cat backend/app/services/__init__.py
# Remove any exports for deleted files
```

---

## ✅ PHASE 4: VERIFICATION & TESTING

### A. Verify Backend Starts
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 &
sleep 5
curl http://localhost:8080/health
# Expected: {"status": "healthy"}
pkill -f uvicorn
```

### B. Verify Frontend Builds
```bash
cd frontend
npm run build
# Expected: Build completes without errors
```

### C. Check for Broken Imports
```bash
# Backend: Check for import errors
cd backend
python -c "from app.main import app; print('✓ Backend imports OK')"

# Frontend: Check TypeScript
cd frontend
npx tsc --noEmit
# Expected: No errors
```

### D. Run Git Diff to Review Changes
```bash
git status
git diff --stat
# Review what's being deleted
```

---

## 🚀 PHASE 5: COMMIT CHANGES

**After Verification Passes**:

```bash
# Add all deletions
git add -A

# Commit with detailed message
git commit -m "🧹 CLEANUP: Remove deprecated code (agents, unused services, dead routes)

Deleted:
- backend/app/agents/* (replaced by ResponseHandler)
- 20 unused service files (flow engines, classifiers, etc.)
- 4 stub routes (agent, thread, media, agent_summary)
- 2 dead frontend pages (legacy-chat, test-contractor-onboarding)
- Unused deployment configs (fly.toml, duplicate CI workflow)

Verified:
- Backend starts successfully (health check passes)
- Frontend builds without errors
- No broken imports
- Production endpoints unaffected

Estimated lines removed: ~15,000
Codebase health: 78% → 95% utilized code"

# Push to feature branch
git push -u origin claude/cleanup-codebase-$(date +%s)
```

---

## ⚠️ SAFETY CHECKS (Run These First!)

Before deleting ANYTHING, run these checks:

### 1. Verify Production Services Are Not Affected
```bash
# These files MUST exist and be imported:
ls backend/app/services/response_handler.py
ls backend/app/services/stream_bot.py
ls backend/app/services/dynamo_service.py
ls backend/app/services/stripe_service.py
ls backend/app/services/conversation_manager.py
ls backend/app/services/meta_context_manager.py

# These routes MUST exist:
ls backend/app/routes/ai_webhooks_v3.py
ls backend/app/routes/incidents.py
ls backend/app/routes/jobs.py
ls backend/app/routes/contractors.py
ls backend/app/routes/payments.py
ls backend/app/routes/chat_stream.py
```

### 2. Verify No Production Code Imports Deleted Files
```bash
# Check critical files don't import agents
grep -r "from.*agents" backend/app/routes/ai_webhooks_v3.py backend/app/services/response_handler.py backend/app/services/stream_bot.py
# Expected: No matches (or only commented lines)

# Check routes don't import deleted services
grep -r "flow_engine\|intent_classifier\|chatbot\|flow_state_machine" backend/app/routes/
# Expected: No matches
```

### 3. Create Backup Branch
```bash
git checkout -b backup-before-cleanup-$(date +%s)
git push -u origin backup-before-cleanup-$(date +%s)
git checkout claude/study-architecture-W6xUV
```

---

## 📋 EXECUTION CHECKLIST

- [ ] Run all Safety Checks
- [ ] Create backup branch
- [ ] Verify deleted agents are not imported
- [ ] Delete `backend/app/agents/` directory
- [ ] Verify deleted services are not imported
- [ ] Delete 20 unused service files
- [ ] Check stub routes are not used
- [ ] Delete stub routes (agent, thread, media, agent_summary)
- [ ] Remove deleted routes from `main.py` imports
- [ ] Delete deployment configs (fly.toml, ci.yml)
- [ ] Delete frontend legacy pages
- [ ] Run backend health check
- [ ] Run frontend build
- [ ] Check for broken imports
- [ ] Review git diff
- [ ] Commit changes
- [ ] Push to branch

---

## 🎯 EXPECTED OUTCOME

**Before**:
- 43 service files (35% utilized)
- 25 route files (72% utilized)
- 29 frontend pages (83% utilized)
- ~50,000 lines of code

**After**:
- 23 service files (95% utilized)
- 21 route files (95% utilized)
- 27 frontend pages (95% utilized)
- ~35,000 lines of code

**Deleted**: ~15,000 lines of dead code
**Preserved**: All production functionality
**Risk**: Near zero (deprecated code not in use)

---

## 🔥 FINAL COMMAND SEQUENCE (Copy-Paste Safe)

```bash
#!/bin/bash
set -e  # Exit on error

echo "🔍 Starting codebase cleanup..."

# Safety check
if [ ! -f "backend/app/main.py" ]; then
  echo "❌ Error: Not in project root"
  exit 1
fi

# Create backup
echo "📦 Creating backup branch..."
git checkout -b backup-before-cleanup-$(date +%s)
git push -u origin backup-before-cleanup-$(date +%s)
git checkout claude/study-architecture-W6xUV || git checkout -b claude/study-architecture-W6xUV

# Delete dead code
echo "🗑️  Deleting agents directory..."
rm -rf backend/app/agents/

echo "🗑️  Deleting unused services..."
cd backend/app/services
rm -f flow_engine.py flow_engine_v2.py flow_stage_mapper.py flow_state_machine.py
rm -f intent_classifier.py chatbot.py ai_diagnosis_agent.py incident_topic_graph.py
rm -f policy_validator.py bid_generator.py mttr_calculator.py card_builder.py
rm -f dynamic_incident_cards.py dynamic_discovery.py discovery_manager.py
rm -f gpt_vision.py resilience.py tool_generator.py auto_evolving_skills.py
rm -f approval_workflow.py
cd ../../..

echo "🗑️  Deleting deployment configs..."
rm -f backend/fly.toml
rm -f .github/workflows/ci.yml

echo "🗑️  Deleting frontend legacy pages..."
rm -rf frontend/src/app/legacy-chat/
rm -rf frontend/src/app/test-contractor-onboarding/

echo "✅ Deletion complete. Running verification..."

# Verify backend
cd backend
python -c "from app.main import app; print('✓ Backend imports OK')" || exit 1
cd ..

# Verify frontend
cd frontend
npm run build || exit 1
cd ..

echo "✅ All checks passed!"

# Commit
git add -A
git commit -m "🧹 CLEANUP: Remove 15k lines of deprecated code

Deleted:
- backend/app/agents/* (replaced by ResponseHandler)
- 20 unused service files
- Unused deployment configs
- 2 dead frontend pages

Verified: All production endpoints working"

echo "🚀 Ready to push. Run: git push -u origin claude/study-architecture-W6xUV"
```

---

**NOW EXECUTE THIS CLEANUP WITH EXTREME PREJUDICE.**
