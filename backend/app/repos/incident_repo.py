from typing import Dict, Any

from app.deps.dynamo import get_dynamo_resource, table_name


class IncidentRepo:

    def __init__(self):
        self.table = get_dynamo_resource().Table(table_name("incidents"))

    def create_incident(self, payload: Dict[str, Any]) -> None:
        self.table.put_item(Item=payload)

    def get_incident(self, incident_id: str) -> Dict[str, Any]:
        resp = self.table.get_item(Key={"incident_id": incident_id})
        return resp.get("Item", {})
