"""
AI Webhooks Route
Handles Stream Chat webhooks for AI bot interactions
"""

import os
import hashlib
import hmac
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, Header
from app.services.stream_bot import get_bot

router = APIRouter()


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify Stream Chat webhook signature"""
    webhook_secret = os.getenv("STREAM_WEBHOOK_SECRET", os.getenv("STREAM_CHAT_API_SECRET", ""))

    if not webhook_secret:
        # In development, skip verification if no secret is set
        if os.getenv("AUTH_DISABLED") == "true":
            return True
        return False

    # Calculate expected signature
    expected_signature = hmac.new(
        webhook_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


@router.post("/ai/stream-webhook")
async def handle_stream_webhook(
    request: Request,
    x_signature: str = Header(None, alias="x-signature")
):
    """
    Handle Stream Chat webhooks for AI bot interactions

    Events handled:
    - message.new: New message from user
    - reaction.new: New reaction to message
    - message.updated: Message edited by user
    """

    # Get raw body for signature verification
    body = await request.body()

    # Verify webhook signature
    if x_signature and not verify_webhook_signature(body, x_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse JSON payload
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    event_type = payload.get("type")

    # Handle different event types
    if event_type == "message.new":
        return await handle_new_message(payload)

    elif event_type == "message.updated":
        # User edited a message - could re-process with AI
        return {"status": "acknowledged", "processed": False}

    elif event_type == "reaction.new":
        # User reacted to a message - could use for feedback
        return await handle_reaction(payload)

    elif event_type == "health.check":
        # Health check from Stream
        return {"status": "healthy"}

    else:
        # Unknown event type
        return {"status": "acknowledged", "processed": False}


async def handle_new_message(payload: Dict[str, Any]) -> Dict[str, str]:
    """Handle new message event"""
    try:
        bot = get_bot()
        result = bot.handle_message_event(payload)

        if result:
            return {"status": "processed", "message_sent": True}
        else:
            return {"status": "ignored", "message_sent": False}

    except Exception as e:
        print(f"[ai-webhook] Error handling message: {e}")
        return {"status": "error", "error": str(e)}


async def handle_reaction(payload: Dict[str, Any]) -> Dict[str, str]:
    """Handle reaction event - can be used for AI feedback"""
    try:
        reaction = payload.get("reaction", {})
        message = payload.get("message", {})
        user = payload.get("user", {})

        reaction_type = reaction.get("type")  # e.g., "like", "love", "thumbs_up"
        message_id = message.get("id")
        user_id = user.get("id")

        # Could use this to track AI response quality
        # For now, just acknowledge
        print(f"[ai-webhook] User {user_id} reacted with {reaction_type} to message {message_id}")

        return {"status": "acknowledged"}

    except Exception as e:
        print(f"[ai-webhook] Error handling reaction: {e}")
        return {"status": "error", "error": str(e)}


@router.post("/ai/init-channel")
async def initialize_ai_channel(request: Request):
    """
    Initialize a new channel with AI bot

    Request body:
    {
        "channel_id": "tenant-123",
        "persona": "tenant"
    }
    """
    try:
        data = await request.json()
        channel_id = data.get("channel_id")
        persona = data.get("persona", "tenant")

        if not channel_id:
            raise HTTPException(status_code=400, detail="channel_id is required")

        if persona not in ["tenant", "landlord", "contractor"]:
            raise HTTPException(status_code=400, detail="Invalid persona")

        bot = get_bot()
        success = bot.add_bot_to_channel(channel_id, persona)

        if success:
            return {
                "status": "success",
                "channel_id": channel_id,
                "bot_id": bot.get_bot_id(persona),
                "persona": persona
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to initialize AI channel")

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ai-webhook] Error initializing channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/send-action")
async def send_ai_action(request: Request):
    """
    Send an AI message with action buttons

    Request body:
    {
        "channel_id": "tenant-123",
        "persona": "tenant",
        "text": "Would you like to create an incident?",
        "actions": [
            {"name": "create_incident", "text": "Yes, create incident", "value": "confirm"},
            {"name": "cancel", "text": "No, cancel", "value": "cancel"}
        ]
    }
    """
    try:
        data = await request.json()
        channel_id = data.get("channel_id")
        persona = data.get("persona", "tenant")
        text = data.get("text", "")
        actions = data.get("actions", [])

        if not channel_id or not text:
            raise HTTPException(status_code=400, detail="channel_id and text are required")

        bot = get_bot()
        bot_id = bot.get_bot_id(persona)

        result = bot.send_action_buttons(
            channel_id=channel_id,
            bot_id=bot_id,
            text=text,
            actions=actions
        )

        if result:
            return {"status": "success", "message": result}
        else:
            raise HTTPException(status_code=500, detail="Failed to send action message")

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ai-webhook] Error sending action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai/bot-status")
async def get_bot_status():
    """Get AI bot status and configuration"""
    try:
        bot = get_bot()

        return {
            "status": "active",
            "bots": {
                persona: {
                    "id": config["id"],
                    "name": config["name"],
                    "description": config["description"]
                }
                for persona, config in bot.bots.items()
            },
            "webhook_configured": bool(os.getenv("STREAM_WEBHOOK_SECRET"))
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
