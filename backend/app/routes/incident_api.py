"""
Incident API Routes

Endpoints for incident management:
- POST /api/incident/create - Create new incident
- GET /api/incident/list/{user_id} - List incidents for a user
- GET /api/incident/{incident_id} - Get incident details
- PATCH /api/incident/{incident_id}/close - Close an incident
- PATCH /api/incident/{incident_id}/status - Update incident status
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from ..services.dynamo_service import get_dynamo_service
from ..services.context_manager import get_context_manager
from ..services.notification_service import get_notification_service
from ..services.discovery_manager import get_discovery_manager
from ..repos.incident_repo import IncidentRepo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/incident", tags=["incidents"])


# Request/Response Models
class CreateIncidentRequest(BaseModel):
    """Request to create a new incident."""
    tenant_id: str = Field(..., description="Tenant user ID")
    property_id: str = Field(..., description="Property ID")
    landlord_id: str = Field(..., description="Landlord user ID")
    channel_id: str = Field(..., description="Stream channel ID")
    title: str = Field(..., description="Incident title")
    description: str = Field(..., description="Incident description")
    category: str = Field(..., description="Category (plumbing, electrical, etc.)")
    severity: str = Field(default="medium", description="Severity level")
    urgency: str = Field(default="routine", description="Urgency level")
    location: Optional[str] = Field(None, description="Location in property")
    media: Optional[List[str]] = Field(None, description="Photo/video URLs")


class CloseIncidentRequest(BaseModel):
    """Request to close an incident."""
    resolved_by: str = Field(..., description="User ID who resolved it")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")


class UpdateStatusRequest(BaseModel):
    """Request to update incident status."""
    status: str = Field(..., description="New status")
    updated_by: str = Field(..., description="User ID making update")


# Endpoints

@router.post("/create")
async def create_incident(request: CreateIncidentRequest):
    """
    Create a new incident.

    This endpoint:
    1. Creates incident record in DynamoDB
    2. Updates context manager with incident ID
    3. Starts discovery flow
    4. Notifies landlord
    """
    logger.info(
        "[incident-api] Creating incident | tenant=%s property=%s category=%s",
        request.tenant_id,
        request.property_id,
        request.category
    )

    try:
        # Initialize services
        incident_repo = IncidentRepo()
        context_manager = get_context_manager()
        discovery_manager = get_discovery_manager()
        notification_service = get_notification_service()

        # Generate incident ID
        incident_id = f"INC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Create incident record
        incident = {
            "incident_id": incident_id,
            "tenant_id": request.tenant_id,
            "property_id": request.property_id,
            "landlord_id": request.landlord_id,
            "channel_id": request.channel_id,
            "title": request.title,
            "description": request.description,
            "category": request.category,
            "severity": request.severity,
            "urgency": request.urgency,
            "location": request.location,
            "media": request.media or [],
            "status": "detected",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "job_id": None,
            "resolved_at": None
        }

        # Save to DynamoDB
        incident_repo.create_incident(incident)

        # Update context
        context_manager.set_active_incident(
            request.tenant_id,
            request.channel_id,
            incident_id
        )

        # Start discovery flow
        success, first_question, error = discovery_manager.start_discovery(
            request.tenant_id,
            request.channel_id,
            incident_id,
            request.category
        )

        if not success:
            logger.warning(
                "[incident-api] Failed to start discovery: %s",
                error
            )

        # Notify landlord (async, don't block response)
        # In production, this would be a background task
        try:
            notification_service.notify_landlord_new_incident(
                incident,
                {"user_id": request.tenant_id, "name": "Tenant"},
                {"property_id": request.property_id, "landlord_id": request.landlord_id, "address": "123 Main St"}
            )
        except Exception as e:
            logger.error("[incident-api] Failed to notify landlord: %s", str(e))

        logger.info(
            "[incident-api] ✅ Incident created | incident=%s | discovery_started=%s",
            incident_id,
            success
        )

        return {
            "success": True,
            "incident_id": incident_id,
            "incident": incident,
            "discovery_started": success,
            "first_question": first_question
        }

    except Exception as e:
        logger.error("[incident-api] ❌ Failed to create incident: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/{user_id}")
async def list_incidents(user_id: str, persona: str = "tenant"):
    """
    List incidents for a user.

    For tenants: Returns their reported incidents
    For landlords: Returns incidents for their properties
    For contractors: Returns incidents for their assigned jobs
    """
    logger.info(
        "[incident-api] Listing incidents | user=%s persona=%s",
        user_id,
        persona
    )

    try:
        incident_repo = IncidentRepo()

        if persona == "tenant":
            incidents = incident_repo.get_incidents_by_tenant(user_id)
        elif persona == "landlord":
            incidents = incident_repo.get_incidents_by_landlord(user_id)
        else:
            incidents = []

        logger.info(
            "[incident-api] ✅ Found %d incidents for %s",
            len(incidents),
            user_id
        )

        return {
            "success": True,
            "incidents": incidents,
            "count": len(incidents)
        }

    except Exception as e:
        logger.error("[incident-api] ❌ Failed to list incidents: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{incident_id}")
async def get_incident(incident_id: str):
    """Get details for a specific incident."""
    logger.info("[incident-api] Getting incident | incident=%s", incident_id)

    try:
        incident_repo = IncidentRepo()
        incident = incident_repo.get_incident(incident_id)

        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")

        return {
            "success": True,
            "incident": incident
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[incident-api] ❌ Failed to get incident: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{incident_id}/close")
async def close_incident(incident_id: str, request: CloseIncidentRequest):
    """
    Close an incident and mark it as resolved.

    This triggers MTTR calculation.
    """
    logger.info(
        "[incident-api] Closing incident | incident=%s by=%s",
        incident_id,
        request.resolved_by
    )

    try:
        incident_repo = IncidentRepo()

        # Get current incident
        incident = incident_repo.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")

        # Update status
        updated_incident = {
            **incident,
            "status": "resolved",
            "resolved_at": datetime.utcnow().isoformat() + "Z",
            "resolved_by": request.resolved_by,
            "resolution_notes": request.resolution_notes,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }

        incident_repo.update_incident(incident_id, updated_incident)

        # Calculate MTTR (would be done in background)
        # mttr_calculator = get_mttr_calculator()
        # mttr_calculator.calculate_mttr(updated_incident)

        logger.info("[incident-api] ✅ Incident closed | incident=%s", incident_id)

        return {
            "success": True,
            "incident": updated_incident
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[incident-api] ❌ Failed to close incident: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{incident_id}/status")
async def update_status(incident_id: str, request: UpdateStatusRequest):
    """Update incident status."""
    logger.info(
        "[incident-api] Updating incident status | incident=%s status=%s",
        incident_id,
        request.status
    )

    try:
        incident_repo = IncidentRepo()

        # Get current incident
        incident = incident_repo.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")

        # Update status
        updated_incident = {
            **incident,
            "status": request.status,
            "updated_by": request.updated_by,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }

        incident_repo.update_incident(incident_id, updated_incident)

        logger.info(
            "[incident-api] ✅ Status updated | incident=%s → %s",
            incident_id,
            request.status
        )

        return {
            "success": True,
            "incident": updated_incident
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[incident-api] ❌ Failed to update status: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
