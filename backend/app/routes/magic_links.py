"""Magic Link API Routes for contractor onboarding."""
import os
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any
import boto3
from botocore.exceptions import ClientError

from ..models.magic_link import (
    MagicLinkCreate,
    MagicLinkVerify,
    MagicLinkResponse,
    MagicLinkVerifyResponse,
)
from ..services.magic_link import magic_link_service
from ..services.contractor import contractor_service
from ..deps.dynamo import get_dynamo_resource, table_name

router = APIRouter(prefix="/api/v1/magic-links", tags=["magic-links"])

# DynamoDB resources
dynamodb = get_dynamo_resource()
jobs_table = dynamodb.Table(table_name("jobs"))
bids_table = dynamodb.Table(table_name("bids"))
payments_table = dynamodb.Table(table_name("payments"))


@router.post("/create", response_model=MagicLinkResponse)
async def create_magic_link(request: MagicLinkCreate):
    """
    Create a magic link for contractor onboarding.

    This endpoint is called by landlords when they want to invite a contractor to a job.
    """
    try:
        # Check if there's already a valid token for this email/job combo
        existing_token = await magic_link_service.get_token_by_email_and_job(
            request.email, request.job_id
        )

        if existing_token:
            # Reuse existing valid token
            magic_link_token = existing_token
        else:
            # Create new token
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            magic_link_token = await magic_link_service.create_magic_link(
                request, frontend_url
            )

        # Construct magic link URL
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        magic_link_url = (
            f"{frontend_url}/contractor-onboarding?token={magic_link_token.token}"
        )

        return MagicLinkResponse(
            token=magic_link_token.token,
            magic_link_url=magic_link_url,
            email=magic_link_token.email,
            job_id=magic_link_token.job_id,
            expires_at=magic_link_token.expires_at,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify", response_model=MagicLinkVerifyResponse)
async def verify_magic_link(request: MagicLinkVerify):
    """
    Verify a magic link token and return associated job information.

    This endpoint is called when a contractor clicks the magic link.
    """
    try:
        # Verify token
        magic_link_token = await magic_link_service.verify_token(request.token)

        if not magic_link_token:
            return MagicLinkVerifyResponse(
                valid=False,
                email="",
                job_id="",
                landlord_id="",
                property_id="",
                tenant_id="",
                message="Invalid or expired token",
            )

        # Check if contractor already exists with this email
        contractor_id = None
        try:
            contractor = await contractor_service.get_contractor_by_email(
                magic_link_token.email
            )
            contractor_id = contractor.contractor_id if contractor else None
            print(f"[magic_links] Contractor lookup for {magic_link_token.email}: {contractor_id or 'Not found'}")
        except Exception as e:
            print(f"[magic_links] Error looking up contractor: {str(e)}")
            # Continue without contractor_id - they'll register as new

        return MagicLinkVerifyResponse(
            valid=True,
            email=magic_link_token.email,
            job_id=magic_link_token.job_id,
            landlord_id=magic_link_token.landlord_id,
            property_id=magic_link_token.property_id,
            tenant_id=magic_link_token.tenant_id,
            contractor_id=contractor_id,
            message=(
                "Welcome back! Redirecting to your dashboard..."
                if contractor_id
                else "Please complete your contractor registration"
            ),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mark-used/{token}")
async def mark_magic_link_used(token: str, contractor_id: str):
    """
    Mark a magic link token as used after contractor registration.

    Args:
        token: The magic link token
        contractor_id: ID of the contractor who used the token
    """
    try:
        success = await magic_link_service.mark_token_used(token, contractor_id)

        if not success:
            raise HTTPException(status_code=404, detail="Token not found")

        return {"message": "Token marked as used", "success": True}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/onboarding-dashboard/{contractor_id}")
async def get_onboarding_dashboard(contractor_id: str):
    """
    Get comprehensive contractor dashboard data for onboarding page.

    This includes:
    - Contractor profile
    - All jobs (available, active, completed)
    - Payment summary
    - Bids submitted

    Args:
        contractor_id: The contractor identifier

    Returns:
        Complete dashboard data
    """
    try:
        # Get contractor profile
        contractor = await contractor_service.get_contractor_by_id(contractor_id)

        if not contractor:
            raise HTTPException(status_code=404, detail="Contractor not found")

        # Get all jobs assigned to this contractor
        active_jobs = []
        completed_jobs = []
        try:
            response = jobs_table.scan(
                FilterExpression="awarded_contractor_id = :cid",
                ExpressionAttributeValues={":cid": contractor_id}
            )
            for job in response.get('Items', []):
                if job.get('status') in ['awarded', 'scheduled', 'in_progress']:
                    active_jobs.append(job)
                elif job.get('status') == 'completed':
                    completed_jobs.append(job)
        except ClientError as e:
            print(f"Error fetching contractor jobs: {str(e)}")

        # Get available jobs that contractor can bid on
        available_jobs = []
        try:
            response = jobs_table.scan(
                FilterExpression="#status IN (:posted, :bidding)",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":posted": "posted",
                    ":bidding": "bidding"
                }
            )
            available_jobs = response.get('Items', [])
        except ClientError as e:
            print(f"Error fetching available jobs: {str(e)}")

        # Get contractor's bids
        contractor_bids = []
        try:
            response = bids_table.scan(
                FilterExpression="contractor_id = :cid",
                ExpressionAttributeValues={":cid": contractor_id}
            )
            contractor_bids = response.get('Items', [])
        except ClientError as e:
            print(f"Error fetching bids: {str(e)}")

        # Get payment summary
        total_earnings = 0.0
        pending_payments = 0.0
        completed_payments = 0.0
        try:
            response = payments_table.scan(
                FilterExpression="contractor_id = :cid",
                ExpressionAttributeValues={":cid": contractor_id}
            )
            for payment in response.get('Items', []):
                amount = float(payment.get('contractor_payout', 0))
                if payment.get('status') == 'completed':
                    completed_payments += amount
                    total_earnings += amount
                elif payment.get('status') in ['pending', 'authorized', 'processing']:
                    pending_payments += amount
        except ClientError as e:
            print(f"Error fetching payments: {str(e)}")

        return {
            "contractor": contractor.model_dump() if contractor else None,
            "jobs": {
                "available": available_jobs,
                "active": active_jobs,
                "completed": completed_jobs,
                "total_available": len(available_jobs),
                "total_active": len(active_jobs),
                "total_completed": len(completed_jobs)
            },
            "bids": {
                "submitted": contractor_bids,
                "total": len(contractor_bids)
            },
            "payments": {
                "total_earnings": total_earnings,
                "pending": pending_payments,
                "completed": completed_payments
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
