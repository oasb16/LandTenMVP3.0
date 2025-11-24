"""
🔒 PRIMARY CONTEXT MANAGER for LandTen V3 AI Orchestrator
THIS IS THE ONLY CONTEXT MANAGER - DO NOT USE context_manager.py

Manages conversation state, flow stages, and context persistence for the LLM orchestrator.
All context operations MUST go through this service.

Key responsibilities:
- Store and retrieve meta-context (user_id, channel_id, stage, active_incident_id, discovery state)
- Track conversation history
- Manage discovery question flow
- Persist context to DynamoDB with TTL
- Provide context to orchestrator for decision-making

CRITICAL: This is the single source of truth for conversational context.
"""
from typing import Dict, Any, Optional, List
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
import json
import logging
from ..config.settings import settings
from ..models.orchestrator_schemas import MetaContext, DiscoveryState, ConversationMessage

logger = logging.getLogger(__name__)


class MetaContextManager:
    """Manages meta-context storage and retrieval"""

    def __init__(self):
        table_prefix = getattr(settings, "TABLE_PREFIX", "landten")
        stage = getattr(settings, "STAGE", "dev")
        self.table_name = f"{table_prefix}_{stage}_chat_contexts"
        self.ttl_hours = getattr(settings, "CONTEXT_TTL_HOURS", 24)
        self._dynamo_client = None
        self._table = None
        self._in_memory_cache = {}  # Fallback cache

    @property
    def dynamo_client(self):
        """Lazy DynamoDB client initialization"""
        if self._dynamo_client is None:
            self._dynamo_client = boto3.client("dynamodb", region_name=settings.AWS_REGION)
        return self._dynamo_client

    @property
    def table(self):
        """Lazy DynamoDB table initialization"""
        if self._table is None:
            dynamo_resource = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
            self._table = dynamo_resource.Table(self.table_name)
        return self._table

    def _get_ttl(self) -> int:
        """Calculate TTL timestamp"""
        return int((datetime.utcnow() + timedelta(hours=self.ttl_hours)).timestamp())

    def _normalize_decimals(self, obj: Any) -> Any:
        """Convert Decimal objects to float/int for JSON serialization"""
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        elif isinstance(obj, dict):
            return {k: self._normalize_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._normalize_decimals(item) for item in obj]
        return obj

    def _deserialize_context(self, raw_context: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize DynamoDB context into standard format"""
        context = self._normalize_decimals(raw_context)

        # Ensure required fields exist
        context.setdefault("persona", "tenant")
        context.setdefault("stage", "idle")
        context.setdefault("active_incident_id", None)
        context.setdefault("active_job_id", None)
        context.setdefault("discovery", {})
        context.setdefault("last_intent", None)
        context.setdefault("last_user_message", None)
        context.setdefault("conversation_history", [])
        context.setdefault("entities", {})
        context.setdefault("metadata", {})

        # Normalize discovery structure
        if "discovery" in context and not isinstance(context["discovery"], dict):
            context["discovery"] = {}

        discovery = context["discovery"]
        discovery.setdefault("question_index", 0)
        discovery.setdefault("questions", [])
        discovery.setdefault("answers", {})

        return context

    async def load_context(
        self,
        user_id: str,
        channel_id: str,
        create_if_missing: bool = True,
    ) -> MetaContext:
        """Load meta-context from DynamoDB"""
        try:
            pk = f"user#{user_id}"
            sk = f"channel#{channel_id}"

            # Try DynamoDB first
            response = self.table.get_item(Key={"pk": pk, "sk": sk})

            if "Item" in response:
                raw_context = response["Item"]
                context_data = self._deserialize_context(raw_context)

                # Remove user_id and channel_id from context_data to avoid duplicate kwargs
                context_data.pop("user_id", None)
                context_data.pop("channel_id", None)

                # Create Pydantic model
                meta_context = MetaContext(
                    user_id=user_id,
                    channel_id=channel_id,
                    **context_data,
                )

                logger.info(f"Loaded context for user {user_id}, channel {channel_id}")
                return meta_context

            elif create_if_missing:
                # Create new context
                return await self._create_new_context(user_id, channel_id)

            else:
                raise ValueError(f"Context not found for user {user_id}, channel {channel_id}")

        except Exception as e:
            logger.error(f"Error loading context from DynamoDB: {e}", exc_info=True)

            # Fallback to in-memory cache
            cache_key = f"{user_id}:{channel_id}"
            if cache_key in self._in_memory_cache:
                logger.warning(f"Using in-memory cached context for {cache_key}")
                return MetaContext(**self._in_memory_cache[cache_key])

            elif create_if_missing:
                logger.warning(f"Creating new in-memory context for {cache_key}")
                return await self._create_new_context(user_id, channel_id)

            raise

    async def _create_new_context(self, user_id: str, channel_id: str) -> MetaContext:
        """Create a new meta-context"""
        now = datetime.utcnow().isoformat()

        meta_context = MetaContext(
            user_id=user_id,
            channel_id=channel_id,
            persona="tenant",
            stage="idle",
            created_at=now,
            updated_at=now,
        )

        # Save to DynamoDB
        await self.save_context(user_id, channel_id, meta_context)

        logger.info(f"Created new context for user {user_id}, channel {channel_id}")
        return meta_context

    async def save_context(
        self,
        user_id: str,
        channel_id: str,
        meta_context: MetaContext,
    ) -> None:
        """Save meta-context to DynamoDB"""
        try:
            pk = f"user#{user_id}"
            sk = f"channel#{channel_id}"

            # Convert Pydantic model to dict
            context_dict = meta_context.model_dump(exclude_none=False)

            # Prepare DynamoDB item
            item = {
                "pk": pk,
                "sk": sk,
                "user_id": user_id,
                "channel_id": channel_id,
                "updated_at": datetime.utcnow().isoformat(),
                "ttl": self._get_ttl(),
                **context_dict,
            }

            # Save to DynamoDB
            self.table.put_item(Item=item)

            # Update in-memory cache
            cache_key = f"{user_id}:{channel_id}"
            self._in_memory_cache[cache_key] = context_dict

            logger.info(f"Saved context for user {user_id}, channel {channel_id}")

        except Exception as e:
            logger.error(f"Error saving context to DynamoDB: {e}", exc_info=True)

            # Fallback to in-memory only
            cache_key = f"{user_id}:{channel_id}"
            self._in_memory_cache[cache_key] = context_dict
            logger.warning(f"Saved context to in-memory cache only: {cache_key}")

    async def update_context(
        self,
        user_id: str,
        channel_id: str,
        updates: Dict[str, Any],
    ) -> MetaContext:
        """Update meta-context with partial updates"""
        # Load current context
        meta_context = await self.load_context(user_id, channel_id)

        # Apply updates
        context_dict = meta_context.model_dump()

        for key, value in updates.items():
            if value is not None or key in updates:  # Allow explicit None to clear fields
                if key == "discovery" and isinstance(value, dict):
                    # Merge discovery updates
                    context_dict["discovery"] = {
                        **context_dict.get("discovery", {}),
                        **value,
                    }
                elif key == "entities" and isinstance(value, dict):
                    # Merge entities
                    context_dict["entities"] = {
                        **context_dict.get("entities", {}),
                        **value,
                    }
                elif key == "metadata" and isinstance(value, dict):
                    # Merge metadata
                    context_dict["metadata"] = {
                        **context_dict.get("metadata", {}),
                        **value,
                    }
                else:
                    context_dict[key] = value

        # Update timestamp
        context_dict["updated_at"] = datetime.utcnow().isoformat()

        # Create updated context
        updated_context = MetaContext(**context_dict)

        # Save to DynamoDB
        await self.save_context(user_id, channel_id, updated_context)

        logger.info(f"Updated context for user {user_id}, channel {channel_id}: {list(updates.keys())}")

        return updated_context

    async def append_message(
        self,
        user_id: str,
        channel_id: str,
        role: str,
        text: str,
    ) -> None:
        """Append message to conversation history"""
        meta_context = await self.load_context(user_id, channel_id)

        message = ConversationMessage(
            role=role,
            text=text,
            timestamp=datetime.utcnow().isoformat(),
        )

        # Append to history (limit to last 20 messages)
        history = meta_context.conversation_history[-19:] + [message]

        await self.update_context(
            user_id,
            channel_id,
            {"conversation_history": [msg.model_dump() for msg in history]},
        )

    async def set_persona(
        self,
        user_id: str,
        channel_id: str,
        persona: str,
    ) -> None:
        """Set user persona"""
        await self.update_context(user_id, channel_id, {"persona": persona})

    async def set_active_incident(
        self,
        user_id: str,
        channel_id: str,
        incident_id: str,
    ) -> None:
        """Set active incident ID"""
        await self.update_context(
            user_id,
            channel_id,
            {
                "active_incident_id": incident_id,
                "discovery": {"incident_id": incident_id},
            },
        )

    async def set_active_job(
        self,
        user_id: str,
        channel_id: str,
        job_id: str,
    ) -> None:
        """Set active job ID"""
        await self.update_context(user_id, channel_id, {"active_job_id": job_id})

    async def clear_active_incident(self, user_id: str, channel_id: str) -> None:
        """Clear active incident"""
        await self.update_context(user_id, channel_id, {"active_incident_id": None})

    async def clear_active_job(self, user_id: str, channel_id: str) -> None:
        """Clear active job"""
        await self.update_context(user_id, channel_id, {"active_job_id": None})

    async def advance_stage(
        self,
        user_id: str,
        channel_id: str,
        new_stage: str,
        additional_updates: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Advance flow stage"""
        updates = {"stage": new_stage}
        if additional_updates:
            updates.update(additional_updates)

        await self.update_context(user_id, channel_id, updates)

    async def reset_discovery(self, user_id: str, channel_id: str) -> None:
        """Reset discovery state"""
        await self.update_context(
            user_id,
            channel_id,
            {
                "discovery": {
                    "question_index": 0,
                    "questions": [],
                    "answers": {},
                }
            },
        )

    async def merge_context_updates(
        self,
        user_id: str,
        channel_id: str,
        context_updates: Dict[str, Any],
    ) -> MetaContext:
        """
        Merge context updates from orchestrator output.
        This is the primary method used by the orchestrator.
        """
        # Filter out None values and empty dicts unless explicitly needed
        filtered_updates = {}

        for key, value in context_updates.items():
            # Skip next_action (it's metadata, not persisted)
            if key == "next_action":
                continue

            # Allow explicit None to clear fields
            if value is None and key in context_updates:
                filtered_updates[key] = None
            elif value is not None:
                filtered_updates[key] = value

        # Update context
        return await self.update_context(user_id, channel_id, filtered_updates)

    async def get_conversation_summary(
        self,
        user_id: str,
        channel_id: str,
        max_messages: int = 10,
    ) -> str:
        """Get formatted conversation history for LLM context"""
        meta_context = await self.load_context(user_id, channel_id)

        history = meta_context.conversation_history[-max_messages:]

        if not history:
            return "No previous conversation."

        lines = []
        for msg in history:
            role = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{role}: {msg.text}")

        return "\n".join(lines)

    async def list_active_contexts(self, user_id: str) -> List[Dict[str, Any]]:
        """List all active contexts for a user"""
        try:
            pk = f"user#{user_id}"

            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": pk},
            )

            contexts = []
            for item in response.get("Items", []):
                contexts.append(self._deserialize_context(item))

            return contexts

        except Exception as e:
            logger.error(f"Error listing contexts: {e}", exc_info=True)
            return []

    async def delete_context(self, user_id: str, channel_id: str) -> None:
        """Delete a context"""
        try:
            pk = f"user#{user_id}"
            sk = f"channel#{channel_id}"

            self.table.delete_item(Key={"pk": pk, "sk": sk})

            # Remove from cache
            cache_key = f"{user_id}:{channel_id}"
            if cache_key in self._in_memory_cache:
                del self._in_memory_cache[cache_key]

            logger.info(f"Deleted context for user {user_id}, channel {channel_id}")

        except Exception as e:
            logger.error(f"Error deleting context: {e}", exc_info=True)

    # ==================== DIAGNOSIS TRACKING METHODS ====================

    async def set_diagnosis_complete(
        self,
        user_id: str,
        channel_id: str,
        incident_id: str,
    ) -> None:
        """
        🚨 CRITICAL FIX: Mark diagnosis as completed for an incident.
        This prevents the orchestrator from calling start_diagnosis multiple times.
        """
        await self.update_context(
            user_id,
            channel_id,
            {
                "metadata": {
                    "diagnosis_complete": True,
                    "last_diagnosis_time": datetime.utcnow().isoformat(),
                    "diagnosed_incident_id": incident_id,
                }
            },
        )
        logger.info(f"✅ Marked diagnosis complete for incident {incident_id}")

    async def track_function_call(
        self,
        user_id: str,
        channel_id: str,
        function_name: str,
    ) -> None:
        """
        Track the last function call made by the orchestrator.
        Used to prevent repeated calls to the same function.
        """
        await self.update_context(
            user_id,
            channel_id,
            {
                "metadata": {
                    "last_tool_called": function_name,
                    "last_tool_called_at": datetime.utcnow().isoformat(),
                }
            },
        )
        logger.info(f"📝 Tracked function call: {function_name}")

    async def get_diagnosis_status(
        self,
        user_id: str,
        channel_id: str,
    ) -> Dict[str, Any]:
        """
        Get diagnosis completion status for current incident.
        Returns dict with diagnosis_complete, last_tool_called, etc.
        """
        meta_context = await self.load_context(user_id, channel_id)
        return {
            "diagnosis_complete": meta_context.metadata.get("diagnosis_complete", False),
            "last_tool_called": meta_context.metadata.get("last_tool_called"),
            "last_diagnosis_time": meta_context.metadata.get("last_diagnosis_time"),
            "diagnosed_incident_id": meta_context.metadata.get("diagnosed_incident_id"),
        }

    async def clear_diagnosis_tracking(
        self,
        user_id: str,
        channel_id: str,
    ) -> None:
        """
        Clear diagnosis tracking when incident is completed or new incident starts.
        """
        await self.update_context(
            user_id,
            channel_id,
            {
                "metadata": {
                    "diagnosis_complete": False,
                    "last_diagnosis_time": None,
                    "diagnosed_incident_id": None,
                }
            },
        )
        logger.info(f"🧹 Cleared diagnosis tracking")


# Singleton instance
_meta_context_manager = None


def get_meta_context_manager() -> MetaContextManager:
    """Get singleton instance of MetaContextManager"""
    global _meta_context_manager
    if _meta_context_manager is None:
        _meta_context_manager = MetaContextManager()
    return _meta_context_manager
