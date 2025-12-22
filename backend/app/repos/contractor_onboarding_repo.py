"""
Contractor Onboarding State Repository

DynamoDB operations for contractor onboarding state tracking.
"""

from typing import Dict, Any, Optional, List
from boto3.dynamodb.conditions import Attr, Key
from ..deps.dynamo import get_dynamo_resource, table_name
import logging

logger = logging.getLogger(__name__)


class ContractorOnboardingRepo:
    """Repository for contractor onboarding state operations."""

    def __init__(self):
        self.table = get_dynamo_resource().Table(table_name("contractor_onboarding_states"))

    def create_or_get_state(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create new onboarding state or get existing one.

        This ensures no duplicate onboarding for the same contractor.

        Args:
            state_data: Onboarding state data

        Returns:
            Created or existing state
        """
        contractor_id = state_data.get("contractor_id")

        # Check if state already exists for this contractor
        existing = self.get_by_contractor_id(contractor_id)

        if existing:
            logger.info(f"[onboarding-repo] Found existing state for contractor {contractor_id}")
            return existing

        # Create new state
        self.table.put_item(Item=state_data)
        logger.info(f"[onboarding-repo] Created new state for contractor {contractor_id}")
        return state_data

    def get_by_state_id(self, state_id: str) -> Optional[Dict[str, Any]]:
        """Get onboarding state by state_id."""
        resp = self.table.get_item(Key={"state_id": state_id})
        return resp.get("Item")

    def get_by_contractor_id(self, contractor_id: str) -> Optional[Dict[str, Any]]:
        """
        Get onboarding state by contractor_id.

        Uses GSI contractor_id-index.
        """
        resp = self.table.query(
            IndexName="contractor_id-index",
            KeyConditionExpression=Key("contractor_id").eq(contractor_id),
            Limit=1
        )
        items = resp.get("Items", [])
        return items[0] if items else None

    def get_by_channel_id(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get onboarding state by channel_id.

        Uses GSI channel_id-index.
        """
        resp = self.table.query(
            IndexName="channel_id-index",
            KeyConditionExpression=Key("channel_id").eq(channel_id),
            Limit=1
        )
        items = resp.get("Items", [])
        return items[0] if items else None

    def get_by_token_id(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Get onboarding state by magic link token_id."""
        resp = self.table.scan(
            FilterExpression=Attr("token_id").eq(token_id),
            Limit=1
        )
        items = resp.get("Items", [])
        return items[0] if items else None

    def update_state(self, state_id: str, updates: Dict[str, Any]) -> None:
        """
        Update onboarding state.

        Args:
            state_id: State ID to update
            updates: Dictionary of fields to update
        """
        # Build update expression
        update_parts = []
        attr_names = {}
        attr_values = {}

        for i, (key, value) in enumerate(updates.items()):
            attr_key = f"#attr{i}"
            value_key = f":val{i}"

            update_parts.append(f"{attr_key} = {value_key}")
            attr_names[attr_key] = key
            attr_values[value_key] = value

        update_expression = "SET " + ", ".join(update_parts)

        self.table.update_item(
            Key={"state_id": state_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=attr_names,
            ExpressionAttributeValues=attr_values
        )

        logger.info(f"[onboarding-repo] Updated state {state_id}")

    def mark_card_sent(self, state_id: str, card_type: str, sent_at: str) -> None:
        """
        Mark that a card was sent to prevent duplicates.

        Args:
            state_id: State ID
            card_type: Type of card (license_verification, identity_verification, etc.)
            sent_at: ISO timestamp when card was sent
        """
        self.table.update_item(
            Key={"state_id": state_id},
            UpdateExpression="SET cards_sent.#card_type = :sent_at, last_interaction_at = :now",
            ExpressionAttributeNames={"#card_type": card_type},
            ExpressionAttributeValues={
                ":sent_at": sent_at,
                ":now": sent_at
            }
        )

        logger.info(f"[onboarding-repo] Marked {card_type} card sent for state {state_id}")

    def update_license_data(self, state_id: str, license_data: Dict[str, Any]) -> None:
        """Update license verification data."""
        self.table.update_item(
            Key={"state_id": state_id},
            UpdateExpression="SET license_data = :data, updated_at = :now, last_interaction_at = :now",
            ExpressionAttributeValues={
                ":data": license_data,
                ":now": license_data.get("submitted_at")
            }
        )

        logger.info(f"[onboarding-repo] Updated license data for state {state_id}")

    def update_identity_data(self, state_id: str, identity_data: Dict[str, Any]) -> None:
        """Update identity verification data."""
        self.table.update_item(
            Key={"state_id": state_id},
            UpdateExpression="SET identity_data = :data, updated_at = :now, last_interaction_at = :now",
            ExpressionAttributeValues={
                ":data": identity_data,
                ":now": identity_data.get("submitted_at")
            }
        )

        logger.info(f"[onboarding-repo] Updated identity data for state {state_id}")

    def update_payment_data(self, state_id: str, payment_data: Dict[str, Any]) -> None:
        """Update payment setup data."""
        self.table.update_item(
            Key={"state_id": state_id},
            UpdateExpression="SET payment_data = :data, updated_at = :now, last_interaction_at = :now",
            ExpressionAttributeValues={
                ":data": payment_data,
                ":now": payment_data.get("setup_started_at")
            }
        )

        logger.info(f"[onboarding-repo] Updated payment data for state {state_id}")

    def mark_completed(self, state_id: str, completed_at: str) -> None:
        """Mark onboarding as completed."""
        self.table.update_item(
            Key={"state_id": state_id},
            UpdateExpression="SET #status = :status, current_step = :step, completed_at = :completed, updated_at = :now",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "completed",
                ":step": "completed",
                ":completed": completed_at,
                ":now": completed_at
            }
        )

        logger.info(f"[onboarding-repo] Marked state {state_id} as completed")

    def list_by_status(self, status: str) -> List[Dict[str, Any]]:
        """List all onboarding states by status."""
        resp = self.table.scan(
            FilterExpression=Attr("status").eq(status)
        )
        return resp.get("Items", [])

    def delete_state(self, state_id: str) -> None:
        """Delete onboarding state (use with caution)."""
        self.table.delete_item(Key={"state_id": state_id})
        logger.warning(f"[onboarding-repo] Deleted state {state_id}")
