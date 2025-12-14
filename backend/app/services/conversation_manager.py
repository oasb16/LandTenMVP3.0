"""
ConversationManager - OpenAI Conversations API Integration

Manages mapping between Slack channels and OpenAI Conversations.
Replaces heavy meta_context storage with lightweight Conversations API.

Key Concepts:
- channel_id → conversation_id mapping (stored in DynamoDB)
- State stored in Conversation metadata + custom items
- Messages/tool calls auto-stored by Conversations API
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import openai

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages OpenAI Conversations for LandTen maintenance system.

    Replaces meta_context with native Conversations API:
    - Lightweight: Only stores channel_id → conversation_id mapping in DynamoDB
    - Server-side: OpenAI stores messages, tool calls, outputs
    - Stateful: Conversation metadata holds user_id, persona, property_id
    - Custom items: Store stage, active_incident_id, discovery state
    """

    def __init__(self, dynamo_service=None):
        """
        Initialize ConversationManager.

        Args:
            dynamo_service: DynamoDB service instance (for mapping storage)
        """
        self.dynamo = dynamo_service
        self.openai_client = openai.AsyncClient(api_key=os.getenv("OPENAI_API_KEY"))

    async def get_or_create_conversation(
        self,
        channel_id: str,
        user_id: str,
        persona: str = "tenant",
        property_id: Optional[str] = None
    ) -> str:
        """
        Get existing conversation_id or create new one.

        Maps channel_id → conversation_id (one-to-one mapping).
        Creates new conversation if mapping doesn't exist.

        Args:
            channel_id: Slack channel ID
            user_id: User identifier
            persona: User role (tenant, landlord, contractor)
            property_id: Optional property identifier

        Returns:
            conversation_id: OpenAI Conversation ID
        """
        # Check if mapping exists
        mapping = self.dynamo.get_conversation_mapping(channel_id) if self.dynamo else None

        if mapping and mapping.get("conversation_id"):
            conversation_id = mapping["conversation_id"]
            logger.info(f"Found existing conversation: {conversation_id} for channel: {channel_id}")
            return conversation_id

        # Create new conversation
        logger.info(f"Creating new conversation for channel: {channel_id}")

        conversation = await self.openai_client.conversations.create(
            metadata={
                "channel_id": channel_id,
                "user_id": user_id,
                "persona": persona,
                "property_id": property_id or "",
                "created_at": datetime.utcnow().isoformat(),
            }
        )

        conversation_id = conversation.id
        logger.info(f"Created conversation: {conversation_id}")

        # Store mapping in DynamoDB
        if self.dynamo:
            self.dynamo.save_conversation_mapping(
                channel_id=channel_id,
                conversation_id=conversation_id,
                user_id=user_id,
                persona=persona
            )
            logger.info(f"Saved mapping: {channel_id} → {conversation_id}")

        return conversation_id

    async def get_conversation_state(self, conversation_id: str) -> Dict[str, Any]:
        """
        Extract current state from conversation.

        Reads conversation items and metadata to reconstruct state
        similar to old meta_context structure.

        Args:
            conversation_id: OpenAI Conversation ID

        Returns:
            dict: State dictionary with stage, active_incident_id, discovery, etc.
        """
        try:
            # Get conversation details
            conversation = await self.openai_client.conversations.retrieve(conversation_id)

            # Get conversation items (messages, tool calls, custom state items)
            items = await self.openai_client.conversations.items.list(conversation_id)

            # Extract state from items
            state = self._extract_state_from_items(items.data)

            # Add metadata
            state["user_id"] = conversation.metadata.get("user_id", "")
            state["channel_id"] = conversation.metadata.get("channel_id", "")
            state["persona"] = conversation.metadata.get("persona", "tenant")
            state["property_id"] = conversation.metadata.get("property_id")

            return state

        except Exception as e:
            logger.error(f"Failed to get conversation state: {e}")
            return {
                "stage": "idle",
                "active_incident_id": None,
                "discovery": {
                    "question_index": 0,
                    "questions": [],
                    "answers": {},
                    "is_active": False
                }
            }

    async def update_conversation_state(
        self,
        conversation_id: str,
        state: Dict[str, Any]
    ):
        """
        Update conversation state.

        Stores state updates as custom items in the conversation.

        Args:
            conversation_id: OpenAI Conversation ID
            state: State dictionary to update (stage, active_incident_id, etc.)
        """
        try:
            # Add custom state item
            await self.add_custom_state_item(
                conversation_id=conversation_id,
                state_type="state_update",
                data=state
            )
            logger.info(f"Updated conversation state: {conversation_id}")

        except Exception as e:
            logger.error(f"Failed to update conversation state: {e}")

    async def add_custom_state_item(
        self,
        conversation_id: str,
        state_type: str,
        data: Dict[str, Any]
    ):
        """
        Add a custom state item to the conversation.

        Custom items are used to store:
        - stage transitions
        - active_incident_id changes
        - discovery state updates
        - Any other state that needs persistence

        Args:
            conversation_id: OpenAI Conversation ID
            state_type: Type of state (e.g., "stage_update", "incident_update")
            data: State data to store
        """
        try:
            await self.openai_client.conversations.items.create(
                conversation_id=conversation_id,
                item={
                    "type": "custom",
                    "custom_type": state_type,
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            logger.debug(f"Added custom state item: {state_type} to {conversation_id}")

        except Exception as e:
            logger.error(f"Failed to add custom state item: {e}")

    def _extract_state_from_items(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract current state from conversation items.

        Scans through items in reverse chronological order to find:
        - Latest stage
        - Latest active_incident_id
        - Latest discovery state

        Args:
            items: List of conversation items

        Returns:
            dict: Extracted state
        """
        state = {
            "stage": "idle",
            "active_incident_id": None,
            "discovery": {
                "question_index": 0,
                "questions": [],
                "answers": {},
                "is_active": False
            }
        }

        # Iterate in reverse (most recent first)
        for item in reversed(items):
            if item.get("type") == "custom":
                custom_type = item.get("custom_type")
                data = item.get("data", {})

                # Update state from custom items
                if "stage" in data and state["stage"] == "idle":
                    state["stage"] = data["stage"]

                if "active_incident_id" in data and not state["active_incident_id"]:
                    state["active_incident_id"] = data["active_incident_id"]

                if "discovery" in data:
                    state["discovery"] = data["discovery"]

        return state

    async def delete_conversation(self, channel_id: str):
        """
        Delete conversation and mapping.

        Use when conversation should be reset or removed.

        Args:
            channel_id: Slack channel ID
        """
        try:
            # Get mapping
            mapping = self.dynamo.get_conversation_mapping(channel_id) if self.dynamo else None

            if mapping and mapping.get("conversation_id"):
                conversation_id = mapping["conversation_id"]

                # Delete from OpenAI (if API supports it)
                # Note: As of now, Conversations API may not have delete endpoint
                # In that case, we just remove the mapping
                logger.info(f"Removing conversation mapping for: {channel_id}")

                # Delete mapping from DynamoDB
                if self.dynamo:
                    self.dynamo.delete_conversation_mapping(channel_id)

            logger.info(f"Deleted conversation for channel: {channel_id}")

        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")


def extract_state_from_conversation(conversation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper function to convert Conversation object to meta_context-like structure.

    This is useful for backward compatibility during migration.

    Args:
        conversation: OpenAI Conversation object

    Returns:
        dict: Meta-context-like state structure
    """
    metadata = conversation.get("metadata", {})

    return {
        "user_id": metadata.get("user_id", ""),
        "channel_id": metadata.get("channel_id", ""),
        "persona": metadata.get("persona", "tenant"),
        "stage": "idle",  # Will be extracted from items
        "active_incident_id": None,  # Will be extracted from items
        "discovery": {
            "question_index": 0,
            "questions": [],
            "answers": {},
            "is_active": False
        },
        "property_id": metadata.get("property_id"),
        "created_at": metadata.get("created_at"),
    }


# Singleton instance
_conversation_manager = None


def get_conversation_manager(dynamo_service=None):
    """Get or create ConversationManager singleton"""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager(dynamo_service=dynamo_service)
    return _conversation_manager
