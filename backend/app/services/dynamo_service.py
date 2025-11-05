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
            "user_id": incident_data.get("user_id") or incident_data.get("tenant_id") or "unknown",
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

        # Add optional fields
        if "discovery_data" in incident_data:
            item["discovery_data"] = incident_data["discovery_data"]

        try:
            table.put_item(Item=item)
            print(f"[IncidentDB] Created incident: {item['incident_id']}")
            return decimal_to_float(item)
        except Exception as e:
            print(f"[IncidentDB] Error creating incident: {e}")
            raise

    @staticmethod
    def get_incident(incident_id: str) -> Optional[Dict[str, Any]]:
        """Get incident by ID"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(IncidentDB.TABLE_NAME)

        try:
            response = table.get_item(Key={"incident_id": incident_id})
            item = response.get("Item")
            return decimal_to_float(item) if item else None
        except Exception as e:
            print(f"[IncidentDB] Error getting incident: {e}")
            return None

    @staticmethod
    def update_incident_status(incident_id: str, status: str, **kwargs) -> bool:
        """Update incident status and optional fields"""
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(IncidentDB.TABLE_NAME)

        update_expr = "SET #status = :status, updated_at = :updated_at"
        expr_values = {
            ":status": status,
            ":updated_at": datetime.now(timezone.utc).isoformat()
        }
        expr_names = {"#status": "status"}

        # Add optional updates
        for key, value in kwargs.items():
            update_expr += f", {key} = :{key}"
            expr_values[f":{key}"] = value

        try:
            table.update_item(
                Key={"incident_id": incident_id},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
                ExpressionAttributeNames=expr_names
            )
            print(f"[IncidentDB] Updated incident {incident_id} status to {status}")
            return True
        except Exception as e:
            print(f"[IncidentDB] Error updating incident: {e}")
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
            print(f"[IncidentDB] Error listing incidents: {e}")
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

        item = {
            "job_id": job_data.get("job_id"),
            "incident_id": job_data.get("incident_id", ""),
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
            print(f"[JobDB] Error creating job: {e}")
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
            print(f"[JobDB] Error getting job: {e}")
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

        for key, value in updates.items():
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
            print(f"[JobDB] Error updating job: {e}")
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
            print(f"[BidDB] Error creating bid: {e}")
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
            print(f"[BidDB] Error listing bids: {e}")
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
            print(f"[BidDB] Error updating bid: {e}")
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
            print(f"[PropertyDB] Error getting property: {e}")
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
            print(f"[PropertyDB] Error listing properties: {e}")
            return []


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
            print(f"[UserDB] Error upserting user: {e}")
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
            print(f"[UserDB] Error getting user: {e}")
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
