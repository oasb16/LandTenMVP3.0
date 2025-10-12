from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.deps.auth import verify_firebase_token

router = APIRouter()

class ChatMessage(BaseModel):
    user_id: str
    role: str
    message: str
    timestamp: Optional[str] = None

@router.post("/chat/send")
def send_message(msg: ChatMessage, token: str = Depends(verify_firebase_token)):
    # TODO: Integrate with Pusher/Firebase and log to DB
    return {"status": "sent", "message": msg}

@router.get("/chat/history/{thread_id}")
def get_history(thread_id: str, token: str = Depends(verify_firebase_token)):
    # TODO: Fetch from DB
    return {"thread_id": thread_id, "messages": []}
