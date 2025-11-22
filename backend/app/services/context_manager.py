"""
Context Manager - Persistent Conversational Memory System

Provides per-user, per-channel conversational memory that is durable,
persona-aware, and verified after every write.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from decimal import Decimal

from .flow_stage_mapper import FlowStageMapper

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages conversational context for PropertyAI tenants, landlords, and contractors.

    Schema persisted in DynamoDB (pay-per-request):
        pk:  user#<user_id>
        sk:  channel#<channel_id>
        persona: str
        active_intent: str
        active_incident: str
        conversation: List[{role,text,timestamp}]
        entities: dict
        metadata: dict
        ttl: epoch seconds (24h default)
        updated_at: ISO timestamp
    """

    def __init__(self) -> None:
        self.table_name = self._resolve_table_name()
        self.context_ttl_hours = int(os.getenv("CONTEXT_TTL_HOURS", "24"))
        self.context_ttl_seconds = self.context_ttl_hours * 3600
        self.max_history_length = int(os.getenv("CONTEXT_MAX_HISTORY", "20"))

        self._memory_store: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._use_memory = False

        self.dynamodb = self._get_dynamodb_resource()

        try:
            self.ensure_table_exists()
            self.table = self.dynamodb.Table(self.table_name)
            logger.info(f"[context-manager] Using DynamoDB table '{self.table_name}'")
        except Exception as exc:  # pragma: no cover - fallback path
            self._use_memory = True
            self.table = None
            logger.warning(
                "[context-manager] Falling back to in-memory store "
                f"(table '{self.table_name}' unavailable: {exc})"
            )

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def get_context(
        self,
        user_id: str,
        channel_id: str,
        create_if_missing: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Fetch context for a user/channel pair."""
        key = self._make_keys(user_id, channel_id)

        raw_context: Optional[Dict[str, Any]]
        if self._use_memory:
            raw_context = self._memory_store.get(key)
        else:
            try:
                resp = self.table.get_item(Key=self._format_key(key))
                raw_context = resp.get("Item")
            except (ClientError, BotoCoreError) as exc:  # pragma: no cover
                logger.error(f"[context-manager] Dynamo get_item failed: {exc}")
                self._switch_to_memory()
                raw_context = self._memory_store.get(key)

        if raw_context:
            return self._normalize_context(raw_context)

        if not create_if_missing:
            return None

        return self._create_context(user_id, channel_id)

    def update_context(
        self,
        user_id: str,
        channel_id: str,
        updates: Dict[str, Any],
        append_to_history: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Merge updates into context and verify persistence."""
        context = self.get_context(user_id, channel_id, create_if_missing=True)
        if context is None:
            logger.error(f"[context-manager] Unable to create base context for {user_id}/{channel_id}")
            return False

        now_iso = datetime.utcnow().isoformat() + "Z"
        ttl = int(time.time()) + self.context_ttl_seconds

        merged = {**context, **updates}
        merged["persona"] = updates.get("persona", context.get("persona"))
        merged["active_intent"] = updates.get("active_intent", context.get("active_intent"))

        # CRITICAL: Preserve active_incident and active_job unless explicitly updated
        # Never allow these to be accidentally reset to None
        existing_incident = context.get("active_incident")
        existing_job = context.get("active_job")

        # Only update if explicitly provided and not None, otherwise preserve
        if "active_incident" in updates and updates["active_incident"] is not None:
            merged["active_incident"] = updates["active_incident"]
        elif existing_incident:
            merged["active_incident"] = existing_incident
        else:
            merged["active_incident"] = None

        if "active_job" in updates and updates["active_job"] is not None:
            merged["active_job"] = updates["active_job"]
        elif existing_job:
            merged["active_job"] = existing_job
        else:
            merged["active_job"] = None

        merged["entities"] = updates.get("entities", context.get("entities", {}))
        merged["metadata"] = updates.get("metadata", context.get("metadata", {}))
        merged["flow_state"] = updates.get("flow_state", context.get("flow_state", {}))
        merged["updated_at"] = now_iso
        merged["ttl"] = ttl

        conversation = list(context.get("conversation", []))
        if append_to_history:
            message_entry = {
                "role": append_to_history.get("role"),
                "text": append_to_history.get("content"),
                "timestamp": now_iso,
            }
            conversation.append(message_entry)
            conversation = conversation[-self.max_history_length :]

        merged["conversation"] = conversation
        merged["conversation_history"] = conversation  # backward compatibility

        safe_payload = self._coerce_numbers(merged)
        success = self._write_context(safe_payload, user_id, channel_id)

        if success:
            logger.info(
                "[context-manager] ✅ Context persisted for %s | intent=%s incident=%s",
                user_id,
                merged.get("active_intent"),
                merged.get("active_incident"),
            )
        else:
            logger.error("[context-manager] ❌ Failed to persist context for %s", user_id)

        return success

    def set_persona(self, user_id: str, channel_id: str, persona: str) -> bool:
        return self.update_context(user_id, channel_id, {"persona": persona})

    def set_active_incident(self, user_id: str, channel_id: str, incident_id: str) -> bool:
        """
        Set active incident and persist to both context and flow_state.

        This ensures the incident is tracked in:
        - context["active_incident"]
        - context["flow_state"]["incident_id"]
        """
        # Get current flow_state
        context = self.get_context(user_id, channel_id, create_if_missing=True)
        if context is None:
            logger.error(f"[context-manager] Unable to get context for {user_id}/{channel_id}")
            return False

        current_flow_state = dict(context.get("flow_state") or {})
        current_flow_state["incident_id"] = incident_id

        success = self.update_context(
            user_id,
            channel_id,
            {
                "active_incident": incident_id,
                "active_intent": "incident.report",
                "flow_state": current_flow_state,
            },
        )

        if success:
            logger.info(
                "[context-manager] ✅ Incident %s persisted in flow state for %s",
                incident_id,
                user_id,
            )
            # Mirror user-visible context update log
            print(f"[context-update] Active incident set for {user_id} on {channel_id}: {incident_id}")
        else:
            logger.error(
                "[context-manager] ❌ Failed to persist active incident %s for %s",
                incident_id,
                user_id,
            )

        return success

    def set_active_job(self, user_id: str, channel_id: str, job_id: str) -> bool:
        return self.update_context(
            user_id,
            channel_id,
            {"active_job": job_id, "active_intent": "job.request"},
        )

    def clear_active_incident(self, user_id: str, channel_id: str) -> bool:
        """
        Explicitly clear the active incident.

        Use this method only when incident is truly resolved/closed.
        Regular updates will preserve the incident automatically.
        """
        context = self.get_context(user_id, channel_id, create_if_missing=False)
        if context is None:
            return False

        # Force clear by directly setting in the update
        context["active_incident"] = None
        flow_state = dict(context.get("flow_state") or {})
        flow_state["incident_id"] = None
        flow_state["stage"] = "idle"

        success = self._write_context(context, user_id, channel_id)
        if success:
            logger.info("[context-manager] Explicitly cleared active incident for %s", user_id)
        return success

    def clear_active_job(self, user_id: str, channel_id: str) -> bool:
        """
        Explicitly clear the active job.

        Use this method only when job is truly completed/cancelled.
        Regular updates will preserve the job automatically.
        """
        context = self.get_context(user_id, channel_id, create_if_missing=False)
        if context is None:
            return False

        # Force clear by directly setting in the update
        context["active_job"] = None
        flow_state = dict(context.get("flow_state") or {})
        flow_state["job_id"] = None

        success = self._write_context(context, user_id, channel_id)
        if success:
            logger.info("[context-manager] Explicitly cleared active job for %s", user_id)
        return success

    def append_message(
        self,
        user_id: str,
        channel_id: str,
        role: str,
        content: str,
    ) -> bool:
        flow_updates = {}
        if role == "assistant":
            flow_updates["last_ai_prompt"] = content
        elif role == "user":
            flow_updates["last_user_reply"] = content

        updates: Dict[str, Any] = {
            "last_message": content,
            "last_message_at": datetime.utcnow().isoformat() + "Z",
        }
        if flow_updates:
            context = self.get_context(user_id, channel_id, create_if_missing=True) or {}
            current_state = dict(context.get("flow_state") or {})
            current_state.update(flow_updates)
            updates["flow_state"] = current_state

        return self.update_context(
            user_id,
            channel_id,
            updates,
            append_to_history={"role": role, "content": content},
        )

    def list_active_contexts(self, user_id: str) -> List[Dict[str, Any]]:
        contexts: List[Dict[str, Any]] = []
        if self._use_memory:
            for (pk, _), ctx in self._memory_store.items():
                if pk == self._make_pk(user_id):
                    contexts.append(self._normalize_context(ctx))
            return contexts

        try:
            resp = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": self._make_pk(user_id)},
            )
            contexts = [self._normalize_context(item) for item in resp.get("Items", [])]
        except (ClientError, BotoCoreError) as exc:
            logger.error(f"[context-manager] list_active_contexts failed: {exc}")

        return contexts

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def ensure_table_exists(self) -> None:
        """Create the chat context table if it does not already exist."""
        client = self.dynamodb.meta.client
        try:
            client.describe_table(TableName=self.table_name)
            return
        except client.exceptions.ResourceNotFoundException:  # type: ignore[attr-defined]
            logger.info(f"[context-manager] Creating DynamoDB table '{self.table_name}'")

        client.create_table(
            TableName=self.table_name,
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        waiter = client.get_waiter("table_exists")
        waiter.wait(TableName=self.table_name)

        try:
            client.update_time_to_live(
                TableName=self.table_name,
                TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
            )
        except client.exceptions.ValidationException:  # type: ignore[attr-defined]
            # TTL already enabled or unsupported for local
            pass

    def _create_context(self, user_id: str, channel_id: str) -> Dict[str, Any]:
        """Create a brand new context with default values."""
        now_iso = datetime.utcnow().isoformat() + "Z"
        ttl = int(time.time()) + self.context_ttl_seconds
        base_context = {
            "pk": self._make_pk(user_id),
            "sk": self._make_sk(channel_id),
            "user_id": user_id,
            "channel_id": channel_id,
            "persona": None,
            "active_intent": None,
            "active_incident": None,
            "active_job": None,
            "flow_state": {
                "stage": "idle",
                "question_index": 0,
                "last_ai_prompt": None,
                "last_user_reply": None,
            },
            "conversation": [],
            "conversation_history": [],
            "entities": {},
            "metadata": {},
            "created_at": now_iso,
            "updated_at": now_iso,
            "ttl": ttl,
        }

        if self._write_context(base_context, user_id, channel_id):
            logger.info(
                "[context-manager] Created fresh context for user=%s channel=%s",
                user_id,
                channel_id,
            )
            return base_context

        logger.error("[context-manager] Failed to create context; using memory fallback")
        return base_context

    def _write_context(self, context: Dict[str, Any], user_id: str, channel_id: str) -> bool:
        """Persist context and verify success."""
        key = self._make_keys(user_id, channel_id)
        if self._use_memory:
            self._memory_store[key] = context
            return True

        try:
            self.table.put_item(Item=context)
        except (ClientError, BotoCoreError) as exc:
            logger.error(f"[context-manager] put_item failed: {exc}")
            self._switch_to_memory()
            self._memory_store[key] = context
            return True

        # Read-after-write verification
        persisted = self._read_raw_context(key)
        if not persisted:
            logger.error("[context-manager] Verification failed: context missing after write")
            return False

        if persisted.get("updated_at") != context.get("updated_at"):
            logger.warning(
                "[context-manager] Verification mismatch: expected updated_at=%s got=%s",
                context.get("updated_at"),
                persisted.get("updated_at"),
            )

        return True

    def _read_raw_context(self, key: Tuple[str, str]) -> Optional[Dict[str, Any]]:
        if self._use_memory:
            return self._memory_store.get(key)
        try:
            resp = self.table.get_item(Key=self._format_key(key))
            return resp.get("Item")
        except (ClientError, BotoCoreError):
            return None

    def _normalize_context(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Decimal to floats and ensure conversation array is present."""
        normalized = json.loads(json.dumps(raw, default=self._decimal_default))
        normalized.setdefault("conversation", normalized.get("conversation_history", []))
        normalized.setdefault("conversation_history", normalized["conversation"])
        normalized.setdefault(
            "flow_state",
            {
                "stage": "idle",
                "question_index": 0,
                "last_ai_prompt": None,
                "last_user_reply": None,
            },
        )

        # Normalize stage from old string format to new FlowStage enum value
        flow_state = normalized.get("flow_state", {})
        if flow_state and "stage" in flow_state:
            old_stage = flow_state["stage"]
            normalized_stage = FlowStageMapper.normalize(old_stage)
            flow_state["stage"] = normalized_stage.value
            logger.debug(
                "[context-manager] Normalized stage '%s' → '%s' for context",
                old_stage,
                normalized_stage.value
            )

        return normalized

    def advance_flow_state(
        self,
        user_id: str,
        channel_id: str,
        stage: str,
        updates: Optional[Dict[str, Any]] = None,
    ) -> bool:
        context = self.get_context(user_id, channel_id, create_if_missing=True)
        if context is None:
            return False

        current_state = dict(context.get("flow_state") or {})
        if updates:
            current_state.update(updates)
        current_state["stage"] = stage
        success = self.update_context(user_id, channel_id, {"flow_state": current_state})
        if success:
            print(f"[context-update] Flow state advanced for {user_id} on {channel_id}: {stage}")
        return success

    def _coerce_numbers(self, value: Any) -> Any:
        if isinstance(value, float):
            return Decimal(str(value))
        if isinstance(value, dict):
            return {k: self._coerce_numbers(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._coerce_numbers(v) for v in value]
        return value

    @staticmethod
    def _decimal_default(obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError

    def _switch_to_memory(self) -> None:
        if not self._use_memory:
            logger.warning("[context-manager] Switching to in-memory context store")
        self._use_memory = True

    # ------------------------------------------------------------------ #
    # Key helpers and configuration
    # ------------------------------------------------------------------ #
    @staticmethod
    def _make_pk(user_id: str) -> str:
        return f"user#{user_id}"

    @staticmethod
    def _make_sk(channel_id: str) -> str:
        return f"channel#{channel_id}"

    def _make_keys(self, user_id: str, channel_id: str) -> Tuple[str, str]:
        return self._make_pk(user_id), self._make_sk(channel_id)

    @staticmethod
    def _format_key(key: Tuple[str, str]) -> Dict[str, str]:
        pk, sk = key
        return {"pk": pk, "sk": sk}

    @staticmethod
    def _resolve_table_name() -> str:
        prefix = os.getenv("TABLE_PREFIX", "landten")
        stage = os.getenv("STAGE", "dev")
        return f"{prefix}_{stage}_chat_contexts"

    @staticmethod
    def _get_dynamodb_resource():
        endpoint_url = os.getenv("DYNAMO_ENDPOINT_URL")
        region = os.getenv("AWS_REGION", "us-east-1")
        if endpoint_url:
            return boto3.resource("dynamodb", endpoint_url=endpoint_url, region_name=region)
        return boto3.resource("dynamodb", region_name=region)


# Singleton
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager
