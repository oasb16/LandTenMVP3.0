"""
Context Manager - Persistent Conversational Memory System

This module provides intelligent, per-user, per-channel context tracking that enables
the AI system to maintain conversational continuity, understand flow state, and make
context-aware decisions.

Features:
- Per-user + per-channel short-term memory
- DynamoDB persistence for durability
- Automatic context expiration (configurable TTL)
- Flow state tracking (incident, job, bid, discovery phases)
- Persona-aware context management
- Thread-safe operations
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages conversational context for the PropertyAI system.

    Context Structure:
    {
        "context_id": "user_id:channel_id",
        "user_id": "user-123",
        "channel_id": "channel-abc",
        "persona": "tenant|landlord|contractor",
        "flow_type": "incident|job|bid|discovery|general",
        "flow_state": "started|in_progress|completed",
        "active_incident_id": "INC-123",
        "active_job_id": "JOB-456",
        "last_intent": "incident.report",
        "last_message": "there's a leak in the kitchen",
        "last_message_at": "2025-10-31T12:00:00Z",
        "entities": {
            "category": "plumbing",
            "severity": "medium",
            "urgency": "immediate"
        },
        "discovery_progress": {
            "current_question": 2,
            "total_questions": 5,
            "answers": {...}
        },
        "policy_state": {
            "can_auto_approve": true,
            "requires_landlord_approval": false
        },
        "conversation_history": [
            {"role": "user", "content": "...", "timestamp": "..."},
            {"role": "assistant", "content": "...", "timestamp": "..."}
        ],
        "metadata": {},
        "created_at": "2025-10-31T11:00:00Z",
        "updated_at": "2025-10-31T12:00:00Z",
        "expires_at": "2025-11-01T12:00:00Z"
    }
    """

    def __init__(self):
        """Initialize the ContextManager with DynamoDB connection."""
        self.table_name = self._get_table_name()
        self.dynamodb = self._get_dynamodb_resource()
        self.table = self.dynamodb.Table(self.table_name)

        # Context expiration settings (24 hours by default)
        self.context_ttl_hours = int(os.getenv("CONTEXT_TTL_HOURS", "24"))

        # Max conversation history to store (last N messages)
        self.max_history_length = int(os.getenv("CONTEXT_MAX_HISTORY", "20"))

        logger.info(f"ContextManager initialized with table: {self.table_name}")

    def _get_table_name(self) -> str:
        """Get the DynamoDB table name for chat contexts."""
        prefix = os.getenv("TABLE_PREFIX", "landtenmvp")
        stage = os.getenv("STAGE", "dev")
        return f"{prefix}_{stage}_chat_contexts"

    def _get_dynamodb_resource(self):
        """Get DynamoDB resource connection."""
        endpoint_url = os.getenv("DYNAMO_ENDPOINT_URL")

        if endpoint_url:
            # Local development
            return boto3.resource(
                'dynamodb',
                endpoint_url=endpoint_url,
                region_name=os.getenv("AWS_REGION", "us-east-1")
            )
        else:
            # Production
            return boto3.resource(
                'dynamodb',
                region_name=os.getenv("AWS_REGION", "us-east-1")
            )

    @staticmethod
    def _make_context_id(user_id: str, channel_id: str) -> str:
        """Create a unique context identifier."""
        return f"{user_id}:{channel_id}"

    @staticmethod
    def _decimal_to_float(obj: Any) -> Any:
        """Convert Decimal objects to float for JSON serialization."""
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: ContextManager._decimal_to_float(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [ContextManager._decimal_to_float(v) for v in obj]
        return obj

    def get_context(
        self,
        user_id: str,
        channel_id: str,
        create_if_missing: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve context for a user in a specific channel.

        Args:
            user_id: The user's ID
            channel_id: The channel ID
            create_if_missing: If True, creates a new context if none exists

        Returns:
            Context dictionary or None if not found and create_if_missing=False
        """
        context_id = self._make_context_id(user_id, channel_id)

        try:
            response = self.table.get_item(Key={"context_id": context_id})

            if "Item" in response:
                context = self._decimal_to_float(response["Item"])

                # Check if context is expired
                if "expires_at" in context:
                    expires_at = datetime.fromisoformat(context["expires_at"].replace("Z", "+00:00"))
                    if datetime.utcnow() > expires_at:
                        logger.info(f"Context {context_id} has expired, creating new one")
                        if create_if_missing:
                            return self._create_new_context(user_id, channel_id)
                        return None

                logger.debug(f"[context-manager] Retrieved context: {context_id}")
                return context

            elif create_if_missing:
                logger.info(f"[context-manager] No context found for {context_id}, creating new")
                return self._create_new_context(user_id, channel_id)

            return None

        except ClientError as e:
            logger.error(f"Error retrieving context {context_id}: {e}")
            if create_if_missing:
                return self._create_new_context(user_id, channel_id)
            return None

    def _create_new_context(self, user_id: str, channel_id: str) -> Dict[str, Any]:
        """Create a new context with default values."""
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=self.context_ttl_hours)

        context = {
            "context_id": self._make_context_id(user_id, channel_id),
            "user_id": user_id,
            "channel_id": channel_id,
            "persona": None,  # Will be detected from channel metadata
            "flow_type": "general",
            "flow_state": "idle",
            "active_incident_id": None,
            "active_job_id": None,
            "last_intent": None,
            "last_message": None,
            "last_message_at": None,
            "entities": {},
            "discovery_progress": {},
            "policy_state": {},
            "conversation_history": [],
            "metadata": {},
            "created_at": now.isoformat() + "Z",
            "updated_at": now.isoformat() + "Z",
            "expires_at": expires_at.isoformat() + "Z"
        }

        # Save to DynamoDB
        try:
            self.table.put_item(Item=context)
            logger.info(f"[context-manager] Created new context: {context['context_id']}")
        except ClientError as e:
            logger.error(f"Error creating context: {e}")

        return context

    def update_context(
        self,
        user_id: str,
        channel_id: str,
        updates: Dict[str, Any],
        append_to_history: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Update context with new information.

        Args:
            user_id: The user's ID
            channel_id: The channel ID
            updates: Dictionary of fields to update
            append_to_history: Optional message to append to conversation history
                              Format: {"role": "user|assistant", "content": "..."}

        Returns:
            True if successful, False otherwise
        """
        context_id = self._make_context_id(user_id, channel_id)
        now = datetime.utcnow().isoformat() + "Z"

        # Get current context to preserve conversation history
        current_context = self.get_context(user_id, channel_id)
        if not current_context:
            logger.error(f"Cannot update non-existent context: {context_id}")
            return False

        # Prepare update expression
        update_expr = "SET updated_at = :updated_at"
        expr_attr_values = {":updated_at": now}

        # Add provided updates
        for key, value in updates.items():
            if key not in ["context_id", "user_id", "channel_id", "created_at"]:
                update_expr += f", {key} = :{key}"
                expr_attr_values[f":{key}"] = value

        # Handle conversation history
        if append_to_history:
            conversation_history = current_context.get("conversation_history", [])

            # Add timestamp to message
            append_to_history["timestamp"] = now

            # Append new message
            conversation_history.append(append_to_history)

            # Keep only last N messages
            if len(conversation_history) > self.max_history_length:
                conversation_history = conversation_history[-self.max_history_length:]

            update_expr += ", conversation_history = :history"
            expr_attr_values[":history"] = conversation_history

        try:
            self.table.update_item(
                Key={"context_id": context_id},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_attr_values
            )
            logger.debug(f"[context-manager] Updated context: {context_id}")
            return True

        except ClientError as e:
            logger.error(f"Error updating context {context_id}: {e}")
            return False

    def set_persona(self, user_id: str, channel_id: str, persona: str) -> bool:
        """Set the persona for a context."""
        return self.update_context(user_id, channel_id, {"persona": persona})

    def set_flow(
        self,
        user_id: str,
        channel_id: str,
        flow_type: str,
        flow_state: str = "in_progress"
    ) -> bool:
        """Set the active flow type and state."""
        return self.update_context(
            user_id,
            channel_id,
            {"flow_type": flow_type, "flow_state": flow_state}
        )

    def set_active_incident(
        self,
        user_id: str,
        channel_id: str,
        incident_id: str
    ) -> bool:
        """Set the active incident ID."""
        return self.update_context(
            user_id,
            channel_id,
            {"active_incident_id": incident_id, "flow_type": "incident"}
        )

    def set_active_job(
        self,
        user_id: str,
        channel_id: str,
        job_id: str
    ) -> bool:
        """Set the active job ID."""
        return self.update_context(
            user_id,
            channel_id,
            {"active_job_id": job_id, "flow_type": "job"}
        )

    def update_discovery_progress(
        self,
        user_id: str,
        channel_id: str,
        progress: Dict[str, Any]
    ) -> bool:
        """Update discovery flow progress."""
        return self.update_context(
            user_id,
            channel_id,
            {"discovery_progress": progress}
        )

    def append_message(
        self,
        user_id: str,
        channel_id: str,
        role: str,
        content: str
    ) -> bool:
        """
        Append a message to the conversation history.

        Args:
            user_id: The user's ID
            channel_id: The channel ID
            role: "user" or "assistant"
            content: The message content

        Returns:
            True if successful
        """
        return self.update_context(
            user_id,
            channel_id,
            {"last_message": content, "last_message_at": datetime.utcnow().isoformat() + "Z"},
            append_to_history={"role": role, "content": content}
        )

    def clear_context(self, user_id: str, channel_id: str) -> bool:
        """
        Clear/reset a context (useful for starting fresh).

        Args:
            user_id: The user's ID
            channel_id: The channel ID

        Returns:
            True if successful
        """
        context_id = self._make_context_id(user_id, channel_id)

        try:
            self.table.delete_item(Key={"context_id": context_id})
            logger.info(f"[context-manager] Cleared context: {context_id}")
            return True
        except ClientError as e:
            logger.error(f"Error clearing context {context_id}: {e}")
            return False

    def get_conversation_history(
        self,
        user_id: str,
        channel_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get conversation history for context.

        Args:
            user_id: The user's ID
            channel_id: The channel ID
            limit: Optional limit on number of messages to return (most recent)

        Returns:
            List of conversation messages
        """
        context = self.get_context(user_id, channel_id, create_if_missing=False)

        if not context:
            return []

        history = context.get("conversation_history", [])

        if limit and len(history) > limit:
            return history[-limit:]

        return history

    def list_active_contexts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all active contexts for a user across all channels.

        Args:
            user_id: The user's ID

        Returns:
            List of active context dictionaries
        """
        try:
            # Scan for contexts matching user_id
            response = self.table.scan(
                FilterExpression="user_id = :uid",
                ExpressionAttributeValues={":uid": user_id}
            )

            contexts = [self._decimal_to_float(item) for item in response.get("Items", [])]

            # Filter out expired contexts
            now = datetime.utcnow()
            active_contexts = []

            for ctx in contexts:
                if "expires_at" in ctx:
                    expires_at = datetime.fromisoformat(ctx["expires_at"].replace("Z", "+00:00"))
                    if now <= expires_at:
                        active_contexts.append(ctx)

            return active_contexts

        except ClientError as e:
            logger.error(f"Error listing contexts for user {user_id}: {e}")
            return []

    def get_active_flows(self, user_id: str, channel_id: str) -> Dict[str, Any]:
        """
        Get summary of active flows for a context.

        Returns:
            Dictionary with active incidents, jobs, and flow states
        """
        context = self.get_context(user_id, channel_id, create_if_missing=False)

        if not context:
            return {
                "has_active_incident": False,
                "has_active_job": False,
                "flow_type": "general",
                "flow_state": "idle"
            }

        return {
            "has_active_incident": bool(context.get("active_incident_id")),
            "has_active_job": bool(context.get("active_job_id")),
            "active_incident_id": context.get("active_incident_id"),
            "active_job_id": context.get("active_job_id"),
            "flow_type": context.get("flow_type", "general"),
            "flow_state": context.get("flow_state", "idle"),
            "last_intent": context.get("last_intent"),
            "discovery_in_progress": bool(context.get("discovery_progress"))
        }


# Singleton instance
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Get or create the singleton ContextManager instance."""
    global _context_manager

    if _context_manager is None:
        _context_manager = ContextManager()

    return _context_manager
