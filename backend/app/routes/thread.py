from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone
from app.deps.auth import verify_firebase_token
from app.repos.thread_repo import ThreadRepo


router = APIRouter()


class ThreadCreate(BaseModel):
    thread_id: str
    title: str
    participants: List[str]


_IN_MEMORY_THREADS: List[dict] = []


@router.post("/thread/create")
def create_thread(thread: ThreadCreate, token: str = Depends(verify_firebase_token)):
    payload = thread.model_dump()
    payload["created_at"] = datetime.now(timezone.utc).isoformat()
    try:
        created = ThreadRepo().create_thread(payload)
        return {"status": "created", "thread": created}
    except Exception:
        _IN_MEMORY_THREADS.append(payload)
        return {"status": "created", "thread": payload, "warning": "Dynamo unavailable; stored in-memory"}


@router.get("/thread/list/{user_id}")
def list_threads(user_id: str, token: str = Depends(verify_firebase_token)):
    try:
        items = ThreadRepo().list_threads_for_user(user_id)
        return {"threads": items}
    except Exception:
        threads = [t for t in _IN_MEMORY_THREADS if user_id in t.get("participants", [])]
        return {"threads": threads, "warning": "Dynamo unavailable; returning in-memory threads"}
