from fastapi import APIRouter, Depends
from app.deps.auth import verify_firebase_token
from app.repos.chat_repo import ChatRepo
from typing import List, Dict


router = APIRouter()


def _summarize_locally(messages: List[Dict]) -> str:
    if not messages:
        return "No conversation yet."
    last_messages = messages[-5:]
    lines = [f"{m.get('role')}: {m.get('message')}" for m in last_messages]
    return "Summary based on last messages:\n- " + "\n- ".join(lines)


@router.get("/agent/summarize_thread/{thread_id}")
def summarize_thread(thread_id: str, token: str = Depends(verify_firebase_token)):
    try:
        messages = ChatRepo().list_messages(thread_id)
    except Exception:
        messages = []

    summary = _summarize_locally(messages)

    return {
        "thread_id": thread_id,
        "summary": summary,
    }
