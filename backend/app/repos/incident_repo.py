from typing import Dict, Any, List

from app.deps.dynamo import get_dynamo_resource, table_name


class IncidentRepo:

    def __init__(self):
        self.table = get_dynamo_resource().Table(table_name("incidents"))

    def create_incident(self, payload: Dict[str, Any]) -> None:
        self.table.put_item(Item=payload)

    def log_incident(self, payload: Dict[str, Any]) -> None:
        """Alias for create_incident for backward compatibility"""
        self.create_incident(payload)

    def get_incident(self, incident_id: str) -> Dict[str, Any]:
        resp = self.table.get_item(Key={"incident_id": incident_id})
        return resp.get("Item", {})

    def list_incidents(self, tenant_id: str) -> List[Dict[str, Any]]:
        """List all incidents for a specific tenant"""
        try:
            # Query using tenant_id as partition key
            resp = self.table.query(
                KeyConditionExpression="tenant_id = :tid",
                ExpressionAttributeValues={":tid": tenant_id}
            )
            return resp.get("Items", [])
        except Exception:
            # If query fails (e.g., no GSI), do a scan (less efficient but works)
            try:
                resp = self.table.scan(
                    FilterExpression="tenant_id = :tid",
                    ExpressionAttributeValues={":tid": tenant_id}
                )
                return resp.get("Items", [])
            except Exception:
                # Return empty list if table doesn't exist or other error
                return []
