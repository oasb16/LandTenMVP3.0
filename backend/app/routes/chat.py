from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.deps.auth import verify_firebase_token
from app.deps.pusher_client import get_pusher_client
from datetime import datetime, timezone
from app.repos.chat_repo import ChatRepo

router = APIRouter()

class ChatMessage(BaseModel):
    thread_id: Optional[str] = "default"
    user_id: str
    role: str
    message: str
    type: str = "text"
    client_id: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    payload: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None

_IN_MEMORY_HISTORY: Dict[str, List[dict]] = {}


def _append_history(thread_id: str, payload: dict) -> None:
    _IN_MEMORY_HISTORY.setdefault(thread_id, []).append(payload)

def _get_pusher():
    return get_pusher_client()

@router.post("/chat/send")
def send_message(msg: ChatMessage, token: str = Depends(verify_firebase_token)):
    # Timestamp if missing
    payload = msg.model_dump()
    if not payload.get("timestamp"):
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()

    thread_id = payload.get("thread_id", "default")

    # Broadcast on aligned channel/event
    p = _get_pusher()
    p.trigger("chat", "message", payload)

    # Persist to DynamoDB
    try:
        ChatRepo().put_message(payload)
    except Exception:
        # Fall back to in-memory for dev/local
        _append_history(thread_id, payload)

    return {"status": "sent", "message": payload}

@router.get("/chat/history/{thread_id}")
def get_history(thread_id: str, token: str = Depends(verify_firebase_token)):
    try:
        items = ChatRepo().list_messages(thread_id)
        return {"thread_id": thread_id, "messages": items}
    except Exception:
        return {"thread_id": thread_id, "messages": _IN_MEMORY_HISTORY.get(thread_id, [])}
