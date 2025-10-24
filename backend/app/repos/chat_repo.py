from __future__ import annotations
from typing import Dict, Any, List
from app.deps.dynamo import get_dynamo_resource, table_name


class ChatRepo:
    def __init__(self):
        self.dynamo = get_dynamo_resource()
        self.table = self.dynamo.Table(table_name("chat_messages"))

    def put_message(self, payload: Dict[str, Any]) -> None:
        # partition by thread_id if provided, else 'default'
        thread_id = payload.get("thread_id", "default")
        item = {
            "thread_id": thread_id,
            "timestamp": payload.get("timestamp"),
            "user_id": payload.get("user_id"),
            "role": payload.get("role"),
            "message": payload.get("message"),
            "type": payload.get("type", "text"),
            "client_id": payload.get("client_id"),
        }
        attachments = payload.get("attachments")
        if attachments is not None:
            item["attachments"] = attachments
        card_payload = payload.get("payload")
        if card_payload is not None:
            item["payload"] = card_payload
        self.table.put_item(Item=item)

    def list_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        resp = self.table.query(
            KeyConditionExpression="#tid = :tid",
            ExpressionAttributeNames={"#tid": "thread_id"},
            ExpressionAttributeValues={":tid": thread_id},
            ScanIndexForward=True,
        )
        return resp.get("Items", [])
