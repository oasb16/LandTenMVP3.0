from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class Incident(BaseModel):
    id: str
    tenant_id: str
    description: str
    status: str
    created_at: Optional[str] = None

@router.post("/incident/create")
def create_incident(incident: Incident):
    # TODO: Log to DB/JSON
    return {"status": "created", "incident": incident}

@router.get("/incident/list/{tenant_id}")
def list_incidents(tenant_id: str):
    # TODO: Fetch from DB/JSON
    return {"tenant_id": tenant_id, "incidents": []}
