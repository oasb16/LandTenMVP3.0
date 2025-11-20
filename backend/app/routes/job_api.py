"""
Job API Routes

Endpoints for job management:
- POST /api/job/create - Create new job from incident
- GET /api/job/list/{user_id} - List jobs for a user
- GET /api/job/{job_id} - Get job details
- PATCH /api/job/{job_id}/status - Update job status
- PATCH /api/job/{job_id}/assign - Assign contractor to job
- POST /api/job/{job_id}/complete - Mark job as completed
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from ..services.job_lifecycle import get_job_lifecycle
from ..services.bid_generator import get_bid_generator
from ..services.notification_service import get_notification_service
from ..repos.job_repo import JobRepo
from ..repos.job_bid_repo import JobBidRepo
from ..repos.incident_repo import IncidentRepo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/job", tags=["jobs"])


# Request/Response Models
class CreateJobRequest(BaseModel):
    """Request to create a job from an incident."""
    incident_id: str = Field(..., description="Incident ID")
    created_by: str = Field(..., description="User ID creating the job")
    persona: str = Field(..., description="User persona")
    estimated_cost: Optional[float] = Field(None, description="Estimated cost")
    urgency: str = Field(default="routine", description="Urgency level")


class UpdateJobStatusRequest(BaseModel):
    """Request to update job status."""
    status: str = Field(..., description="New status")
    updated_by: str = Field(..., description="User ID making update")
    notes: Optional[str] = Field(None, description="Status update notes")


class AssignContractorRequest(BaseModel):
    """Request to assign contractor to job."""
    contractor_id: str = Field(..., description="Contractor ID")
    bid_id: str = Field(..., description="Selected bid ID")
    assigned_by: str = Field(..., description="User ID assigning contractor")


class CompleteJobRequest(BaseModel):
    """Request to mark job as completed."""
    contractor_id: str = Field(..., description="Contractor ID")
    completion_photos: Optional[List[str]] = Field(None, description="Completion photo URLs")
    completion_notes: Optional[str] = Field(None, description="Completion notes")


# Endpoints

@router.post("/create")
async def create_job(request: CreateJobRequest):
    """
    Create a new job from an incident.

    This endpoint:
    1. Creates job record
    2. Generates contractor bids
    3. Checks if approval required
    4. Sends notifications
    """
    logger.info(
        "[job-api] Creating job | incident=%s by=%s persona=%s",
        request.incident_id,
        request.created_by,
        request.persona
    )

    try:
        # Get incident
        incident_repo = IncidentRepo()
        incident = incident_repo.get_incident(request.incident_id)

        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")

        # Initialize services
        job_lifecycle = get_job_lifecycle()
        bid_generator = get_bid_generator()
        job_repo = JobRepo()
        bid_repo = JobBidRepo()

        # Determine estimated cost if not provided
        estimated_cost = request.estimated_cost
        if not estimated_cost:
            # Use severity to estimate cost
            cost_map = {
                "low": 150.0,
                "medium": 300.0,
                "high": 500.0,
                "emergency": 750.0
            }
            estimated_cost = cost_map.get(incident.get("severity", "medium"), 300.0)

        # Create job
        success, job, error = job_lifecycle.create_job(
            incident=incident,
            estimated_cost=estimated_cost,
            urgency=request.urgency,
            persona=request.persona,
            created_by=request.created_by
        )

        if not success:
            raise HTTPException(status_code=500, detail=error)

        # Save job to DynamoDB
        job_repo.create_job(job)

        # Generate contractor bids
        bids = bid_generator.generate_bids(
            job_id=job["job_id"],
            category=incident.get("category", "general"),
            severity=incident.get("severity", "medium"),
            urgency=request.urgency,
            description=incident.get("description", ""),
            num_bids=3
        )

        # Save bids to DynamoDB
        for bid in bids:
            bid_repo.create_bid(bid)

        # Update incident with job_id
        incident_repo.update_incident(
            request.incident_id,
            {**incident, "job_id": job["job_id"], "status": "job_created"}
        )

        logger.info(
            "[job-api] ✅ Job created | job=%s | %d bids generated | approval_required=%s",
            job["job_id"],
            len(bids),
            job.get("requires_approval")
        )

        return {
            "success": True,
            "job_id": job["job_id"],
            "job": job,
            "bids": bids,
            "requires_approval": job.get("requires_approval"),
            "approval_type": job.get("approval_type")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[job-api] ❌ Failed to create job: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/{user_id}")
async def list_jobs(user_id: str, persona: str = "tenant"):
    """
    List jobs for a user.

    For tenants: Returns jobs for their incidents
    For landlords: Returns jobs for their properties
    For contractors: Returns jobs assigned to them
    """
    logger.info(
        "[job-api] Listing jobs | user=%s persona=%s",
        user_id,
        persona
    )

    try:
        job_repo = JobRepo()

        if persona == "tenant":
            jobs = job_repo.get_jobs_by_tenant(user_id)
        elif persona == "landlord":
            jobs = job_repo.get_jobs_by_landlord(user_id)
        elif persona == "contractor":
            jobs = job_repo.get_jobs_by_contractor(user_id)
        else:
            jobs = []

        logger.info(
            "[job-api] ✅ Found %d jobs for %s",
            len(jobs),
            user_id
        )

        return {
            "success": True,
            "jobs": jobs,
            "count": len(jobs)
        }

    except Exception as e:
        logger.error("[job-api] ❌ Failed to list jobs: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}")
async def get_job(job_id: str):
    """Get details for a specific job."""
    logger.info("[job-api] Getting job | job=%s", job_id)

    try:
        job_repo = JobRepo()
        job = job_repo.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return {
            "success": True,
            "job": job
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[job-api] ❌ Failed to get job: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{job_id}/status")
async def update_status(job_id: str, request: UpdateJobStatusRequest):
    """Update job status with validation."""
    logger.info(
        "[job-api] Updating job status | job=%s status=%s",
        job_id,
        request.status
    )

    try:
        job_repo = JobRepo()
        job_lifecycle = get_job_lifecycle()

        # Get current job
        job = job_repo.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Transition status
        success, updated_job, error = job_lifecycle.transition_status(
            job=job,
            new_status=request.status,
            actor_id=request.updated_by,
            notes=request.notes
        )

        if not success:
            raise HTTPException(status_code=400, detail=error)

        # Save updated job
        job_repo.update_job(job_id, updated_job)

        logger.info(
            "[job-api] ✅ Job status updated | job=%s → %s",
            job_id,
            request.status
        )

        return {
            "success": True,
            "job": updated_job
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[job-api] ❌ Failed to update status: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{job_id}/assign")
async def assign_contractor(job_id: str, request: AssignContractorRequest):
    """Assign a contractor to a job and update bid statuses."""
    logger.info(
        "[job-api] Assigning contractor | job=%s contractor=%s",
        job_id,
        request.contractor_id
    )

    try:
        job_repo = JobRepo()
        bid_repo = JobBidRepo()
        notification_service = get_notification_service()

        # Get job
        job = job_repo.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Update job with contractor
        updated_job = {
            **job,
            "contractor_id": request.contractor_id,
            "status": "approved",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }

        job_repo.update_job(job_id, updated_job)

        # Update selected bid status to accepted
        bid_repo.update_bid_status(request.bid_id, "accepted")

        # Update other bids for this job to rejected
        all_bids = bid_repo.get_bids_by_job(job_id)
        for bid in all_bids:
            if bid["bid_id"] != request.bid_id:
                bid_repo.update_bid_status(bid["bid_id"], "rejected")

        # Notify contractor (async)
        # This would use notification_service.notify_contractor_job_assigned()

        logger.info(
            "[job-api] ✅ Contractor assigned | job=%s contractor=%s",
            job_id,
            request.contractor_id
        )

        return {
            "success": True,
            "job": updated_job
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[job-api] ❌ Failed to assign contractor: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/complete")
async def complete_job(job_id: str, request: CompleteJobRequest):
    """Mark a job as completed."""
    logger.info(
        "[job-api] Completing job | job=%s contractor=%s",
        job_id,
        request.contractor_id
    )

    try:
        job_repo = JobRepo()
        job_lifecycle = get_job_lifecycle()

        # Get job
        job = job_repo.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Mark completed
        success, updated_job, error = job_lifecycle.mark_completed(
            job=job,
            contractor_id=request.contractor_id,
            completion_photos=request.completion_photos,
            completion_notes=request.completion_notes
        )

        if not success:
            raise HTTPException(status_code=500, detail=error)

        # Save job
        job_repo.update_job(job_id, updated_job)

        logger.info("[job-api] ✅ Job completed | job=%s", job_id)

        return {
            "success": True,
            "job": updated_job
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[job-api] ❌ Failed to complete job: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
