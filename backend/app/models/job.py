"""
Job models for contractor bidding and work completion.

Jobs are created from incidents and go through:
Posted → Bidding → Awarded → Scheduled → In Progress → Completed → Paid
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Status progression for jobs."""
    POSTED = "posted"  # Job posted, open for bids
    BIDDING = "bidding"  # Actively accepting bids
    AWARDED = "awarded"  # Bid accepted, contractor assigned
    SCHEDULED = "scheduled"  # Work date scheduled
    IN_PROGRESS = "in_progress"  # Contractor is performing work
    COMPLETED = "completed"  # Work finished, pending payment
    PAID = "paid"  # Payment processed, job closed


class PaymentStatus(str, Enum):
    """Payment status for jobs."""
    PENDING = "pending"  # No payment initiated
    AUTHORIZED = "authorized"  # Payment authorized but not captured
    PROCESSING = "processing"  # Payment being processed
    COMPLETED = "completed"  # Payment successful
    FAILED = "failed"  # Payment failed
    REFUNDED = "refunded"  # Payment refunded


class JobPhoto(BaseModel):
    """Photo of completed work."""
    photo_id: str = Field(
        default_factory=lambda: f"photo_{uuid4().hex[:12]}",
        description="Unique photo identifier"
    )
    s3_url: str = Field(..., description="S3 URL of the photo")
    thumbnail_url: Optional[str] = Field(None, description="S3 URL of thumbnail")
    uploaded_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When photo was uploaded"
    )
    caption: Optional[str] = Field(None, description="Optional photo caption")
    uploaded_by: str = Field(..., description="User ID who uploaded (typically contractor)")


class Job(BaseModel):
    """Main job model for contractor work assignments."""

    # Identifiers
    job_id: str = Field(
        default_factory=lambda: f"job_{uuid4().hex[:12]}",
        description="Unique job identifier"
    )
    incident_id: str = Field(..., description="Incident that generated this job")
    property_id: str = Field(..., description="Property where work is needed")
    landlord_id: str = Field(..., description="Landlord posting the job")
    tenant_id: str = Field(..., description="Tenant affected by the issue")

    # Job details
    title: str = Field(..., description="Job title/summary", max_length=200)
    description: str = Field(..., description="Detailed job description and requirements")
    category: str = Field(..., description="Job category (plumbing, electrical, etc.)")
    urgency: str = Field(..., description="Urgency level (routine, urgent, emergency)")

    # Budget
    budget_min: Optional[float] = Field(
        None,
        description="Minimum budget range (optional)",
        ge=0
    )
    budget_max: Optional[float] = Field(
        None,
        description="Maximum budget range (optional)",
        ge=0
    )

    # Status
    status: JobStatus = Field(
        default=JobStatus.POSTED,
        description="Current job status"
    )

    # Contractor assignment
    awarded_contractor_id: Optional[str] = Field(
        None,
        description="Contractor ID who won the bid"
    )
    awarded_bid_id: Optional[str] = Field(
        None,
        description="Winning bid ID"
    )

    # Scheduling
    scheduled_date: Optional[datetime] = Field(
        None,
        description="When work is scheduled to begin"
    )
    completion_date: Optional[datetime] = Field(
        None,
        description="When work was actually completed"
    )

    # Completion
    completion_photos: List[JobPhoto] = Field(
        default_factory=list,
        description="Photos of completed work"
    )
    completion_notes: Optional[str] = Field(
        None,
        description="Contractor's notes about completed work"
    )

    # Payment
    payment_status: PaymentStatus = Field(
        default=PaymentStatus.PENDING,
        description="Payment processing status"
    )
    stripe_payment_intent_id: Optional[str] = Field(
        None,
        description="Stripe PaymentIntent ID for tracking"
    )
    final_amount: Optional[float] = Field(
        None,
        description="Final agreed amount (from winning bid)",
        ge=0
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When job was posted"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    awarded_at: Optional[datetime] = Field(
        None,
        description="When bid was awarded"
    )

    # Metadata
    bid_count: int = Field(
        default=0,
        description="Number of bids received",
        ge=0
    )
    notes: Optional[str] = Field(
        None,
        description="Additional notes from landlord"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "job_id": "job_a1b2c3d4e5f6",
                "incident_id": "inc_123456789abc",
                "property_id": "prop_123456789abc",
                "landlord_id": "user_landlord456",
                "tenant_id": "user_tenant123",
                "title": "Fix kitchen sink leak",
                "description": "Kitchen sink is leaking underneath. Need plumber to repair/replace pipes.",
                "category": "plumbing",
                "urgency": "urgent",
                "budget_min": 100.0,
                "budget_max": 300.0,
                "status": "posted",
                "payment_status": "pending",
                "bid_count": 0,
                "created_at": "2025-12-07T10:00:00Z",
                "updated_at": "2025-12-07T10:00:00Z"
            }
        }


class JobCreate(BaseModel):
    """Request model for creating a new job."""
    incident_id: str
    property_id: str
    landlord_id: str
    tenant_id: str
    title: str = Field(..., max_length=200)
    description: str
    category: str
    urgency: str
    budget_min: Optional[float] = Field(None, ge=0)
    budget_max: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None


class JobUpdate(BaseModel):
    """Request model for updating a job."""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    budget_min: Optional[float] = Field(None, ge=0)
    budget_max: Optional[float] = Field(None, ge=0)
    status: Optional[JobStatus] = None
    awarded_contractor_id: Optional[str] = None
    awarded_bid_id: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    completion_notes: Optional[str] = None
    payment_status: Optional[PaymentStatus] = None
    stripe_payment_intent_id: Optional[str] = None
    final_amount: Optional[float] = Field(None, ge=0)
    bid_count: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class JobAward(BaseModel):
    """Request model for awarding a job to a contractor."""
    awarded_contractor_id: str
    awarded_bid_id: str
    final_amount: float = Field(..., ge=0)
    scheduled_date: Optional[datetime] = None
    notes: Optional[str] = None
