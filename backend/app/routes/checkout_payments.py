"""
Stripe Checkout payment routes for LandTen platform.

Provides endpoints for three payment flows:
1. Landlord → Contractor payments (job completion)
2. Tenant → Landlord payments (rent/fees)
3. Landlord → Platform payments (platform fees)
"""

import logging
from fastapi import APIRouter, HTTPException
from datetime import datetime

from ..models.checkout_payment import (
    JobPaymentRequest,
    RentPaymentRequest,
    PlatformFeeRequest,
    CheckoutSessionResponse,
)
from ..services.stripe_service import StripeService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/job-payment", response_model=CheckoutSessionResponse)
async def create_job_payment_session(request: JobPaymentRequest):
    """
    Create a Stripe checkout session for landlord paying contractor.

    Use this when a landlord wants to pay a contractor for a completed job.

    Returns:
        Checkout URL for the landlord to complete payment
    """
    try:
        stripe_service = StripeService()

        result = stripe_service.create_job_payment_session(
            job_id=request.job_id,
            bid_id=request.bid_id,
            contractor_name=request.contractor_name,
            contractor_email=request.contractor_email,
            landlord_email=request.landlord_email,
            amount=request.amount,
            description=request.description or "",
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to create checkout session")
            )

        logger.info(f"Job payment session created: job_id={request.job_id}, amount=${request.amount}")

        return CheckoutSessionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job payment session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rent-payment", response_model=CheckoutSessionResponse)
async def create_rent_payment_session(request: RentPaymentRequest):
    """
    Create a Stripe checkout session for tenant paying rent.

    Use this when a tenant wants to pay their monthly rent.

    Returns:
        Checkout URL for the tenant to complete payment
    """
    try:
        stripe_service = StripeService()

        result = stripe_service.create_rent_payment_session(
            property_id=request.property_id,
            tenant_name=request.tenant_name,
            tenant_email=request.tenant_email,
            landlord_email=request.landlord_email,
            amount=request.amount,
            period=request.period or "",
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to create checkout session")
            )

        logger.info(f"Rent payment session created: property_id={request.property_id}, amount=${request.amount}")

        return CheckoutSessionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating rent payment session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform-fee", response_model=CheckoutSessionResponse)
async def create_platform_fee_session(request: PlatformFeeRequest):
    """
    Create a Stripe checkout session for landlord paying platform fees.

    Use this for subscription fees or one-time platform charges.

    Returns:
        Checkout URL for the landlord to complete payment
    """
    try:
        stripe_service = StripeService()

        result = stripe_service.create_platform_fee_session(
            landlord_id=request.landlord_id,
            landlord_email=request.landlord_email,
            landlord_name=request.landlord_name,
            amount=request.amount,
            description=request.description,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to create checkout session")
            )

        logger.info(f"Platform fee session created: landlord_id={request.landlord_id}, amount=${request.amount}")

        return CheckoutSessionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating platform fee session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def payment_health_check():
    """
    Health check for payment services.

    Returns:
        Status of payment integration
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "LandTen Stripe Checkout Integration",
        "payment_flows": [
            "job_payment",
            "rent_payment",
            "platform_fee"
        ]
    }
