from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class AgentRequest(BaseModel):
    thread_id: str
    message: str
    role: str

@router.post("/agent/summary")
def agent_summary(req: AgentRequest):
    # TODO: Call OpenAI API, return summary
    return {"summary": f"Summary for {req.thread_id} by {req.role}"}
