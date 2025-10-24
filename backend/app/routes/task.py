from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime, timezone
from app.deps.auth import verify_firebase_token
from app.repos.task_repo import TaskRepo


router = APIRouter()


_IN_MEMORY_TASKS: List[dict] = []


class TaskCreate(BaseModel):
    task_id: str
    title: str
    description: str
    persona: str  # primary persona (tenant/landlord/contractor)
    created_by: str
    assigned_to: str
    status: str = "pending"


class TaskStatusUpdate(BaseModel):
    task_id: str
    status: str


@router.post("/task/create")
def create_task(task: TaskCreate, token: str = Depends(verify_firebase_token)):
    payload = task.model_dump()
    payload["created_at"] = datetime.now(timezone.utc).isoformat()
    try:
        created = TaskRepo().create_task(payload)
        return {"status": "created", "task": created}
    except Exception:
        _IN_MEMORY_TASKS.append(payload)
        return {"status": "created", "task": payload, "warning": "Dynamo unavailable; stored in-memory"}


@router.get("/task/list/{persona}")
def list_tasks(persona: str, token: str = Depends(verify_firebase_token)):
    try:
        items = TaskRepo().list_tasks(persona)
        return {"tasks": items}
    except Exception:
        items = [t for t in _IN_MEMORY_TASKS if t.get("persona") == persona or t.get("assigned_to") == persona]
        return {"tasks": items, "warning": "Dynamo unavailable; returning in-memory tasks"}


@router.post("/task/update_status")
def update_task_status(update: TaskStatusUpdate, token: str = Depends(verify_firebase_token)):
    payload = update.model_dump()
    try:
        TaskRepo().update_status(payload["task_id"], payload["status"])
    except Exception:
        for task in _IN_MEMORY_TASKS:
            if task.get("task_id") == payload["task_id"]:
                task["status"] = payload["status"]
                break
    return {"status": "updated"}
