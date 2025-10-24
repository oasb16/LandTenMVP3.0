from typing import Dict, Any, List
from datetime import datetime, timezone
from app.deps.dynamo import get_dynamo_resource, table_name


class TaskRepo:
    def __init__(self):
        self.table = get_dynamo_resource().Table(table_name("tasks"))

    def create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "task_id": payload.get("task_id"),
            "created_at": payload.get("created_at", now),
            "title": payload.get("title"),
            "description": payload.get("description", ""),
            "status": payload.get("status", "pending"),
            "created_by": payload.get("created_by"),
            "assigned_to": payload.get("assigned_to"),
            "persona": payload.get("persona"),
        }
        self.table.put_item(Item=item)
        return item

    def list_tasks(self, persona: str) -> List[Dict[str, Any]]:
        resp = self.table.scan()
        items = resp.get("Items", [])
        return [item for item in items if item.get("persona") == persona or item.get("assigned_to") == persona]

    def update_status(self, task_id: str, status: str) -> None:
        self.table.update_item(
            Key={"task_id": task_id},
            UpdateExpression="SET #s = :status",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":status": status},
        )
