"""
Payment models for LandTen platform - Stripe Checkout integration.

Handles three payment flows:
1. Landlord → Contractor payments (job completion)
2. Tenant → Landlord payments (rent/fees)
3. Landlord → Platform payments (platform fees)
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class PaymentType(str, Enum):
    """Type of payment."""
    JOB_COMPLETION = "job_completion"
    RENT = "rent"
    PLATFORM_FEE = "platform_fee"


class PaymentSessionStatus(str, Enum):
    """Payment session status."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Request Models for creating checkout sessions

class JobPaymentRequest(BaseModel):
    """Request to create a job payment checkout session."""
    job_id: str = Field(..., description="Job ID")
    bid_id: str = Field(..., description="Winning bid ID")
    contractor_name: str = Field(..., description="Contractor name")
    contractor_email: str = Field(..., description="Contractor email")
    landlord_email: str = Field(..., description="Landlord email (payer)")
    amount: float = Field(..., gt=0, description="Payment amount in USD")
    description: Optional[str] = Field(None, description="Job description")
    success_url: Optional[str] = Field(None, description="Success redirect URL")
    cancel_url: Optional[str] = Field(None, description="Cancel redirect URL")


class RentPaymentRequest(BaseModel):
    """Request to create a rent payment checkout session."""
    property_id: str = Field(..., description="Property ID")
    tenant_name: str = Field(..., description="Tenant name")
    tenant_email: str = Field(..., description="Tenant email (payer)")
    landlord_email: str = Field(..., description="Landlord email (receiver)")
    amount: float = Field(..., gt=0, description="Rent amount in USD")
    period: Optional[str] = Field(None, description="Rent period (e.g., 'January 2024')")
    success_url: Optional[str] = Field(None, description="Success redirect URL")
    cancel_url: Optional[str] = Field(None, description="Cancel redirect URL")


class PlatformFeeRequest(BaseModel):
    """Request to create a platform fee checkout session."""
    landlord_id: str = Field(..., description="Landlord ID")
    landlord_email: str = Field(..., description="Landlord email (payer)")
    landlord_name: str = Field(..., description="Landlord name")
    amount: float = Field(..., gt=0, description="Fee amount in USD")
    description: Optional[str] = Field("Platform subscription fee", description="Fee description")
    success_url: Optional[str] = Field(None, description="Success redirect URL")
    cancel_url: Optional[str] = Field(None, description="Cancel redirect URL")


# Response Models

class CheckoutSessionResponse(BaseModel):
    """Response from creating a checkout session."""
    success: bool = Field(..., description="Whether session creation was successful")
    checkoutUrl: Optional[str] = Field(None, description="Stripe checkout URL")
    sessionId: Optional[str] = Field(None, description="Stripe session ID")
    error: Optional[str] = Field(None, description="Error message if failed")


# Payment record models (for tracking in database)

class PaymentRecord(BaseModel):
    """Payment record for tracking transactions."""
    id: str = Field(..., description="Payment record ID")
    payment_type: PaymentType = Field(..., description="Type of payment")
    stripe_session_id: str = Field(..., description="Stripe checkout session ID")
    amount: float = Field(..., description="Payment amount in USD")
    status: PaymentSessionStatus = Field(default=PaymentSessionStatus.PENDING)

    # Payer info
    payer_email: str = Field(..., description="Email of person paying")
    payer_name: Optional[str] = Field(None, description="Name of person paying")

    # Receiver info (for rent and job payments)
    receiver_email: Optional[str] = Field(None, description="Email of person receiving")

    # Related entity IDs
    job_id: Optional[str] = Field(None, description="Related job ID")
    bid_id: Optional[str] = Field(None, description="Related bid ID")
    property_id: Optional[str] = Field(None, description="Related property ID")
    landlord_id: Optional[str] = Field(None, description="Related landlord ID")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None, description="When payment was completed")

    # Metadata
    period: Optional[str] = Field(None, description="Period for rent payments")
    description: Optional[str] = Field(None, description="Payment description")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class WebhookEvent(BaseModel):
    """Stripe webhook event data."""
    event_type: str = Field(..., description="Stripe event type")
    session_id: str = Field(..., description="Checkout session ID")
    payment_status: str = Field(..., description="Payment status")
    amount_total: Optional[int] = Field(None, description="Total amount in cents")
    customer_email: Optional[str] = Field(None, description="Customer email")
    metadata: Optional[dict] = Field(None, description="Custom metadata")
