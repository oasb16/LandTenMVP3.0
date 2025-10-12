from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class Job(BaseModel):
    id: str
    incident_id: str
    contractor_id: str
    status: str
    scheduled_time: Optional[str] = None

@router.post("/job/create")
def create_job(job: Job):
    # TODO: Log to DB/JSON
    return {"status": "created", "job": job}

@router.get("/job/list/{contractor_id}")
def list_jobs(contractor_id: str):
    # TODO: Fetch from DB/JSON
    return {"contractor_id": contractor_id, "jobs": []}
