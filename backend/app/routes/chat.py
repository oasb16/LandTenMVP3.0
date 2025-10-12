from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.deps.auth import verify_firebase_token
from pusher import Pusher

router = APIRouter()

class ChatMessage(BaseModel):
    user_id: str
    role: str
    message: str
    timestamp: Optional[str] = None

@router.post("/chat/send")
def send_message(msg: ChatMessage, token: str = Depends(verify_firebase_token)):
    # Integrate with Pusher
    pusher = Pusher(
        app_id="2062969",
        key="2178d446fd16f6575323",
        secret="0672cb1dd96b90d4ba0b",
        cluster="us2",
        ssl=True
    )
    pusher.trigger("my-channel", "my-event", {"message": msg.message, "user_id": msg.user_id, "role": msg.role, "timestamp": msg.timestamp})
    # TODO: Log to DB
    return {"status": "sent", "message": msg}

@router.get("/chat/history/{thread_id}")
def get_history(thread_id: str, token: str = Depends(verify_firebase_token)):
    # TODO: Fetch from DB
    return {"thread_id": thread_id, "messages": []}
