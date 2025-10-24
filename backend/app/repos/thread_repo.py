from typing import Dict, Any, List
from datetime import datetime, timezone
from app.deps.dynamo import get_dynamo_resource, table_name


class ThreadRepo:
    def __init__(self):
        self.table = get_dynamo_resource().Table(table_name("threads"))

    def create_thread(self, thread: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "thread_id": thread.get("thread_id"),
            "created_at": thread.get("created_at", now),
            "title": thread.get("title", "Untitled thread"),
            "participants": thread.get("participants", []),
        }
        self.table.put_item(Item=item)
        return item

    def list_threads_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        # For MVP, scan (small scale); TODO: add GSI for participants
        resp = self.table.scan()
        items = resp.get("Items", [])
        return [item for item in items if user_id in item.get("participants", [])]
