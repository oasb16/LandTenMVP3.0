"""
AI Webhooks Route - Intelligent Intent Routing System
Handles Stream Chat webhooks with context-aware, policy-bounded AI interactions
"""

import os
import hashlib
import hmac
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Header
from app.services.stream_bot import get_bot
from app.services.context_manager import get_context_manager
from app.services.ai_reasoning import get_ai_reasoning
from app.services.policy_validator import get_policy_validator

logger = logging.getLogger(__name__)
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
    """
    Intelligent message handler with context-aware intent routing.

    This replaces the rigid button-driven flow with adaptive AI reasoning:
    1. Retrieve or create conversational context
    2. Detect user intent using AI reasoning
    3. Validate actions against persona policies
    4. Route to appropriate handler dynamically
    5. Update context with new information
    """
    try:
        # Extract message data
        message = payload.get("message", {})
        user = payload.get("user", {})
        channel_id = payload.get("channel_id", "unknown")
        message_text = message.get("text", "")
        user_id = user.get("id", "unknown")
        is_bot = user.get("role") == "admin" or user.get("name", "").startswith("ai-")

        logger.info(f"[ai-webhook] ========== Incoming Message ==========")
        logger.info(f"[ai-webhook] Channel: {channel_id}")
        logger.info(f"[ai-webhook] User: {user_id} ({user.get('name', 'unknown')})")
        logger.info(f"[ai-webhook] Message: {message_text[:100]}")
        logger.info(f"[ai-webhook] Is bot: {is_bot}")

        # Ignore messages from bots
        if is_bot:
            logger.info("[ai-webhook] Ignoring bot message")
            return {"status": "ignored", "reason": "bot_message"}

        # Check if message has metadata indicating agent is disabled
        metadata = message.get("metadata", {})
        agent_enabled = metadata.get("agentEnabled", True)

        if not agent_enabled:
            logger.info("[ai-webhook] Agent disabled by user - ignoring message")
            return {"status": "ignored", "reason": "agent_disabled"}

        # Get services
        context_manager = get_context_manager()
        ai_reasoning = get_ai_reasoning()
        policy_validator = get_policy_validator()
        bot = get_bot()

        # Get or create context
        context = context_manager.get_context(user_id, channel_id, create_if_missing=True)

        if not context:
            logger.error("[ai-webhook] Failed to get/create context")
            return {"status": "error", "error": "context_creation_failed"}

        logger.info(f"[ai-webhook] Context retrieved: flow_type={context.get('flow_type')}, "
                   f"last_intent={context.get('last_intent')}")

        # Detect persona from channel or context
        persona = await _detect_persona(channel_id, context, bot)
        logger.info(f"[ai-webhook] Detected persona: {persona}")

        # Update context with persona if not set
        if not context.get("persona"):
            context_manager.set_persona(user_id, channel_id, persona)
            context["persona"] = persona

        # Append user message to conversation history
        context_manager.append_message(user_id, channel_id, "user", message_text)

        # Infer intent using AI reasoning
        logger.info("[ai-webhook] Inferring intent with AI reasoning...")
        intent_result = ai_reasoning.infer_intent(message_text, context, persona)

        intent = intent_result["intent"]
        confidence = intent_result["confidence"]
        entities = intent_result["entities"]
        card_type = intent_result["card_type"]

        logger.info(f"[ai-webhook] Intent detected: {intent} (confidence: {confidence:.2f})")
        logger.info(f"[ai-webhook] Entities: {entities}")
        logger.info(f"[ai-webhook] Card type: {card_type}")

        # Validate intent against persona policy
        is_valid, violation_message = policy_validator.validate_intent(intent, persona)

        if not is_valid:
            logger.warning(f"[ai-webhook] Intent '{intent}' blocked by policy for {persona}")
            # Send polite decline message
            bot.send_message(
                channel_id=channel_id,
                bot_id=bot.get_bot_id(persona),
                text=violation_message,
                metadata={"context_type": "policy_violation", "intent": intent}
            )
            return {"status": "blocked", "reason": "policy_violation", "intent": intent}

        # Update context with intent
        context_manager.update_context(
            user_id,
            channel_id,
            {
                "last_intent": intent,
                "entities": entities,
                "last_message": message_text
            }
        )

        # Route to appropriate handler based on intent
        logger.info(f"[ai-webhook] Routing to handler for intent: {intent}")
        result = await route_intent(
            intent=intent,
            entities=entities,
            context=context,
            persona=persona,
            channel_id=channel_id,
            user_id=user_id,
            message_text=message_text,
            payload=payload
        )

        if result:
            logger.info(f"[ai-webhook] ✅ SUCCESS: Intent '{intent}' handled successfully")
            # Append bot response to history
            if result.get("response_text"):
                context_manager.append_message(
                    user_id,
                    channel_id,
                    "assistant",
                    result["response_text"]
                )
            return {
                "status": "processed",
                "intent": intent,
                "confidence": confidence,
                "channel_id": channel_id,
                "result": result
            }
        else:
            logger.warning(f"[ai-webhook] Handler returned no result for intent: {intent}")
            return {
                "status": "no_action",
                "intent": intent,
                "reason": "handler_returned_none"
            }

    except Exception as e:
        logger.error(f"[ai-webhook] ❌ ERROR: Exception while handling message: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "hint": "Check backend logs for stack trace"
        }


