"""Contractor Service for business logic."""
from typing import Optional
from app.repos.contractor_repo import ContractorRepo
from app.models.contractor import Contractor


class ContractorService:
    """Service for contractor operations."""

    def __init__(self):
        self.repo = ContractorRepo()

    async def get_contractor_by_email(self, email: str) -> Optional[Contractor]:
        """
        Get contractor by email address.

        Args:
            email: Contractor email

        Returns:
            Contractor if found, None otherwise
        """
        contractor_data = self.repo.get_by_email(email)
        if not contractor_data:
            return None
        return Contractor(**contractor_data)

    async def get_contractor_by_id(self, contractor_id: str) -> Optional[Contractor]:
        """
        Get contractor by ID.

        Args:
            contractor_id: Contractor ID

        Returns:
            Contractor if found, None otherwise
        """
        contractor_data = self.repo.get_profile(contractor_id)
        if not contractor_data:
            return None
        return Contractor(**contractor_data)


# Singleton instance
contractor_service = ContractorService()
