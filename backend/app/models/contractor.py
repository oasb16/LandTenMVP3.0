"""
Contractor models for service providers in the marketplace.

Contractors register, build profiles, and bid on jobs.
They receive payments via Stripe Connect.
"""

from datetime import datetime
from enum import StrEnum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, EmailStr


class ContractorStatus(StrEnum):
    """Contractor account status."""
    PENDING = "pending"  # Registration submitted, awaiting verification
    ACTIVE = "active"  # Verified and can bid on jobs
    SUSPENDED = "suspended"  # Temporarily suspended
    DEACTIVATED = "deactivated"  # Account deactivated


class InsuranceStatus(StrEnum):
    """Insurance verification status."""
    NOT_VERIFIED = "not_verified"
    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"


class Contractor(BaseModel):
    """Main contractor model for service providers."""

    # Identifiers
    contractor_id: str = Field(
        default_factory=lambda: f"cont_{uuid4().hex[:12]}",
        description="Unique contractor identifier"
    )
    user_id: str = Field(..., description="Associated user account ID")

    # Business information
    business_name: str = Field(..., description="Legal or DBA business name")
    email: EmailStr = Field(..., description="Business contact email")
    phone: str = Field(..., description="Business phone number")

    # Service details
    categories: List[str] = Field(
        default_factory=list,
        description="Service categories (plumbing, electrical, hvac, etc.)"
    )
    service_zip_codes: List[str] = Field(
        default_factory=list,
        description="ZIP codes where contractor provides service"
    )

    # Performance metrics
    rating: Optional[float] = Field(
        None,
        description="Average rating from completed jobs (0-5)",
        ge=0,
        le=5
    )
    total_jobs: int = Field(
        default=0,
        description="Total number of jobs bid on",
        ge=0
    )
    completed_jobs: int = Field(
        default=0,
        description="Number of successfully completed jobs",
        ge=0
    )

    # Credentials
    license_number: Optional[str] = Field(
        None,
        description="Professional license number (if applicable)"
    )
    insurance_verified: InsuranceStatus = Field(
        default=InsuranceStatus.NOT_VERIFIED,
        description="Insurance verification status"
    )
    insurance_expiry_date: Optional[datetime] = Field(
        None,
        description="When insurance expires (if verified)"
    )

    # Payment
    stripe_account_id: Optional[str] = Field(
        None,
        description="Stripe Connect account ID for receiving payments"
    )
    stripe_onboarding_complete: bool = Field(
        default=False,
        description="Whether Stripe onboarding is complete"
    )

    # Status
    status: ContractorStatus = Field(
        default=ContractorStatus.PENDING,
        description="Account status"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When contractor registered"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last profile update"
    )
    verified_at: Optional[datetime] = Field(
        None,
        description="When account was verified"
    )

    # Additional information
    bio: Optional[str] = Field(
        None,
        description="Contractor bio/description",
        max_length=1000
    )
    website: Optional[str] = Field(
        None,
        description="Business website URL"
    )
    profile_photo_url: Optional[str] = Field(
        None,
        description="S3 URL of profile photo"
    )

    # Financial metrics
    total_earnings: float = Field(
        default=0.0,
        description="Total earnings from completed jobs",
        ge=0
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "contractor_id": "cont_a1b2c3d4e5f6",
                "user_id": "user_987654321xyz",
                "business_name": "ABC Plumbing Services",
                "email": "contact@abcplumbing.com",
                "phone": "+1-555-123-4567",
                "categories": ["plumbing", "hvac"],
                "service_zip_codes": ["94102", "94103", "94104"],
                "rating": 4.8,
                "total_jobs": 150,
                "completed_jobs": 127,
                "license_number": "CA-PL-12345",
                "insurance_verified": "verified",
                "status": "active",
                "stripe_onboarding_complete": True,
                "total_earnings": 45000.0,
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-12-07T10:00:00Z"
            }
        }


class ContractorCreate(BaseModel):
    """Request model for contractor registration."""
    user_id: str
    business_name: str
    email: EmailStr
    phone: str
    categories: List[str] = Field(default_factory=list)
    service_zip_codes: List[str] = Field(default_factory=list)
    license_number: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=1000)
    website: Optional[str] = None


class ContractorUpdate(BaseModel):
    """Request model for updating contractor profile."""
    business_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    categories: Optional[List[str]] = None
    service_zip_codes: Optional[List[str]] = None
    license_number: Optional[str] = None
    insurance_verified: Optional[InsuranceStatus] = None
    insurance_expiry_date: Optional[datetime] = None
    status: Optional[ContractorStatus] = None
    bio: Optional[str] = Field(None, max_length=1000)
    website: Optional[str] = None
    profile_photo_url: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContractorMetricsUpdate(BaseModel):
    """Internal model for updating contractor performance metrics."""
    rating: Optional[float] = Field(None, ge=0, le=5)
    total_jobs: Optional[int] = Field(None, ge=0)
    completed_jobs: Optional[int] = Field(None, ge=0)
    total_earnings: Optional[float] = Field(None, ge=0)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
