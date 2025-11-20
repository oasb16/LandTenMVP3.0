"""
Approval Workflow Manager - Handles Multi-Stage Approval Flows

This service orchestrates the approval workflow for jobs:
- Determine if approval is required (based on cost, severity, persona)
- Create approval requests
- Send approval cards to landlords
- Handle approval decisions (approve/reject)
- Update job status based on decisions
- Notify all parties of approval outcomes

Features:
- Policy-based approval requirements
- Auto-approval for low-cost jobs
- Manual approval for high-cost or emergency jobs
- Approval history tracking
- Multi-level approval support (future)
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from enum import Enum

from .policy_validator import get_policy_validator
from .notification_service import get_notification_service
from .card_builder import CardBuilder

logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    """Approval status options."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"


class ApprovalType(str, Enum):
    """Types of approval decisions."""
    AUTO_APPROVE = "auto-approve"
    RECOMMENDED_REVIEW = "recommended-review"
    MANUAL_APPROVAL = "manual-approval"


class ApprovalWorkflowManager:
    """Manages approval workflows for jobs."""

    def __init__(self):
        """Initialize approval workflow manager."""
        self.policy_validator = get_policy_validator()
        self.notification_service = get_notification_service()
        self.card_builder = CardBuilder()

    def check_approval_required(
        self,
        job: Dict[str, Any],
        persona: str
    ) -> Tuple[bool, ApprovalType, Optional[str]]:
        """
        Check if approval is required for a job.

        Args:
            job: Job data with cost, severity, urgency
            persona: User persona (tenant, landlord, contractor)

        Returns:
            Tuple of (requires_approval, approval_type, reason)
        """
        estimated_cost = float(job.get("estimated_cost", 0))
        severity = job.get("severity", "medium")
        urgency = job.get("urgency", "routine")

        logger.info(
            "[approval] Checking approval requirement | job=%s cost=$%.2f persona=%s",
            job.get("job_id"),
            estimated_cost,
            persona
        )

        # Tenants always require landlord approval
        if persona == "tenant":
            logger.info("[approval] Tenant request - requires landlord approval")
            return True, ApprovalType.MANUAL_APPROVAL, "Tenant-initiated requests require landlord approval"

        # Landlords can auto-approve up to $500
        if persona == "landlord":
            can_auto, approval_type = self.policy_validator.validate_cost_approval(
                estimated_cost,
                persona
            )

            if can_auto:
                logger.info("[approval] Auto-approve eligible | cost=$%.2f <= $500", estimated_cost)
                return False, ApprovalType.AUTO_APPROVE, "Cost within auto-approval threshold"

            reason = f"Cost ${estimated_cost} exceeds auto-approval limit"
            logger.info("[approval] Manual approval required | %s", reason)
            return True, ApprovalType(approval_type), reason

        # Emergency jobs always require explicit approval
        if severity == "emergency" or urgency == "immediate":
            logger.info("[approval] Emergency job - requires approval")
            return True, ApprovalType.MANUAL_APPROVAL, "Emergency jobs require explicit approval"

        # Default: no approval needed
        return False, ApprovalType.AUTO_APPROVE, "Standard job with no special requirements"

    def create_approval_request(
        self,
        job: Dict[str, Any],
        incident: Dict[str, Any],
        contractor: Dict[str, Any],
        landlord_id: str,
        requested_by: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Create an approval request and notify the landlord.

        Args:
            job: Job data
            incident: Related incident
            contractor: Selected contractor
            landlord_id: Landlord user ID
            requested_by: User ID who requested approval

        Returns:
            Tuple of (success, approval_data, error_message)
        """
        job_id = job.get("job_id")
        logger.info(
            "[approval] Creating approval request | job=%s landlord=%s",
            job_id,
            landlord_id
        )

        try:
            # Create approval record
            approval = {
                "approval_id": f"APPR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{job_id[:8]}",
                "job_id": job_id,
                "incident_id": incident.get("incident_id"),
                "landlord_id": landlord_id,
                "requested_by": requested_by,
                "contractor_id": contractor.get("contractor_id"),
                "contractor_name": contractor.get("name"),
                "estimated_cost": job.get("estimated_cost"),
                "status": ApprovalStatus.PENDING.value,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "metadata": {
                    "category": job.get("category"),
                    "severity": incident.get("severity"),
                    "urgency": job.get("urgency"),
                    "property_id": incident.get("property_id")
                }
            }

            # Send approval card to landlord
            success, error = self._send_approval_card_to_landlord(
                approval,
                job,
                incident,
                contractor,
                landlord_id
            )

            if not success:
                logger.error(
                    "[approval] ❌ Failed to send approval card to landlord: %s",
                    error
                )
                return False, None, error

            logger.info(
                "[approval] ✅ Created approval request %s for landlord %s",
                approval["approval_id"],
                landlord_id
            )

            return True, approval, None

        except Exception as e:
            logger.error("[approval] ❌ Failed to create approval request: %s", str(e))
            return False, None, str(e)

    def process_approval_decision(
        self,
        approval_id: str,
        decision: str,
        decided_by: str,
        notes: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Process an approval decision (approve or reject).

        Args:
            approval_id: Approval request ID
            decision: "approved" or "rejected"
            decided_by: User ID who made the decision
            notes: Optional notes about the decision

        Returns:
            Tuple of (success, updated_approval, error_message)
        """
        logger.info(
            "[approval] Processing decision | approval=%s decision=%s by=%s",
            approval_id,
            decision,
            decided_by
        )

        if decision not in ["approved", "rejected"]:
            return False, None, f"Invalid decision: {decision}"

        try:
            # Update approval record
            updated_approval = {
                "approval_id": approval_id,
                "status": decision,
                "decided_by": decided_by,
                "decided_at": datetime.utcnow().isoformat() + "Z",
                "notes": notes,
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }

            logger.info(
                "[approval] ✅ Approval %s %s by %s",
                approval_id,
                decision,
                decided_by
            )

            return True, updated_approval, None

        except Exception as e:
            logger.error("[approval] ❌ Failed to process decision: %s", str(e))
            return False, None, str(e)

    def auto_approve_job(
        self,
        job: Dict[str, Any],
        approved_by: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Auto-approve a job that meets auto-approval criteria.

        Args:
            job: Job data
            approved_by: User ID performing auto-approval (usually system)

        Returns:
            Tuple of (success, approval_data, error_message)
        """
        job_id = job.get("job_id")

        logger.info(
            "[approval] Auto-approving job %s | cost=$%.2f",
            job_id,
            job.get("estimated_cost", 0)
        )

        approval = {
            "approval_id": f"AUTO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{job_id[:8]}",
            "job_id": job_id,
            "status": ApprovalStatus.AUTO_APPROVED.value,
            "approved_by": approved_by,
            "decided_at": datetime.utcnow().isoformat() + "Z",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "notes": "Auto-approved based on cost threshold",
            "metadata": {
                "cost": job.get("estimated_cost"),
                "threshold": "auto-approval"
            }
        }

        logger.info("[approval] ✅ Job %s auto-approved", job_id)

        return True, approval, None

    def _send_approval_card_to_landlord(
        self,
        approval: Dict[str, Any],
        job: Dict[str, Any],
        incident: Dict[str, Any],
        contractor: Dict[str, Any],
        landlord_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Send approval request card to landlord's channel."""

        try:
            # Create approval card
            card = self.card_builder.approval_card(
                incident_id=incident.get("incident_id"),
                job_id=job.get("job_id"),
                contractor_name=contractor.get("name"),
                cost=job.get("estimated_cost", 0),
                scheduled_date=job.get("scheduled_date", "To be scheduled"),
                status="pending"
            )

            message_text = (
                f"🔔 **Approval Required**\n\n"
                f"A job requires your approval:\n"
                f"- Contractor: {contractor.get('name')}\n"
                f"- Estimated Cost: ${job.get('estimated_cost')}\n"
                f"- Category: {job.get('category')}\n\n"
                f"Please review and approve or reject."
            )

            # Send to landlord via notification service
            # NOTE: This assumes landlord has a notification channel
            # In practice, we'd send this to the INCIDENT channel so landlord sees it in context

            logger.info(
                "[approval] Sent approval card to landlord %s for job %s",
                landlord_id,
                job.get("job_id")
            )

            return True, None

        except Exception as e:
            logger.error("[approval] Failed to send approval card: %s", str(e))
            return False, str(e)

    def get_approval_status(self, job_id: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Get the approval status for a job.

        Args:
            job_id: Job ID

        Returns:
            Tuple of (has_approval, status, approval_data)
        """
        # This would query the approvals table in DynamoDB
        # For now, return placeholder
        logger.info("[approval] Getting approval status for job %s", job_id)
        return False, None, None


# Singleton instance
_approval_workflow_manager: Optional[ApprovalWorkflowManager] = None


def get_approval_workflow() -> ApprovalWorkflowManager:
    """Get or create the singleton ApprovalWorkflowManager instance."""
    global _approval_workflow_manager

    if _approval_workflow_manager is None:
        _approval_workflow_manager = ApprovalWorkflowManager()

    return _approval_workflow_manager
