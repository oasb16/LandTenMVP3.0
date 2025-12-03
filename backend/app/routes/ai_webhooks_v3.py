"""
AI Webhooks V3 - LLM-Driven Orchestrator Architecture
Complete rewrite: No hardcoded logic, no classifiers, no flow engines.
All intelligence flows through the LLM orchestrator.
"""
import os
import hashlib
import hmac
import logging
import time
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, Header

from ..config.settings import settings
from ..services.stream_bot import get_bot
from ..services.meta_context_manager import get_meta_context_manager
from ..services.orchestrator import get_orchestrator
from ..services.ai_support_orchestrator import get_ai_support_orchestrator
from ..functions.function_registry import (
    get_function_definitions,
    execute_function,
)
from ..models.orchestrator_schemas import MetaContext, FunctionResult

router = APIRouter()
logger = logging.getLogger(__name__)


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
            hashlib.sha256,
        ).hexdigest()

        is_valid = hmac.compare_digest(signature, expected_signature)

        if not is_valid:
            logger.error(f"Invalid webhook signature - expected: {expected_signature[:8]}..., got: {signature[:8]}...")

        return is_valid

    except Exception as e:
        logger.error(f"Exception during signature verification: {e}", exc_info=True)
        return False


@router.post("/ai/stream-webhook")
async def handle_stream_webhook(
    request: Request,
    x_signature: str = Header(None, alias="x-signature"),
):
    """
    Universal webhook handler for Stream Chat events.

    Events handled:
    - message.new: New message from user
    - reaction.new: New reaction to message
    - message.updated: Message edited by user
    - health.check: Stream Chat health check
    """
    start_time = time.time()
    logger.info("========== Incoming webhook request ==========")

    # Get raw body for signature verification
    try:
        body = await request.body()
        logger.debug(f"Received {len(body)} bytes of payload")
    except Exception as e:
        logger.error(f"Failed to read request body: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read request body: {e}")

    # Verify webhook signature
    if x_signature:
        logger.debug("Verifying webhook signature")
        if not verify_webhook_signature(body, x_signature):
            logger.error("Webhook signature verification FAILED")
            raise HTTPException(
                status_code=401,
                detail={"error": "Invalid webhook signature", "hint": "Check STREAM_WEBHOOK_SECRET configuration"},
            )
        logger.debug("Signature verified successfully")
    else:
        logger.warning("No x-signature header present - skipping verification")

    # Parse JSON payload
    try:
        payload = await request.json()
        event_type = payload.get("type")
        logger.info(f"Event type: {event_type}")
    except Exception as e:
        logger.error(f"Failed to parse JSON payload: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    # Handle different event types
    if event_type == "message.new":
        logger.info("Routing to handle_new_message()")
        return await handle_new_message(payload)

    elif event_type == "message.updated":
        logger.info("Event type message.updated - acknowledging without processing")
        return {"status": "acknowledged", "processed": False, "event_type": event_type}

    elif event_type == "reaction.new":
        logger.info("Routing to handle_reaction()")
        return await handle_reaction(payload)

    elif event_type == "ai_intent":
        logger.info("Routing to handle_ai_intent() - Amazon-style flow")
        return await handle_ai_intent(payload)

    elif event_type == "health.check":
        logger.info("Health check received - responding healthy")
        return {"status": "healthy", "service": "ai-webhook-v3", "version": "3.0"}

    else:
        logger.warning(f"Unknown event type '{event_type}' - acknowledging without processing")
        return {"status": "acknowledged", "processed": False, "event_type": event_type}


async def _save_graph_background(graph, user_id: str):
    """
    Save incident graph in background without blocking webhook response.
    Reduces webhook latency by 1-2 seconds per save operation.
    """
    try:
        await asyncio.to_thread(graph.save)
        logger.debug(f"✅ Background graph save completed for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Background graph save failed for user {user_id}: {e}")


async def handle_new_message(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Universal message handler using LLM orchestrator.
    No hardcoded logic - all decisions made by LLM.
    """
    try:
        start_time = time.time()

        # Extract message details
        message = payload.get("message", {})
        metadata = message.get("metadata", {}) or {}
        user = payload.get("user", {})
        channel_id = payload.get("channel_id", "unknown")
        user_id = user.get("id", "unknown")
        message_text = message.get("text", "")

        logger.info(f"========== New Message ==========")
        logger.info(f"Channel: {channel_id}")
        logger.info(f"User: {user_id} ({user.get('name', 'unknown')})")
        logger.info(f"Text: {message_text[:120]}")

        # Ignore bot messages
        if user.get("is_bot") or str(user_id).startswith("ai-"):
            logger.debug(f"Ignoring bot message from: {user_id}")
            return {"status": "ignored", "reason": "bot_message"}

        # Check if agent is enabled
        agent_enabled = metadata.get("agentEnabled", True)
        if agent_enabled is False:
            logger.debug("Agent disabled via metadata for this message")
            return {"status": "ignored", "reason": "agent_disabled"}

        # Initialize services
        bot = get_bot()
        context_manager = get_meta_context_manager()
        orchestrator = get_orchestrator()

        # Load or create meta-context
        logger.debug(f"Loading context for user={user_id} channel={channel_id}")
        meta_context = await context_manager.load_context(user_id, channel_id, create_if_missing=True)

        # Detect persona if not set
        if not meta_context.persona or meta_context.persona == "tenant":
            persona = metadata.get("persona") or await _detect_persona(channel_id, bot)
            meta_context.persona = persona
            await context_manager.save_context(user_id, channel_id, meta_context)

        logger.info(f"Persona: {meta_context.persona}, Stage: {meta_context.stage}")

        # 🚀 PHASE OMEGA: Agent Router Integration
        agent_enhanced_context = None
        agent_blocks_orchestrator = False
        try:
            from ..agents.agent_router import get_agent_router

            agent_router = get_agent_router()
            agent_response = await agent_router.route(
                message=message_text,
                context={
                    "stage": meta_context.stage,
                    "active_incident_id": meta_context.active_incident_id,
                    "persona": meta_context.persona,
                    "metadata": meta_context.metadata,
                },
            )

            if agent_response and agent_response.get("agent_response"):
                agent_enhanced_context = agent_response.get("agent_response")
                logger.info(f"🤖 Routed to {agent_response.get('agent_type', 'unknown')} agent")

                # PHASE OMEGA OBJECTIVE #1: STOP SIGNAL ROUTING
                # If agent blocks orchestrator, return immediately without calling orchestrator
                if agent_response.get("block_orchestrator"):
                    logger.info(f"🛑 Agent blocked orchestrator - returning agent result directly")
                    agent_blocks_orchestrator = True

        except Exception as e:
            logger.error(f"Agent routing error: {e}", exc_info=True)

        # 🚀 PHASE OMEGA: Topic Graph Update
        try:
            from ..services.incident_topic_graph import get_incident_graph

            if meta_context.active_incident_id:
                incident_graph = get_incident_graph(user_id)

                # PHASE OMEGA OBJECTIVE #3: TOPIC GRAPH PERSISTENCE
                # Save in background to avoid blocking webhook response
                asyncio.create_task(_save_graph_background(incident_graph, user_id))

                shift_result = incident_graph.detect_topic_shift(
                    new_message=message_text,
                    current_incident_id=meta_context.active_incident_id,
                )

                if shift_result.get("is_shift"):
                    logger.info(f"🔀 Topic shift detected: {shift_result.get('reason')}")

                    target_incident = shift_result.get("target_incident_id")

                    if target_incident:
                        logger.info(f"↪️ Switching to existing incident: {target_incident}")
                        meta_context = await context_manager.update_context(
                            user_id,
                            channel_id,
                            {
                                "active_incident_id": target_incident,
                                "stage": shift_result.get("target_stage", "discovery"),
                            },
                        )

                        # PHASE OMEGA OBJECTIVE #3: TOPIC GRAPH PERSISTENCE
                        # Save in background to avoid blocking webhook response
                        asyncio.create_task(_save_graph_background(incident_graph, user_id))

        except Exception as e:
            logger.error(f"Topic graph update error: {e}", exc_info=True)

        # 🚀 PHASE OMEGA: Dynamic Incident Cards
        enhanced_metadata = {
            "persona": meta_context.persona,
            "stage": meta_context.stage,
            "active_incident_id": meta_context.active_incident_id,
        }

        try:
            from ..services.dynamic_incident_cards import get_card_generator

            card_generator = get_card_generator()
            enhanced_metadata["card_generator_available"] = True

        except Exception as e:
            logger.error(f"Card generator initialization error: {e}", exc_info=True)
            enhanced_metadata["card_generator_available"] = False

        # Append user message to conversation history
        await context_manager.append_message(user_id, channel_id, "user", message_text)

        # Reload context after appending message
        meta_context = await context_manager.load_context(user_id, channel_id)

        # PHASE OMEGA OBJECTIVE #1: If agent blocked orchestrator, return immediately
        if agent_blocks_orchestrator:
            logger.info("Agent blocked orchestrator - skipping orchestration")
            return {
                "status": "success",
                "intent": "agent_handled",
                "agent_response": agent_enhanced_context,
            }

        # Get available functions
        available_functions = get_function_definitions()

        # Call orchestrator
        logger.info("Calling LLM orchestrator...")
        orchestrator_output = await orchestrator.run(
            user_message=message_text,
            meta_context=meta_context,
            available_functions=available_functions,
        )

        logger.info(f"Orchestrator result: intent={orchestrator_output.intent}, function={orchestrator_output.function_call.name or 'none'}")
        logger.debug(f"Reasoning: {orchestrator_output.reasoning}")

        # PHASE OMEGA OBJECTIVE #2: CANONICAL STAGE ROUTING - Let orchestrator apply stage updates
        if orchestrator_output.context_updates:
            context_update_dict = orchestrator_output.context_updates.model_dump(exclude_none=True)
            if context_update_dict:
                logger.debug(f"Applying orchestrator context updates: {list(context_update_dict.keys())}")
                meta_context = await context_manager.merge_context_updates(
                    user_id,
                    channel_id,
                    context_update_dict,
                )

        # Execute function if requested
        function_sent_user_message = False
        function_result = None
        if orchestrator_output.function_call.name:
            logger.info(f"Executing function: {orchestrator_output.function_call.name}")

            # Build context for function execution
            function_context = {
                "user_id": user_id,
                "channel_id": channel_id,
                "persona": meta_context.persona,
            }

            # Inject meta-context fields into function arguments
            function_args = {**orchestrator_output.function_call.arguments}

            # Special handling for discovery answer recording
            if orchestrator_output.function_call.name == "record_discovery_answer":
                function_args["total_questions"] = len(meta_context.discovery.questions)

            # Execute function
            function_result = await execute_function(
                function_name=orchestrator_output.function_call.name,
                arguments=function_args,
                context=function_context,
            )

            logger.info(f"Function result: success={function_result.success}, message={function_result.message}")

            # PHASE OMEGA OBJECTIVE #8: FUNCTION-CALL OUTPUT GUARD
            # Check if function already sent a user message
            if function_result.data and function_result.data.get("user_message_sent"):
                function_sent_user_message = True
                logger.info("Function already sent user message - skipping orchestrator response")

            # Update context with function result data
            if function_result.success and function_result.data:
                context_updates = {}

                # Update active incident/job IDs if function created them
                if "incident_id" in function_result.data and not meta_context.active_incident_id:
                    context_updates["active_incident_id"] = function_result.data["incident_id"]
                    logger.info(f"✅ Set active_incident_id: {function_result.data['incident_id']}")

                if "job_id" in function_result.data and not meta_context.active_job_id:
                    context_updates["active_job_id"] = function_result.data["job_id"]
                    logger.info(f"✅ Set active_job_id: {function_result.data['job_id']}")

                # 🚨 CRITICAL: Check if discovery was auto-started by create_incident
                # If discovery_auto_started=True, DO NOT call start_discovery again
                if function_result.data.get("discovery_auto_started"):
                    logger.info(f"✅ Discovery auto-started by create_incident, updating stage to discovery")
                    context_updates["stage"] = "discovery"
                    # Discovery questions and first question were already sent by create_incident
                    # DO NOT trigger start_discovery again

                # Update discovery state if function returned discovery info
                if "questions" in function_result.data:
                    context_updates["discovery"] = {
                        "questions": function_result.data["questions"],
                        "question_index": function_result.data.get("question_index", 0),
                        "incident_id": function_result.data.get("incident_id"),
                    }
                    logger.info(f"✅ Updated discovery state: Q{function_result.data.get('question_index', 0) + 1}/{len(function_result.data['questions'])}")

                # Update discovery question index if advancing
                if "next_question_index" in function_result.data:
                    current_discovery = meta_context.discovery.model_dump()
                    current_discovery["question_index"] = function_result.data["next_question_index"]
                    context_updates["discovery"] = current_discovery
                    logger.info(f"✅ Advanced to discovery Q{function_result.data['next_question_index'] + 1}")

                # Check if discovery is complete
                if function_result.data.get("discovery_complete"):
                    context_updates["stage"] = "discovery_complete"
                    logger.info("✅ Discovery complete, transitioning to discovery_complete stage")

                # Apply all context updates
                if context_updates:
                    meta_context = await context_manager.update_context(user_id, channel_id, context_updates)
                    logger.info(f"✅ Context updated: {list(context_updates.keys())}")

            # Check if we need multi-turn function calling
            next_action = orchestrator_output.context_updates.next_action
            if next_action and function_result.success:
                logger.info(f"Multi-turn action requested: {next_action}")

                # Call orchestrator again with function result
                orchestrator_output_2 = await orchestrator.run(
                    user_message=f"Function '{orchestrator_output.function_call.name}' completed successfully. {next_action}",
                    meta_context=meta_context,
                    available_functions=available_functions,
                    function_result=function_result,
                )

                # Execute second function if requested
                if orchestrator_output_2.function_call.name:
                    logger.info(f"Executing second function: {orchestrator_output_2.function_call.name}")

                    function_args_2 = {**orchestrator_output_2.function_call.arguments}

                    # Inject special parameters
                    if orchestrator_output_2.function_call.name == "start_discovery":
                        if "incident_id" not in function_args_2 and meta_context.active_incident_id:
                            function_args_2["incident_id"] = meta_context.active_incident_id

                    function_result_2 = await execute_function(
                        function_name=orchestrator_output_2.function_call.name,
                        arguments=function_args_2,
                        context=function_context,
                    )

                    logger.info(f"Second function result: success={function_result_2.success}")

                    # Update context from second function
                    if function_result_2.success and function_result_2.data:
                        if "questions" in function_result_2.data:
                            await context_manager.update_context(
                                user_id,
                                channel_id,
                                {
                                    "discovery": {
                                        "questions": function_result_2.data["questions"],
                                        "question_index": function_result_2.data.get("question_index", 0),
                                    },
                                    "stage": "discovery",
                                },
                            )

                # Use second orchestrator's response if available
                if orchestrator_output_2.response_to_user:
                    orchestrator_output.response_to_user = orchestrator_output_2.response_to_user

        # 🚨 Handle special intents (garbage, errors, etc.)
        if orchestrator_output.intent in ["garbage_input", "off_topic"]:
            logger.info(f"🗑️ Garbage/off-topic input detected: {orchestrator_output.intent}")
            # Send friendly fallback message
            fallback_messages = {
                "garbage_input": "I'm here to help with property maintenance issues. If you're experiencing a problem (leak, broken appliance, etc.), please describe it and I'll help you report it.",
                "off_topic": "I'm focused on property maintenance. If you have a maintenance issue, I'm here to help report and track it.",
            }
            fallback_text = fallback_messages.get(orchestrator_output.intent, "I'm here to help with maintenance issues.")

            bot.send_ai_message(
                channel_id=channel_id,
                persona=meta_context.persona,
                text=fallback_text,
                metadata={"intent": orchestrator_output.intent},
            )

            return {
                "status": "acknowledged",
                "intent": orchestrator_output.intent,
                "reason": "garbage_or_offtopic",
            }

        # Handle JSON parse errors
        if orchestrator_output.intent == "json_parse_error":
            logger.error(f"🚨 LLM JSON parse error: {orchestrator_output.reasoning}")
            # Don't send error to user, just log and return
            return {
                "status": "error",
                "intent": "json_parse_error",
                "reason": "LLM output invalid JSON",
            }

        # PHASE OMEGA OBJECTIVE #8: FUNCTION-CALL OUTPUT GUARD
        # Send response to user if LLM provided one AND function didn't already send one
        if orchestrator_output.response_to_user and not function_sent_user_message:
            logger.info(f"Sending LLM response to user: {orchestrator_output.response_to_user[:100]}")

            response_metadata = {
                "intent": orchestrator_output.intent,
                "persona": meta_context.persona,
                "stage": meta_context.stage,
            }

            bot.send_ai_message(
                channel_id=channel_id,
                persona=meta_context.persona,
                text=orchestrator_output.response_to_user,
                metadata=response_metadata,
            )

            # Append to conversation history
            await context_manager.append_message(
                user_id,
                channel_id,
                "assistant",
                orchestrator_output.response_to_user,
            )

        # 🚀 PHASE OMEGA: Record interaction for auto-evolving skills
        try:
            from ..services.orchestrator import record_agent_interaction

            if agent_enhanced_context:
                await record_agent_interaction(
                    user_id=user_id,
                    agent_type="multi_agent",
                    user_message=message_text,
                    agent_response=orchestrator_output.response_to_user or "",
                    outcome="success" if orchestrator_output.function_call.name else "chat",
                )
        except Exception as e:
            logger.error(f"Error recording interaction: {e}", exc_info=True)

        # Log performance
        duration = (time.time() - start_time) * 1000
        logger.info(f"Message processing completed in {duration:.2f}ms")

        return {
            "status": "success",
            "intent": orchestrator_output.intent,
            "function_executed": orchestrator_output.function_call.name,
            "duration_ms": duration,
        }

    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)

        # Send error message to user
        try:
            bot = get_bot()
            bot.send_ai_message(
                channel_id=channel_id,
                persona="tenant",
                text="I encountered an error processing your request. Please try again or contact support.",
                metadata={"error": True},
            )
        except:
            pass

        return {"status": "error", "error": str(e)}


async def handle_reaction(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle reaction events (feedback mechanism)"""
    try:
        reaction = payload.get("reaction", {})
        user = payload.get("user", {})
        message = payload.get("message", {})

        reaction_type = reaction.get("type")
        user_id = user.get("id")
        message_id = message.get("id")

        logger.info(f"Reaction received: {reaction_type} from user {user_id} on message {message_id}")

        # Log feedback for analytics
        # In the future, this could update model training data

        return {"status": "acknowledged", "reaction": reaction_type}

    except Exception as e:
        logger.error(f"Error handling reaction: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


async def _detect_persona(channel_id: str, bot) -> str:
    """
    Detect user persona from channel using Stream Bot service.
    Fallback to 'tenant' if detection fails.
    """
    try:
        return bot.get_channel_persona(channel_id) or "tenant"
    except Exception as e:
        logger.error(f"Error detecting persona: {e}", exc_info=True)
        return "tenant"


async def handle_ai_intent(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle AI Support intent events - Amazon-style guided flow.

    Frontend sends: ai_intent event with { intent, payload }
    Backend responds: ai_state event with { stage, ui_mode, payload }
    """
    try:
        start_time = time.time()

        # Extract event details
        user = payload.get("user", {})
        channel_id = payload.get("channel_id", "unknown")
        user_id = user.get("id", "unknown")

        # Extract intent and payload from custom event data
        intent = payload.get("intent")
        intent_payload = payload.get("payload", {}) or {}

        logger.info(f"========== AI Intent Event ==========")
        logger.info(f"Channel: {channel_id}")
        logger.info(f"User: {user_id}")
        logger.info(f"Intent: {intent}")
        logger.info(f"Payload: {intent_payload}")

        # Ignore bot messages
        if user.get("is_bot"):
            logger.debug(f"Ignoring bot intent from: {user_id}")
            return {"status": "ignored", "reason": "bot_message"}

        # Get persona from payload or detect from channel
        persona = intent_payload.get("persona")
        if not persona:
            bot = get_bot()
            persona = await _detect_persona(channel_id, bot) or "tenant"

        # Initialize AI Support orchestrator
        orchestrator = get_ai_support_orchestrator()

        # Process intent through orchestrator
        logger.info(f"Processing intent '{intent}' with orchestrator")
        state_result = await orchestrator.handle_intent(
            intent=intent,
            payload=intent_payload,
            channel_id=channel_id,
            user_id=user_id,
            persona=persona
        )

        logger.info(f"Orchestrator result: stage={state_result.get('stage')}, ui_mode={state_result.get('ui_mode')}")

        # Send ai_state event back to channel
        bot = get_bot()
        from stream_chat import StreamChat

        # Get Stream client from bot
        stream_client = bot.client
        channel = stream_client.channel("messaging", channel_id)

        # Send ai_state custom event
        ai_state_event = {
            "type": "ai_state",
            **state_result
        }

        logger.info(f"Sending ai_state event: {ai_state_event}")
        channel.send_event(ai_state_event, user_id=user_id)

        # Log performance
        duration = (time.time() - start_time) * 1000
        logger.info(f"AI Intent processing completed in {duration:.2f}ms")

        return {
            "status": "success",
            "intent": intent,
            "stage": state_result.get("stage"),
            "ui_mode": state_result.get("ui_mode"),
            "duration_ms": duration,
        }

    except Exception as e:
        logger.error(f"Error handling AI intent: {e}", exc_info=True)

        # Send fallback state to channel
        try:
            bot = get_bot()
            from stream_chat import StreamChat
            stream_client = bot.client
            channel = stream_client.channel("messaging", channel_id)

            fallback_event = {
                "type": "ai_state",
                "stage": "intro",
                "ui_mode": "fallback",
                "payload": {
                    "error": f"An error occurred: {str(e)}"
                }
            }

            channel.send_event(fallback_event, user_id=user_id)
        except:
            pass

        return {"status": "error", "error": str(e)}


# ==================== ADDITIONAL ENDPOINTS ====================


@router.post("/ai/init-channel")
async def init_channel(request: Request):
    """Initialize AI channel with persona bot"""
    try:
        data = await request.json()
        channel_id = data.get("channel_id")
        persona = data.get("persona", "tenant")
        user_id = data.get("user_id")

        if not channel_id or not user_id:
            raise HTTPException(status_code=400, detail="channel_id and user_id required")

        bot = get_bot()
        context_manager = get_meta_context_manager()

        # Create initial context
        meta_context = await context_manager.load_context(user_id, channel_id, create_if_missing=True)
        meta_context.persona = persona
        await context_manager.save_context(user_id, channel_id, meta_context)

        # Send welcome message
        welcome_messages = {
            "tenant": "👋 Hi! I'm your LandTen maintenance assistant. Report any issues and I'll help get them resolved quickly.",
            "landlord": "👋 Welcome! I'll keep you updated on maintenance requests and help manage approvals efficiently.",
            "contractor": "👋 Hi! I'll notify you about new jobs and help coordinate maintenance work.",
        }

        welcome_text = welcome_messages.get(persona, welcome_messages["tenant"])

        bot.send_ai_message(
            channel_id=channel_id,
            persona=persona,
            text=welcome_text,
            metadata={"type": "welcome"},
        )

        logger.info(f"Initialized channel {channel_id} for {persona} user {user_id}")

        return {"status": "success", "channel_id": channel_id, "persona": persona}

    except Exception as e:
        logger.error(f"Error initializing channel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai/bot-status")
async def get_bot_status():
    """Get AI bot configuration and status"""
    try:
        orchestrator = get_orchestrator()

        return {
            "status": "operational",
            "version": "3.0-orchestrator",
            "model": orchestrator.model,
            "temperature": orchestrator.temperature,
            "architecture": "llm-driven",
            "features": [
                "universal_orchestrator",
                "function_calling",
                "meta_context_management",
                "multi_turn_reasoning",
                "dynamic_intent_classification",
            ],
        }

    except Exception as e:
        logger.error(f"Error getting bot status: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
