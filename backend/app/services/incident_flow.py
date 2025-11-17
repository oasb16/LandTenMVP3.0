import os
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List, Optional

from ..repos.incident_repo import IncidentRepo
from .chatbot import agent_reply
from .dynamo_service import JobDB, save_channel_snapshot
from .context_manager import get_context_manager
import time


INCIDENT_THRESHOLD_LOW = float(os.getenv("INCIDENT_THRESHOLD_LOW", "200"))
INCIDENT_THRESHOLD_MEDIUM = float(os.getenv("INCIDENT_THRESHOLD_MEDIUM", "500"))
INCIDENT_THRESHOLD_HIGH = float(os.getenv("INCIDENT_THRESHOLD_HIGH", "999999"))


def classify_issue(summary: str) -> Tuple[str, str, str]:
    text = summary.lower()
    category = "plumbing"
    if "electrical" in text or "outlet" in text:
        category = "electrical"
    severity = "medium"
    urgency = "routine"
    keywords = {"flood": ("high", "immediate"), "gas": ("high", "immediate"), "leak": ("medium", "immediate")}
    for key, value in keywords.items():
        if key in text:
            severity, urgency = value
            break
    return category, severity, urgency


def diy_suggestions(category: str) -> List[str]:
    suggestions = {
        "plumbing": [
            "Tighten any visible fittings slightly with a wrench.",
            "Place a temporary fix and secure area.",
            "Cordone off the perimeter and check if issue persists.",
        ],
        "electrical": [
            "Turn off the breaker controlling the outlet.",
            "Inspect for scorch marks; do not touch exposed wires.",
        ],
    }
    return suggestions.get(category, ["Please gather photos or short videos to help diagnose."])


def create_incident_record(thread_id: str, tenant_email: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    repo = IncidentRepo()
    # Use UTC ISO timestamps for Dynamo
    now = datetime.utcnow().isoformat()
    incident_id = payload.get("incident_id") or f"INC-{int(datetime.utcnow().timestamp())}"
    item = {
        "user_id": thread_id,
        "incident_id": incident_id,
        "thread_id": thread_id,
        "tenant_email": tenant_email,
        "tenant_id": payload.get("tenant_id", tenant_email),
        "landlord_id": payload.get("landlord_id"),
        "category": payload.get("category"),
        "severity": payload.get("severity"),
        "urgency": payload.get("urgency"),
        "summary": payload.get("summary"),
        "diy_attempted": payload.get("diy_attempted", False),
        "diy_result": payload.get("diy_result"),
        "media": payload.get("media", []),
        "created_at": now,
        "first_response_at": payload.get("first_response_at"),
        "resolved_at": payload.get("resolved_at"),
        "mttr_target_hours": payload.get("mttr_target_hours", 8 if payload.get("urgency") == "immediate" else 48),
        "assigned_contractor": payload.get("assigned_contractor"),
        "status": payload.get("status", "detected"),
        "status_metric_flags": payload.get("status_metric_flags", {}),
    }
    try:
        repo.create_incident(item)
        # Validate persistence
        assert "incident_id" in item, "Incident must have an ID"
        print(f"[incident-flow] ✅ Incident persisted successfully: {incident_id}")
        return item
    except Exception as e:
        print(f"[error][incident-flow] Failed to create incident {incident_id}: {e}")
        raise


def create_work_order(incident: Dict[str, Any], title: str = None) -> Dict[str, Any]:
    """Create a work order (job) for a given incident and persist via JobDB.

    Returns the created job record.
    """
    job_id = f"JOB-{int(time.time())}"
    job_payload = {
        "job_id": job_id,
        "incident_id": incident.get("incident_id"),
        "property_id": incident.get("property_id"),
        "landlord_id": incident.get("landlord_id"),
        "title": title or f"Work order for {incident.get('summary')[:60]}",
        "category": incident.get("category"),
        "estimated_cost": incident.get("estimated_cost", ""),
        "urgency": incident.get("urgency", "routine"),
        "status": "created",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "channel_id": incident.get("thread_id"),
    }

    job = JobDB.create_job(job_payload)
    print(f"[workorder-flow] ✅ Created work order {job.get('job_id')} for incident {incident.get('incident_id')}")
    return job


def summarize_for_landlord(incident: Dict[str, Any]) -> str:
    return (
        f"Issue Summary:\n"
        f"- Category: {incident.get('category')}\n"
        f"- Severity: {incident.get('severity')}\n"
        f"- Urgency: {incident.get('urgency')}\n"
        f"- DIY Attempted: {incident.get('diy_attempted')}\n"
        f"- DIY Result: {incident.get('diy_result')}\n"
        f"- Description: {incident.get('summary')}\n"
        f"Incident ID: {incident.get('incident_id')}"
    )


def threshold_decision(estimate: float) -> str:
    if estimate <= INCIDENT_THRESHOLD_LOW:
        return "auto-approve"
    if estimate <= INCIDENT_THRESHOLD_MEDIUM:
        return "recommended-review"
    if estimate <= INCIDENT_THRESHOLD_HIGH:
        return "manual-approval"
    return "manual-approval"


def generate_contractor_bids(category: str) -> List[Dict[str, Any]]:
    base = 150 if category == "plumbing" else 220
    return [
        {"name": "RapidFix", "quote": base, "eta": "Next business day"},
        {"name": "Prime Contractors", "quote": base + 45, "eta": "48 hours"},
        {"name": "SafeHome Pros", "quote": base + 90, "eta": "Same week"},
    ]


def register_incident_from_card(
    incident_payload: Dict[str, Any],
    incident_response: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Unified helper to register an incident from a card payload.

    This function:
    1. Generates or extracts incident_id
    2. Creates the incident record in DynamoDB
    3. Returns the complete incident record with metadata

    Args:
        incident_payload: Payload containing incident details (user_id, category, severity, etc.)
        incident_response: Optional response from send_incident_card containing incident_id

    Returns:
        Complete incident record with incident_id

    Example:
        >>> incident_response = bot.send_incident_card(...)
        >>> record = register_incident_from_card(incident_payload, incident_response)
        >>> print(record["incident_id"])  # INC-123456789
    """
    # Extract or generate incident_id
    incident_id = None
    if incident_response:
        incident_id = incident_response.get("incident_id")
    if not incident_id:
        incident_id = incident_payload.get("incident_id")
    if not incident_id:
        incident_id = f"INC-{int(datetime.now(timezone.utc).timestamp())}"

    print(f"[incident-flow] 📋 Registering incident {incident_id}")

    # Create complete incident record
    record = create_incident_record(
        thread_id=incident_payload.get("thread_id", incident_payload.get("user_id", "unknown")),
        tenant_email=incident_payload.get("tenant_email", incident_payload.get("tenant_name", "unknown")),
        payload={
            "incident_id": incident_id,
            "category": incident_payload.get("category", "general"),
            "severity": incident_payload.get("severity", "medium"),
            "urgency": incident_payload.get("urgency", "routine"),
            "summary": incident_payload.get("summary", incident_payload.get("description", "")),
            "diy_attempted": incident_payload.get("diy_attempted", False),
            "diy_result": incident_payload.get("diy_result"),
            "media": incident_payload.get("media", []),
            "estimated_cost": incident_payload.get("estimated_cost"),
            "approval_threshold": incident_payload.get("approval_threshold"),
        },
    )

    print(f"[incident-flow] ✅ Incident {incident_id} registered and persisted")

    return record
