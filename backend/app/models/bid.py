"""
Bid models for contractor proposals on jobs.

Contractors submit bids with pricing, timeline, and details.
Landlord reviews and accepts/rejects bids.
"""

from datetime import datetime
from enum import StrEnum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class BidStatus(StrEnum):
    """Status progression for bids."""
    SUBMITTED = "submitted"  # Bid submitted by contractor
    UNDER_REVIEW = "under_review"  # Landlord is reviewing
    ACCEPTED = "accepted"  # Landlord accepted the bid
    REJECTED = "rejected"  # Landlord rejected the bid
    WITHDRAWN = "withdrawn"  # Contractor withdrew their bid


class Bid(BaseModel):
    """Main bid model for contractor proposals."""

    # Identifiers
    bid_id: str = Field(
        default_factory=lambda: f"bid_{uuid4().hex[:12]}",
        description="Unique bid identifier"
    )
    job_id: str = Field(..., description="Job this bid is for")
    contractor_id: str = Field(..., description="Contractor submitting the bid")

    # Contractor info (denormalized for quick display)
    contractor_name: str = Field(..., description="Business name of contractor")
    contractor_rating: Optional[float] = Field(
        None,
        description="Contractor's average rating (0-5)",
        ge=0,
        le=5
    )
    contractor_jobs_completed: int = Field(
        default=0,
        description="Number of jobs contractor has completed",
        ge=0
    )

    # Pricing breakdown
    amount: float = Field(..., description="Total bid amount", gt=0)
    materials_cost: Optional[float] = Field(
        None,
        description="Estimated materials cost",
        ge=0
    )
    labor_cost: Optional[float] = Field(
        None,
        description="Estimated labor cost",
        ge=0
    )

    # Timeline
    estimated_hours: Optional[float] = Field(
        None,
        description="Estimated hours to complete",
        gt=0
    )
    proposed_start_date: Optional[datetime] = Field(
        None,
        description="When contractor can start work"
    )
    estimated_completion_days: Optional[int] = Field(
        None,
        description="Estimated days to complete after starting",
        gt=0
    )

    # Proposal details
    description: str = Field(
        ...,
        description="Detailed proposal description and approach"
    )
    notes: Optional[str] = Field(
        None,
        description="Additional notes or qualifications"
    )

    # Status
    status: BidStatus = Field(
        default=BidStatus.SUBMITTED,
        description="Current bid status"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When bid was submitted"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    reviewed_at: Optional[datetime] = Field(
        None,
        description="When landlord reviewed the bid"
    )

    # Rejection/withdrawal reason
    status_reason: Optional[str] = Field(
        None,
        description="Reason for rejection or withdrawal"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "bid_id": "bid_a1b2c3d4e5f6",
                "job_id": "job_123456789abc",
                "contractor_id": "cont_987654321xyz",
                "contractor_name": "ABC Plumbing Services",
                "contractor_rating": 4.8,
                "contractor_jobs_completed": 127,
                "amount": 250.0,
                "materials_cost": 75.0,
                "labor_cost": 175.0,
                "estimated_hours": 3.0,
                "proposed_start_date": "2025-12-10T09:00:00Z",
                "estimated_completion_days": 1,
                "description": "I can fix the kitchen sink leak by replacing the P-trap and supply lines. I have all materials in stock.",
                "status": "submitted",
                "created_at": "2025-12-07T10:00:00Z",
                "updated_at": "2025-12-07T10:00:00Z"
            }
        }


class BidCreate(BaseModel):
    """Request model for creating a new bid."""
    job_id: str
    contractor_id: str
    contractor_name: str
    contractor_rating: Optional[float] = Field(None, ge=0, le=5)
    contractor_jobs_completed: int = Field(default=0, ge=0)
    amount: float = Field(..., gt=0)
    materials_cost: Optional[float] = Field(None, ge=0)
    labor_cost: Optional[float] = Field(None, ge=0)
    estimated_hours: Optional[float] = Field(None, gt=0)
    proposed_start_date: Optional[datetime] = None
    estimated_completion_days: Optional[int] = Field(None, gt=0)
    description: str
    notes: Optional[str] = None


class BidUpdate(BaseModel):
    """Request model for updating a bid."""
    amount: Optional[float] = Field(None, gt=0)
    materials_cost: Optional[float] = Field(None, ge=0)
    labor_cost: Optional[float] = Field(None, ge=0)
    estimated_hours: Optional[float] = Field(None, gt=0)
    proposed_start_date: Optional[datetime] = None
    estimated_completion_days: Optional[int] = Field(None, gt=0)
    description: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[BidStatus] = None
    status_reason: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BidReview(BaseModel):
    """Request model for reviewing a bid (accept/reject)."""
    status: BidStatus = Field(..., description="New status (accepted or rejected)")
    status_reason: Optional[str] = Field(
        None,
        description="Reason for decision (especially for rejection)"
    )
