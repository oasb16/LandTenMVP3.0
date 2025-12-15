from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging
from ..deps.auth import verify_firebase_token
from ..deps.pusher_client import get_pusher_client
from ..repos.chat_repo import ChatRepo

router = APIRouter()
logger = logging.getLogger(__name__)

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
    # Log incoming message details
    logger.info(f"📨 [CHAT/SEND] Received message from user_id={msg.user_id}, role={msg.role}, type={msg.type}")
    logger.info(f"📨 [CHAT/SEND] Message text: {msg.message[:100]}..." if len(msg.message) > 100 else f"📨 [CHAT/SEND] Message text: {msg.message}")
    logger.info(f"📨 [CHAT/SEND] Thread ID: {msg.thread_id}")

    # Log attachments if present
    if msg.attachments:
        logger.info(f"📎 [CHAT/SEND] ✅ Message has {len(msg.attachments)} attachment(s)")
        for idx, attachment in enumerate(msg.attachments):
            logger.info(f"📎 [CHAT/SEND] Attachment {idx + 1}: type={attachment.get('type')}, {attachment}")
    else:
        logger.info(f"📎 [CHAT/SEND] ⚠️ No attachments in message (attachments field is None or empty)")

    # Timestamp if missing
    payload = msg.model_dump()
    if not payload.get("timestamp"):
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()

    thread_id = payload.get("thread_id", "default")

    logger.info(f"📤 [CHAT/SEND] Broadcasting to Pusher channel='chat' event='message' for thread_id={thread_id}")

    # Broadcast on aligned channel/event
    try:
        p = _get_pusher()
        p.trigger("chat", "message", payload)
        logger.info(f"✅ [CHAT/SEND] Successfully broadcasted to Pusher")
    except Exception as e:
        logger.error(f"❌ [CHAT/SEND] Failed to broadcast to Pusher: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to broadcast message: {str(e)}")

    # Persist to DynamoDB
    try:
        ChatRepo().put_message(payload)
        logger.info(f"💾 [CHAT/SEND] Successfully persisted to DynamoDB")
    except Exception as e:
        logger.warning(f"⚠️ [CHAT/SEND] Failed to persist to DynamoDB, using in-memory: {e}")
        # Fall back to in-memory for dev/local
        _append_history(thread_id, payload)

    logger.info(f"✅ [CHAT/SEND] Message processing complete for thread_id={thread_id}")
    return {"status": "sent", "message": payload}

@router.get("/chat/history/{thread_id}")
def get_history(thread_id: str, token: str = Depends(verify_firebase_token)):
    try:
        items = ChatRepo().list_messages(thread_id)
        return {"thread_id": thread_id, "messages": items}
    except Exception:
        return {"thread_id": thread_id, "messages": _IN_MEMORY_HISTORY.get(thread_id, [])}
