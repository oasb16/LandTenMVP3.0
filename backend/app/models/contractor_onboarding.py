"""
Contractor Onboarding State Models

Tracks the complete onboarding journey for each contractor with proper data linkage.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import uuid4


class OnboardingStep(str, Enum):
    """Onboarding flow steps."""
    WELCOME = "welcome"
    LICENSE_VERIFICATION = "license_verification"
    IDENTITY_VERIFICATION = "identity_verification"
    PAYMENT_SETUP = "payment_setup"
    COMPLETED = "completed"


class OnboardingStatus(str, Enum):
    """Overall onboarding status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class LicenseData(BaseModel):
    """License verification data."""
    license_number: str
    business_address: str
    website: Optional[str] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    verified: bool = False
    verified_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class IdentityData(BaseModel):
    """Identity verification data."""
    jumio_transaction_id: Optional[str] = None
    verification_status: str = "not_started"  # not_started, pending, approved, rejected
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class PaymentData(BaseModel):
    """Payment setup data."""
    stripe_account_id: Optional[str] = None
    stripe_onboarding_complete: bool = False
    onboarding_url: Optional[str] = None
    setup_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class ContractorOnboardingState(BaseModel):
    """
    Complete onboarding state for a contractor.

    This model ties together all aspects of contractor onboarding:
    - contractor_id: Links to the contractor record
    - channel_id: Links to the Stream Chat channel (unique conversation)
    - token_id: Links to the magic link token used for initial access
    - Stores all card submission data for rebuilding UI
    """

    # Primary identifiers - THE BILLION DOLLAR DATA MODEL
    state_id: str = Field(
        default_factory=lambda: f"onboard_{uuid4().hex[:12]}",
        description="Unique onboarding state identifier"
    )
    contractor_id: str = Field(..., description="Contractor being onboarded")
    channel_id: str = Field(..., description="Stream Chat channel ID for this onboarding")
    token_id: Optional[str] = Field(None, description="Magic link token that started this onboarding")

    # Contractor basic info (immutable after creation)
    email: str = Field(..., description="Contractor email (immutable)")
    business_name: Optional[str] = Field(None, description="Business name (immutable after first set)")
    phone: Optional[str] = Field(None, description="Phone number")

    # Onboarding progress
    current_step: OnboardingStep = Field(
        default=OnboardingStep.WELCOME,
        description="Current step in onboarding flow"
    )
    status: OnboardingStatus = Field(
        default=OnboardingStatus.NOT_STARTED,
        description="Overall onboarding status"
    )

    # Card data (allows rebuilding UI from saved data)
    license_data: Optional[LicenseData] = Field(None, description="License verification data")
    identity_data: Optional[IdentityData] = Field(None, description="Identity verification data")
    payment_data: Optional[PaymentData] = Field(None, description="Payment setup data")

    # Tracking
    cards_sent: Dict[str, datetime] = Field(
        default_factory=dict,
        description="Track which cards were sent and when (prevents duplicates)"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When onboarding started"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="When onboarding completed"
    )
    last_interaction_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last time contractor interacted with chat"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (job_id, referral source, etc.)"
    )

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "state_id": "onboard_a1b2c3d4e5f6",
                "contractor_id": "cont_x1y2z3a4b5c6",
                "channel_id": "contractor-cont_x1y2z3a4b5c6",
                "token_id": "token_abc123def456",
                "email": "contractor@example.com",
                "business_name": "ABC Plumbing",
                "phone": "+1-555-123-4567",
                "current_step": "license_verification",
                "status": "in_progress",
                "license_data": {
                    "license_number": "CA-PL-12345",
                    "business_address": "123 Main St, San Francisco, CA 94102",
                    "website": "https://abcplumbing.com",
                    "submitted_at": "2025-12-22T10:00:00Z",
                    "verified": False
                },
                "cards_sent": {
                    "license_verification": "2025-12-22T10:00:00Z"
                }
            }
        }


class OnboardingStateUpdate(BaseModel):
    """Update model for onboarding state."""
    current_step: Optional[OnboardingStep] = None
    status: Optional[OnboardingStatus] = None
    license_data: Optional[LicenseData] = None
    identity_data: Optional[IdentityData] = None
    payment_data: Optional[PaymentData] = None
    business_name: Optional[str] = None
    phone: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CardSubmission(BaseModel):
    """Generic card submission data."""
    contractor_id: str
    card_type: str  # license_verification, identity_verification, bank_setup
    data: Dict[str, Any]
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
