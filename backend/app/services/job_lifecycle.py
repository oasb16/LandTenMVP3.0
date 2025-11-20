"""
Job Lifecycle Manager - Orchestrates Job State Transitions

This service manages the complete lifecycle of jobs:
- Job creation from incidents
- Status transitions (created → approved → in_progress → completed → paid)
- Validation of state transitions
- Side effects for each transition (notifications, context updates, etc.)
- Integration with approval workflow
- Integration with payment processing

Valid State Transitions:
    created → approved (landlord approves)
    created → rejected (landlord rejects)
    approved → scheduled (contractor schedules)
    scheduled → in_progress (contractor starts work)
    in_progress → completed (contractor finishes)
    completed → paid (landlord pays)
    any → cancelled (landlord cancels)
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

from .approval_workflow import get_approval_workflow
from .notification_service import get_notification_service
from .mttr_calculator import get_mttr_calculator
from .context_manager import get_context_manager

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status options."""
    CREATED = "created"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAID = "paid"
    CANCELLED = "cancelled"


class JobLifecycleManager:
    """Manages job lifecycle and state transitions."""

    # Valid state transitions
    VALID_TRANSITIONS = {
        JobStatus.CREATED: [JobStatus.APPROVED, JobStatus.REJECTED, JobStatus.CANCELLED],
        JobStatus.APPROVED: [JobStatus.SCHEDULED, JobStatus.CANCELLED],
        JobStatus.SCHEDULED: [JobStatus.IN_PROGRESS, JobStatus.CANCELLED],
        JobStatus.IN_PROGRESS: [JobStatus.COMPLETED, JobStatus.CANCELLED],
        JobStatus.COMPLETED: [JobStatus.PAID],
        JobStatus.REJECTED: [],
        JobStatus.PAID: [],
        JobStatus.CANCELLED: []
    }

    def __init__(self):
        """Initialize job lifecycle manager."""
        self.approval_workflow = get_approval_workflow()
        self.notification_service = get_notification_service()
        self.mttr_calculator = get_mttr_calculator()
        self.context_manager = get_context_manager()

    def create_job(
        self,
        incident: Dict[str, Any],
        estimated_cost: float,
        urgency: str,
        persona: str,
        created_by: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Create a new job from an incident.

        Args:
            incident: Incident data
            estimated_cost: Estimated cost
            urgency: Urgency level
            persona: User persona
            created_by: User ID who created the job

        Returns:
            Tuple of (success, job_data, error_message)
        """
        incident_id = incident.get("incident_id")

        logger.info(
            "[job-lifecycle] Creating job | incident=%s cost=$%.2f persona=%s",
            incident_id,
            estimated_cost,
            persona
        )

        try:
            # Generate job ID
            job_id = f"JOB-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

            # Create job record
            job = {
                "job_id": job_id,
                "incident_id": incident_id,
                "property_id": incident.get("property_id"),
                "landlord_id": incident.get("landlord_id"),
                "tenant_id": incident.get("tenant_id"),
                "title": incident.get("title", f"{incident.get('category')} Repair"),
                "description": incident.get("description"),
                "category": incident.get("category"),
                "severity": incident.get("severity"),
                "urgency": urgency,
                "estimated_cost": estimated_cost,
                "final_cost": None,
                "status": JobStatus.CREATED.value,
                "contractor_id": None,
                "created_by": created_by,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "scheduled_date": None,
                "completion_date": None,
                "metadata": {}
            }

            # Check if approval required
            requires_approval, approval_type, reason = self.approval_workflow.check_approval_required(
                job,
                persona
            )

            job["requires_approval"] = requires_approval
            job["approval_type"] = approval_type.value

            logger.info(
                "[job-lifecycle] ✅ Job created | job=%s | approval_required=%s",
                job_id,
                requires_approval
            )

            return True, job, None

        except Exception as e:
            logger.error("[job-lifecycle] ❌ Failed to create job: %s", str(e))
            return False, None, str(e)

    def transition_status(
        self,
        job: Dict[str, Any],
        new_status: str,
        actor_id: str,
        notes: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Transition job to a new status with validation.

        Args:
            job: Current job data
            new_status: Target status
            actor_id: User performing the transition
            notes: Optional notes about the transition

        Returns:
            Tuple of (success, updated_job, error_message)
        """
        job_id = job.get("job_id")
        current_status = job.get("status")

        logger.info(
            "[job-lifecycle] Transitioning job %s: %s → %s by %s",
            job_id,
            current_status,
            new_status,
            actor_id
        )

        # Validate transition
        is_valid, error = self._validate_transition(current_status, new_status)
        if not is_valid:
            logger.error("[job-lifecycle] ❌ Invalid transition: %s", error)
            return False, None, error

        try:
            # Update job
            updated_job = job.copy()
            updated_job["status"] = new_status
            updated_job["updated_at"] = datetime.utcnow().isoformat() + "Z"

            # Execute side effects based on new status
            self._execute_transition_side_effects(updated_job, current_status, new_status, actor_id)

            logger.info(
                "[job-lifecycle] ✅ Job transitioned | job=%s | %s → %s",
                job_id,
                current_status,
                new_status
            )

            return True, updated_job, None

        except Exception as e:
            logger.error(
                "[job-lifecycle] ❌ Failed to transition job %s: %s",
                job_id,
                str(e)
            )
            return False, None, str(e)

    def mark_completed(
        self,
        job: Dict[str, Any],
        contractor_id: str,
        completion_photos: Optional[list] = None,
        completion_notes: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Mark a job as completed.

        Args:
            job: Job data
            contractor_id: Contractor ID
            completion_photos: Optional list of photo URLs
            completion_notes: Optional notes about completion

        Returns:
            Tuple of (success, updated_job, error_message)
        """
        success, updated_job, error = self.transition_status(
            job,
            JobStatus.COMPLETED.value,
            contractor_id,
            completion_notes
        )

        if not success:
            return False, None, error

        # Add completion data
        updated_job["completion_date"] = datetime.utcnow().isoformat() + "Z"
        updated_job["completion_photos"] = completion_photos or []
        updated_job["completion_notes"] = completion_notes

        return True, updated_job, None

    def mark_paid(
        self,
        job: Dict[str, Any],
        final_cost: float,
        payment_id: str,
        paid_by: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Mark a job as paid.

        Args:
            job: Job data
            final_cost: Final payment amount
            payment_id: Stripe transfer ID
            paid_by: User ID who made payment

        Returns:
            Tuple of (success, updated_job, error_message)
        """
        success, updated_job, error = self.transition_status(
            job,
            JobStatus.PAID.value,
            paid_by
        )

        if not success:
            return False, None, error

        # Add payment data
        updated_job["final_cost"] = final_cost
        updated_job["payment_id"] = payment_id
        updated_job["paid_at"] = datetime.utcnow().isoformat() + "Z"

        return True, updated_job, None

    def _validate_transition(
        self,
        current_status: str,
        new_status: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate if a status transition is allowed."""

        try:
            current = JobStatus(current_status)
            new = JobStatus(new_status)
        except ValueError:
            return False, f"Invalid status value"

        allowed_transitions = self.VALID_TRANSITIONS.get(current, [])

        if new not in allowed_transitions:
            return False, f"Cannot transition from {current_status} to {new_status}"

        return True, None

    def _execute_transition_side_effects(
        self,
        job: Dict[str, Any],
        old_status: str,
        new_status: str,
        actor_id: str
    ) -> None:
        """Execute side effects when transitioning job status."""

        job_id = job.get("job_id")

        # APPROVED: Notify contractor, create schedule
        if new_status == JobStatus.APPROVED.value:
            logger.info("[job-lifecycle] Job approved - triggering notifications")
            # Notification would happen here

        # COMPLETED: Notify tenant, calculate MTTR for incident
        elif new_status == JobStatus.COMPLETED.value:
            logger.info("[job-lifecycle] Job completed - notifying tenant")
            # Notification would happen here

        # PAID: Close incident, record MTTR
        elif new_status == JobStatus.PAID.value:
            logger.info("[job-lifecycle] Job paid - closing incident")
            # Close incident and calculate MTTR would happen here


# Singleton instance
_job_lifecycle_manager: Optional[JobLifecycleManager] = None


def get_job_lifecycle() -> JobLifecycleManager:
    """Get or create the singleton JobLifecycleManager instance."""
    global _job_lifecycle_manager

    if _job_lifecycle_manager is None:
        _job_lifecycle_manager = JobLifecycleManager()

    return _job_lifecycle_manager
