"""Magic Link Service for contractor onboarding."""
import os
from datetime import datetime
from typing import Optional
import boto3
from botocore.exceptions import ClientError

from ..models.magic_link import MagicLinkToken, MagicLinkCreate


class MagicLinkService:
    """Service for managing magic link tokens."""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        table_prefix = os.getenv("TABLE_PREFIX", "landten")
        self.table_name = f"{table_prefix}-magic-links"
        self.table = self.dynamodb.Table(self.table_name)

    async def create_magic_link(
        self, request: MagicLinkCreate, frontend_url: str
    ) -> MagicLinkToken:
        """
        Create a new magic link token.

        Args:
            request: Magic link creation request
            frontend_url: Base frontend URL for constructing the magic link

        Returns:
            MagicLinkToken with generated token and metadata
        """
        # Create token
        token = MagicLinkToken(
            email=request.email,
            job_id=request.job_id,
            landlord_id=request.landlord_id,
            property_id=request.property_id,
            tenant_id=request.tenant_id,
        )

        # Save to DynamoDB
        try:
            self.table.put_item(Item=token.model_dump(mode="json"))
        except ClientError as e:
            raise Exception(f"Failed to create magic link: {str(e)}")

        return token

    async def verify_token(self, token: str) -> Optional[MagicLinkToken]:
        """
        Verify a magic link token.

        Args:
            token: The token string to verify

        Returns:
            MagicLinkToken if valid, None otherwise
        """
        try:
            # Scan for token (in production, consider using GSI)
            response = self.table.scan(
                FilterExpression="token = :token", ExpressionAttributeValues={":token": token}
            )

            if not response.get("Items"):
                return None

            magic_link = MagicLinkToken(**response["Items"][0])

            # Check if valid
            if not magic_link.is_valid():
                return None

            return magic_link

        except ClientError as e:
            print(f"Error verifying token: {str(e)}")
            return None

    async def mark_token_used(self, token: str, contractor_id: str) -> bool:
        """
        Mark a token as used.

        Args:
            token: The token string
            contractor_id: ID of contractor who used the token

        Returns:
            True if successful, False otherwise
        """
        try:
            # Find token first
            response = self.table.scan(
                FilterExpression="token = :token", ExpressionAttributeValues={":token": token}
            )

            if not response.get("Items"):
                return False

            token_id = response["Items"][0]["token_id"]

            # Update token
            self.table.update_item(
                Key={"token_id": token_id},
                UpdateExpression="SET is_used = :used, used_at = :used_at, contractor_id = :cid",
                ExpressionAttributeValues={
                    ":used": True,
                    ":used_at": datetime.utcnow().isoformat(),
                    ":cid": contractor_id,
                },
            )
            return True

        except ClientError as e:
            print(f"Error marking token as used: {str(e)}")
            return False

    async def get_token_by_email_and_job(
        self, email: str, job_id: str
    ) -> Optional[MagicLinkToken]:
        """
        Get an existing valid token for email and job combination.

        Args:
            email: Contractor email
            job_id: Job ID

        Returns:
            MagicLinkToken if found and valid, None otherwise
        """
        try:
            response = self.table.scan(
                FilterExpression="email = :email AND job_id = :job_id AND is_used = :used",
                ExpressionAttributeValues={
                    ":email": email,
                    ":job_id": job_id,
                    ":used": False,
                },
            )

            for item in response.get("Items", []):
                magic_link = MagicLinkToken(**item)
                if magic_link.is_valid():
                    return magic_link

            return None

        except ClientError as e:
            print(f"Error getting token: {str(e)}")
            return None


# Singleton instance
magic_link_service = MagicLinkService()
