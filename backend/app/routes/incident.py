from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.deps.auth import verify_firebase_token
from app.repos.incident_repo import IncidentRepo
from datetime import datetime, timezone

router = APIRouter()

class Incident(BaseModel):
    id: str
    tenant_id: str
    description: str
    status: str
    created_at: Optional[str] = None
_IN_MEMORY_INCIDENTS: List[dict] = []


@router.post("/incident/create")
def create_incident(incident: Incident, token: str = Depends(verify_firebase_token)):
    payload = incident.model_dump()
    if not payload.get("created_at"):
        payload["created_at"] = datetime.now(timezone.utc).isoformat()
    try:
        IncidentRepo().log_incident(payload)
        return {"status": "created", "incident": payload}
    except Exception:
        _IN_MEMORY_INCIDENTS.append(payload)
        return {
            "status": "created",
            "incident": payload,
            "warning": "Dynamo unavailable; stored in-memory",
        }


@router.get("/incident/list/{tenant_id}")
def list_incidents(tenant_id: str, token: str = Depends(verify_firebase_token)):
    try:
        items = IncidentRepo().list_incidents(tenant_id)
        return {"tenant_id": tenant_id, "incidents": items}
    except Exception:
        items = [i for i in _IN_MEMORY_INCIDENTS if i.get("tenant_id") == tenant_id]
        return {
            "tenant_id": tenant_id,
            "incidents": items,
            "warning": "Dynamo unavailable; returning in-memory incidents",
        }
