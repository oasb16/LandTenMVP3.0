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
    """
    Verify Stream Chat webhook signature using HMAC SHA256

    Returns:
        True if signature is valid or verification is disabled
        False if signature is invalid
    """
    webhook_secret = os.getenv("STREAM_WEBHOOK_SECRET", os.getenv("STREAM_CHAT_API_SECRET", ""))

    if not webhook_secret:
        # In development, skip verification if no secret is set
        if os.getenv("AUTH_DISABLED") == "true":
            print("[ai-webhook] WARNING: Webhook signature verification DISABLED (AUTH_DISABLED=true)")
            return True
        print("[ai-webhook] ERROR: STREAM_WEBHOOK_SECRET not configured, rejecting webhook")
        return False

    # Calculate expected signature
    try:
        expected_signature = hmac.new(
            webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        is_valid = hmac.compare_digest(signature, expected_signature)

        if is_valid:
            print("[ai-webhook] Webhook signature verified successfully")
        else:
            print(f"[ai-webhook] ERROR: Invalid webhook signature - expected: {expected_signature[:8]}..., got: {signature[:8]}...")

        return is_valid

    except Exception as e:
        print(f"[ai-webhook] ERROR: Exception during signature verification: {e}")
        return False


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
    - health.check: Stream Chat health check
    """
    print("[ai-webhook] ========== Incoming webhook request ==========")

    # Get raw body for signature verification
    try:
        body = await request.body()
        print(f"[ai-webhook] Received {len(body)} bytes of payload")
    except Exception as e:
        print(f"[ai-webhook] ERROR: Failed to read request body: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read request body: {e}")

    # Verify webhook signature
    if x_signature:
        print(f"[ai-webhook] Verifying webhook signature (x-signature header present)")
        if not verify_webhook_signature(body, x_signature):
            print("[ai-webhook] ERROR: Webhook signature verification FAILED")
            raise HTTPException(
                status_code=401,
                detail={"error": "Invalid webhook signature", "hint": "Check STREAM_WEBHOOK_SECRET configuration"}
            )
    else:
        print("[ai-webhook] WARNING: No x-signature header present - skipping verification")

    # Parse JSON payload
    try:
        payload = await request.json()
        event_type = payload.get("type")
        print(f"[ai-webhook] Event type: {event_type}")
    except Exception as e:
        print(f"[ai-webhook] ERROR: Failed to parse JSON payload: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    # Handle different event types
    if event_type == "message.new":
        print("[ai-webhook] Routing to handle_new_message()")
        return await handle_new_message(payload)

    elif event_type == "message.updated":
        print("[ai-webhook] Event type message.updated - acknowledging without processing")
        # User edited a message - could re-process with AI
        return {"status": "acknowledged", "processed": False, "event_type": event_type}

    elif event_type == "reaction.new":
        print("[ai-webhook] Routing to handle_reaction()")
        # User reacted to a message - could use for feedback
        return await handle_reaction(payload)

    elif event_type == "health.check":
        print("[ai-webhook] Health check received - responding healthy")
        # Health check from Stream
        return {"status": "healthy", "service": "ai-webhook", "version": "1.0"}

    else:
        print(f"[ai-webhook] WARNING: Unknown event type '{event_type}' - acknowledging without processing")
        # Unknown event type
        return {"status": "acknowledged", "processed": False, "event_type": event_type}


async def handle_new_message(payload: Dict[str, Any]) -> Dict[str, str]:
    """Handle new message event with comprehensive logging"""
    try:
        message = payload.get("message", {})
        user = payload.get("user", {})
        channel_id = payload.get("channel_id", "unknown")
        message_text = message.get("text", "")

        print(f"[ai-webhook] Processing message.new event:")
        print(f"[ai-webhook]   - Channel: {channel_id}")
        print(f"[ai-webhook]   - User: {user.get('id', 'unknown')} ({user.get('name', 'unknown')})")
        print(f"[ai-webhook]   - Message: {message_text[:100]}{'...' if len(message_text) > 100 else ''}")
        print(f"[ai-webhook]   - Is bot: {user.get('is_bot', False)}")

        bot = get_bot()
        result = bot.handle_message_event(payload)

        if result:
            print(f"[ai-webhook] SUCCESS: AI bot responded to message in channel {channel_id}")
            return {
                "status": "processed",
                "message_sent": True,
                "channel_id": channel_id,
                "user_id": user.get('id')
            }
        else:
            print(f"[ai-webhook] INFO: Message ignored (likely from bot or no action needed)")
            return {
                "status": "ignored",
                "message_sent": False,
                "reason": "Bot message or no action required"
            }

    except Exception as e:
        print(f"[ai-webhook] ERROR: Exception while handling message: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "hint": "Check backend logs for stack trace"
        }


async def handle_reaction(payload: Dict[str, Any]) -> Dict[str, str]:
    """Handle reaction event - can be used for AI feedback"""
    try:
        reaction = payload.get("reaction", {})
        message = payload.get("message", {})
        user = payload.get("user", {})

        reaction_type = reaction.get("type")  # e.g., "like", "love", "thumbs_up"
        message_id = message.get("id")
        user_id = user.get("id")

        print(f"[ai-webhook] Processing reaction.new event:")
        print(f"[ai-webhook]   - User: {user_id}")
        print(f"[ai-webhook]   - Reaction: {reaction_type}")
        print(f"[ai-webhook]   - Message ID: {message_id}")

        # Could use this to track AI response quality
        # For now, just acknowledge
        print(f"[ai-webhook] SUCCESS: Reaction acknowledged (future: track AI quality)")

        return {
            "status": "acknowledged",
            "reaction_type": reaction_type,
            "user_id": user_id
        }

    except Exception as e:
        print(f"[ai-webhook] ERROR: Exception while handling reaction: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "hint": "Check backend logs for stack trace"
        }


@router.post("/ai/init-channel")
async def initialize_ai_channel(request: Request):
    """
    Initialize or repair an AI channel and ensure the persona bot is a member.

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

        print(f"[ai-webhook] Initializing AI channel:")
        print(f"[ai-webhook]   - Channel ID: {channel_id}")
        print(f"[ai-webhook]   - Persona: {persona}")

        # --- Validation ---
        if not channel_id:
            raise HTTPException(
                status_code=400,
                detail={"error": "channel_id is required", "hint": "Provide channel_id in request body"}
            )

        if persona not in ["tenant", "landlord", "contractor"]:
            raise HTTPException(
                status_code=400,
                detail={"error": f"Invalid persona: {persona}",
                        "hint": "Must be one of: tenant, landlord, contractor"}
            )

        # --- Get bot + client ---
        bot = get_bot()
        client = bot.client
        bot_id = bot.get_bot_id(persona)

        print(f"[ai-webhook] Ensuring channel '{channel_id}' exists...")

        # --- Ensure channel exists or create it ---
        try:
            channel = client.channel("messaging", channel_id)
            channel.query()  # check existence
            print(f"[ai-webhook] Channel '{channel_id}' already exists.")
        except Exception:
            print(f"[ai-webhook] Channel '{channel_id}' not found, creating...")
            channel = client.channel("messaging", channel_id, {
                "name": f"{persona.capitalize()} Channel",
                "persona": persona,
                "description": f"AI-managed {persona} channel",
            })
            # Create the channel using the bot as creator
            channel.create(user_id=bot_id)
            print(f"[ai-webhook] Channel '{channel_id}' created by {bot_id}")

        # --- Safely update channel metadata ---
        try:
            channel.update({
                "persona": persona,
                "description": f"AI-managed {persona} chat channel",
                "last_initialized_at": __import__("datetime").datetime.utcnow().isoformat(),
            })
            print(f"[ai-webhook] Updated metadata for '{channel_id}'")
        except TypeError:
            # Older SDK fallback
            channel.update({"data": {
                "persona": persona,
                "description": f"AI-managed {persona} chat channel",
                "last_initialized_at": __import__("datetime").datetime.utcnow().isoformat(),
            }})
            print(f"[ai-webhook] Fallback metadata update for '{channel_id}'")
        except Exception as e:
            print(f"[ai-webhook] Warning: could not update channel metadata ({e})")

        # --- Ensure bot membership ---
        try:
            state = channel.query(state=True)
            members = [m.get("user_id") for m in state.get("members", [])]
            if bot_id in members:
                print(f"[ai-webhook] Bot '{bot_id}' already a member of '{channel_id}'")
            else:
                channel.add_members(
                    [bot_id],
                    message={
                        "text": f"🤖 {bot_id} joined as PropertyAI assistant",
                        "user": {"id": bot_id},  # ✅ required for server-side auth
                    },
                )
                print(f"[ai-webhook] Added bot '{bot_id}' to channel '{channel_id}'")
        except Exception as e:
            print(f"[ai-webhook] Warning: could not add bot ({e})")

        channel.send_message({"text": f"{bot_id} joined the channel"}, user_id=bot_id)

        # --- Return success ---
        return {
            "status": "success",
            "channel_id": channel_id,
            "bot_id": bot_id,
            "persona": persona,
            "message": f"AI bot ensured and ready for {persona} persona"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ai-webhook] ERROR: Exception during channel initialization: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "hint": "Check backend logs for stack trace"}
        )

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

        print(f"[ai-webhook] Sending action message:")
        print(f"[ai-webhook]   - Channel: {channel_id}")
        print(f"[ai-webhook]   - Persona: {persona}")
        print(f"[ai-webhook]   - Text: {text[:100]}{'...' if len(text) > 100 else ''}")
        print(f"[ai-webhook]   - Actions: {len(actions)} buttons")

        if not channel_id or not text:
            print("[ai-webhook] ERROR: Missing required fields (channel_id or text)")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "channel_id and text are required",
                    "hint": "Provide both channel_id and text in request body"
                }
            )

        bot = get_bot()
        bot_id = bot.get_bot_id(persona)

        result = bot.send_action_buttons(
            channel_id=channel_id,
            bot_id=bot_id,
            text=text,
            actions=actions
        )

        if result:
            print(f"[ai-webhook] SUCCESS: Action message sent to channel {channel_id}")
            return {
                "status": "success",
                "message": result,
                "channel_id": channel_id,
                "action_count": len(actions)
            }
        else:
            print(f"[ai-webhook] ERROR: Failed to send action message")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Failed to send action message",
                    "hint": "Check if channel exists and bot is a member"
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ai-webhook] ERROR: Exception during send action: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "hint": "Check backend logs for stack trace"
            }
        )


@router.get("/ai/bot-status")
async def get_bot_status():
    """Get AI bot status and configuration"""
    try:
        print("[ai-webhook] Checking bot status...")

        bot = get_bot()

        webhook_configured = bool(os.getenv("STREAM_WEBHOOK_SECRET"))
        stream_api_key = bool(os.getenv("STREAM_CHAT_API_KEY"))
        stream_api_secret = bool(os.getenv("STREAM_CHAT_API_SECRET"))

        print("[ai-webhook] Bot status check completed successfully")

        return {
            "status": "active",
            "service": "PropertyAI Bot System",
            "version": "1.0",
            "bots": {
                persona: {
                    "id": config["id"],
                    "name": config["name"],
                    "description": config["description"]
                }
                for persona, config in bot.bots.items()
            },
            "configuration": {
                "webhook_secret_configured": webhook_configured,
                "stream_api_key_configured": stream_api_key,
                "stream_api_secret_configured": stream_api_secret
            },
            "personas_available": ["tenant", "landlord", "contractor"]
        }

    except Exception as e:
        print(f"[ai-webhook] ERROR: Exception during status check: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "hint": "Check backend logs for stack trace"
        }
