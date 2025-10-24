from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from app.deps.auth import verify_firebase_token
from app.repos.profile_repo import ProfileRepo


router = APIRouter()


_IN_MEMORY_PROFILES: Dict[str, Dict[str, str]] = {}


class ProfileUpdate(BaseModel):
    user_id: str
    persona: str


@router.get("/profile/{user_id}")
def get_profile(user_id: str, token: str = Depends(verify_firebase_token)):
    try:
        data = ProfileRepo().get_profile(user_id)
        if data:
            return data
    except Exception:
        pass
    return _IN_MEMORY_PROFILES.get(user_id, {"user_id": user_id, "persona": None})


@router.post("/profile")
def upsert_profile(update: ProfileUpdate, token: str = Depends(verify_firebase_token)):
    payload = update.model_dump()
    try:
        ProfileRepo().upsert_profile(payload["user_id"], payload["persona"])
    except Exception:
        _IN_MEMORY_PROFILES[payload["user_id"]] = payload
        return {"status": "stored", "profile": payload, "warning": "Dynamo unavailable; stored in-memory"}
    return {"status": "stored", "profile": payload}
