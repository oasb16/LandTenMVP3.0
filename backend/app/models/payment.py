"""
Payment models for job transactions via Stripe.

Handles landlord payments to contractors with 15% platform fee.
Landlord pays gross amount → Platform takes 15% → Contractor receives 85%
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class PaymentStatus(StrEnum):
    """Payment processing status."""
    PENDING = "pending"  # Payment not yet initiated
    AUTHORIZED = "authorized"  # Payment authorized but not captured
    PROCESSING = "processing"  # Payment being processed
    COMPLETED = "completed"  # Payment successful, contractor paid
    FAILED = "failed"  # Payment failed
    REFUNDED = "refunded"  # Payment refunded to landlord
    DISPUTED = "disputed"  # Payment disputed/chargeback


class Payment(BaseModel):
    """Main payment model for job transactions."""

    # Identifiers
    payment_id: str = Field(
        default_factory=lambda: f"pay_{uuid4().hex[:12]}",
        description="Unique payment identifier"
    )
    job_id: str = Field(..., description="Job this payment is for")
    bid_id: str = Field(..., description="Winning bid this payment is based on")

    # Parties
    landlord_id: str = Field(..., description="Landlord making the payment")
    contractor_id: str = Field(..., description="Contractor receiving payment")

    # Amounts (all in USD)
    gross_amount: float = Field(
        ...,
        description="Total amount landlord pays (100%)",
        gt=0
    )
    platform_fee: float = Field(
        ...,
        description="Platform fee (15% of gross)",
        ge=0
    )
    contractor_payout: float = Field(
        ...,
        description="Amount contractor receives (85% of gross)",
        gt=0
    )

    # Stripe integration
    stripe_payment_intent_id: Optional[str] = Field(
        None,
        description="Stripe PaymentIntent ID for landlord charge"
    )
    stripe_transfer_id: Optional[str] = Field(
        None,
        description="Stripe Transfer ID for contractor payout"
    )

    # Status
    status: PaymentStatus = Field(
        default=PaymentStatus.PENDING,
        description="Current payment status"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When payment record was created"
    )
    authorized_at: Optional[datetime] = Field(
        None,
        description="When payment was authorized"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="When payment was fully processed"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )

    # Error handling
    error_message: Optional[str] = Field(
        None,
        description="Error message if payment failed"
    )
    retry_count: int = Field(
        default=0,
        description="Number of retry attempts for failed payments",
        ge=0
    )

    # Refund tracking
    refund_amount: Optional[float] = Field(
        None,
        description="Amount refunded (if status=refunded)",
        ge=0
    )
    refund_reason: Optional[str] = Field(
        None,
        description="Reason for refund"
    )
    refunded_at: Optional[datetime] = Field(
        None,
        description="When refund was processed"
    )

    # Metadata
    notes: Optional[str] = Field(
        None,
        description="Additional notes about the payment"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "payment_id": "pay_a1b2c3d4e5f6",
                "job_id": "job_123456789abc",
                "bid_id": "bid_987654321xyz",
                "landlord_id": "user_landlord456",
                "contractor_id": "cont_contractor789",
                "gross_amount": 250.0,
                "platform_fee": 37.5,
                "contractor_payout": 212.5,
                "status": "pending",
                "created_at": "2025-12-07T10:00:00Z",
                "updated_at": "2025-12-07T10:00:00Z",
                "retry_count": 0
            }
        }


class PaymentCreate(BaseModel):
    """Request model for creating a payment."""
    job_id: str
    bid_id: str
    landlord_id: str
    contractor_id: str
    gross_amount: float = Field(..., gt=0)

    def calculate_splits(self) -> tuple[float, float]:
        """
        Calculate platform fee and contractor payout.

        Returns:
            tuple: (platform_fee, contractor_payout)
        """
        platform_fee = round(self.gross_amount * 0.15, 2)  # 15%
        contractor_payout = round(self.gross_amount * 0.85, 2)  # 85%
        return platform_fee, contractor_payout


class PaymentUpdate(BaseModel):
    """Request model for updating payment status."""
    status: Optional[PaymentStatus] = None
    stripe_payment_intent_id: Optional[str] = None
    stripe_transfer_id: Optional[str] = None
    authorized_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PaymentRefund(BaseModel):
    """Request model for processing a refund."""
    refund_amount: float = Field(..., gt=0, description="Amount to refund")
    refund_reason: str = Field(..., description="Reason for the refund")


class PaymentSummary(BaseModel):
    """Summary model for payment analytics."""
    total_payments: int = Field(default=0, description="Total number of payments")
    total_gross: float = Field(default=0.0, description="Total gross amount")
    total_platform_fees: float = Field(default=0.0, description="Total platform fees collected")
    total_contractor_payouts: float = Field(default=0.0, description="Total paid to contractors")
    completed_count: int = Field(default=0, description="Number of completed payments")
    pending_count: int = Field(default=0, description="Number of pending payments")
    failed_count: int = Field(default=0, description="Number of failed payments")
