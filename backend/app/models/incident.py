"""
Incident models for property management workflow system.

Represents tenant-reported incidents that flow through the system:
Tenant reports → Discovery → Landlord review → Job creation → Completion
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class IncidentStatus(str, Enum):
    """Status progression for incidents."""
    CREATED = "created"  # Initial state when tenant reports
    DISCOVERY = "discovery"  # AI is gathering additional information
    LANDLORD_REVIEW = "landlord_review"  # Waiting for landlord decision
    JOB_CREATED = "job_created"  # Job has been posted for contractors
    COMPLETED = "completed"  # Incident resolved
    CANCELLED = "cancelled"  # Incident cancelled (duplicate, resolved directly, etc.)


class IncidentCategory(str, Enum):
    """Categories of maintenance incidents."""
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    HVAC = "hvac"
    APPLIANCE = "appliance"
    STRUCTURAL = "structural"
    PEST_CONTROL = "pest_control"
    LANDSCAPING = "landscaping"
    SECURITY = "security"
    OTHER = "other"


class IncidentUrgency(str, Enum):
    """Urgency levels for incidents."""
    ROUTINE = "routine"  # Can wait, normal maintenance
    URGENT = "urgent"  # Should be addressed within days
    EMERGENCY = "emergency"  # Requires immediate attention


class IncidentPhoto(BaseModel):
    """Photo attached to an incident."""
    photo_id: str = Field(
        default_factory=lambda: f"photo_{uuid4().hex[:12]}",
        description="Unique photo identifier"
    )
    s3_url: str = Field(..., description="S3 URL of the photo")
    thumbnail_url: Optional[str] = Field(None, description="S3 URL of thumbnail (if generated)")
    uploaded_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When photo was uploaded"
    )
    caption: Optional[str] = Field(None, description="Optional photo caption")
    uploaded_by: str = Field(..., description="User ID who uploaded the photo")


class Incident(BaseModel):
    """Main incident model representing a tenant-reported issue."""

    # Identifiers
    incident_id: str = Field(
        default_factory=lambda: f"inc_{uuid4().hex[:12]}",
        description="Unique incident identifier"
    )
    property_id: str = Field(..., description="Property where incident occurred")
    unit_id: Optional[str] = Field(None, description="Specific unit (if multi-unit property)")
    tenant_id: str = Field(..., description="Tenant who reported the incident")
    landlord_id: str = Field(..., description="Landlord/property manager responsible")

    # Incident details
    title: str = Field(..., description="Brief title/summary of the incident", max_length=200)
    description: str = Field(..., description="Detailed description of the issue")
    category: IncidentCategory = Field(..., description="Category of the incident")
    urgency: IncidentUrgency = Field(
        default=IncidentUrgency.ROUTINE,
        description="How urgently this needs attention"
    )

    # Status and workflow
    status: IncidentStatus = Field(
        default=IncidentStatus.CREATED,
        description="Current status in the workflow"
    )

    # Media and discovery
    photos: List[IncidentPhoto] = Field(
        default_factory=list,
        description="Photos attached to the incident"
    )
    discovery_data: Optional[dict] = Field(
        None,
        description="Data gathered during AI discovery phase (questions/answers, damage assessment, etc.)"
    )

    # Job linkage
    job_id: Optional[str] = Field(
        None,
        description="ID of the job created from this incident (if status=job_created)"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When incident was first reported"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )

    # Additional metadata
    estimated_cost: Optional[float] = Field(
        None,
        description="Estimated repair cost (from AI or landlord)"
    )
    notes: Optional[str] = Field(
        None,
        description="Additional notes from landlord or system"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True  # Serialize enums as their values
        json_schema_extra = {
            "example": {
                "incident_id": "inc_a1b2c3d4e5f6",
                "property_id": "prop_123456789abc",
                "unit_id": "unit_2a",
                "tenant_id": "user_tenant123",
                "landlord_id": "user_landlord456",
                "title": "Kitchen sink leaking",
                "description": "Water is dripping from under the kitchen sink. Noticed it yesterday.",
                "category": "plumbing",
                "urgency": "urgent",
                "status": "created",
                "photos": [],
                "created_at": "2025-12-07T10:00:00Z",
                "updated_at": "2025-12-07T10:00:00Z"
            }
        }


class IncidentCreate(BaseModel):
    """Request model for creating a new incident."""
    property_id: str
    unit_id: Optional[str] = None
    tenant_id: str
    landlord_id: str
    title: str = Field(..., max_length=200)
    description: str
    category: IncidentCategory
    urgency: IncidentUrgency = IncidentUrgency.ROUTINE
    photos: List[IncidentPhoto] = Field(default_factory=list)


class IncidentUpdate(BaseModel):
    """Request model for updating an incident."""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    category: Optional[IncidentCategory] = None
    urgency: Optional[IncidentUrgency] = None
    status: Optional[IncidentStatus] = None
    discovery_data: Optional[dict] = None
    job_id: Optional[str] = None
    estimated_cost: Optional[float] = None
    notes: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
