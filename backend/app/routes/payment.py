"""
Payment routes for hotel check-in/check-out with Elavon and Stripe.

Provides endpoints for:
- Elavon authentication (token retrieval)
- Pre-authorization (check-in)
- Payment completion (checkout)
- Stripe checkout sessions
- Elavon mobile checkout
- Email and SMS sending
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Response
from datetime import datetime

from ..models.hotel_payment import (
    ElavonTokenRequest,
    ElavonPreAuthRequest,
    ElavonCompletionRequest,
    StripeCheckoutRequest,
    ElavonCheckoutRequest,
    SendEmailRequest,
    SendSMSRequest,
)
from ..services.elavon_service import get_elavon_service
from ..services.stripe_service import StripeService
from ..services.email_service import get_email_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/elavon/token")
async def get_elavon_token(request: ElavonTokenRequest):
    """
    Get authentication token from Elavon.

    Returns:
        Token and expiration timestamp
    """
    try:
        elavon_service = get_elavon_service()

        result = await elavon_service.get_token(
            merchant_id=request.merchant_id,
            user_id=request.user_id,
            pin=request.pin,
            api_endpoint=request.api_endpoint,
        )

        return result

    except Exception as e:
        logger.error(f"Error getting Elavon token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/elavon/preauth")
async def elavon_pre_authorize(request: ElavonPreAuthRequest):
    """
    Pre-authorize a payment via Elavon terminal.

    This is used during check-in to hold funds on guest's card.

    Returns:
        Transaction ID and status
    """
    try:
        if not request.token:
            raise HTTPException(status_code=400, detail="Token is required")

        elavon_service = get_elavon_service()

        result = await elavon_service.pre_authorize(
            token=request.token,
            amount=request.amount,
            terminal_id=request.terminal_id,
            merchant_id=request.merchant_id,
            api_endpoint="https://uat.pos.hpi.elavonaws.com",  # TODO: Make configurable
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in pre-authorization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/elavon/completion")
async def elavon_complete_payment(request: ElavonCompletionRequest):
    """
    Complete/capture a pre-authorized payment via Elavon terminal.

    This is used during checkout to capture the held funds.

    Returns:
        Transaction ID and status
    """
    try:
        elavon_service = get_elavon_service()

        result = await elavon_service.complete_payment(
            token=request.token,
            original_transaction_id=request.original_transaction_id,
            amount=request.amount,
            terminal_id=request.terminal_id,
            merchant_id=request.merchant_id,
            api_endpoint="https://uat.pos.hpi.elavonaws.com",  # TODO: Make configurable
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in payment completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/elavon/checkout-session")
async def elavon_create_checkout_session(request: ElavonCheckoutRequest):
    """
    Create a mobile checkout session via Elavon Converge.

    Returns:
        Checkout URL for guest to complete payment on their device
    """
    try:
        elavon_service = get_elavon_service()

        result = await elavon_service.create_checkout_session(
            merchant_id=request.merchant_id,
            user_id=request.user_id,
            pin=request.pin,
            amount=request.amount,
            transaction_type=request.transaction_type,
            first_name=request.first_name or "",
            last_name=request.last_name or "",
            email=request.email or "",
            invoice_number=request.invoice_number or "",
            is_test_mode=request.is_test_mode,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to create checkout session")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Elavon checkout session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stripe/checkout-session")
async def stripe_create_checkout_session(request: StripeCheckoutRequest):
    """
    Create a Stripe checkout session for hotel payment.

    Returns:
        Checkout URL for guest to complete payment via Stripe
    """
    try:
        stripe_service = StripeService()

        result = stripe_service.create_hotel_checkout_session(
            amount=request.amount,
            guest_name=request.guest_name,
            guest_email=request.guest_email,
            guest_phone=request.guest_phone,
            reservation_id=request.reservation_id,
            hotel_name=request.hotel_name or "Hotel",
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to create checkout session")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Stripe checkout session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-checkout-email")
async def send_checkout_email(request: SendEmailRequest):
    """
    Send checkout email (payment link or receipt).

    Returns:
        Success status and email ID
    """
    try:
        email_service = get_email_service()

        result = await email_service.send_checkout_email(
            guest_email=request.guest_email,
            guest_name=request.guest_name,
            amount=request.amount,
            email_type=request.type,
            hotel_name=request.hotel_name or "Hotel",
            checkout_url=request.checkout_url,
            room_number=request.room_number,
            nights=request.nights,
            check_in_date=request.check_in_date,
            check_out_date=request.check_out_date,
            room_charges=request.room_charges,
            additional_charges=request.additional_charges,
            transaction_id=request.transaction_id,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to send email")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-checkout-sms")
async def send_checkout_sms(request: SendSMSRequest):
    """
    Send checkout SMS with payment link.

    Note: This is currently a placeholder. Implement with Twilio or similar.

    Returns:
        Success status and message ID
    """
    try:
        email_service = get_email_service()

        result = await email_service.send_sms(
            phone_number=request.phone_number,
            guest_name=request.guest_name,
            amount=request.amount,
            checkout_url=request.checkout_url,
            hotel_name=request.hotel_name or "Hotel",
        )

        return result

    except Exception as e:
        logger.error(f"Error sending SMS: {e}")
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
        "service": "Payment Integration - Elavon & Stripe",
    }
