"""
DynamoDB Service Layer for LandTen MVP 3.0
Handles all database operations for incidents, jobs, bids, properties, and users
"""

import os
import boto3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from decimal import Decimal
import json
import time

# Boto3 client singleton
_dynamodb_client = None
_dynamodb_resource = None

# 🔒 STRICT WHITELIST for incident update fields (must match function_registry.py)
# ONLY these fields are allowed in incident updates
# ALL other fields will be STRIPPED before reaching DynamoDB
ALLOWED_INCIDENT_FIELDS = {
    "incident_id", "title", "description", "status", "category",
    "severity", "urgency", "discovery_responses", "discovery_answers",
    "updated_at", "created_at", "resolution_notes", "completed_at",
    "location", "discovery_index", "property_id", "tenant_id",
    "media_urls", "discovery_data"
}


def get_dynamodb_client():
    """Get or create DynamoDB client (thread-safe singleton)"""
    global _dynamodb_client
    if _dynamodb_client is None:
        region = os.getenv("AWS_REGION", "us-east-1")
        _dynamodb_client = boto3.client(
            "dynamodb",
            region_name=region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
    return _dynamodb_client


def get_dynamodb_resource():
    """Get or create DynamoDB resource (for higher-level operations)"""
    global _dynamodb_resource
    if _dynamodb_resource is None:
        region = os.getenv("AWS_REGION", "us-east-1")
        _dynamodb_resource = boto3.resource(
            "dynamodb",
            region_name=region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
    return _dynamodb_resource


def decimal_to_float(obj):
    """Convert Decimal to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj


class IncidentDB:
    """Manage landten_incidents table"""

    TABLE_NAME = "landten_incidents"

    @staticmethod
    def create_incident(incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new incident in DynamoDB

        Schema:
        - incident_id (PK): string
        - tenant_id: string
        - property_id: string
        - title: string
        - description: string
        - category: string (plumbing, electrical, etc.)
        - severity: string (low, medium, high, emergency)
        - urgency: string (routine, urgent, immediate)
        - status: string (detected, discovery, work_order, completed)
        - created_at: string (ISO timestamp)
        - updated_at: string (ISO timestamp)
        - channel_id: string (Stream Chat channel)
        - media_urls: list of strings
        - discovery_data: map (optional)
        """
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(IncidentDB.TABLE_NAME)

        now = datetime.now(timezone.utc).isoformat()

        item = {
            # Always include DynamoDB's expected partition key
            # CRITICAL FIX: Never use "unknown" as user_id - it breaks queries
            "user_id": incident_data.get("user_id") or incident_data.get("tenant_id"),
            # Optional sort key if your schema requires it
            "incident_id": incident_data.get("incident_id"),
            "tenant_id": incident_data.get("tenant_id", "unknown"),
            "property_id": incident_data.get("property_id", "unknown"),
            "title": incident_data.get("title", ""),
            "description": incident_data.get("description", ""),
            "category": incident_data.get("category", "general"),
            "severity": incident_data.get("severity", "medium"),
            "urgency": incident_data.get("urgency", "routine"),
            "status": incident_data.get("status", "detected"),
            "created_at": incident_data.get("created_at", now),
            "updated_at": now,
            "channel_id": incident_data.get("channel_id", ""),
            "media_urls": incident_data.get("media_urls", []),
        }

        # Validate user_id is present
        if not item.get("user_id"):
            raise ValueError("user_id is required to create incident")

        # Add optional fields
        if "discovery_data" in incident_data:
            item["discovery_data"] = incident_data["discovery_data"]

        try:
            table.put_item(Item=item)
            print(f"[IncidentDB] Created incident: {item['incident_id']}")
            return decimal_to_float(item)
        except Exception as e:
            print(f"[IncidentDB] ❌ Error creating incident: {e}")
            raise

    @staticmethod
    def get_incident(incident_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get incident by ID (requires both user_id and incident_id for composite key)"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(IncidentDB.TABLE_NAME)

        try:
            # If no user_id provided, try scanning (slower but fallback-safe)
            if user_id:
                key = {"user_id": user_id, "incident_id": incident_id}
                response = table.get_item(Key=key)
            else:
                print(f"[IncidentDB] get_incident fallback scan for {incident_id}")
                response = table.scan(
                    FilterExpression="incident_id = :iid",
                    ExpressionAttributeValues={":iid": incident_id},
                    Limit=1
                )
                items = response.get("Items", [])
                return decimal_to_float(items[0]) if items else None

            item = response.get("Item")
            return decimal_to_float(item) if item else None

        except Exception as e:
            print(f"[IncidentDB] ❌ Error getting incident: {e}")
            return None


    @staticmethod
    def update_incident_status(incident_id: str, status: str, user_id: Optional[str] = None, **kwargs) -> bool:
        """Update incident status and optional fields (requires both keys)"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(IncidentDB.TABLE_NAME)

        # CRITICAL FIX: Build update expression incrementally to avoid overlaps
        update_parts = []
        expr_values = {}
        expr_names = {}

        # Always update these fields
        update_parts.append("#status = :status")
        update_parts.append("updated_at = :updated_at")
        expr_names["#status"] = "status"
        expr_values[":status"] = status
        expr_values[":updated_at"] = datetime.now(timezone.utc).isoformat()

        # CRITICAL: Apply STRICT whitelist filtering
        # Strip 'status', 'incident_id', 'user_id', 'updated_at' - they're handled separately
        forbidden_keys = {"status", "incident_id", "user_id", "updated_at", "channel_id",
                          "stage", "persona", "model", "metadata", "routing"}

        kwargs_filtered = {}
        filtered_out = []

        for key, value in kwargs.items():
            # Skip forbidden keys
            if key in forbidden_keys:
                filtered_out.append(key)
                continue

            # Only allow fields in ALLOWED_INCIDENT_FIELDS
            if key in ALLOWED_INCIDENT_FIELDS:
                kwargs_filtered[key] = value
            else:
                filtered_out.append(key)

        if filtered_out:
            print(f"[IncidentDB] 🔒 Filtered out {len(filtered_out)} forbidden fields: {filtered_out}")

        # Build update expression for allowed fields only (avoiding duplicates)
        for key, value in kwargs_filtered.items():
            # Use ExpressionAttributeNames for reserved keywords
            attr_name = f"#{key}"
            attr_value = f":{key}"

            # Check for duplicate paths
            if attr_name in expr_names:
                print(f"[IncidentDB] ⚠️ Skipping duplicate field: {key}")
                continue

            update_parts.append(f"{attr_name} = {attr_value}")
            expr_names[attr_name] = key
            expr_values[attr_value] = value

        # Assemble final expression
        update_expr = "SET " + ", ".join(update_parts)

        print(f"[IncidentDB] ✅ Updating incident {incident_id}: status={status}, fields={list(kwargs_filtered.keys())}")

        try:
            if not user_id:
                print(f"[IncidentDB] ⚠️ Missing user_id for update_incident_status, attempting fallback scan...")
                # Use None to trigger scan-based lookup
                found = IncidentDB.get_incident(incident_id, user_id=None)
                if found:
                    user_id = found.get("user_id")

                if not user_id or user_id == "unknown":
                    print(f"[IncidentDB] ❌ Cannot update {incident_id} — user_id still missing after scan.")
                    return False

            table.update_item(
                Key={"user_id": user_id, "incident_id": incident_id},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
                ExpressionAttributeNames=expr_names
            )
            print(f"[IncidentDB] ✅ Successfully updated incident {incident_id}")
            return True
        except Exception as e:
            print(f"[IncidentDB] ❌ Error updating incident: {e}")
            print(f"[IncidentDB]    UpdateExpression: {update_expr}")
            print(f"[IncidentDB]    ExpressionAttributeNames: {expr_names}")
            return False


    @staticmethod
    def list_incidents_by_tenant(tenant_id: str) -> List[Dict[str, Any]]:
        """List all incidents for a tenant"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(IncidentDB.TABLE_NAME)

        try:
            response = table.scan(
                FilterExpression="tenant_id = :tid",
                ExpressionAttributeValues={":tid": tenant_id}
            )
            items = response.get("Items", [])
            return [decimal_to_float(item) for item in items]
        except Exception as e:
            print(f"[IncidentDB] ❌ Error listing incidents: {e}")
            return []


class JobDB:
    """Manage landten_jobs table"""

    TABLE_NAME = "landten_jobs"

    @staticmethod
    def create_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new job in DynamoDB

        Schema:
        - job_id (PK): string
        - incident_id: string
        - property_id: string
        - landlord_id: string
        - contractor_id: string (optional until assigned)
        - title: string
        - category: string
        - estimated_cost: string
        - final_cost: string (optional)
        - urgency: string
        - status: string (created, approved, scheduled, in_progress, completed)
        - created_at: string
        - updated_at: string
        - scheduled_date: string (optional)
        - completion_date: string (optional)
        - channel_id: string
        """
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(JobDB.TABLE_NAME)

        now = datetime.now(timezone.utc).isoformat()

        # 🚨 CRITICAL FIX: ALWAYS extract user_id from job_data
        # DynamoDB requires user_id as a key field
        item = {
            "job_id": job_data.get("job_id"),
            "incident_id": job_data.get("incident_id", ""),
            "user_id": job_data.get("user_id", ""),  # 🚨 FIX: Extract user_id from job_data
            "property_id": job_data.get("property_id", "unknown"),
            "landlord_id": job_data.get("landlord_id", "unknown"),
            "title": job_data.get("title", ""),
            "category": job_data.get("category", "general"),
            "estimated_cost": job_data.get("estimated_cost", ""),
            "urgency": job_data.get("urgency", "routine"),
            "status": job_data.get("status", "created"),
            "created_at": job_data.get("created_at", now),
            "updated_at": now,
            "channel_id": job_data.get("channel_id", ""),
        }

        # Add optional fields
        for field in ["contractor_id", "final_cost", "scheduled_date", "completion_date"]:
            if field in job_data:
                item[field] = job_data[field]

        try:
            table.put_item(Item=item)
            print(f"[JobDB] Created job: {item['job_id']}")
            return decimal_to_float(item)
        except Exception as e:
            print(f"[JobDB] ❌ Error creating job: {e}")
            raise

    @staticmethod
    def get_job(job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(JobDB.TABLE_NAME)

        try:
            response = table.get_item(Key={"job_id": job_id})
            item = response.get("Item")
            return decimal_to_float(item) if item else None
        except Exception as e:
            print(f"[JobDB] ❌ Error getting job: {e}")
            return None

    @staticmethod
    def update_job(job_id: str, **updates) -> bool:
        """Update job fields"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(JobDB.TABLE_NAME)

        if not updates:
            return True

        update_expr = "SET updated_at = :updated_at"
        expr_values = {":updated_at": datetime.now(timezone.utc).isoformat()}

        # CRITICAL FIX: Skip updated_at in loop to avoid duplicate paths
        # updated_at is already added above, so filter it out from updates
        for key, value in updates.items():
            if key == "updated_at":
                continue  # Skip to avoid "Two document paths overlap" error
            update_expr += f", {key} = :{key}"
            expr_values[f":{key}"] = value

        try:
            table.update_item(
                Key={"job_id": job_id},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values
            )
            print(f"[JobDB] Updated job {job_id}: {updates}")
            return True
        except Exception as e:
            print(f"[JobDB] ❌ Error updating job: {e}")
            return False


class BidDB:
    """Manage landten_job_bids table"""

    TABLE_NAME = "landten_job_bids"

    @staticmethod
    def create_bid(bid_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new bid in DynamoDB

        Schema:
        - bid_id (PK): string
        - job_id: string
        - contractor_id: string
        - contractor_name: string
        - quote: number
        - eta: string
        - rating: number
        - distance: string
        - status: string (pending, accepted, rejected)
        - created_at: string
        - updated_at: string
        """
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(BidDB.TABLE_NAME)

        now = datetime.now(timezone.utc).isoformat()

        item = {
            "bid_id": bid_data.get("bid_id"),
            "job_id": bid_data.get("job_id", ""),
            "contractor_id": bid_data.get("contractor_id", "unknown"),
            "contractor_name": bid_data.get("contractor_name", ""),
            "quote": Decimal(str(bid_data.get("quote", 0))),
            "eta": bid_data.get("eta", ""),
            "rating": Decimal(str(bid_data.get("rating", 0))),
            "distance": bid_data.get("distance", ""),
            "status": bid_data.get("status", "pending"),
            "created_at": bid_data.get("created_at", now),
            "updated_at": now,
        }

        try:
            table.put_item(Item=item)
            print(f"[BidDB] Created bid: {item['bid_id']}")
            return decimal_to_float(item)
        except Exception as e:
            print(f"[BidDB] ❌ Error creating bid: {e}")
            raise

    @staticmethod
    def list_bids_by_job(job_id: str) -> List[Dict[str, Any]]:
        """List all bids for a job"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(BidDB.TABLE_NAME)

        try:
            response = table.scan(
                FilterExpression="job_id = :jid",
                ExpressionAttributeValues={":jid": job_id}
            )
            items = response.get("Items", [])
            return [decimal_to_float(item) for item in items]
        except Exception as e:
            print(f"[BidDB] ❌ Error listing bids: {e}")
            return []

    @staticmethod
    def update_bid_status(bid_id: str, status: str) -> bool:
        """Update bid status"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(BidDB.TABLE_NAME)

        try:
            table.update_item(
                Key={"bid_id": bid_id},
                UpdateExpression="SET #status = :status, updated_at = :updated_at",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":status": status,
                    ":updated_at": datetime.now(timezone.utc).isoformat()
                }
            )
            print(f"[BidDB] Updated bid {bid_id} status to {status}")
            return True
        except Exception as e:
            print(f"[BidDB] ❌ Error updating bid: {e}")
            return False


class PropertyDB:
    """Manage landten_property table"""

    TABLE_NAME = "landten_property"

    @staticmethod
    def get_property(property_id: str) -> Optional[Dict[str, Any]]:
        """Get property by ID"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(PropertyDB.TABLE_NAME)

        try:
            response = table.get_item(Key={"id": property_id})
            item = response.get("Item")
            return decimal_to_float(item) if item else None
        except Exception as e:
            print(f"[PropertyDB] ❌ Error getting property: {e}")
            return None

    @staticmethod
    def list_properties_by_landlord(landlord_id: str) -> List[Dict[str, Any]]:
        """List all properties for a landlord"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(PropertyDB.TABLE_NAME)

        try:
            response = table.scan(
                FilterExpression="landlord_id = :lid",
                ExpressionAttributeValues={":lid": landlord_id}
            )
            items = response.get("Items", [])
            return [decimal_to_float(item) for item in items]
        except Exception as e:
            print(f"[PropertyDB] ❌ Error listing properties: {e}")
            return []


class DynamicToolDB:
    """Manage landten_dev_dynamic_tools table for AI-generated diagnostic tools"""

    TABLE_NAME = "landten_dev_dynamic_tools"

    @staticmethod
    def create_tool(tool_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new dynamic tool in DynamoDB

        Schema:
        - tool_id (PK): string
        - tool_name: string (unique identifier)
        - code: string (Python source code)
        - description: string
        - category: string (plumbing, electrical, hvac, etc.)
        - created_by: string (llm, user_id, etc.)
        - created_at: string (ISO timestamp)
        - updated_at: string (ISO timestamp)
        - metadata: map (function signature, docstring, parameters)
        - usage_count: number
        - last_used_at: string (ISO timestamp, nullable)
        - version: number
        """
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(DynamicToolDB.TABLE_NAME)

        now = datetime.now(timezone.utc).isoformat()

        item = {
            "tool_id": tool_data.get("tool_id"),
            "tool_name": tool_data.get("tool_name"),
            "code": tool_data.get("code"),
            "description": tool_data.get("description", "No description"),
            "category": tool_data.get("category", "general"),
            "created_by": tool_data.get("created_by", "llm"),
            "created_at": tool_data.get("created_at", now),
            "updated_at": now,
            "metadata": tool_data.get("metadata", {}),
            "usage_count": tool_data.get("usage_count", 0),
            "version": tool_data.get("version", 1),
        }

        # Optional fields
        if "last_used_at" in tool_data and tool_data["last_used_at"]:
            item["last_used_at"] = tool_data["last_used_at"]

        try:
            table.put_item(Item=item)
            print(f"[DynamicToolDB] ✅ Created tool: {item['tool_name']} ({item['tool_id']})")
            return decimal_to_float(item)
        except Exception as e:
            print(f"[DynamicToolDB] ❌ Error creating tool: {e}")
            raise

    @staticmethod
    def get_tool(tool_id: str) -> Optional[Dict[str, Any]]:
        """Get tool by ID"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(DynamicToolDB.TABLE_NAME)

        try:
            response = table.get_item(Key={"tool_id": tool_id})
            item = response.get("Item")
            return decimal_to_float(item) if item else None
        except Exception as e:
            print(f"[DynamicToolDB] ❌ Error getting tool: {e}")
            return None

    @staticmethod
    def get_tool_by_name(tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool by name (scan operation)"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(DynamicToolDB.TABLE_NAME)

        try:
            response = table.scan(
                FilterExpression="tool_name = :tname",
                ExpressionAttributeValues={":tname": tool_name},
                Limit=1
            )
            items = response.get("Items", [])
            return decimal_to_float(items[0]) if items else None
        except Exception as e:
            print(f"[DynamicToolDB] ❌ Error getting tool by name: {e}")
            return None

    @staticmethod
    def list_all_tools() -> List[Dict[str, Any]]:
        """List all dynamic tools"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(DynamicToolDB.TABLE_NAME)

        try:
            response = table.scan()
            items = response.get("Items", [])
            print(f"[DynamicToolDB] 📦 Loaded {len(items)} tools from DynamoDB")
            return [decimal_to_float(item) for item in items]
        except Exception as e:
            print(f"[DynamicToolDB] ❌ Error listing tools: {e}")
            return []

    @staticmethod
    def list_tools_by_category(category: str) -> List[Dict[str, Any]]:
        """List all tools in a category"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(DynamicToolDB.TABLE_NAME)

        try:
            response = table.scan(
                FilterExpression="category = :cat",
                ExpressionAttributeValues={":cat": category}
            )
            items = response.get("Items", [])
            return [decimal_to_float(item) for item in items]
        except Exception as e:
            print(f"[DynamicToolDB] ❌ Error listing tools by category: {e}")
            return []

    @staticmethod
    def update_tool_usage(tool_id: str) -> bool:
        """Update usage stats when tool is executed"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(DynamicToolDB.TABLE_NAME)

        try:
            table.update_item(
                Key={"tool_id": tool_id},
                UpdateExpression="SET usage_count = usage_count + :inc, last_used_at = :now, updated_at = :now",
                ExpressionAttributeValues={
                    ":inc": 1,
                    ":now": datetime.now(timezone.utc).isoformat()
                }
            )
            return True
        except Exception as e:
            print(f"[DynamicToolDB] ❌ Error updating tool usage: {e}")
            return False

    @staticmethod
    def delete_tool(tool_id: str) -> bool:
        """Delete a tool from DynamoDB"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(DynamicToolDB.TABLE_NAME)

        try:
            table.delete_item(Key={"tool_id": tool_id})
            print(f"[DynamicToolDB] 🗑️ Deleted tool: {tool_id}")
            return True
        except Exception as e:
            print(f"[DynamicToolDB] ❌ Error deleting tool: {e}")
            return False


class UserDB:
    """Manage landten_users table"""

    TABLE_NAME = "landten_users"

    @staticmethod
    def upsert_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update user in DynamoDB

        Schema:
        - user_id (PK): string
        - email: string
        - name: string
        - persona: string (tenant, landlord, contractor)
        - created_at: string
        - updated_at: string
        - last_seen: string
        """
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(UserDB.TABLE_NAME)

        now = datetime.now(timezone.utc).isoformat()

        item = {
            "user_id": user_data.get("user_id"),
            "email": user_data.get("email", ""),
            "name": user_data.get("name", ""),
            "persona": user_data.get("persona", "tenant"),
            "last_seen": now,
        }

        # Set created_at only if new user
        try:
            existing = table.get_item(Key={"user_id": item["user_id"]}).get("Item")
            if existing:
                item["created_at"] = existing.get("created_at", now)
                item["updated_at"] = now
            else:
                item["created_at"] = now
                item["updated_at"] = now

            table.put_item(Item=item)
            print(f"[UserDB] Upserted user: {item['user_id']}")
            return decimal_to_float(item)
        except Exception as e:
            print(f"[UserDB] ❌ Error upserting user: {e}")
            raise

    @staticmethod
    def get_user(user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(UserDB.TABLE_NAME)

        try:
            response = table.get_item(Key={"user_id": user_id})
            item = response.get("Item")
            return decimal_to_float(item) if item else None
        except Exception as e:
            print(f"[UserDB] ❌ Error getting user: {e}")
            return None


def save_channel_snapshot(channel_id: str, snapshot: Dict[str, Any]) -> None:
    """Save a lightweight channel snapshot for analytics/debugging.

    This stores snapshots in a dedicated table 'channel_snapshots'. The table
    should be created ahead of time (or this will raise). Each item contains
    channel_id (PK), snapshot (map), and timestamp (int).
    """
    dynamodb = get_dynamodb_resource()
    table_name = os.getenv("CHANNEL_SNAPSHOTS_TABLE", "channel_snapshots")
    table = dynamodb.Table(table_name)
    try:
        item = {"channel_id": channel_id, "snapshot": snapshot, "timestamp": int(time.time())}
        table.put_item(Item=item)
        print(f"[dynamo] Saved channel snapshot for {channel_id}")
    except Exception as e:
        print(f"[dynamo] Failed to save channel snapshot: {e}")


def record_mttr_event(incident_id: str, event: Dict[str, Any]) -> None:
    """Record MTTR lifecycle events for an incident.

    event should contain keys like 'first_response_at', 'resolved_at', 'created_at'.
    """
    dynamodb = get_dynamodb_resource()
    table_name = os.getenv("MTTR_EVENTS_TABLE", "mttr_events")
    table = dynamodb.Table(table_name)
    try:
        item = {"incident_id": incident_id, **event, "timestamp": int(time.time())}
        table.put_item(Item=item)
        print(f"[sla-metrics] Recorded MTTR event for {incident_id}")
    except Exception as e:
        print(f"[sla-metrics] Failed to record MTTR event: {e}")


def record_ai_feedback(feedback: Dict[str, Any]) -> None:
    """Persist training feedback for AI models.

    feedback example: {"incident_id": "INC-...", "label": "severity.high", "correct": True}
    """
    dynamodb = get_dynamodb_resource()
    table_name = os.getenv("AI_FEEDBACK_TABLE", "ai_training_feedback")
    table = dynamodb.Table(table_name)
    try:
        item = {**feedback, "timestamp": int(time.time())}
        table.put_item(Item=item)
        print(f"[ai-feedback] Saved AI training feedback")
    except Exception as e:
        print(f"[ai-feedback] Failed to save feedback: {e}")


def get_aggregated_metrics(entity_type: str, entity_id: str) -> Dict[str, Any]:
    """Return lightweight aggregated metrics for tenant/landlord/contractor.

    This is a placeholder that can be replaced by a proper analytics pipeline.
    """
    # For now return stubbed metrics; a proper implementation would query DynamoDB or a metrics store
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "mttr_hours": None,
        "fill_rate": None,
        "engagement": None,
    }


class DynamoService:
    """Unified interface to all DynamoDB operations.

    This wrapper provides a single object with all database methods
    for easier dependency injection and testing.
    """

    # Incident operations
    @staticmethod
    def create_incident(incident_data: Dict[str, Any]) -> Dict[str, Any]:
        return IncidentDB.create_incident(incident_data)

    @staticmethod
    def get_incident(incident_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return IncidentDB.get_incident(incident_id, user_id)

    @staticmethod
    def update_incident_status(incident_id: str, status: str, user_id: Optional[str] = None, **kwargs) -> bool:
        return IncidentDB.update_incident_status(incident_id, status, user_id, **kwargs)

    @staticmethod
    def list_incidents_by_tenant(tenant_id: str) -> List[Dict[str, Any]]:
        return IncidentDB.list_incidents_by_tenant(tenant_id)

    # Job operations
    @staticmethod
    def create_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
        return JobDB.create_job(job_data)

    @staticmethod
    def get_job(job_id: str) -> Optional[Dict[str, Any]]:
        return JobDB.get_job(job_id)

    @staticmethod
    def update_job(job_id: str, **updates) -> bool:
        return JobDB.update_job(job_id, **updates)

    # Bid operations
    @staticmethod
    def create_bid(bid_data: Dict[str, Any]) -> Dict[str, Any]:
        return BidDB.create_bid(bid_data)

    @staticmethod
    def list_bids_by_job(job_id: str) -> List[Dict[str, Any]]:
        return BidDB.list_bids_by_job(job_id)

    @staticmethod
    def update_bid_status(bid_id: str, status: str) -> bool:
        return BidDB.update_bid_status(bid_id, status)

    # Property operations
    @staticmethod
    def get_property(property_id: str) -> Optional[Dict[str, Any]]:
        return PropertyDB.get_property(property_id)

    @staticmethod
    def list_properties_by_landlord(landlord_id: str) -> List[Dict[str, Any]]:
        return PropertyDB.list_properties_by_landlord(landlord_id)

    # User operations
    @staticmethod
    def upsert_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
        return UserDB.upsert_user(user_data)

    @staticmethod
    def get_user(user_id: str) -> Optional[Dict[str, Any]]:
        return UserDB.get_user(user_id)

    # Dynamic tool operations
    @staticmethod
    def create_dynamic_tool(tool_data: Dict[str, Any]) -> Dict[str, Any]:
        return DynamicToolDB.create_tool(tool_data)

    @staticmethod
    def get_dynamic_tool(tool_id: str) -> Optional[Dict[str, Any]]:
        return DynamicToolDB.get_tool(tool_id)

    @staticmethod
    def get_dynamic_tool_by_name(tool_name: str) -> Optional[Dict[str, Any]]:
        return DynamicToolDB.get_tool_by_name(tool_name)

    @staticmethod
    def list_all_dynamic_tools() -> List[Dict[str, Any]]:
        return DynamicToolDB.list_all_tools()

    @staticmethod
    def list_dynamic_tools_by_category(category: str) -> List[Dict[str, Any]]:
        return DynamicToolDB.list_tools_by_category(category)

    @staticmethod
    def update_dynamic_tool_usage(tool_id: str) -> bool:
        return DynamicToolDB.update_tool_usage(tool_id)

    @staticmethod
    def delete_dynamic_tool(tool_id: str) -> bool:
        return DynamicToolDB.delete_tool(tool_id)

    # Conversation mapping operations (for Responses API migration)
    @staticmethod
    def save_conversation_mapping(
        channel_id: str,
        conversation_id: str,
        user_id: str = "",
        persona: str = "tenant"
    ) -> bool:
        """
        Store channel_id → conversation_id mapping.

        Used by ConversationManager to map Slack channels to OpenAI Conversations.

        Args:
            channel_id: Slack channel ID
            conversation_id: OpenAI Conversation ID
            user_id: User identifier
            persona: User role (tenant, landlord, contractor)

        Returns:
            bool: True if successful
        """
        dynamodb = get_dynamodb_resource()
        table_name = os.getenv("CONVERSATION_MAPPING_TABLE", "landten_conversation_mappings")
        table = dynamodb.Table(table_name)

        try:
            now = datetime.now(timezone.utc).isoformat()
            item = {
                "channel_id": channel_id,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "persona": persona,
                "created_at": now,
                "updated_at": now,
            }
            table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"[conversation-mapping] Failed to save mapping: {e}")
            return False

    @staticmethod
    def get_conversation_mapping(channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve conversation_id for a channel.

        Args:
            channel_id: Slack channel ID

        Returns:
            dict or None: Mapping data if found, None otherwise
        """
        dynamodb = get_dynamodb_resource()
        table_name = os.getenv("CONVERSATION_MAPPING_TABLE", "landten_conversation_mappings")
        table = dynamodb.Table(table_name)

        try:
            response = table.get_item(Key={"channel_id": channel_id})
            return response.get("Item")
        except Exception as e:
            print(f"[conversation-mapping] Failed to get mapping for {channel_id}: {e}")
            return None

    @staticmethod
    def delete_conversation_mapping(channel_id: str) -> bool:
        """
        Delete channel → conversation mapping.

        Args:
            channel_id: Slack channel ID

        Returns:
            bool: True if successful
        """
        dynamodb = get_dynamodb_resource()
        table_name = os.getenv("CONVERSATION_MAPPING_TABLE", "landten_conversation_mappings")
        table = dynamodb.Table(table_name)

        try:
            table.delete_item(Key={"channel_id": channel_id})
            return True
        except Exception as e:
            print(f"[conversation-mapping] Failed to delete mapping: {e}")
            return False


_dynamo_service = None


def get_dynamo_service() -> DynamoService:
    """Get singleton DynamoService instance"""
    global _dynamo_service
    if _dynamo_service is None:
        _dynamo_service = DynamoService()
    return _dynamo_service
