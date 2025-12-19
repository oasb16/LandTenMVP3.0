"""Magic Link Token Models for contractor onboarding."""
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field
import secrets
import uuid


class MagicLinkToken(BaseModel):
    """Magic link token for contractor onboarding."""

    token_id: str = Field(default_factory=lambda: f"mlt_{uuid.uuid4().hex}")
    token: str = Field(default_factory=lambda: secrets.token_urlsafe(32))

    # Associated data
    email: str
    job_id: str
    landlord_id: str
    property_id: str
    tenant_id: str

    # Token lifecycle
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(hours=48)
    )
    used_at: Optional[datetime] = None

    # Status
    is_used: bool = False
    is_expired: bool = False

    # Contractor created from this link
    contractor_id: Optional[str] = None

    def is_valid(self) -> bool:
        """Check if token is still valid."""
        if self.is_used:
            return False
        if self.is_expired:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        return True

    def mark_used(self, contractor_id: str):
        """Mark token as used."""
        self.is_used = True
        self.used_at = datetime.utcnow()
        self.contractor_id = contractor_id


class MagicLinkCreate(BaseModel):
    """Request to create a magic link."""

    email: str
    job_id: str
    landlord_id: str
    property_id: str
    tenant_id: str


class MagicLinkVerify(BaseModel):
    """Request to verify a magic link token."""

    token: str


class MagicLinkResponse(BaseModel):
    """Response with magic link information."""

    token: str
    magic_link_url: str
    email: str
    job_id: str
    expires_at: datetime


class MagicLinkVerifyResponse(BaseModel):
    """Response from magic link verification."""

    valid: bool
    email: str
    job_id: str
    landlord_id: str
    property_id: str
    tenant_id: str
    contractor_id: Optional[str] = None  # If contractor already exists
    message: str
