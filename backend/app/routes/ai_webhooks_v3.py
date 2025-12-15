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
from ..services.response_handler import get_response_handler
from ..services.conversation_manager import get_conversation_manager
from ..services.meta_context_manager import get_meta_context_manager
# DEPRECATED: Orchestrator replaced by ResponseHandler (Responses API)
# from ..services.orchestrator import get_orchestrator
# from ..services.ai_support_orchestrator import get_ai_support_orchestrator
from ..functions.function_registry import (
    get_function_definitions,
    execute_function,
)
from ..models.orchestrator_schemas import MetaContext, FunctionResult
from ..services.task_queue import get_task_queue, TaskType

router = APIRouter()
logger = logging.getLogger(__name__)

# 🔒 IDEMPOTENCY: Track processed webhook event IDs to prevent duplicates
_processed_events: set = set()  # In production, use Redis with TTL
_processed_events_lock = asyncio.Lock()
MAX_PROCESSED_EVENTS = 10000  # Limit memory usage


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

    # 🔒 CRITICAL FIX: Enforce webhook signature validation (no bypass)
    if not x_signature:
        # Check if auth is explicitly disabled (dev/test only)
        if os.getenv("AUTH_DISABLED") != "true":
            logger.error("⛔ Webhook rejected: Missing x-signature header")
            raise HTTPException(
                status_code=401,
                detail={"error": "Missing webhook signature", "hint": "x-signature header required"},
            )
        else:
            logger.warning("⚠️ AUTH_DISABLED=true - allowing unsigned webhook (DEV MODE ONLY)")
    else:
        logger.debug("Verifying webhook signature")
        if not verify_webhook_signature(body, x_signature):
            logger.error("⛔ Webhook signature verification FAILED")
            raise HTTPException(
                status_code=401,
                detail={"error": "Invalid webhook signature", "hint": "Check STREAM_WEBHOOK_SECRET configuration"},
            )
        logger.debug("✅ Signature verified successfully")

    # Parse JSON payload
    try:
        payload = await request.json()
        event_type = payload.get("type")
        logger.info(f"Event type: {event_type}")
    except Exception as e:
        logger.error(f"Failed to parse JSON payload: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    # 🔒 IDEMPOTENCY: Check if this exact event was already processed
    event_id = None
    if event_type == "message.new":
        message = payload.get("message", {})
        event_id = message.get("id")  # Use Stream's message ID as idempotency key

        if event_id:
            async with _processed_events_lock:
                if event_id in _processed_events:
                    logger.warning(f"⚠️ Duplicate event detected: {event_id} - returning cached response")
                    return {"status": "duplicate", "event_id": event_id, "message": "Already processed"}

                # Mark as processing (before releasing lock to prevent race)
                _processed_events.add(event_id)

                # Prevent memory leak: trim old events if too many
                if len(_processed_events) > MAX_PROCESSED_EVENTS:
                    # Remove oldest 20% of events (simple FIFO)
                    to_remove = list(_processed_events)[:2000]
                    _processed_events.difference_update(to_remove)
                    logger.debug(f"🧹 Trimmed processed events cache ({len(to_remove)} removed)")
        else:
            logger.warning("⚠️ message.new event missing message.id - cannot enforce idempotency")

    # Handle different event types
    if event_type == "message.new":
        logger.info("Routing to handle_new_message() [ASYNC QUEUE MODE]")
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
    🚨 DEPRECATED: Removed to prevent duplicate concurrent saves.
    Incident graph is now saved ONCE at the end of message processing.
    """
    logger.warning("⚠️ _save_graph_background called but deprecated - graph saved at end of processing")
    pass


async def handle_new_message(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    FIRE-AND-FORGET webhook handler - NEVER blocks.

    This is the NEW async-queue-based handler that:
    1. Sends immediate fallback message
    2. Queues task for background processing
    3. Returns 200 OK in <200ms

    This prevents H12 timeouts from 429 rate-limit errors.
    """
    try:
        # Extract message details
        message = payload.get("message", {})
        user = payload.get("user", {})
        channel_id = payload.get("channel_id", "unknown")
        user_id = user.get("id", "unknown")
        message_text = message.get("text", "")
        attachments = message.get("attachments", [])  # 🔥 EXTRACT ATTACHMENTS

        logger.info(f"========== ASYNC QUEUE MODE: New Message ==========")
        logger.info(f"Channel: {channel_id}")
        logger.info(f"User: {user_id} ({user.get('name', 'unknown')})")
        logger.info(f"Text: {message_text[:120] if message_text else '[No text - photo only]'}")
        logger.info(f"📎 Attachments: {len(attachments)} attachment(s)")
        if attachments:
            for idx, att in enumerate(attachments):
                logger.info(f"   📎 Attachment {idx + 1}: type={att.get('type')}, mime={att.get('mime_type')}, url={att.get('url', att.get('image_url', att.get('asset_url', 'N/A')))[:80]}")

        # Ignore bot messages
        if user.get("is_bot") or str(user_id).startswith("ai-"):
            logger.debug(f"Ignoring bot message from: {user_id}")
            return {"status": "ignored", "reason": "bot_message"}

        # Check if agent is enabled
        metadata = message.get("metadata", {}) or {}
        agent_enabled = metadata.get("agentEnabled", True)
        if agent_enabled is False:
            logger.debug("Agent disabled via metadata for this message")
            return {"status": "ignored", "reason": "agent_disabled"}

        # Send typing indicator (native GetStream feature - replaces processing messages)
        try:
            from stream_chat import StreamChat
            api_key = os.getenv("STREAM_CHAT_API_KEY")
            api_secret = os.getenv("STREAM_CHAT_API_SECRET")

            if api_key and api_secret:
                # Parse channel type from channel_id (format: "messaging:landtenmvp3")
                channel_type, channel_name = (
                    tuple(channel_id.split(":", 1)) if ":" in channel_id else ("messaging", channel_id)
                )

                client = StreamChat(api_key, api_secret)
                channel = client.channel(channel_type, channel_name)

                # Get the bot user ID based on channel persona
                bot = get_bot()
                persona = bot.get_channel_persona(channel_id) or "tenant"
                bot_user_id = bot.get_bot_id(persona)

                # Send typing.start event from bot user
                channel.send_event({"type": "typing.start"}, bot_user_id)
                logger.debug(f"✅ Sent typing indicator for {persona} bot ({bot_user_id})")
        except Exception as e:
            logger.warning(f"⚠️ Failed to send typing indicator: {e}")

        # Queue task for background processing
        task_queue = get_task_queue()
        queued = await task_queue.enqueue(
            task_type=TaskType.PROCESS_MESSAGE,
            payload=payload,
            user_id=user_id,
            channel_id=channel_id,
        )

        if queued:
            logger.info(f"✅ Task queued for background processing")
            return {
                "status": "queued",
                "message": "Processing in background",
                "user_id": user_id,
                "channel_id": channel_id,
            }
        else:
            logger.error(f"❌ Task queue full - load shedding")
            return {
                "status": "shed",
                "message": "Queue full, sent overload message",
                "user_id": user_id,
                "channel_id": channel_id,
            }

    except Exception as e:
        logger.error(f"Error in async queue handler: {e}", exc_info=True)

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


async def handle_new_message_background(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    BACKGROUND processing handler - runs in task queue worker.

    This is the ORIGINAL handler logic, now moved to background.
    Called by task queue workers, NOT by webhooks directly.
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
        attachments = message.get("attachments", [])  # 🔥 EXTRACT ATTACHMENTS

        logger.info(f"========== New Message ==========")
        logger.info(f"Channel: {channel_id}")
        logger.info(f"User: {user_id} ({user.get('name', 'unknown')})")
        logger.info(f"Text: {message_text[:120] if message_text else '[No text - photo only]'}")
        logger.info(f"📎 Attachments: {len(attachments)} attachment(s)")
        if attachments:
            for idx, att in enumerate(attachments):
                att_type = att.get('type', 'unknown')
                att_mime = att.get('mime_type', 'unknown')
                att_url = att.get('url') or att.get('image_url') or att.get('asset_url', 'N/A')
                logger.info(f"   📎 Attachment {idx + 1}: type={att_type}, mime={att_mime}, url={att_url[:80]}")
                # For images, log if AI analysis is present
                if 'ai_analysis' in att:
                    logger.info(f"      🤖 AI Analysis present: {att.get('ai_analysis', '')[:60]}...")

        # Ignore bot messages
        if user.get("is_bot") or str(user_id).startswith("ai-"):
            logger.debug(f"Ignoring bot message from: {user_id}")
            return {"status": "ignored", "reason": "bot_message"}

        # Check if agent is enabled
        agent_enabled = metadata.get("agentEnabled", True)
        if agent_enabled is False:
            logger.debug("Agent disabled via metadata for this message")
            return {"status": "ignored", "reason": "agent_disabled"}

        # ============================================================================
        # NEW: RESPONSES API SINGLE-FLOW ARCHITECTURE
        # ============================================================================
        # Using ResponseHandler (replaces TenantAgent + Orchestrator dual-agent flow)

        # Initialize services
        bot = get_bot()
        response_handler = get_response_handler()
        conversation_manager = get_conversation_manager()

        # Detect persona
        persona = metadata.get("persona", "tenant")
        if not persona or persona == "tenant":
            persona = await _detect_persona(channel_id, bot)

        logger.info(f"Processing message with ResponseHandler for persona: {persona}")

        # 🔥 CRITICAL FIX: Build complete message with attachments
        # For photo-only messages, create descriptive text from attachments
        complete_message = message_text
        if not complete_message and attachments:
            # Photo-only message - describe attachments
            image_count = sum(1 for att in attachments if 'image' in att.get('mime_type', '') or att.get('type') == 'image')
            file_count = len(attachments) - image_count

            parts = []
            if image_count > 0:
                parts.append(f"{image_count} photo{'s' if image_count > 1 else ''}")
            if file_count > 0:
                parts.append(f"{file_count} file{'s' if file_count > 1 else ''}")

            complete_message = f"[User sent {', '.join(parts)}]"
            logger.info(f"📸 Photo-only message detected, generated description: {complete_message}")

        # Process message using new single-flow architecture
        try:
            result = await response_handler.process_message(
                channel_id=channel_id,
                user_id=user_id,
                message=complete_message,
                persona=persona,
                attachments=attachments  # 🔥 PASS ATTACHMENTS TO HANDLER
            )

            if result.get("success"):
                logger.info(f"✅ Message processed successfully: {result.get('tool_calls_executed', 0)} tool calls executed")

                # Log performance
                duration = (time.time() - start_time) * 1000
                logger.info(f"Message processing completed in {duration:.2f}ms")

                return {
                    "status": "success",
                    "conversation_id": result.get("conversation_id"),
                    "tool_calls_executed": result.get("tool_calls_executed", 0),
                    "duration_ms": duration,
                }
            else:
                logger.error(f"❌ Message processing failed: {result.get('error')}")

                # Send error message to user
                bot.send_ai_message(
                    channel_id=channel_id,
                    persona=persona,
                    text="I encountered an error processing your request. Please try again.",
                    metadata={"error": result.get("error")}
                )

                return {
                    "status": "error",
                    "error": result.get("error")
                }

        except Exception as e:
            logger.error(f"Exception in ResponseHandler: {e}", exc_info=True)

            # Send error message to user
            bot.send_ai_message(
                channel_id=channel_id,
                persona=persona,
                text="I encountered an unexpected error. Please try again.",
                metadata={"exception": str(e)}
            )

            return {
                "status": "error",
                "exception": str(e)
            }

        # ============================================================================
        # OLD DUAL-AGENT FLOW (Deprecated - kept for rollback)
        # ============================================================================
        # # Initialize services
        # bot = get_bot()
        # context_manager = get_meta_context_manager()
        # orchestrator = get_orchestrator()
        #
        # # Load or create meta-context
        # logger.debug(f"Loading context for user={user_id} channel={channel_id}")
        # meta_context = await context_manager.load_context(user_id, channel_id, create_if_missing=True)
        #
        # # Detect persona if not set
        # if not meta_context.persona or meta_context.persona == "tenant":
        #     persona = metadata.get("persona") or await _detect_persona(channel_id, bot)
        #     meta_context.persona = persona
        #     # 🚨 CRITICAL FIX: Defer save to batch writes at end of message processing
        #     await context_manager.save_context(user_id, channel_id, meta_context, defer=True)
        #
        # logger.info(f"Persona: {meta_context.persona}, Stage: {meta_context.stage}")
        #
        # 🚀 PHASE OMEGA: Agent Router Integration
        #         agent_enhanced_context = None
        #         agent_blocks_orchestrator = False
        #         try:
        #             from ..agents.agent_router import get_agent_router
        # 
        #             agent_router = get_agent_router()
        #             agent_response = await agent_router.route(
        #                 message=message_text,
        #                 context={
        #                     "stage": meta_context.stage,
        #                     "active_incident_id": meta_context.active_incident_id,
        #                     "persona": meta_context.persona,
        #                     "metadata": meta_context.metadata,
        #                 },
        #             )
        # 
        #             if agent_response and agent_response.get("agent_response"):
        #                 agent_enhanced_context = agent_response.get("agent_response")
        #                 logger.info(f"🤖 Routed to {agent_response.get('agent_type', 'unknown')} agent")
        # 
        #                 # PHASE OMEGA OBJECTIVE #1: STOP SIGNAL ROUTING
        #                 # If agent blocks orchestrator, return immediately without calling orchestrator
        #                 if agent_response.get("block_orchestrator"):
        #                     logger.info(f"🛑 Agent blocked orchestrator - returning agent result directly")
        #                     agent_blocks_orchestrator = True
        # 
        #         except Exception as e:
        #             logger.error(f"Agent routing error: {e}", exc_info=True)
        # 
        #         # 🚀 PHASE OMEGA: Topic Graph Update
        #         try:
        #             from ..services.incident_topic_graph import get_incident_graph
        # 
        #             if meta_context.active_incident_id:
        #                 incident_graph = get_incident_graph(user_id)
        # 
        #                 # 🚨 CRITICAL FIX: Removed duplicate background saves (caused concurrent write races)
        #                 # Graph is now saved ONCE at end of message processing
        # 
        #                 shift_result = incident_graph.detect_topic_shift(
        #                     new_message=message_text,
        #                     current_incident_id=meta_context.active_incident_id,
        #                 )
        # 
        #                 if shift_result.get("is_shift"):
        #                     logger.info(f"🔀 Topic shift detected: {shift_result.get('reason')}")
        # 
        #                     target_incident = shift_result.get("target_incident_id")
        # 
        #                     if target_incident:
        #                         logger.info(f"↪️ Switching to existing incident: {target_incident}")
        #                         meta_context = await context_manager.update_context(
        #                             user_id,
        #                             channel_id,
        #                             {
        #                                 "active_incident_id": target_incident,
        #                                 "stage": shift_result.get("target_stage", "discovery"),
        #                             },
        #                         )
        # 
        #                         # 🚨 CRITICAL FIX: Graph saved once at end, not here
        # 
        #         except Exception as e:
        #             logger.error(f"Topic graph update error: {e}", exc_info=True)
        # 
        #         # 🚀 PHASE OMEGA: Dynamic Incident Cards
        #         enhanced_metadata = {
        #             "persona": meta_context.persona,
        #             "stage": meta_context.stage,
        #             "active_incident_id": meta_context.active_incident_id,
        #         }
        # 
        #         try:
        #             from ..services.dynamic_incident_cards import get_card_generator
        # 
        #             card_generator = get_card_generator()
        #             enhanced_metadata["card_generator_available"] = True
        # 
        #         except Exception as e:
        #             logger.error(f"Card generator initialization error: {e}", exc_info=True)
        #             enhanced_metadata["card_generator_available"] = False
        # 
        #         # Append user message to conversation history
        #         await context_manager.append_message(user_id, channel_id, "user", message_text)
        # 
        #         # Reload context after appending message
        #         meta_context = await context_manager.load_context(user_id, channel_id)
        # 
        #         # 🔧 STATE NORMALIZATION: Fix corrupted discovery state
        #         # Clear discovery state ONLY if stage is incompatible AND discovery is not actively in use
        #         # For pre-incident discovery: stage="discovery", incident_id=None is VALID
        #         # For post-incident discovery: stage="discovery", incident_id=set is VALID
        #         # Only clear if stage is NOT "discovery" but discovery has leftover questions from a completed flow
        #         if meta_context.stage not in ["discovery", "idle"] and meta_context.discovery and len(meta_context.discovery.questions) > 0:
        #             # Check if discovery is actually complete (incident was already created)
        #             if meta_context.active_incident_id and meta_context.stage in ["detected", "diagnosing", "work_order", "completed"]:
        #                 logger.warning(f"⚠️ Detected stale discovery state: stage={meta_context.stage} but discovery has {len(meta_context.discovery.questions)} leftover questions. Clearing discovery state.")
        #                 await context_manager.update_context(user_id, channel_id, {
        #                     "discovery": {
        #                         "question_index": 0,
        #                         "questions": [],
        #                         "answers": {},
        #                         "is_active": False,
        #                     }
        #                 })
        #                 meta_context = await context_manager.load_context(user_id, channel_id)
        # 
        #         # PHASE OMEGA OBJECTIVE #1: If agent blocked orchestrator, return immediately
        #         if agent_blocks_orchestrator:
        #             logger.info("Agent blocked orchestrator - skipping orchestration")
        #             return {
        #                 "status": "success",
        #                 "intent": "agent_handled",
        #                 "agent_response": agent_enhanced_context,
        #             }
        # 
        #         # Get available functions
        #         available_functions = get_function_definitions()
        # 
        #         # Call orchestrator
        #         logger.info("Calling LLM orchestrator...")
        #         orchestrator_output = await orchestrator.run(
        #             user_message=message_text,
        #             meta_context=meta_context,
        #             available_functions=available_functions,
        #         )
        # 
        #         logger.info(f"Orchestrator result: intent={orchestrator_output.intent}, function={orchestrator_output.function_call.name or 'none'}")
        #         logger.debug(f"Reasoning: {orchestrator_output.reasoning}")
        # 
        #         # PHASE OMEGA OBJECTIVE #2: CANONICAL STAGE ROUTING - Let orchestrator apply stage updates
        #         if orchestrator_output.context_updates:
        #             context_update_dict = orchestrator_output.context_updates.model_dump(exclude_none=True)
        #             if context_update_dict:
        #                 logger.debug(f"Applying orchestrator context updates: {list(context_update_dict.keys())}")
        #                 meta_context = await context_manager.merge_context_updates(
        #                     user_id,
        #                     channel_id,
        #                     context_update_dict,
        #                 )
        # 
        #         # Execute function if requested
        #         function_sent_user_message = False
        #         function_result = None
        #         if orchestrator_output.function_call.name:
        #             logger.info(f"Executing function: {orchestrator_output.function_call.name}")
        # 
        #             # Build context for function execution
        #             function_context = {
        #                 "user_id": user_id,
        #                 "channel_id": channel_id,
        #                 "persona": meta_context.persona,
        #             }
        # 
        #             # Inject meta-context fields into function arguments
        #             function_args = {**orchestrator_output.function_call.arguments}
        # 
        #             # Special handling for discovery answer recording
        #             if orchestrator_output.function_call.name == "record_discovery_answer":
        #                 # Auto-inject question_index from meta_context if not provided
        #                 if "question_index" not in function_args:
        #                     function_args["question_index"] = meta_context.discovery.question_index
        #                     logger.info(f"✅ Auto-injected question_index={meta_context.discovery.question_index} from meta_context")
        # 
        #                 # Auto-inject total_questions from meta_context
        #                 function_args["total_questions"] = len(meta_context.discovery.questions)
        # 
        #             # Execute function
        #             function_result = await execute_function(
        #                 function_name=orchestrator_output.function_call.name,
        #                 arguments=function_args,
        #                 context=function_context,
        #             )
        # 
        #             logger.info(f"Function result: success={function_result.success}, message={function_result.message}")
        # 
        #             # PHASE OMEGA OBJECTIVE #8: FUNCTION-CALL OUTPUT GUARD
        #             # Check if function already sent a user message
        #             if function_result.data and function_result.data.get("user_message_sent"):
        #                 function_sent_user_message = True
        #                 logger.info("Function already sent user message - skipping orchestrator response")
        # 
        #             # Update context with function result data
        #             if function_result.success and function_result.data:
        #                 context_updates = {}
        # 
        #                 # Update active incident/job IDs if function created them
        #                 if "incident_id" in function_result.data and not meta_context.active_incident_id:
        #                     context_updates["active_incident_id"] = function_result.data["incident_id"]
        #                     logger.info(f"✅ Set active_incident_id: {function_result.data['incident_id']}")
        # 
        #                 if "job_id" in function_result.data and not meta_context.active_job_id:
        #                     context_updates["active_job_id"] = function_result.data["job_id"]
        #                     logger.info(f"✅ Set active_job_id: {function_result.data['job_id']}")
        # 
        #                 # 🚨 CRITICAL: Check if discovery was auto-started by create_incident
        #                 # If discovery_auto_started=True, DO NOT call start_discovery again
        #                 if function_result.data.get("discovery_auto_started"):
        #                     logger.info(f"✅ Discovery auto-started by create_incident, updating stage to discovery")
        #                     context_updates["stage"] = "discovery"
        #                     # Discovery questions and first question were already sent by create_incident
        #                     # DO NOT trigger start_discovery again
        # 
        #                 # Update discovery state if function returned discovery info
        #                 if "questions" in function_result.data:
        #                     context_updates["discovery"] = {
        #                         "questions": function_result.data["questions"],
        #                         "question_index": function_result.data.get("question_index", 0),
        #                         "incident_id": function_result.data.get("incident_id"),
        #                         "is_active": True,
        #                         "answers": function_result.data.get("discovery_data", {}).get("answers", {}),
        #                     }
        #                     # Mark stage as discovery for pre-incident flow
        #                     # Check if incident_id is None (pre-incident discovery), not if meta_context has no active_incident_id
        #                     if function_result.data.get("incident_id") is None:
        #                         context_updates["stage"] = "discovery"
        #                         logger.info("✅ Updated stage to 'discovery' for pre-incident flow")
        #                     logger.info(f"✅ Updated discovery state: Q{function_result.data.get('question_index', 0) + 1}/{len(function_result.data['questions'])}")
        # 
        #                 # Update discovery question index and answers if advancing
        #                 if "next_question_index" in function_result.data:
        #                     current_discovery = meta_context.discovery.model_dump()
        #                     current_discovery["question_index"] = function_result.data["next_question_index"]
        #                     current_discovery["is_active"] = True
        # 
        #                     # Update answers if provided (pre-incident flow)
        #                     if function_result.data.get("discovery_data"):
        #                         current_discovery["answers"] = function_result.data["discovery_data"].get("answers", {})
        #                         current_discovery["questions"] = function_result.data["discovery_data"].get("questions", current_discovery.get("questions", []))
        # 
        #                     context_updates["discovery"] = current_discovery
        #                     logger.info(f"✅ Advanced to discovery Q{function_result.data['next_question_index'] + 1}")
        # 
        #                 # 🚨 NEW: Check if discovery is complete
        #                 if function_result.data.get("discovery_complete"):
        #                     # For pre-incident discovery: call create_incident_from_discovery
        #                     # Check if incident_id is None (pre-incident discovery), not if meta_context has no active_incident_id
        #                     # because there might be an OLD incident still "active" in the context
        #                     if function_result.data.get("incident_id") is None and function_result.data.get("discovery_data"):
        #                         logger.info("✅ Pre-incident discovery complete - creating incident from Q&A")
        # 
        #                         # Get the last user message (initial issue report)
        #                         initial_message = text if text else "Maintenance issue reported"
        # 
        #                         # Build discovery_data with initial message
        #                         discovery_data = function_result.data["discovery_data"]
        #                         discovery_data["initial_message"] = initial_message
        # 
        #                         # Call create_incident_from_discovery
        #                         from ..functions.function_registry import create_incident_from_discovery
        #                         incident_result = await create_incident_from_discovery(
        #                             channel_id=channel_id,
        #                             user_id=user_id,
        #                             discovery_data=discovery_data,
        #                             property_id=meta_context.metadata.get("property_id"),
        #                         )
        # 
        #                         if incident_result.success:
        #                             incident_id = incident_result.data.get("incident_id")
        #                             context_updates["active_incident_id"] = incident_id
        #                             context_updates["stage"] = "detected"  # Incident created, move to detected
        #                             context_updates["discovery"] = {
        #                                 "is_active": False,
        #                                 "question_index": 0,
        #                                 "questions": [],
        #                                 "answers": {},
        #                                 "incident_id": None,
        #                             }
        #                             logger.info(f"✅ Created incident {incident_id} from discovery")
        #                             function_sent_user_message = True  # create_incident_from_discovery sends message
        #                         else:
        #                             logger.error(f"Failed to create incident from discovery: {incident_result.error}")
        #                     else:
        #                         # Traditional flow: incident exists, mark as discovery_complete
        #                         context_updates["stage"] = "discovery_complete"
        #                         logger.info("✅ Discovery complete, transitioning to discovery_complete stage")
        # 
        #                 # Apply all context updates
        #                 if context_updates:
        #                     meta_context = await context_manager.update_context(user_id, channel_id, context_updates)
        #                     logger.info(f"✅ Context updated: {list(context_updates.keys())}")
        # 
        #             # Check if we need multi-turn function calling
        #             next_action = orchestrator_output.context_updates.next_action
        #             if next_action and function_result.success:
        #                 logger.info(f"Multi-turn action requested: {next_action}")
        # 
        #                 # Call orchestrator again with function result
        #                 orchestrator_output_2 = await orchestrator.run(
        #                     user_message=f"Function '{orchestrator_output.function_call.name}' completed successfully. {next_action}",
        #                     meta_context=meta_context,
        #                     available_functions=available_functions,
        #                     function_result=function_result,
        #                 )
        # 
        #                 # Execute second function if requested
        #                 if orchestrator_output_2.function_call.name:
        #                     logger.info(f"Executing second function: {orchestrator_output_2.function_call.name}")
        # 
        #                     function_args_2 = {**orchestrator_output_2.function_call.arguments}
        # 
        #                     # NOTE: DO NOT auto-inject incident_id for start_discovery
        #                     # If orchestrator omits incident_id, it means pre-incident discovery (collect info before creating incident)
        #                     # Auto-injecting old incident_id would corrupt the discovery flow
        # 
        #                     function_result_2 = await execute_function(
        #                         function_name=orchestrator_output_2.function_call.name,
        #                         arguments=function_args_2,
        #                         context=function_context,
        #                     )
        # 
        #                     logger.info(f"Second function result: success={function_result_2.success}")
        # 
        #                     # Update context from second function
        #                     if function_result_2.success and function_result_2.data:
        #                         if "questions" in function_result_2.data:
        #                             await context_manager.update_context(
        #                                 user_id,
        #                                 channel_id,
        #                                 {
        #                                     "discovery": {
        #                                         "questions": function_result_2.data["questions"],
        #                                         "question_index": function_result_2.data.get("question_index", 0),
        #                                     },
        #                                     "stage": "discovery",
        #                                 },
        #                             )
        # 
        #                 # Use second orchestrator's response if available
        #                 if orchestrator_output_2.response_to_user:
        #                     orchestrator_output.response_to_user = orchestrator_output_2.response_to_user
        # 
        #         # 🚨 Handle special intents (garbage, errors, etc.)
        #         if orchestrator_output.intent in ["garbage_input", "off_topic"]:
        #             logger.info(f"🗑️ Garbage/off-topic input detected: {orchestrator_output.intent}")
        #             # Send friendly fallback message
        #             fallback_messages = {
        #                 "garbage_input": "I'm here to help with property maintenance issues. If you're experiencing a problem (leak, broken appliance, etc.), please describe it and I'll help you report it.",
        #                 "off_topic": "I'm focused on property maintenance. If you have a maintenance issue, I'm here to help report and track it.",
        #             }
        #             fallback_text = fallback_messages.get(orchestrator_output.intent, "I'm here to help with maintenance issues.")
        # 
        #             bot.send_ai_message(
        #                 channel_id=channel_id,
        #                 persona=meta_context.persona,
        #                 text=fallback_text,
        #                 metadata={"intent": orchestrator_output.intent},
        #             )
        # 
        #             return {
        #                 "status": "acknowledged",
        #                 "intent": orchestrator_output.intent,
        #                 "reason": "garbage_or_offtopic",
        #             }
        # 
        #         # Handle JSON parse errors
        #         if orchestrator_output.intent == "json_parse_error":
        #             logger.error(f"🚨 LLM JSON parse error: {orchestrator_output.reasoning}")
        #             # Don't send error to user, just log and return
        #             return {
        #                 "status": "error",
        #                 "intent": "json_parse_error",
        #                 "reason": "LLM output invalid JSON",
        #             }
        # 
        #         # PHASE OMEGA OBJECTIVE #8: FUNCTION-CALL OUTPUT GUARD
        #         # Send response to user if LLM provided one AND function didn't already send one
        #         if orchestrator_output.response_to_user and not function_sent_user_message:
        #             logger.info(f"Sending LLM response to user: {orchestrator_output.response_to_user[:100]}")
        # 
        #             response_metadata = {
        #                 "intent": orchestrator_output.intent,
        #                 "persona": meta_context.persona,
        #                 "stage": meta_context.stage,
        #             }
        # 
        #             bot.send_ai_message(
        #                 channel_id=channel_id,
        #                 persona=meta_context.persona,
        #                 text=orchestrator_output.response_to_user,
        #                 metadata=response_metadata,
        #             )
        # 
        #             # Append to conversation history
        #             await context_manager.append_message(
        #                 user_id,
        #                 channel_id,
        #                 "assistant",
        #                 orchestrator_output.response_to_user,
        #         )
        #
        # # 🚀 PHASE OMEGA: Record interaction for auto-evolving skills
        # try:
        #     from ..services.orchestrator import record_agent_interaction
        #
        #     if agent_enhanced_context:
        #         await record_agent_interaction(
        #             user_id=user_id,
        #             agent_type="multi_agent",
        #             user_message=message_text,
        #             agent_response=orchestrator_output.response_to_user or "",
        #             outcome="success" if orchestrator_output.function_call.name else "chat",
        #         )
        # except Exception as e:
        #     logger.error(f"Error recording interaction: {e}", exc_info=True)
        #
        # # Log performance
        # duration = (time.time() - start_time) * 1000
        # logger.info(f"Message processing completed in {duration:.2f}ms")
        #
        # # 🚨 CRITICAL FIX: Flush all pending context writes (batched for performance)
        # try:
        #     flushed_count = await context_manager.flush_pending_writes()
        #     if flushed_count > 0:
        #         logger.info(f"✅ Flushed {flushed_count} batched context writes")
        # except Exception as flush_error:
        #     logger.error(f"Failed to flush context writes: {flush_error}", exc_info=True)
        #
        # # 🚨 CRITICAL FIX: Save incident graph ONCE at end (prevents duplicate concurrent saves)
        # try:
        #     from ..services.incident_topic_graph import get_incident_graph
        #
        #     if meta_context.active_incident_id:
        #         incident_graph = get_incident_graph(user_id)
        #         # Only save if graph has nodes (prevents zero-node overwrites)
        #         if len(incident_graph.nodes) > 0:
        #             await asyncio.to_thread(incident_graph.save)
        #             logger.info(f"💾 Saved incident graph ({len(incident_graph.nodes)} nodes)")
        #         else:
        #             logger.debug("⏭️ Skipping graph save (no nodes)")
        # except Exception as graph_error:
        #     logger.error(f"Failed to save incident graph: {graph_error}", exc_info=True)
        #
        # return {
        #     "status": "success",
        #     "intent": orchestrator_output.intent,
        #     "function_executed": orchestrator_output.function_call.name,
        #     "duration_ms": duration,
        # }
        #
        # ============================================================================
        # END OLD FLOW
        # ============================================================================

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
            "version": "3.0-orchestrator-async",
            "model": orchestrator.model,
            "temperature": orchestrator.temperature,
            "architecture": "llm-driven-async-queue",
            "features": [
                "universal_orchestrator",
                "function_calling",
                "meta_context_management",
                "multi_turn_reasoning",
                "dynamic_intent_classification",
                "rate_limit_management",
                "async_task_queue",
                "load_shedding",
            ],
        }

    except Exception as e:
        logger.error(f"Error getting bot status: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


@router.get("/ai/rate-limits")
async def get_rate_limits():
    """Get current rate-limit status for all models"""
    try:
        from ..services.rate_limit_manager import get_rate_limit_manager

        rate_limiter = get_rate_limit_manager()
        all_quotas = rate_limiter.get_all_quotas()

        return {
            "status": "ok",
            "quotas": {
                model: {
                    "rpm_used": quota.rpm_used,
                    "rpm_limit": quota.rpm_limit,
                    "rpm_available": quota.rpm_available,
                    "tpm_used": quota.tpm_used,
                    "tpm_limit": quota.tpm_limit,
                    "tpm_available": quota.tpm_available,
                    "utilization_pct": round(quota.utilization_pct, 2),
                }
                for model, quota in all_quotas.items()
            },
        }

    except Exception as e:
        logger.error(f"Error getting rate limits: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


@router.get("/ai/queue-status")
async def get_queue_status():
    """Get current task queue status"""
    try:
        task_queue = get_task_queue()
        stats = task_queue.get_stats()

        return {
            "status": "ok",
            "queue_size": stats["queue_size"],
            "max_size": stats["max_size"],
            "workers": stats["workers"],
            "running": stats["running"],
            "utilization_pct": round(stats["utilization_pct"], 2),
            "stats": stats["stats"],
        }

    except Exception as e:
        logger.error(f"Error getting queue status: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


@router.get("/ai/health")
async def get_health():
    """Comprehensive health check including rate limits and queue"""
    try:
        from ..services.rate_limit_manager import get_rate_limit_manager

        orchestrator = get_orchestrator()
        rate_limiter = get_rate_limit_manager()
        task_queue = get_task_queue()

        all_quotas = rate_limiter.get_all_quotas()
        queue_stats = task_queue.get_stats()

        # Calculate overall health
        max_utilization = max(quota.utilization_pct for quota in all_quotas.values())
        queue_utilization = queue_stats["utilization_pct"]

        health_status = "healthy"
        if max_utilization > 95 or queue_utilization > 95:
            health_status = "critical"
        elif max_utilization > 80 or queue_utilization > 80:
            health_status = "warning"

        return {
            "status": health_status,
            "version": "3.0-async",
            "timestamp": time.time(),
            "orchestrator": {
                "model": orchestrator.model,
                "temperature": orchestrator.temperature,
            },
            "rate_limits": {
                "max_utilization_pct": round(max_utilization, 2),
                "models": {
                    model: {
                        "utilization_pct": round(quota.utilization_pct, 2),
                        "rpm_available": quota.rpm_available,
                        "tpm_available": quota.tpm_available,
                    }
                    for model, quota in all_quotas.items()
                },
            },
            "queue": {
                "size": queue_stats["queue_size"],
                "max_size": queue_stats["max_size"],
                "utilization_pct": round(queue_utilization, 2),
                "workers": queue_stats["workers"],
                "running": queue_stats["running"],
                "total_processed": queue_stats["stats"]["total_processed"],
                "total_failed": queue_stats["stats"]["total_failed"],
                "total_shed": queue_stats["stats"]["total_shed"],
            },
        }

    except Exception as e:
        logger.error(f"Error in health check: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
