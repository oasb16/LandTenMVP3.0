from typing import Dict, Any, List

from ..deps.dynamo import get_dynamo_resource, table_name


class ScheduleRepo:
    def __init__(self):
        self.table = get_dynamo_resource().Table(table_name("schedules"))

    def add_entry(self, entity_id: str, schedule_id: str, entry: Dict[str, Any]) -> None:
        payload = {
            "entity_id": entity_id,
            "schedule_id": schedule_id,
            **entry,
        }
        self.table.put_item(Item=payload)

    def list_entries(self, entity_id: str) -> List[Dict[str, Any]]:
        resp = self.table.query(
            KeyConditionExpression="#eid = :eid",
            ExpressionAttributeNames={"#eid": "entity_id"},
            ExpressionAttributeValues={":eid": entity_id},
        )
        return resp.get("Items", [])
