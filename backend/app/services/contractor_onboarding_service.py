"""
Contractor Onboarding Service

Business logic for production-grade contractor onboarding.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import logging

from ..models.contractor_onboarding import (
    ContractorOnboardingState,
    OnboardingStep,
    OnboardingStatus,
    LicenseData,
    IdentityData,
    PaymentData,
    CardSubmission
)
from ..repos.contractor_onboarding_repo import ContractorOnboardingRepo
from ..repos.contractor_repo import ContractorRepo

logger = logging.getLogger(__name__)


class ContractorOnboardingService:
    """Service for contractor onboarding operations."""

    def __init__(self):
        self.onboarding_repo = ContractorOnboardingRepo()
        self.contractor_repo = ContractorRepo()

    async def create_or_get_onboarding_state(
        self,
        contractor_id: str,
        channel_id: str,
        email: str,
        token_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContractorOnboardingState:
        """
        Create or retrieve existing onboarding state for a contractor.

        This prevents duplicate onboarding and ensures we can resume progress.

        Args:
            contractor_id: Contractor ID
            channel_id: Stream Chat channel ID
            email: Contractor email
            token_id: Magic link token ID (if applicable)
            metadata: Additional metadata (job_id, etc.)

        Returns:
            Onboarding state
        """
        # Check if state already exists
        existing_state = self.onboarding_repo.get_by_contractor_id(contractor_id)

        if existing_state:
            logger.info(f"[onboarding-service] Resuming existing onboarding for {contractor_id}")
            return ContractorOnboardingState(**existing_state)

        # Create new state
        state = ContractorOnboardingState(
            contractor_id=contractor_id,
            channel_id=channel_id,
            email=email,
            token_id=token_id,
            metadata=metadata or {},
            status=OnboardingStatus.IN_PROGRESS
        )

        state_dict = state.model_dump(mode='json')
        self.onboarding_repo.create_or_get_state(state_dict)

        logger.info(f"[onboarding-service] Created new onboarding state for {contractor_id}")
        return state

    async def get_state_by_contractor_id(
        self,
        contractor_id: str
    ) -> Optional[ContractorOnboardingState]:
        """Get onboarding state by contractor ID."""
        state_data = self.onboarding_repo.get_by_contractor_id(contractor_id)
        if not state_data:
            return None
        return ContractorOnboardingState(**state_data)

    async def get_state_by_channel_id(
        self,
        channel_id: str
    ) -> Optional[ContractorOnboardingState]:
        """Get onboarding state by channel ID."""
        state_data = self.onboarding_repo.get_by_channel_id(channel_id)
        if not state_data:
            return None
        return ContractorOnboardingState(**state_data)

    async def has_card_been_sent(
        self,
        contractor_id: str,
        card_type: str
    ) -> bool:
        """
        Check if a card has already been sent to prevent duplicates.

        Args:
            contractor_id: Contractor ID
            card_type: Card type (license_verification, identity_verification, etc.)

        Returns:
            True if card was already sent
        """
        state = await self.get_state_by_contractor_id(contractor_id)
        if not state:
            return False

        return card_type in state.cards_sent

    async def mark_card_sent(
        self,
        contractor_id: str,
        card_type: str
    ) -> None:
        """Mark that a card was sent."""
        state = await self.get_state_by_contractor_id(contractor_id)
        if not state:
            logger.warning(f"[onboarding-service] Cannot mark card sent - state not found for {contractor_id}")
            return

        now = datetime.utcnow().isoformat()
        self.onboarding_repo.mark_card_sent(state.state_id, card_type, now)

    async def submit_license_data(
        self,
        contractor_id: str,
        license_number: str,
        business_address: str,
        website: Optional[str] = None
    ) -> ContractorOnboardingState:
        """
        Submit license verification data.

        Updates both onboarding state AND contractor profile.

        Args:
            contractor_id: Contractor ID
            license_number: License number
            business_address: Business address
            website: Website URL

        Returns:
            Updated onboarding state
        """
        state = await self.get_state_by_contractor_id(contractor_id)
        if not state:
            raise ValueError(f"Onboarding state not found for contractor {contractor_id}")

        # Create license data
        license_data = LicenseData(
            license_number=license_number,
            business_address=business_address,
            website=website,
            submitted_at=datetime.utcnow()
        )

        # Update onboarding state
        self.onboarding_repo.update_license_data(
            state.state_id,
            license_data.model_dump(mode='json')
        )

        # Update contractor profile
        self.contractor_repo.table.update_item(
            Key={"contractor_id": contractor_id},
            UpdateExpression="SET license_number = :license, website = :website, onboarding_license_submitted = :submitted, onboarding_current_step = :step, updated_at = :now",
            ExpressionAttributeValues={
                ":license": license_number,
                ":website": website or "",
                ":submitted": True,
                ":step": OnboardingStep.IDENTITY_VERIFICATION,
                ":now": datetime.utcnow().isoformat()
            }
        )

        # Update current step
        self.onboarding_repo.update_state(state.state_id, {
            "current_step": OnboardingStep.IDENTITY_VERIFICATION,
            "updated_at": datetime.utcnow().isoformat()
        })

        logger.info(f"[onboarding-service] Submitted license data for {contractor_id}")

        # Return updated state
        return await self.get_state_by_contractor_id(contractor_id)

    async def submit_identity_verification(
        self,
        contractor_id: str,
        jumio_transaction_id: Optional[str] = None,
        verification_status: str = "pending"
    ) -> ContractorOnboardingState:
        """
        Submit identity verification data.

        Args:
            contractor_id: Contractor ID
            jumio_transaction_id: Jumio transaction ID
            verification_status: Verification status

        Returns:
            Updated onboarding state
        """
        state = await self.get_state_by_contractor_id(contractor_id)
        if not state:
            raise ValueError(f"Onboarding state not found for contractor {contractor_id}")

        # Create identity data
        identity_data = IdentityData(
            jumio_transaction_id=jumio_transaction_id,
            verification_status=verification_status,
            submitted_at=datetime.utcnow()
        )

        # Update onboarding state
        self.onboarding_repo.update_identity_data(
            state.state_id,
            identity_data.model_dump(mode='json')
        )

        # Update contractor profile
        self.contractor_repo.table.update_item(
            Key={"contractor_id": contractor_id},
            UpdateExpression="SET onboarding_identity_verified = :verified, onboarding_current_step = :step, updated_at = :now",
            ExpressionAttributeValues={
                ":verified": verification_status == "approved",
                ":step": OnboardingStep.PAYMENT_SETUP,
                ":now": datetime.utcnow().isoformat()
            }
        )

        # Update current step
        self.onboarding_repo.update_state(state.state_id, {
            "current_step": OnboardingStep.PAYMENT_SETUP,
            "updated_at": datetime.utcnow().isoformat()
        })

        logger.info(f"[onboarding-service] Submitted identity verification for {contractor_id}")

        return await self.get_state_by_contractor_id(contractor_id)

    async def submit_payment_setup(
        self,
        contractor_id: str,
        stripe_account_id: str,
        onboarding_url: str,
        stripe_onboarding_complete: bool = False
    ) -> ContractorOnboardingState:
        """
        Submit payment setup data (Stripe Connect).

        Args:
            contractor_id: Contractor ID
            stripe_account_id: Stripe Connect account ID
            onboarding_url: Stripe onboarding URL
            stripe_onboarding_complete: Whether Stripe onboarding is complete

        Returns:
            Updated onboarding state
        """
        state = await self.get_state_by_contractor_id(contractor_id)
        if not state:
            raise ValueError(f"Onboarding state not found for contractor {contractor_id}")

        # Create payment data
        payment_data = PaymentData(
            stripe_account_id=stripe_account_id,
            stripe_onboarding_complete=stripe_onboarding_complete,
            onboarding_url=onboarding_url,
            setup_started_at=datetime.utcnow()
        )

        # Update onboarding state
        self.onboarding_repo.update_payment_data(
            state.state_id,
            payment_data.model_dump(mode='json')
        )

        # Update contractor profile
        self.contractor_repo.table.update_item(
            Key={"contractor_id": contractor_id},
            UpdateExpression="SET stripe_account_id = :stripe_id, stripe_onboarding_complete = :complete, onboarding_payment_setup = :setup, updated_at = :now",
            ExpressionAttributeValues={
                ":stripe_id": stripe_account_id,
                ":complete": stripe_onboarding_complete,
                ":setup": True,
                ":now": datetime.utcnow().isoformat()
            }
        )

        # If Stripe onboarding is complete, mark onboarding as done
        if stripe_onboarding_complete:
            await self.complete_onboarding(contractor_id)

        logger.info(f"[onboarding-service] Submitted payment setup for {contractor_id}")

        return await self.get_state_by_contractor_id(contractor_id)

    async def complete_onboarding(self, contractor_id: str) -> None:
        """Mark onboarding as completed."""
        state = await self.get_state_by_contractor_id(contractor_id)
        if not state:
            logger.warning(f"[onboarding-service] Cannot complete - state not found for {contractor_id}")
            return

        now = datetime.utcnow().isoformat()

        # Update onboarding state
        self.onboarding_repo.mark_completed(state.state_id, now)

        # Update contractor profile
        self.contractor_repo.table.update_item(
            Key={"contractor_id": contractor_id},
            UpdateExpression="SET onboarding_complete = :complete, onboarding_current_step = :step, #status = :status, updated_at = :now",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":complete": True,
                ":step": OnboardingStep.COMPLETED,
                ":status": "active",  # Activate contractor
                ":now": now
            }
        )

        logger.info(f"[onboarding-service] Completed onboarding for {contractor_id}")

    async def get_onboarding_progress(
        self,
        contractor_id: str
    ) -> Dict[str, Any]:
        """
        Get onboarding progress for UI display.

        Returns:
            Progress information including current step, completed steps, and saved data
        """
        state = await self.get_state_by_contractor_id(contractor_id)
        if not state:
            return {
                "status": "not_started",
                "current_step": "welcome",
                "progress_percentage": 0,
                "steps": {
                    "license_verification": {"completed": False, "data": None},
                    "identity_verification": {"completed": False, "data": None},
                    "payment_setup": {"completed": False, "data": None}
                }
            }

        # Calculate progress
        steps_completed = 0
        total_steps = 3

        if state.license_data:
            steps_completed += 1
        if state.identity_data and state.identity_data.verification_status == "approved":
            steps_completed += 1
        if state.payment_data and state.payment_data.stripe_onboarding_complete:
            steps_completed += 1

        progress_percentage = int((steps_completed / total_steps) * 100)

        return {
            "status": state.status,
            "current_step": state.current_step,
            "progress_percentage": progress_percentage,
            "steps": {
                "license_verification": {
                    "completed": state.license_data is not None,
                    "data": state.license_data.model_dump(mode='json') if state.license_data else None
                },
                "identity_verification": {
                    "completed": state.identity_data is not None and state.identity_data.verification_status == "approved",
                    "data": state.identity_data.model_dump(mode='json') if state.identity_data else None
                },
                "payment_setup": {
                    "completed": state.payment_data is not None and state.payment_data.stripe_onboarding_complete,
                    "data": state.payment_data.model_dump(mode='json') if state.payment_data else None
                }
            },
            "created_at": state.created_at.isoformat() if isinstance(state.created_at, datetime) else state.created_at,
            "last_interaction_at": state.last_interaction_at.isoformat() if isinstance(state.last_interaction_at, datetime) else state.last_interaction_at
        }


# Singleton instance
contractor_onboarding_service = ContractorOnboardingService()
