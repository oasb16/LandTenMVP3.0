# 🚀 Deployment Guide - Rate-Limit Fix & Async Architecture

## Overview

This deployment fixes critical 429 rate-limit handling that was causing H12 timeouts (30s+ webhook blocks) in production.

### What Changed:
- ✅ **Fire-and-forget webhook pattern** - Webhooks now return in <200ms
- ✅ **Centralized rate-limit management** - Pre-flight RPM/TPM checks
- ✅ **Async task queue** - Background LLM processing
- ✅ **Custom OpenAI wrapper** - Non-blocking retries (max 10s)
- ✅ **Load shedding** - Graceful degradation under high load
- ✅ **Health monitoring** - New endpoints for observability

---

## Files Changed

### New Files Created:
1. `backend/app/services/rate_limit_manager.py` - Centralized rate-limit tracking
2. `backend/app/services/task_queue.py` - Async background task processing
3. `backend/app/services/openai_wrapper.py` - Rate-limit-aware OpenAI client
4. `ARCHITECTURE_RATE_LIMIT_FIX.md` - Complete architecture documentation
5. `DEPLOYMENT_GUIDE_RATE_LIMIT_FIX.md` - This file

### Files Modified:
1. `backend/app/routes/ai_webhooks_v3.py` - Fire-and-forget pattern + health endpoints
2. `backend/app/services/orchestrator.py` - Use OpenAI wrapper
3. `backend/app/agents/base_agent.py` - Use OpenAI wrapper
4. `backend/app/services/ai_service.py` - Async version with rate-limit awareness
5. `backend/app/functions/function_registry.py` - Use async AI service
6. `backend/app/main.py` - Start/stop task queue on app lifecycle

---

## Pre-Deployment Checklist

### 1. Review Code Changes
```bash
# Review all changes
git status
git diff

# Ensure all new files are staged
git add backend/app/services/rate_limit_manager.py
git add backend/app/services/task_queue.py
git add backend/app/services/openai_wrapper.py
```

### 2. Test Locally (Optional but Recommended)
```bash
# Start local server
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# In another terminal, test health endpoints
curl http://localhost:8080/ai/health
curl http://localhost:8080/ai/rate-limits
curl http://localhost:8080/ai/queue-status
```

### 3. Check Dependencies
```bash
# Ensure OpenAI library is installed
pip install openai

# No new dependencies required - everything uses existing packages
```

---

## Deployment Steps

### Step 1: Commit Changes
```bash
git add .
git commit -m "🔥 Fix critical 429 handling: async queue + rate-limit management

- Add fire-and-forget webhook pattern (returns <200ms)
- Implement centralized rate-limit manager (RPM/TPM tracking)
- Add async task queue for background LLM processing
- Replace OpenAI direct calls with rate-limit-aware wrapper
- Add load shedding for queue overflow
- Add health monitoring endpoints

Fixes: H12 timeouts from OpenAI 429 errors
Architecture: See ARCHITECTURE_RATE_LIMIT_FIX.md"
```

### Step 2: Push to Remote
```bash
# Push to feature branch
git push -u origin claude/fix-rate-limit-handling-01BqMev8exFo5Z2KGX8dQiG6

# Monitor for failures
# If push fails due to network, retry with exponential backoff
# (2s, 4s, 8s, 16s as specified in requirements)
```

### Step 3: Deploy to Heroku
```bash
# Push to main (or create PR first)
git push origin claude/fix-rate-limit-handling-01BqMev8exFo5Z2KGX8dQiG6:main

# OR if you need to deploy directly:
git push heroku claude/fix-rate-limit-handling-01BqMev8exFo5Z2KGX8dQiG6:main
```

### Step 4: Monitor Deployment
```bash
# Watch logs in real-time
heroku logs --tail --app=landten-mvp

# Look for these success indicators:
# [STARTUP] ✅ Task queue started
# [STARTUP] ✅ Backend Ready (V2 + V3 + Async Queue)
```

---

## Post-Deployment Verification

### 1. Health Check
```bash
# Check overall health
curl https://your-app.herokuapp.com/ai/health

# Expected response:
{
  "status": "healthy",  # or "warning" or "critical"
  "version": "3.0-async",
  "rate_limits": {
    "max_utilization_pct": 0.0,  # Should be low initially
    "models": { ... }
  },
  "queue": {
    "size": 0,  # Should start at 0
    "utilization_pct": 0.0,
    "workers": 5  # 5 workers running
  }
}
```

### 2. Rate Limit Monitoring
```bash
# Check rate-limit quotas
curl https://your-app.herokuapp.com/ai/rate-limits

# Expected response:
{
  "status": "ok",
  "quotas": {
    "gpt-4o-mini": {
      "rpm_used": 0,
      "rpm_limit": 500,
      "rpm_available": 500,
      "tpm_used": 0,
      "tpm_limit": 200000,
      "tpm_available": 200000,
      "utilization_pct": 0.0
    },
    "gpt-4o": { ... }
  }
}
```

### 3. Queue Status
```bash
# Check task queue
curl https://your-app.herokuapp.com/ai/queue-status

# Expected response:
{
  "status": "ok",
  "queue_size": 0,
  "max_size": 1000,
  "workers": 5,
  "running": true,
  "utilization_pct": 0.0,
  "stats": {
    "total_queued": 0,
    "total_processed": 0,
    "total_failed": 0,
    "total_shed": 0
  }
}
```

