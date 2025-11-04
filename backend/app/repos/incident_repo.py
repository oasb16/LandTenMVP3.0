from typing import Dict, Any, List
from datetime import datetime, timezone

from app.deps.dynamo import get_dynamo_resource, table_name


class IncidentRepo:
    """Repository for incident persistence and retrieval"""

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


def persist_incident(incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unified incident persistence helper.

    This function provides a single entry point for creating incidents
    with consistent schema and error handling.

    Args:
        incident_data: Dictionary containing incident fields

    Returns:
        Dictionary with persisted incident data including incident_id

    Example:
        >>> persist_incident({
        ...     "user_id": "user-123",
        ...     "category": "plumbing",
        ...     "severity": "high",
        ...     "summary": "Water leak in kitchen"
        ... })
    """
    repo = IncidentRepo()

    # Generate incident_id if not provided
    incident_id = incident_data.get("incident_id") or f"INC-{int(datetime.now(timezone.utc).timestamp())}"

    # Build complete incident record with defaults
    now = datetime.now(timezone.utc).isoformat()
    incident_record = {
        "incident_id": incident_id,
        "thread_id": incident_data.get("thread_id", incident_data.get("channel_id", "unknown")),
        "tenant_email": incident_data.get("tenant_email", incident_data.get("user_id", "unknown")),
        "category": incident_data.get("category", "general"),
        "severity": incident_data.get("severity", "medium"),
        "urgency": incident_data.get("urgency", "routine"),
        "summary": incident_data.get("summary", incident_data.get("description", "")),
        "diy_attempted": incident_data.get("diy_attempted", False),
        "diy_result": incident_data.get("diy_result"),
        "media": incident_data.get("media", []),
        "created_at": incident_data.get("created_at", now),
        "status": incident_data.get("status", "pending"),
    }

    # Add optional fields if provided
    for optional_field in ["estimated_cost", "approval_threshold", "metadata"]:
        if optional_field in incident_data:
            incident_record[optional_field] = incident_data[optional_field]

    # Persist to DynamoDB
    try:
        repo.create_incident(incident_record)
        print(f"[incident-repo] ✅ Incident {incident_id} persisted successfully")
    except Exception as exc:
        print(f"[incident-repo] ❌ Failed to persist incident {incident_id}: {exc}")
        raise

    return incident_record
