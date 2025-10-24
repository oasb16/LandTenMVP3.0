from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.deps.auth import verify_firebase_token
from app.repos.job_repo import JobRepo
from datetime import datetime, timezone

router = APIRouter()

class Job(BaseModel):
    id: str
    incident_id: str
    contractor_id: str
    status: str
    scheduled_time: Optional[str] = None
_IN_MEMORY_JOBS: List[dict] = []


@router.post("/job/create")
def create_job(job: Job, token: str = Depends(verify_firebase_token)):
    payload = job.model_dump()
    if not payload.get("scheduled_time"):
        payload["scheduled_time"] = datetime.now(timezone.utc).isoformat()
    try:
        JobRepo().create_job(payload)
        return {"status": "created", "job": payload}
    except Exception:
        _IN_MEMORY_JOBS.append(payload)
        return {
            "status": "created",
            "job": payload,
            "warning": "Dynamo unavailable; stored in-memory",
        }


@router.get("/job/list/{contractor_id}")
def list_jobs(contractor_id: str, token: str = Depends(verify_firebase_token)):
    try:
        items = JobRepo().list_jobs(contractor_id)
        return {"contractor_id": contractor_id, "jobs": items}
    except Exception:
        items = [j for j in _IN_MEMORY_JOBS if j.get("contractor_id") == contractor_id]
        return {
            "contractor_id": contractor_id,
            "jobs": items,
            "warning": "Dynamo unavailable; returning in-memory jobs",
        }