### 4. Test Webhook Response Time
```bash
# Send test message via Stream Chat
# OR use webhook test:
curl -X POST https://your-app.herokuapp.com/ai/stream-webhook \
  -H "Content-Type: application/json" \
  -H "x-signature: test" \
  -d '{
    "type": "message.new",
    "message": {
      "text": "test message",
      "id": "test-123"
    },
    "user": {
      "id": "test-user",
      "name": "Test User"
    },
    "channel_id": "test-channel"
  }'

# Expected:
# - Response time: <200ms (verify in Heroku logs)
# - Response: {"status": "queued", "message": "Processing in background"}
# - User sees "I'm working on your request..." message immediately
```

---

## Monitoring in Production

### Key Metrics to Watch

1. **Webhook Response Time**
   - Target: <200ms (always)
   - Alert if: >500ms

2. **Rate-Limit Utilization**
   - Target: <80%
   - Alert if: >90%
   - Check: `GET /ai/rate-limits`

3. **Queue Size**
   - Target: <500
   - Alert if: >800 (load shedding starts)
   - Check: `GET /ai/queue-status`

4. **Queue Processing Rate**
   - Monitor: `total_processed` / `total_queued`
   - Target: >95% success rate
   - Alert if: `total_failed` / `total_processed` > 5%

5. **Load Shedding Events**
   - Monitor: `total_shed`
   - Alert if: >10 per hour
   - Action: Scale up workers or reduce load

### Heroku Logs to Monitor

```bash
# Filter for key events
heroku logs --tail | grep -E "(Rate limit|Queue|429|H12)"

# Success indicators:
# ✅ Task queued for background processing
# ✅ OpenAI success: tokens=X, time=Xs

# Warning indicators:
# ⚠️ Queue approaching capacity
# ⚠️ Rate-limit fallback: gpt-4o → gpt-4o-mini

# Error indicators:
# ⛔ Rate limit PRE-FLIGHT BLOCK
# ⛔ Max retry time exceeded
# 🚨 Queue FULL - REJECTING task
```

---

## Troubleshooting

### Problem: High rate-limit utilization

**Symptoms:**
- `/ai/rate-limits` shows utilization > 90%
- Logs show "Rate limit PRE-FLIGHT BLOCK"

**Solutions:**
1. Check if orchestrator prompt is too large (reduce token usage)
2. Use gpt-4o-mini for agents instead of gpt-4o
3. Increase retry delay or reduce retry count
4. Contact OpenAI to increase rate limits

### Problem: Queue overload

**Symptoms:**
- `/ai/queue-status` shows size > 800
- Logs show "Queue FULL - REJECTING task"
- Users see "high volume" messages

**Solutions:**
1. Increase worker count in `task_queue.py` (default: 5)
2. Scale up Heroku dynos
3. Implement Redis-based queue for persistence
4. Add auto-scaling based on queue size

### Problem: Slow webhook responses

**Symptoms:**
- Webhook responses > 500ms
- Heroku logs show delays

**Solutions:**
1. Check if queue startup is blocking (should be async)
2. Verify Stream Bot connection is not blocking
3. Profile code with `time.time()` measurements
4. Check for synchronous I/O in webhook handler

### Problem: Workers not processing tasks

**Symptoms:**
- Queue size increasing
- `total_processed` not incrementing
- Worker logs missing

**Solutions:**
1. Check `/ai/queue-status` - verify `running: true`
2. Check Heroku logs for worker errors
3. Restart app: `heroku restart --app=landten-mvp`
4. Verify task_queue.start() was called on startup

---

## Rollback Plan

If issues occur in production:

### Option 1: Quick Rollback (Revert Git)
```bash
# Revert to previous commit
git revert HEAD
git push origin main

# OR force push previous version
git reset --hard <previous-commit-hash>
git push --force origin main
```

### Option 2: Disable Async Queue (Emergency)
```python
# In ai_webhooks_v3.py, temporarily bypass queue:
async def handle_new_message(payload):
    # Comment out queue logic, call background handler directly
    return await handle_new_message_background(payload)
```

### Option 3: Increase OpenAI Timeout
```python
# In openai_wrapper.py, increase MAX_TOTAL_RETRY_TIME:
MAX_TOTAL_RETRY_TIME = 25.0  # Increase from 10s
```

---

## Performance Expectations

### Before Fix:
- Webhook latency: 2000-30000ms (under 429 errors)
- Failure rate: 40% (H12 timeouts)
- User experience: Timeouts, no response

### After Fix:
- Webhook latency: <200ms (always)
- Failure rate: <1% (graceful degradation)
- User experience: Always get response (immediate or queued)

---

## Next Steps

1. **Monitor for 24 hours** - Watch metrics closely
2. **Tune parameters** - Adjust queue size, worker count based on load
3. **Consider Redis** - For persistent queue if needed
4. **Add alerting** - Set up monitoring alerts for key metrics
5. **Load testing** - Simulate high traffic to validate capacity

---

## Support

If issues arise:
1. Check Heroku logs: `heroku logs --tail`
2. Check health endpoint: `/ai/health`
3. Review architecture doc: `ARCHITECTURE_RATE_LIMIT_FIX.md`
4. Contact team for assistance

---

## End of Deployment Guide
