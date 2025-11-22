"""
AI Webhooks V2 - Fallback Route (Restored)
This file provides a working fallback webhook for Stream Chat.
V3 orchestrator is preferred but this ensures the app doesn't crash.
"""
import os
import hashlib
import hmac
import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, Header

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify Stream Chat webhook signature using HMAC SHA256"""
    webhook_secret = os.getenv("STREAM_WEBHOOK_SECRET", os.getenv("STREAM_CHAT_API_SECRET", ""))

    if not webhook_secret:
        if os.getenv("AUTH_DISABLED") == "true":
            logger.warning("Webhook signature verification DISABLED (AUTH_DISABLED=true)")
            return True
        logger.error("STREAM_WEBHOOK_SECRET not configured, rejecting webhook")
        return False

    try:
        expected_signature = hmac.new(
            webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Exception during signature verification: {e}")
        return False


@router.post("/ai/stream-webhook-v2")
async def handle_stream_webhook_v2(
    request: Request,
    x_signature: str = Header(None, alias="x-signature")
):
    """
    V2 Fallback webhook handler for Stream Chat events.
    Basic implementation to prevent crashes while V3 is being stabilized.
    """
    try:
        # Get raw body for signature verification
        body = await request.body()

        # Verify signature if provided
        if x_signature and not verify_webhook_signature(body, x_signature):
            raise HTTPException(
                status_code=401,
                detail={"error": "Invalid webhook signature"}
            )

        # Parse payload
        payload = await request.json()
        event_type = payload.get("type")

        logger.info(f"[V2 Webhook] Received event: {event_type}")

        # Handle events
        if event_type == "message.new":
            # Basic acknowledgment - V3 will handle if available
            return {"status": "acknowledged", "message": "V2 fallback received message"}

        elif event_type == "health.check":
            return {"status": "healthy", "service": "ai-webhook-v2"}

        elif event_type == "reaction.new":
            return {"status": "acknowledged", "message": "V2 fallback received reaction"}

        else:
            return {"status": "acknowledged", "event_type": event_type}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[V2 Webhook] Error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
