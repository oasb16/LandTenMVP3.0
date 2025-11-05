# SMART_AUTOMATION_PIPELINE

This document describes the end-to-end enhanced automation added to PropertyAI.

## Flow (high-level)

message -> webhook -> ai_analysis -> decision -> discovery -> incident -> work order -> bids -> assignment -> metrics

## Key additions

- ai_analysis: each incoming message is analyzed for category, severity, urgency, and next_action. Logged under [ai-analysis].
- channel_state.metadata enriched with: urgency_level, category, priority_score, assigned_contractor, tenant_id, landlord_id, mttr_target_hours, status_metric_flags.
- Incidents persisted with: incident_id, category, urgency, assigned_contractor, mttr_target_hours, status. Logged under [incident-flow].
- Work orders created via create_work_order and recorded under [workorder-flow].
- MTTR events recorded in Dynamo table `mttr_events`. Logged under [sla-metrics].
- AI feedback saved to `ai_training_feedback` via record_ai_feedback.

## Data schema examples

channel_state.metadata:
- timestamp: epoch
- persona: tenant
- urgency_level: immediate|urgent|routine
- category: plumbing|electrical|hvac|finance
- priority_score: float
- assigned_contractor: string
- tenant_id: string
- landlord_id: string
- mttr_target_hours: int
- status_metric_flags: {late: bool, resolved: bool, sla_violated: bool}

incident object (example):
{
  "incident_id": "INC-1699090000",
  "thread_id": "messaging:channel-1",
  "tenant_email": "tenant@example.com",
  "tenant_id": "user-123",
  "landlord_id": "landlord-1",
  "category": "plumbing",
  "severity": "high",
  "urgency": "immediate",
  "summary": "Kitchen sink leaking",
  "created_at": "2025-11-04T12:00:00Z",
  "mttr_target_hours": 8,
  "assigned_contractor": "RapidFix",
  "status": "detected",
}

## Example log lines

[ai-analysis] {"category": "plumbing", "severity": "high", "urgency": "immediate", "next_action": "create_incident"}
[discovery] Starting new discovery flow ...
[incident-flow] 💾 Persisted incident INC-... into channel data
[workorder-flow] ✅ Created work order JOB-... for incident INC-...
[sla-metrics] {"channel_id": "messaging:ch1", "incident_id": "INC-...", "priority_score": 0.75, "mttr_target_hours": 8}

## Next steps and improvements

- Implement an analytics pipeline to compute MTTR and fill_rate aggregates efficiently (e.g., via Lambda + scheduled queries).
- Add unit tests and integration tests for SLA breach logic.
- Expand AI feedback loop to continuously retrain classification models based on `ai_training_feedback`.

