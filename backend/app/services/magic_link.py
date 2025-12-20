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
        # Initialize DynamoDB resource with region from environment
        region = os.getenv("AWS_REGION", "us-east-1")
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
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
            # Convert to dict with ISO datetime strings for DynamoDB
            token_dict = token.model_dump()

            # Convert datetime objects to ISO strings
            if isinstance(token_dict.get('created_at'), datetime):
                token_dict['created_at'] = token_dict['created_at'].isoformat()
            if isinstance(token_dict.get('expires_at'), datetime):
                token_dict['expires_at'] = token_dict['expires_at'].isoformat()
            if token_dict.get('used_at') and isinstance(token_dict['used_at'], datetime):
                token_dict['used_at'] = token_dict['used_at'].isoformat()

            print(f"[MagicLinkService] Saving token to DynamoDB: {token.token_id}")
            print(f"[MagicLinkService] Token: {token.token[:20]}...")
            print(f"[MagicLinkService] Table: {self.table_name}")
            print(f"[MagicLinkService] Token dict keys: {list(token_dict.keys())}")

            self.table.put_item(Item=token_dict)

            print(f"[MagicLinkService] ✓ Token saved successfully to {self.table_name}")
        except ClientError as e:
            print(f"[MagicLinkService] ✗ DynamoDB ClientError: {str(e)}")
            raise Exception(f"Failed to create magic link: {str(e)}")
        except Exception as e:
            print(f"[MagicLinkService] ✗ Unexpected error: {str(e)}")
            raise

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
            print(f"[MagicLinkService] Verifying token: {token[:20]}...")
            print(f"[MagicLinkService] Scanning table: {self.table_name}")

            # Scan for token (in production, consider using GSI)
            # Note: 'token' is a reserved keyword in DynamoDB, so we use ExpressionAttributeNames
            response = self.table.scan(
                FilterExpression="#token = :token_value",
                ExpressionAttributeNames={"#token": "token"},
                ExpressionAttributeValues={":token_value": token}
            )

            print(f"[MagicLinkService] Scan returned {len(response.get('Items', []))} items")

            if not response.get("Items"):
                print(f"[MagicLinkService] ✗ Token not found in database")
                # Let's also check what tokens ARE in the table
                all_response = self.table.scan()
                print(f"[MagicLinkService] Total items in table: {len(all_response.get('Items', []))}")
                if all_response.get('Items'):
                    print(f"[MagicLinkService] Sample token IDs in table: {[item.get('token_id') for item in all_response.get('Items', [])[:3]]}")
                return None

            print(f"[MagicLinkService] ✓ Token found in database")
            item_data = response["Items"][0]
            print(f"[MagicLinkService] Token data keys: {list(item_data.keys())}")

            magic_link = MagicLinkToken(**item_data)

            # Check if valid
            print(f"[MagicLinkService] Checking if token is valid...")
            print(f"[MagicLinkService]   is_used: {magic_link.is_used}")
            print(f"[MagicLinkService]   is_expired: {magic_link.is_expired}")
            print(f"[MagicLinkService]   expires_at: {magic_link.expires_at}")
            print(f"[MagicLinkService]   current time: {datetime.utcnow()}")

            if not magic_link.is_valid():
                print(f"[MagicLinkService] ✗ Token is not valid")
                return None

            print(f"[MagicLinkService] ✓ Token is valid")
            return magic_link

        except ClientError as e:
            print(f"[MagicLinkService] ✗ DynamoDB ClientError: {str(e)}")
            return None
        except Exception as e:
            print(f"[MagicLinkService] ✗ Unexpected error during verification: {str(e)}")
            import traceback
            traceback.print_exc()
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
            # Note: 'token' is a reserved keyword in DynamoDB, so we use ExpressionAttributeNames
            response = self.table.scan(
                FilterExpression="#token = :token_value",
                ExpressionAttributeNames={"#token": "token"},
                ExpressionAttributeValues={":token_value": token}
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