async def _detect_persona(
    channel_id: str,
    context: Dict[str, Any],
    bot
) -> str:
    """
    Detect persona from channel metadata or context.

    Priority:
    1. Context persona (if already set)
    2. Channel metadata
    3. Default to 'tenant'
    """
    # Check context first
    if context.get("persona"):
        return context["persona"]

    # Check channel metadata
    try:
        persona = bot.get_channel_persona(channel_id)
        if persona:
            return persona
    except Exception as e:
        logger.warning(f"[ai-webhook] Error detecting persona from channel: {e}")

    # Default to tenant
    return "tenant"


async def route_intent(
    intent: str,
    entities: Dict[str, Any],
    context: Dict[str, Any],
    persona: str,
    channel_id: str,
    user_id: str,
    message_text: str,
    payload: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Dynamic intent router - replaces rigid if/else chains.

    Routes to appropriate handler based on intent classification.
    """
    bot = get_bot()

    # Map intents to handlers
    if intent == "incident.report":
        return await handle_incident_report(
            bot, channel_id, user_id, persona, message_text, entities, context
        )

    elif intent in ["incident.followup", "discovery.response"]:
        return await handle_discovery_followup(
            bot, channel_id, user_id, persona, message_text, entities, context
        )

    elif intent == "job.request":
        return await handle_job_request(
            bot, channel_id, user_id, persona, message_text, entities, context
        )

    elif intent == "job.inquiry" or intent == "job.status":
        return await handle_job_inquiry(
            bot, channel_id, user_id, persona, message_text, entities, context
        )

    elif intent == "bids.request":
        return await handle_bids_request(
            bot, channel_id, user_id, persona, entities, context
        )

    elif intent == "approval.request":
        return await handle_approval_request(
            bot, channel_id, user_id, persona, entities, context
        )

    elif intent == "approval.decision":
        return await handle_approval_decision(
            bot, channel_id, user_id, persona, message_text, entities, context
        )

    elif intent == "greeting":
        return await handle_greeting(
            bot, channel_id, user_id, persona, message_text
        )

    elif intent == "help":
        return await handle_help_request(
            bot, channel_id, user_id, persona, context
        )

    elif intent == "general.chat":
        return await handle_general_assistance(
            bot, channel_id, user_id, persona, message_text, context
        )

    else:
        # Fallback: use the original bot handler
        logger.warning(f"[ai-webhook] No specific handler for intent '{intent}', using fallback")
        result = bot.handle_message_event(payload)
        return {"response_text": "I understand you need help. Let me assist you.", "fallback": True}


# ============================================================================
# Intent Handlers - Dynamic, context-aware response generation
# ============================================================================

async def handle_incident_report(
    bot, channel_id: str, user_id: str, persona: str,
    message_text: str, entities: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle new incident report with intelligence."""
    logger.info("[ai-webhook] 🔧 Handling incident report...")

    # Use the bot's existing incident detection logic
    result = bot.detect_incident_in_message(message_text)

    if result:
        # Create incident and send card
        incident_result = bot.send_incident_card(
            channel_id=channel_id,
            user_id=user_id,
            text=message_text
        )

        if incident_result:
            # Update context with incident ID
            incident_id = incident_result.get("incident_id")
            context_manager = get_context_manager()
            context_manager.set_active_incident(user_id, channel_id, incident_id)

            return {
                "response_text": "I've detected an issue and created an incident.",
                "incident_id": incident_id,
                "action": "incident_created"
            }

    return {"response_text": "Let me help you with that issue.", "action": "general_help"}


async def handle_discovery_followup(
    bot, channel_id: str, user_id: str, persona: str,
    message_text: str, entities: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle discovery follow-up responses."""
    logger.info("[ai-webhook] 📋 Handling discovery follow-up...")

    # Get active incident
    incident_id = context.get("active_incident_id")

    if not incident_id:
        return {"response_text": "I don't have an active incident to follow up on. What's the issue?"}

    # For now, use bot's existing discovery logic
    # TODO: Replace with discovery_manager when implemented
    bot_id = bot.get_bot_id(persona)
    bot.send_message(
        channel_id=channel_id,
        bot_id=bot_id,
        text=f"Thanks for that information! Let me continue gathering details about incident {incident_id}.",
        metadata={"context_type": "discovery", "incident_id": incident_id}
    )

    return {
        "response_text": "Discovery question sent",
        "action": "discovery_continue",
        "incident_id": incident_id
    }


async def handle_job_request(
    bot, channel_id: str, user_id: str, persona: str,
    message_text: str, entities: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle job creation request."""
    logger.info("[ai-webhook] 🔨 Handling job request...")

    bot_id = bot.get_bot_id(persona)
    bot.send_message(
        channel_id=channel_id,
        bot_id=bot_id,
        text="I can help you create a work order. Let me gather the necessary information.",
        metadata={"context_type": "job_request"}
    )

    return {"response_text": "Job request acknowledged", "action": "job_request"}


async def handle_job_inquiry(
    bot, channel_id: str, user_id: str, persona: str,
    message_text: str, entities: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle job inquiry or status check."""
    logger.info("[ai-webhook] ℹ️  Handling job inquiry...")

    active_job_id = context.get("active_job_id")

    bot_id = bot.get_bot_id(persona)

    if active_job_id:
        text = f"Your active job is {active_job_id}. Let me get the latest status for you."
    else:
        text = "You don't have any active jobs at the moment. Would you like to create one?"

    bot.send_message(
        channel_id=channel_id,
        bot_id=bot_id,
        text=text,
        metadata={"context_type": "job_inquiry", "job_id": active_job_id}
    )

    return {"response_text": text, "action": "job_inquiry", "job_id": active_job_id}


async def handle_bids_request(
    bot, channel_id: str, user_id: str, persona: str,
    entities: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle contractor bids request."""
    logger.info("[ai-webhook] 👷 Handling bids request...")

    active_job_id = context.get("active_job_id")
    active_incident_id = context.get("active_incident_id")

    bot_id = bot.get_bot_id(persona)

    if not active_job_id and not active_incident_id:
        bot.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text="To view contractor bids, we need to create a job first. What issue needs fixing?",
            metadata={"context_type": "bids_request"}
        )
        return {"response_text": "No active job for bids", "action": "need_job_first"}

    # Use existing bid generation logic
    # This will be enhanced when we refactor stream_bot.py
    bot.send_message(
        channel_id=channel_id,
        bot_id=bot_id,
        text="Let me fetch contractor bids for you...",
        metadata={"context_type": "bids", "job_id": active_job_id}
    )

    return {"response_text": "Bids request processed", "action": "bids_requested"}


async def handle_approval_request(
    bot, channel_id: str, user_id: str, persona: str,
    entities: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle approval request."""
    logger.info("[ai-webhook] ✅ Handling approval request...")

    bot_id = bot.get_bot_id(persona)
    bot.send_message(
        channel_id=channel_id,
        bot_id=bot_id,
        text="I'll prepare the approval request for you.",
        metadata={"context_type": "approval"}
    )

    return {"response_text": "Approval request sent", "action": "approval_requested"}


async def handle_approval_decision(
    bot, channel_id: str, user_id: str, persona: str,
    message_text: str, entities: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle approval decision (approve/reject)."""
    logger.info("[ai-webhook] 🎯 Handling approval decision...")

    # Detect approval/rejection from message
    message_lower = message_text.lower()
    is_approval = any(word in message_lower for word in ["approve", "yes", "accept", "ok"])

    bot_id = bot.get_bot_id(persona)

    if is_approval:
        text = "Great! I've recorded your approval. Processing next steps..."
    else:
        text = "Understood. I've recorded your decision."

    bot.send_message(
        channel_id=channel_id,
        bot_id=bot_id,
        text=text,
        metadata={"context_type": "approval_decision", "approved": is_approval}
    )

    return {"response_text": text, "action": "approval_decision", "approved": is_approval}


async def handle_greeting(
    bot, channel_id: str, user_id: str, persona: str, message_text: str
) -> Dict[str, Any]:
    """Handle friendly greetings."""
    logger.info("[ai-webhook] 👋 Handling greeting...")

    bot_id = bot.get_bot_id(persona)

    greetings = {
        "tenant": "Hello! I'm your PropertyAI assistant. I'm here to help with any property issues or questions you have. What can I help you with today?",
        "landlord": "Hello! I'm your PropertyAI property management assistant. I can help you manage incidents, approve jobs, and oversee contractors. What would you like to do?",
        "contractor": "Hello! I'm your PropertyAI job assistant. I can help you view available jobs and manage your work. What do you need?"
    }

    text = greetings.get(persona, "Hello! How can I help you today?")

    bot.send_message(
        channel_id=channel_id,
        bot_id=bot_id,
        text=text,
        metadata={"context_type": "greeting"}
    )

    return {"response_text": text, "action": "greeting"}


async def handle_help_request(
    bot, channel_id: str, user_id: str, persona: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle help requests with persona-specific guidance."""
    logger.info("[ai-webhook] 🆘 Handling help request...")

    policy_validator = get_policy_validator()
    capabilities = policy_validator.get_persona_capabilities(persona)

    bot_id = bot.get_bot_id(persona)

    help_text = f"""I'm here to help! As a {persona}, here's what I can assist you with:

"""

    if persona == "tenant":
        help_text += """• Report property issues and maintenance needs
• Track incident status
• Get DIY suggestions for minor issues
• View job progress

Just describe any issue you're experiencing, and I'll guide you through the process!"""

    elif persona == "landlord":
        help_text += """• Review and approve work orders
• View contractor bids
• Manage property incidents
• Track costs and approvals
• Oversee maintenance workflows

You can ask me about pending approvals, view bids, or check on any active incidents!"""

    elif persona == "contractor":
        help_text += """• View assigned jobs
• Check job details and requirements
• Update job status
• Submit work completion

Ask me about your active jobs or upcoming work!"""

    bot.send_message(
        channel_id=channel_id,
        bot_id=bot_id,
        text=help_text,
        metadata={"context_type": "help", "persona": persona}
    )

    return {"response_text": help_text, "action": "help_provided"}


async def handle_general_assistance(
    bot, channel_id: str, user_id: str, persona: str,
    message_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle general conversation with creative, policy-bounded responses."""
    logger.info("[ai-webhook] 💬 Handling general assistance...")

    # Use the bot's AI service for general responses
    bot_id = bot.get_bot_id(persona)

    # Get AI response
    try:
        from app.services.ai_service import get_ai_response

        # Build conversation context
        conversation_history = context.get("conversation_history", [])

        ai_response = get_ai_response(
            message=message_text,
            persona=persona,
            context=f"Recent conversation: {conversation_history[-3:]}" if conversation_history else None
        )

        bot.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text=ai_response,
            metadata={"context_type": "general", "persona": persona}
        )

        return {"response_text": ai_response, "action": "general_chat"}

    except Exception as e:
        logger.error(f"[ai-webhook] Error getting AI response: {e}")
        fallback_text = "I'm here to help! Could you tell me more about what you need?"

        bot.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text=fallback_text,
            metadata={"context_type": "general"}
        )

        return {"response_text": fallback_text, "action": "fallback"}


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
