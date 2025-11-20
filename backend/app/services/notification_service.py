"""
Notification Service - Multi-Channel Cross-Persona Notifications

This service handles sending notifications to users across different personas:
- Find user's Stream Chat channel
- Send notifications to landlords when tenants report issues
- Send notifications to contractors when assigned to jobs
- Send notifications to tenants when jobs are completed
- Support both in-app (Stream) and email notifications

Key Features:
- Persona-based routing
- Multi-party notifications (tenant + landlord + contractor)
- Channel discovery and creation
- Notification templates
- Delivery tracking
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from stream_chat import StreamChat

from .card_builder import CardBuilder

logger = logging.getLogger(__name__)


class NotificationService:
    """Manages cross-persona notifications via Stream Chat."""

    def __init__(self, stream_client: Optional[StreamChat] = None):
        """
        Initialize notification service.

        Args:
            stream_client: Optional Stream Chat client (will be injected)
        """
        self.stream_client = stream_client
        self.card_builder = CardBuilder()

    def set_stream_client(self, client: StreamChat) -> None:
        """Set the Stream Chat client after initialization."""
        self.stream_client = client

    def notify_landlord_new_incident(
        self,
        incident: Dict[str, Any],
        tenant_info: Dict[str, Any],
        property_info: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Notify landlord when tenant reports a new incident.

        Args:
            incident: Incident data
            tenant_info: Tenant information
            property_info: Property information

        Returns:
            Tuple of (success, error_message)
        """
        if not self.stream_client:
            logger.error("[notification] Stream client not configured")
            return False, "Stream client not configured"

        landlord_id = property_info.get("landlord_id")
        if not landlord_id:
            logger.error("[notification] No landlord_id found for property")
            return False, "No landlord found"

        try:
            # Find or create landlord's channel
            channel = self._get_or_create_user_channel(
                landlord_id,
                "landlord",
                f"landlord-incidents-{landlord_id}"
            )

            if not channel:
                return False, "Could not create landlord channel"

            # Create incident card
            card = self.card_builder.incident_card(
                incident_id=incident["incident_id"],
                title=incident.get("title", "New Maintenance Issue"),
                description=incident.get("description", ""),
                severity=incident.get("severity", "medium"),
                images=incident.get("media", []),
                tenant_name=tenant_info.get("name", tenant_info.get("email")),
                property_address=property_info.get("address"),
                status="detected"
            )

            # Send message
            message_text = (
                f"🔔 **New Incident Reported**\n\n"
                f"Tenant {tenant_info.get('name')} has reported a {incident.get('category', 'maintenance')} issue "
                f"at {property_info.get('address')}."
            )

            response = channel.send_message({
                "text": message_text,
                "attachments": [card],
                "metadata": {
                    "notification_type": "incident_created",
                    "incident_id": incident["incident_id"],
                    "tenant_id": tenant_info.get("user_id"),
                    "property_id": property_info.get("property_id")
                }
            }, user_id="landten-bot")

            logger.info(
                "[notification] ✅ Notified landlord %s about incident %s",
                landlord_id,
                incident["incident_id"]
            )

            return True, None

        except Exception as e:
            logger.error(
                "[notification] ❌ Failed to notify landlord %s: %s",
                landlord_id,
                str(e)
            )
            return False, str(e)

    def notify_contractor_job_assigned(
        self,
        job: Dict[str, Any],
        contractor: Dict[str, Any],
        incident: Dict[str, Any],
        property_info: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Notify contractor when assigned to a job.

        Args:
            job: Job data
            contractor: Contractor information
            incident: Related incident
            property_info: Property information

        Returns:
            Tuple of (success, error_message)
        """
        if not self.stream_client:
            return False, "Stream client not configured"

        contractor_id = contractor.get("contractor_id")
        if not contractor_id:
            return False, "No contractor_id provided"

        try:
            # Find or create contractor's channel
            channel = self._get_or_create_user_channel(
                contractor_id,
                "contractor",
                f"contractor-jobs-{contractor_id}"
            )

            if not channel:
                return False, "Could not create contractor channel"

            # Create work order card
            card = self.card_builder.work_order_card(
                incident_id=incident["incident_id"],
                job_id=job["job_id"],
                title=job.get("title", "New Job Assignment"),
                category=job.get("category", "general"),
                estimated_cost=f"${job.get('estimated_cost', 0)}",
                urgency=job.get("urgency", "routine"),
                status="approved",
                property=property_info.get("address"),
                scheduled_date=job.get("scheduled_date")
            )

            message_text = (
                f"🔨 **New Job Assignment**\n\n"
                f"You've been assigned to a {job.get('category')} job at {property_info.get('address')}.\n"
                f"Payment: ${job.get('estimated_cost', 0)}"
            )

            channel.send_message({
                "text": message_text,
                "attachments": [card],
                "metadata": {
                    "notification_type": "job_assigned",
                    "job_id": job["job_id"],
                    "incident_id": incident["incident_id"],
                    "property_id": property_info.get("property_id")
                }
            }, user_id="landten-bot")

            logger.info(
                "[notification] ✅ Notified contractor %s about job %s",
                contractor_id,
                job["job_id"]
            )

            return True, None

        except Exception as e:
            logger.error(
                "[notification] ❌ Failed to notify contractor %s: %s",
                contractor_id,
                str(e)
            )
            return False, str(e)

    def notify_tenant_job_completed(
        self,
        job: Dict[str, Any],
        tenant_id: str,
        contractor: Dict[str, Any],
        completion_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Notify tenant when job is completed.

        Args:
            job: Job data
            tenant_id: Tenant ID
            contractor: Contractor information
            completion_data: Completion details (photos, notes, etc.)

        Returns:
            Tuple of (success, error_message)
        """
        if not self.stream_client:
            return False, "Stream client not configured"

        try:
            # Find tenant's incident channel (original channel where they reported the issue)
            # This assumes the channel ID is stored in the job or incident
            channel_id = job.get("channel_id") or f"incident-{job.get('incident_id')}"

            channel = self.stream_client.channel("messaging", channel_id)

            # Create completion card
            card = self.card_builder.completion_card(
                incident_id=job["incident_id"],
                job_id=job["job_id"],
                contractor_name=contractor.get("name", "Contractor"),
                cost=job.get("final_cost", job.get("estimated_cost", 0)),
                completion_date=completion_data.get("completion_date", datetime.utcnow().isoformat()),
                before_photos=completion_data.get("before_photos", []),
                after_photos=completion_data.get("after_photos", [])
            )

            message_text = (
                f"✅ **Job Completed**\n\n"
                f"Great news! The work has been completed by {contractor.get('name')}.\n"
                f"Please review the work and let us know if you're satisfied."
            )

            channel.send_message({
                "text": message_text,
                "attachments": [card],
                "metadata": {
                    "notification_type": "job_completed",
                    "job_id": job["job_id"],
                    "incident_id": job["incident_id"],
                    "contractor_id": contractor.get("contractor_id")
                }
            }, user_id="landten-bot")

            logger.info(
                "[notification] ✅ Notified tenant %s about job completion %s",
                tenant_id,
                job["job_id"]
            )

            return True, None

        except Exception as e:
            logger.error(
                "[notification] ❌ Failed to notify tenant %s: %s",
                tenant_id,
                str(e)
            )
            return False, str(e)

    def notify_multi_party(
        self,
        notification_type: str,
        recipients: List[Dict[str, str]],
        message_text: str,
        card_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[bool, Optional[str]]]:
        """
        Send notification to multiple parties (tenant, landlord, contractor).

        Args:
            notification_type: Type of notification
            recipients: List of recipients with user_id and persona
            message_text: Message text
            card_data: Optional card attachment
            metadata: Optional metadata

        Returns:
            Dictionary mapping user_id to (success, error_message)
        """
        results = {}

        for recipient in recipients:
            user_id = recipient.get("user_id")
            persona = recipient.get("persona")

            if not user_id or not persona:
                results[user_id or "unknown"] = (False, "Missing user_id or persona")
                continue

            try:
                channel = self._get_or_create_user_channel(
                    user_id,
                    persona,
                    f"{persona}-notifications-{user_id}"
                )

                if not channel:
                    results[user_id] = (False, "Could not create channel")
                    continue

                message = {
                    "text": message_text,
                    "metadata": {
                        "notification_type": notification_type,
                        **(metadata or {})
                    }
                }

                if card_data:
                    message["attachments"] = [card_data]

                channel.send_message(message, user_id="landten-bot")

                results[user_id] = (True, None)
                logger.info("[notification] ✅ Notified %s (%s)", user_id, persona)

            except Exception as e:
                results[user_id] = (False, str(e))
                logger.error("[notification] ❌ Failed to notify %s: %s", user_id, str(e))

        return results

    def _get_or_create_user_channel(
        self,
        user_id: str,
        persona: str,
        channel_id: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get or create a user's notification channel.

        Args:
            user_id: User ID
            persona: User persona (tenant, landlord, contractor)
            channel_id: Optional specific channel ID

        Returns:
            Stream Channel instance or None
        """
        if not self.stream_client:
            return None

        try:
            # Generate channel ID if not provided
            if not channel_id:
                channel_id = f"{persona}-{user_id}"

            # Create or get channel
            channel = self.stream_client.channel(
                "messaging",
                channel_id,
                data={
                    "name": f"{persona.title()} Notifications",
                    "members": [user_id, "landten-bot"],
                    "created_by_id": "landten-bot",
                    "persona": persona
                }
            )

            channel.create(user_id="landten-bot")

            return channel

        except Exception as e:
            # Channel might already exist
            try:
                channel = self.stream_client.channel("messaging", channel_id)
                return channel
            except:
                logger.error(
                    "[notification] Failed to create/get channel for %s: %s",
                    user_id,
                    str(e)
                )
                return None


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create the singleton NotificationService instance."""
    global _notification_service

    if _notification_service is None:
        _notification_service = NotificationService()

    return _notification_service
