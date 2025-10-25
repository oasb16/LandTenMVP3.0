import os
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List

from app.repos.incident_repo import IncidentRepo
from app.services.chatbot import agent_reply


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
            "Place a bucket under the leak and turn off nearby valves.",
            "Dry the area and check if the leak persists.",
        ],
        "electrical": [
            "Turn off the breaker controlling the outlet.",
            "Inspect for scorch marks; do not touch exposed wires.",
        ],
    }
    return suggestions.get(category, ["Please gather photos or short videos to help diagnose."])


def create_incident_record(thread_id: str, tenant_email: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    repo = IncidentRepo()
    now = datetime.now(timezone.utc).isoformat()
    item = {
        "incident_id": payload.get("incident_id") or f"INC-{int(datetime.now().timestamp())}",
        "thread_id": thread_id,
        "tenant_email": tenant_email,
        "category": payload.get("category"),
        "severity": payload.get("severity"),
        "urgency": payload.get("urgency"),
        "summary": payload.get("summary"),
        "diy_attempted": payload.get("diy_attempted", False),
        "diy_result": payload.get("diy_result"),
        "media": payload.get("media", []),
        "created_at": now,
        "status": "pending",
    }
    repo.create_incident(item)
    return item


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
