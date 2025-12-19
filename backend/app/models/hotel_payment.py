"""
Hotel payment models for guest check-in/check-out with Elavon and Stripe.

Handles pre-authorization, payment completion, and mobile checkout.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import uuid4

from pydantic import BaseModel, Field


class PaymentProvider(str, Enum):
    """Payment provider type."""
    ELAVON = "elavon"
    STRIPE = "stripe"


class PaymentStatus(str, Enum):
    """Payment status."""
    PENDING = "pending"
    PRE_AUTHORIZED = "pre_authorized"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    FAILED = "failed"


class ReservationStatus(str, Enum):
    """Reservation status."""
    PENDING = "pending"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"


class ChargeCategory(str, Enum):
    """Charge category type."""
    ROOM = "room"
    RESTAURANT = "restaurant"
    BAR = "bar"
    SPA = "spa"
    LAUNDRY = "laundry"
    MINIBAR = "minibar"
    OTHER = "other"


class Charge(BaseModel):
    """Individual charge for a reservation."""
    id: str = Field(
        default_factory=lambda: f"chg_{uuid4().hex[:12]}",
        description="Unique charge identifier"
    )
    reservation_id: str = Field(..., description="Reservation this charge belongs to")
    description: str = Field(..., description="Description of the charge")
    amount: float = Field(..., gt=0, description="Charge amount in USD")
    category: ChargeCategory = Field(..., description="Category of the charge")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the charge was created"
    )


class Reservation(BaseModel):
    """Hotel reservation with payment information."""
    id: str = Field(
        default_factory=lambda: f"res_{uuid4().hex[:12]}",
        description="Unique reservation identifier"
    )
    guest_id: str = Field(..., description="Guest/user ID")
    guest_name: str = Field(..., description="Guest name")
    guest_email: str = Field(..., description="Guest email")
    guest_phone: Optional[str] = Field(None, description="Guest phone number")

    room_id: str = Field(..., description="Room identifier")
    room_number: Optional[str] = Field(None, description="Room number")

    check_in_date: datetime = Field(..., description="Check-in date/time")
    check_out_date: datetime = Field(..., description="Check-out date/time")

    status: ReservationStatus = Field(
        default=ReservationStatus.PENDING,
        description="Current reservation status"
    )

    # Payment fields
    pre_auth_transaction_id: Optional[str] = Field(
        None,
        description="Pre-authorization transaction ID"
    )
    pre_auth_amount: Optional[float] = Field(
        None,
        description="Pre-authorized amount"
    )
    final_transaction_id: Optional[str] = Field(
        None,
        description="Final completion transaction ID"
    )

    room_charges: float = Field(default=0.0, description="Total room charges")
    additional_charges: List[Charge] = Field(
        default_factory=list,
        description="Additional charges (restaurant, spa, etc.)"
    )
    total_charges: float = Field(default=0.0, description="Total amount charged")

    payment_status: PaymentStatus = Field(
        default=PaymentStatus.PENDING,
        description="Current payment status"
    )
    payment_provider: Optional[PaymentProvider] = Field(
        None,
        description="Payment provider used"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When reservation was created"
    )
    checked_in_at: Optional[datetime] = Field(
        None,
        description="When guest checked in"
    )
    checked_out_at: Optional[datetime] = Field(
        None,
        description="When guest checked out"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )

    # Metadata
    notes: Optional[str] = Field(None, description="Additional notes")

    def calculate_total_charges(self) -> float:
        """Calculate total charges including room and additional charges."""
        additional_total = sum(charge.amount for charge in self.additional_charges)
        return self.room_charges + additional_total

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class ElavonConfig(BaseModel):
    """Elavon configuration."""
    merchant_id: str
    user_id: str
    pin: str
    terminal_id: str
    api_endpoint: str
    is_test_mode: bool = True

    # Token (transient)
    token: Optional[str] = None
    token_expires_at: Optional[datetime] = None

    # Mobile checkout (Converge)
    checkout_js_enabled: bool = False
    converge_merchant_id: Optional[str] = None
    converge_user_id: Optional[str] = None
    converge_pin: Optional[str] = None


class PaymentConfigModel(BaseModel):
    """Payment configuration."""
    active_provider: PaymentProvider = PaymentProvider.ELAVON
    elavon: Optional[ElavonConfig] = None
    stripe_enabled: bool = True


# Request/Response Models

class ElavonTokenRequest(BaseModel):
    """Request to get Elavon token."""
    merchant_id: str
    user_id: str
    pin: str
    api_endpoint: str


class ElavonPreAuthRequest(BaseModel):
    """Request to pre-authorize payment."""
    token: str
    amount: float = Field(..., gt=0)
    terminal_id: str
    merchant_id: str


class ElavonCompletionRequest(BaseModel):
    """Request to complete/capture payment."""
    token: str
    original_transaction_id: str
    amount: float = Field(..., gt=0)
    terminal_id: str
    merchant_id: str


class StripeCheckoutRequest(BaseModel):
    """Request to create Stripe checkout session."""
    amount: float = Field(..., gt=0)
    guest_name: str
    guest_email: str
    guest_phone: Optional[str] = None
    reservation_id: str
    hotel_name: Optional[str] = "Hotel"


class ElavonCheckoutRequest(BaseModel):
    """Request to create Elavon mobile checkout session."""
    merchant_id: str
    user_id: str
    pin: str
    amount: float = Field(..., gt=0)
    transaction_type: str = "ccsale"
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    email: Optional[str] = ""
    invoice_number: Optional[str] = ""
    is_test_mode: bool = True


class SendEmailRequest(BaseModel):
    """Request to send checkout email."""
    guest_email: str
    guest_name: str
    amount: float
    hotel_name: Optional[str] = "Hotel"
    checkout_url: Optional[str] = None
    type: str = "payment_link"  # payment_link or receipt
    room_number: Optional[str] = None
    nights: Optional[int] = None
    check_in_date: Optional[str] = None
    check_out_date: Optional[str] = None
    room_charges: Optional[float] = None
    additional_charges: Optional[List[dict]] = None
    transaction_id: Optional[str] = None


class SendSMSRequest(BaseModel):
    """Request to send checkout SMS."""
    phone_number: str
    guest_name: str
    amount: float
    checkout_url: str
    hotel_name: Optional[str] = "Hotel"
