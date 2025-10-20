from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.deps.auth import verify_firebase_token
from pusher import Pusher
from datetime import datetime, timezone

router = APIRouter()

class ChatMessage(BaseModel):
    user_id: str
    role: str
    message: str
    timestamp: Optional[str] = None

_IN_MEMORY_HISTORY: list[dict] = []

def _get_pusher():
    # Prefer env-configured pusher; fallback to existing values
    import os
    app_id = os.getenv("PUSHER_APP_ID", "2062969")
    key = os.getenv("PUSHER_KEY", "2178d446fd16f6575323")
    secret = os.getenv("PUSHER_SECRET", "0672cb1dd96b90d4ba0b")
    cluster = os.getenv("PUSHER_CLUSTER", "us2")
    return Pusher(app_id=app_id, key=key, secret=secret, cluster=cluster, ssl=True)

@router.post("/chat/send")
def send_message(msg: ChatMessage, token: str = Depends(verify_firebase_token)):
    # Timestamp if missing
    payload = msg.dict()
    if not payload.get("timestamp"):
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Broadcast on aligned channel/event
    p = _get_pusher()
    p.trigger("chat", "message", payload)

    # In-memory history stub
    _IN_MEMORY_HISTORY.append(payload)

    return {"status": "sent", "message": payload}

@router.get("/chat/history/{thread_id}")
def get_history(thread_id: str, token: str = Depends(verify_firebase_token)):
    # Stub: return all messages; later filter by thread_id
    return {"thread_id": thread_id, "messages": _IN_MEMORY_HISTORY}
