from typing import Dict, Any, List
from app.deps.dynamo import get_dynamo_resource, table_name


class IncidentRepo:
    def __init__(self):
        self.table = get_dynamo_resource().Table(table_name("incidents"))

    def log_incident(self, incident: Dict[str, Any]) -> None:
        self.table.put_item(Item=incident)

    def list_incidents(self, user_id: str) -> List[Dict[str, Any]]:
        # For MVP: partition on user_id
        resp = self.table.query(
            KeyConditionExpression="#uid = :uid",
            ExpressionAttributeNames={"#uid": "user_id"},
            ExpressionAttributeValues={":uid": user_id},
            ScanIndexForward=False,
        )
        return resp.get("Items", [])

