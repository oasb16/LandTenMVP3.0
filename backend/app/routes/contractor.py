from uuid import uuid4
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.deps.auth import verify_firebase_token
from app.repos.contractor_repo import ContractorRepo
from app.repos.job_bid_repo import JobBidRepo
from app.repos.schedule_repo import ScheduleRepo

router = APIRouter()


class ContractorProfile(BaseModel):
    contractor_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    skills: List[str] = []
    documents: List[Dict[str, Any]] = []
    biography: Optional[str] = None


class AvailabilityEntry(BaseModel):
    contractor_id: str
    start: str
    end: str
    note: Optional[str] = None


@router.get("/contractor/profile/{contractor_id}")
def get_contractor_profile(contractor_id: str, token: str = Depends(verify_firebase_token)):
    item = ContractorRepo().get_profile(contractor_id)
    if not item:
        return {"contractor_id": contractor_id, "profile": None}
    return {"contractor_id": contractor_id, "profile": item}


@router.post("/contractor/profile")
def upsert_contractor_profile(profile: ContractorProfile, token: str = Depends(verify_firebase_token)):
    ContractorRepo().upsert_profile(profile.model_dump())
    return {"status": "saved", "profile": profile}


@router.get("/contractor/bids/{contractor_id}")
def list_contractor_bids(contractor_id: str, token: str = Depends(verify_firebase_token)):
    bids = JobBidRepo().list_for_contractor(contractor_id)
    return {"contractor_id": contractor_id, "bids": bids}


@router.post("/contractor/availability")
def add_availability(entry: AvailabilityEntry, token: str = Depends(verify_firebase_token)):
    schedule_id = f"slot-{uuid4().hex[:8]}"
    ScheduleRepo().add_entry(
        entry.contractor_id,
        schedule_id,
        {"start": entry.start, "end": entry.end, "note": entry.note or ""},
    )
    return {"status": "saved", "schedule_id": schedule_id}


@router.get("/contractor/availability/{contractor_id}")
def list_availability(contractor_id: str, token: str = Depends(verify_firebase_token)):
    slots = ScheduleRepo().list_entries(contractor_id)
    return {"contractor_id": contractor_id, "availability": slots}
