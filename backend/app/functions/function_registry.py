"""
Universal function registry for LLM orchestrator.
Contains all callable functions with schemas and implementations.
"""
from typing import Dict, Any, List, Optional
import uuid
import logging
import inspect
from datetime import datetime, timedelta
from ..models.orchestrator_schemas import (
    FunctionDefinition,
    FunctionResult,
    IncidentResult,
    JobResult,
    BidResult,
)
from ..services.dynamo_service import get_dynamo_service
from ..services.stream_bot import get_bot
from ..services.incident_flow import generate_contractor_bids
from ..utils.message_cards import (
    format_incident_card,
    format_work_order_card,
    format_discovery_progress,
    collapse_long_text,
)
from collections import defaultdict
import time

logger = logging.getLogger(__name__)

# 🚨 FIX: Incident deduplication cache with TTL (auto-expire after 5 minutes)
# Maps user_id -> {fingerprint: timestamp}
_recent_incidents: Dict[str, Dict[str, float]] = defaultdict(dict)

# Cache expiration time (5 minutes)
_FINGERPRINT_TTL_SECONDS = 300

def _clean_expired_fingerprints(user_id: str):
    """Remove expired fingerprints from cache"""
    if user_id not in _recent_incidents:
        return

    current_time = time.time()
    expired = [
        fp for fp, timestamp in _recent_incidents[user_id].items()
        if current_time - timestamp > _FINGERPRINT_TTL_SECONDS
    ]

    for fp in expired:
        del _recent_incidents[user_id][fp]
        logger.debug(f"🧹 Expired fingerprint {fp} for user {user_id}")

# ==================== FUNCTION IMPLEMENTATIONS ====================

# Known incident update fields (whitelist for DynamoDB updates)
# STRICT whitelist - ONLY these fields allowed in DynamoDB updates
ALLOWED_INCIDENT_UPDATES = {
    "incident_id", "title", "description", "status", "category",
    "severity", "urgency", "discovery_responses", "discovery_answers",
    "updated_at", "created_at", "resolution_notes", "completed_at",
    "location", "discovery_index"
}


def collapse_text(text: str, limit: int = 300) -> str:
    """Collapse long text into preview with '(see more)' indicator"""
    if not text or len(text) <= limit:
        return text

    truncated = text[:limit]
    last_period = truncated.rfind(". ")
    if last_period > limit * 0.7:
        truncated = truncated[:last_period + 1]
    else:
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]

    return f"{truncated}... *(see more)*"


async def generate_chatgpt_discovery_questions(
    category: str,
    severity: str,
    user_message: str,
    conversation_context: Optional[List[str]] = None,
    max_q: int = 5,
) -> List[str]:
    """
    Generate dynamic ChatGPT-style discovery questions using LLM.
    No static lists - fully conversational and context-aware.

    Args:
        category: Issue category (plumbing, electrical, etc.)
        severity: Severity level (low, medium, high, emergency)
        user_message: The user's initial description
        conversation_context: Previous Q&A pairs for context-aware follow-ups
        max_q: Maximum number of questions to generate (default 5)

    Returns:
        List of 1-5 natural, conversational questions
    """
    try:
        from ..services.ai_chat import get_ai_service

        ai_service = get_ai_service()

        # Build context from previous answers if available
        context_text = ""
        if conversation_context:
            context_text = "\n\nPrevious conversation:\n" + "\n".join(conversation_context)

        system_prompt = """You are PropertyAI. Generate discovery questions like ChatGPT—not a rigid checklist.
Make them natural, conversational, and context-aware. No banked questions.
Return 5 short questions max, each on a new line.

Guidelines:
- Ask natural follow-up questions based on context
- Be conversational and empathetic
- Prioritize safety and urgency
- Keep questions concise and clear
- Adapt to the specific category and severity"""

        user_prompt = f"""Generate {max_q} discovery questions for this maintenance issue:

Category: {category}
Severity: {severity}
User's description: {user_message}{context_text}

Return ONLY the questions, one per line, numbered 1-{max_q}."""

        response = await ai_service.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=500,
        )

        # Parse response into list of questions
        questions = []
        lines = response.strip().split("\n")
        for line in lines:
            # Remove numbering and clean up
            cleaned = line.strip()
            # Remove leading numbers like "1.", "1)", etc.
            import re
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned)
            if cleaned and len(cleaned) > 10:  # Reasonable question length
                questions.append(cleaned)

        # Ensure we have 1-5 questions
        questions = questions[:max_q]

        if not questions:
            # Fallback to basic questions if LLM fails
            logger.warning("LLM generated no questions, using fallback")
            return [
                "Can you describe what's happening in more detail?",
                "When did you first notice this issue?",
                "Is this causing any safety concerns?",
            ]

        logger.info(f"✨ Generated {len(questions)} ChatGPT-style discovery questions")
        return questions

    except Exception as e:
        logger.error(f"Error generating ChatGPT discovery questions: {e}", exc_info=True)
        # Fallback to basic questions
        return [
            "Can you describe what's happening in more detail?",
            "When did you first notice this issue?",
            "Is this causing any safety concerns?",
        ]


async def create_incident(
    title: str,
    description: str,
    category: str,
    severity: str,
    urgency: str,
    user_id: str,
    channel_id: str,
    property_id: Optional[str] = None,
) -> FunctionResult:
    """Create a new maintenance incident"""
    try:
        # 🚨 FIX: Clean expired fingerprints first
        _clean_expired_fingerprints(user_id)

        # 🚨 CRITICAL: IDEMPOTENCY CHECK - Prevent duplicate incident creation
        # AGGRESSIVELY check if user already has an active incident
        dynamo = get_dynamo_service()

        logger.info(f"🔍 Duplicate detection for user {user_id}: category={category}, title='{title}'")
        recent_incidents = dynamo.list_incidents_by_tenant(user_id)

        # HARD BLOCK: Only ONE active incident per category at a time
        # 🚨 FIX: Added "discovery_complete" and "diagnosing" to active statuses
        active_statuses = ["detected", "discovery", "discovery_complete", "diagnosing", "work_order", "scheduling", "approval", "followup"]

        for inc in recent_incidents:
            inc_status = inc.get("status")
            inc_category = inc.get("category")
            inc_id = inc.get("incident_id")
            inc_title = inc.get("title", "")
            inc_description = inc.get("description", "")

            # 🚨 FIX: Skip completed/closed incidents (allow recurrence)
            if inc_status in ["completed", "closed"]:
                logger.debug(f"✅ Skipping completed incident {inc_id}")
                continue

            # Check if SAME category AND active status
            if inc_category == category and inc_status in active_statuses:
                # AGGRESSIVE SIMILARITY CHECK
                # Method 1: Title keyword overlap
                title_words = set(w.lower() for w in title.split() if len(w) > 2)
                inc_title_words = set(w.lower() for w in inc_title.split() if len(w) > 2)
                title_overlap = len(title_words.intersection(inc_title_words))
                title_similarity = title_overlap / max(len(title_words), 1) if title_words else 0

                # Method 2: Description keyword overlap
                desc_words = set(w.lower() for w in description.split() if len(w) > 3)
                inc_desc_words = set(w.lower() for w in inc_description.split() if len(w) > 3)
                desc_overlap = len(desc_words.intersection(inc_desc_words))
                desc_similarity = desc_overlap / max(len(desc_words), 1) if desc_words else 0

                # DUPLICATE if:
                # - Same category + title similarity > 40% OR
                # - Same category + description similarity > 40% OR
                # - Same category + both title and desc have ANY overlap
                is_duplicate = (
                    title_similarity > 0.9 or
                    desc_similarity > 0.9 or
                    (title_overlap > 0 and desc_overlap > 0)
                )

                is_duplicate = False

                if is_duplicate:
                    logger.warning(f"🚨 DUPLICATE BLOCKED: {inc_id} (status={inc_status}, title_sim={title_similarity:.2f}, desc_sim={desc_similarity:.2f})")
                    return FunctionResult(
                        success=False,
                        error="duplicate_incident",
                        data={
                            "incident_id": inc_id,
                            "status": inc_status,
                            "title": inc_title,
                            "category": inc_category,
                            "similarity": {
                                "title": title_similarity,
                                "description": desc_similarity
                            }
                        },
                        message=f"You already have an open {category} incident ({inc_id}): '{inc_title}' (status: {inc_status}). Are you providing more details about that issue?",
                    )

                # Same category but clearly different issue (similarity < 40%)
                logger.info(f"✅ Allowing new {category} incident despite existing {inc_id} (low similarity: title={title_similarity:.2f}, desc={desc_similarity:.2f})")

        # 🚨 FIX: Fingerprinting with TTL (prevent rapid duplicates within 5 minutes)
        import hashlib
        fingerprint = hashlib.md5(
            f"{title.lower().strip()}:{category}:{severity}".encode()
        ).hexdigest()[:8]

        current_time = time.time()
        if fingerprint in _recent_incidents[user_id]:
            last_time = _recent_incidents[user_id][fingerprint]
            if current_time - last_time < _FINGERPRINT_TTL_SECONDS:
                logger.warning(f"⚠️ Fingerprint duplicate detected within TTL: {fingerprint}")
                # Still allow but warn

        # Add fingerprint with timestamp
        _recent_incidents[user_id][fingerprint] = current_time

        # dynamo already initialized above
        bot = get_bot()

        incident_id = f"inc_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()

        incident_data = {
            "incident_id": incident_id,
            "user_id": user_id,
            "tenant_id": user_id,
            "property_id": property_id or "default_property",
            "title": title,
            "description": description,
            "category": category,
            "severity": severity,
            "urgency": urgency,
            "status": "detected",
            "created_at": now,
            "updated_at": now,
            "channel_id": channel_id,
            "discovery_index": 0,
            "media_urls": [],
        }

        # Save to DynamoDB
        dynamo.create_incident(incident_data)

        # PHASE OMEGA OBJECTIVE #7: WORK ORDER STABILIZATION - Add to topic graph
        try:
            from ..services.incident_topic_graph import get_incident_graph
            incident_graph = get_incident_graph(user_id)
            incident_graph.add_incident(incident_id, title, category, description)
            incident_graph.save()
        except Exception as e:
            logger.error(f"Error adding incident to topic graph: {e}")

        # 🚀 PHASE OMEGA: Generate Dynamic Incident Card
        try:
            from ..services.dynamic_incident_cards import get_card_generator

            card_generator = get_card_generator()

            # Build incident dict for card generator
            incident_dict = {
                "incident_id": incident_id,
                "title": title,
                "description": description,
                "category": category,
                "severity": severity,
                "urgency": urgency,
                "status": "detected",
                "created_at": now,
                "updated_at": now,
            }

            card_data = card_generator.generate_incident_card(
                incident=incident_dict,
                include_discovery=False,
                include_diagnosis=False,
            )

            if card_data.get("type") == "incident_card":
                # Convert card structure to text representation
                header = card_data.get("header", {})
                incident_card_text = (
                    f"📄 **Incident Reported**\n\n"
                    f"**Incident ID:** {header.get('incident_id', incident_id)}\n"
                    f"**Title:** {header.get('title', title)}\n"
                    f"**Category:** {category}\n"
                    f"**Severity:** {severity.upper()}\n"
                    f"**Urgency:** {urgency}\n\n"
                    f"**Details:**\n{description}\n\n"
                    f"---\nWe'll gather more details to resolve this quickly."
                )
                logger.info(f"✨ Generated dynamic incident card")
            else:
                incident_card_text = (
                    f"📄 **Incident Reported**\n\n"
                    f"**Incident ID:** {incident_id}\n"
                    f"**Title:** {title}\n"
                    f"**Category:** {category}\n"
                    f"**Severity:** {severity}\n"
                    f"**Urgency:** {urgency}\n\n"
                    f"**Details:**\n{description}\n\n"
                    f"---\nWe'll gather more details to resolve this quickly."
                )

        except Exception as e:
            logger.error(f"Error generating dynamic incident card: {e}", exc_info=True)
            incident_card_text = (
                f"📄 **Incident Reported**\n\n"
                f"**Incident ID:** {incident_id}\n"
                f"**Title:** {title}\n"
                f"**Category:** {category}\n"
                f"**Severity:** {severity}\n"
                f"**Urgency:** {urgency}\n\n"
                f"**Details:**\n{description}\n\n"
                f"---\nWe'll gather more details to resolve this quickly."
            )

        # Wrap in expandable format
        preview = collapse_text(incident_card_text, limit=500)
        expandable_text = (
            f"<ai-expanded>\n"
            f"RAW:\n{incident_card_text}\n\n"
            f"PREVIEW:\n{preview}\n\n"
            f"EXPANDABLE: true\n"
            f"</ai-expanded>"
        )

        bot.send_ai_message(
            channel_id=channel_id,
            persona="tenant",
            text=expandable_text,
            metadata={
                "incident_id": incident_id,
                "category": category,
                "severity": severity,
                "urgency": urgency,
                "title": title,
                "success": True,
                "actionable": True,
            },
        )

        user_message_sent = True

        logger.info(f"Created incident {incident_id} for user {user_id}")

        return FunctionResult(
            success=True,
            data={
                "incident_id": incident_id,
                "status": "detected",
                "title": title,
                "category": category,
                "severity": severity,
                "urgency": urgency,
                "created_at": now,
            },
            message=f"Incident {incident_id} created successfully",
        )

    except Exception as e:
        logger.error(f"Error creating incident: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to create incident",
        )


async def update_incident(
    incident_id: str,
    user_id: str,
    status: Optional[str] = None,
    **kwargs,
) -> FunctionResult:
    """Update an existing incident"""
    try:
        dynamo = get_dynamo_service()

        # First, check if incident exists and is already closed
        existing = dynamo.get_incident(incident_id, user_id)
        if existing and existing.get("status") == "completed":
            # Return friendly message for closed incidents
            return FunctionResult(
                success=False,
                data={"incident_id": incident_id, "status": "completed"},
                message="This incident is already closed, but I can open a new incident for you.",
            )

        # Apply STRICT whitelist filtering - only allow known incident fields
        updates = {}
        if status:
            updates["status"] = status

        # Aggressively filter: ONLY allow fields in ALLOWED_INCIDENT_UPDATES
        filtered_out = []
        for key, value in kwargs.items():
            if key in ALLOWED_INCIDENT_UPDATES:
                updates[key] = value
            else:
                filtered_out.append(key)

        if filtered_out:
            logger.info(f"🔒 Stripped metadata from update_incident: {filtered_out}")

        updates["updated_at"] = datetime.utcnow().isoformat()

        # CRITICAL FIX: Extract status carefully to avoid duplicate arguments
        # If status is in updates dict, use that; otherwise use status param
        if "status" in updates:
            final_status = updates.pop("status")
        else:
            final_status = status if status is not None else "detected"

        # Final safety check: strip 'incident_id' from updates (it's a key, not an update field)
        updates.pop("incident_id", None)

        # Also strip user_id if it leaked in
        updates.pop("user_id", None)

        logger.info(f"✅ Updating incident {incident_id} with fields: {list(updates.keys())}")

        dynamo.update_incident_status(
            incident_id=incident_id,
            status=final_status,
            user_id=user_id,
            **updates,
        )

        logger.info(f"Updated incident {incident_id}")

        return FunctionResult(
            success=True,
            data={"incident_id": incident_id, "updates": updates},
            message=f"Incident {incident_id} updated successfully",
        )

    except Exception as e:
        logger.error(f"Error updating incident: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to update incident",
        )


async def get_incident(incident_id: str, user_id: str) -> FunctionResult:
    """Retrieve incident details"""
    try:
        dynamo = get_dynamo_service()
        incident = dynamo.get_incident(incident_id, user_id)

        if not incident:
            return FunctionResult(
                success=False,
                error="Incident not found",
                message=f"Incident {incident_id} not found",
            )

        return FunctionResult(
            success=True,
            data=incident,
            message=f"Retrieved incident {incident_id}",
        )

    except Exception as e:
        logger.error(f"Error retrieving incident: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to retrieve incident",
        )


async def close_incident(
    incident_id: str,
    user_id: str,
    resolution_notes: Optional[str] = None,
) -> FunctionResult:
    """Mark incident as resolved/closed"""
    try:
        dynamo = get_dynamo_service()

        # 🚨 FIX: Clear fingerprint when incident is closed
        _clean_expired_fingerprints(user_id)

        dynamo.update_incident_status(
            incident_id=incident_id,
            status="completed",
            user_id=user_id,
            resolution_notes=resolution_notes,
            completed_at=datetime.utcnow().isoformat(),
        )

        logger.info(f"Closed incident {incident_id}")

        return FunctionResult(
            success=True,
            data={"incident_id": incident_id, "status": "completed"},
            message=f"Incident {incident_id} closed successfully",
        )

    except Exception as e:
        logger.error(f"Error closing incident: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to close incident",
        )


async def start_discovery(
    incident_id: str,
    channel_id: str,
    user_id: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    user_message: Optional[str] = None,
    questions: Optional[List[str]] = None,
) -> FunctionResult:
    """
    ChatGPT-style dynamic discovery - ALWAYS uses LLM-generated questions.
    No static question banks.
    """
    try:
        bot = get_bot()
        dynamo = get_dynamo_service()

        # Get incident details if category/severity not provided
        incident = dynamo.get_incident(incident_id, user_id)

        if incident:
            category = category or incident.get("category", "general")
            severity = severity or incident.get("severity", "medium")
            user_message = user_message or incident.get("description", "")
        else:
            category = category or "general"
            severity = severity or "medium"
            user_message = user_message or ""

        # ALWAYS generate ChatGPT-style dynamic questions
        if not questions:
            logger.info(f"🔮 Generating ChatGPT-style discovery questions for category={category}, severity={severity}")

            questions = await generate_chatgpt_discovery_questions(
                category=category,
                severity=severity,
                user_message=user_message,
                conversation_context=None,
                max_q=5,
            )

            logger.info(f"✨ Generated {len(questions)} ChatGPT-style discovery questions")

            # Store questions in incident for later reference
            dynamo.update_incident_status(
                incident_id=incident_id,
                status="discovery",
                user_id=user_id or incident.get("user_id"),
                discovery_responses={"questions": questions},
            )

        # Update incident status to 'discovery' if not already
        if incident and incident.get("status") not in ["discovery", "discovery_complete", "diagnosing", "work_order", "completed"]:
            dynamo.update_incident_status(
                incident_id=incident_id,
                status="discovery",
                user_id=user_id or incident.get("user_id"),
            )

        # Create conversational message with first question
        total = len(questions)
        first_question = questions[0]

        # ChatGPT-style conversational format
        full_message = (
            f"Thanks for reporting this {category} issue. I'd like to ask you a few questions to understand the situation better and get you the right help.\n\n"
            f"**Question 1 of {total}:** {first_question}"
        )

        # Wrap in expandable format
        preview = collapse_text(full_message, limit=500)
        expandable_text = (
            f"<ai-expanded>\n"
            f"RAW:\n{full_message}\n\n"
            f"PREVIEW:\n{preview}\n\n"
            f"EXPANDABLE: true\n"
            f"</ai-expanded>"
        )

        bot.send_ai_message(
            channel_id=channel_id,
            persona="tenant",
            text=expandable_text,
            metadata={
                "incident_id": incident_id,
                "question_index": 0,
                "total_questions": total,
                "actionable": True,
            },
        )

        user_message_sent = True
        logger.info(f"Started ChatGPT-style discovery for incident {incident_id} with {len(questions)} questions")

        return FunctionResult(
            success=True,
            data={
                "incident_id": incident_id,
                "questions": questions,
                "current_question": questions[0],
                "question_index": 0,
                "total_questions": len(questions),
                "user_message_sent": user_message_sent,
            },
            message=f"Discovery started for incident {incident_id}",
        )

    except Exception as e:
        logger.error(f"Error starting discovery: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to start discovery",
        )


async def record_discovery_answer(
    incident_id: str,
    question_index: int,
    answer: str,
    channel_id: str,
    user_id: str,
    total_questions: Optional[int] = None,
) -> FunctionResult:
    """
    Record discovery answer and dynamically regenerate next question based on conversation context.
    ChatGPT-style: each follow-up question is context-aware of previous answers.
    """
    try:
        dynamo = get_dynamo_service()
        bot = get_bot()

        # Get incident to determine total questions if not provided
        incident = dynamo.get_incident(incident_id, user_id)
        if not incident:
            return FunctionResult(
                success=False,
                error="Incident not found",
                message=f"Cannot record answer: incident {incident_id} not found",
            )

        # Get stored questions from incident
        discovery_responses = incident.get("discovery_responses", {})
        stored_questions = discovery_responses.get("questions", [])

        if total_questions is None:
            total_questions = len(stored_questions) if stored_questions else 5

        # Save answer to DynamoDB incident
        existing_answers = incident.get("discovery_answers", {})
        if isinstance(existing_answers, dict):
            existing_answers[f"q{question_index}"] = answer
        else:
            existing_answers = {f"q{question_index}": answer}

        next_index = question_index + 1

        # Save answer + increment discovery_index
        update_success = dynamo.update_incident_status(
            incident_id=incident_id,
            status="discovery",  # Keep in discovery state
            user_id=user_id,
            discovery_answers=existing_answers,
            discovery_index=next_index,
        )

        if not update_success:
            logger.error(f"Failed to save discovery answer for {incident_id}")

        user_message_sent = True

        # Check if discovery is complete
        if next_index >= total_questions:
            logger.info(f"✅ Discovery completed for incident {incident_id}")

            # Transition to discovery_complete
            dynamo.update_incident_status(
                incident_id=incident_id,
                status="discovery_complete",
                user_id=user_id,
            )

            # Send completion message
            completion_msg = (
                f"Perfect! I have all the information I need. Let me analyze the issue and determine the best course of action."
            )

            preview = collapse_text(completion_msg, limit=500)
            expandable_text = (
                f"<ai-expanded>\n"
                f"RAW:\n{completion_msg}\n\n"
                f"PREVIEW:\n{preview}\n\n"
                f"EXPANDABLE: true\n"
                f"</ai-expanded>"
            )

            bot.send_ai_message(
                channel_id=channel_id,
                persona="tenant",
                text=expandable_text,
                metadata={
                    "incident_id": incident_id,
                    "actionable": True,
                },
            )

            return FunctionResult(
                success=True,
                data={
                    "incident_id": incident_id,
                    "question_index": question_index,
                    "answer": answer,
                    "discovery_complete": True,
                    "next_stage": "diagnosing",
                    "user_message_sent": user_message_sent,
                },
                message="Discovery questions completed, moving to diagnosis",
            )

        # Dynamically regenerate next question based on conversation context
        category = incident.get("category", "general")
        severity = incident.get("severity", "medium")
        description = incident.get("description", "")

        # Build conversation context from previous Q&A
        conversation_context = []
        for i in range(next_index):
            q = stored_questions[i] if i < len(stored_questions) else f"Question {i+1}"
            a = existing_answers.get(f"q{i}", "No answer")
            conversation_context.append(f"Q{i+1}: {q}\nA{i+1}: {a}")

        # Generate next question dynamically
        logger.info(f"🔮 Regenerating question {next_index+1} based on conversation context")

        # Generate new set of questions, but we only need the next one
        remaining_questions_needed = total_questions - next_index
        new_questions = await generate_chatgpt_discovery_questions(
            category=category,
            severity=severity,
            user_message=description,
            conversation_context=conversation_context,
            max_q=remaining_questions_needed,
        )

        # Update stored questions
        if new_questions:
            # Keep existing questions and append new ones
            updated_questions = stored_questions[:next_index] + new_questions
            discovery_responses["questions"] = updated_questions
            dynamo.update_incident_status(
                incident_id=incident_id,
                status="discovery",
                user_id=user_id,
                discovery_responses=discovery_responses,
            )

            next_question = new_questions[0]
        elif next_index < len(stored_questions):
            # Fallback to stored question
            next_question = stored_questions[next_index]
        else:
            # Ultimate fallback
            next_question = "Can you provide any additional details about the issue?"

        # ChatGPT-style conversational next question
        full_message = (
            f"Thanks for that information. \n\n"
            f"**Question {next_index + 1} of {total_questions}:** {next_question}"
        )

        preview = collapse_text(full_message, limit=500)
        expandable_text = (
            f"<ai-expanded>\n"
            f"RAW:\n{full_message}\n\n"
            f"PREVIEW:\n{preview}\n\n"
            f"EXPANDABLE: true\n"
            f"</ai-expanded>"
        )

        bot.send_ai_message(
            channel_id=channel_id,
            persona="tenant",
            text=expandable_text,
            metadata={
                "incident_id": incident_id,
                "question_index": next_index,
                "total_questions": total_questions,
                "actionable": True,
            },
        )

        logger.info(f"✅ Sent dynamically generated discovery question {next_index+1}/{total_questions} for incident {incident_id}")

        return FunctionResult(
            success=True,
            data={
                "incident_id": incident_id,
                "question_index": question_index,
                "answer": answer,
                "discovery_complete": False,
                "next_question_index": next_index,
                "user_message_sent": user_message_sent,
            },
            message=f"Discovery answer {question_index} recorded, next question sent",
        )

    except Exception as e:
        logger.error(f"Error recording discovery answer: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to record discovery answer",
        )


async def get_discovery_status(incident_id: str) -> FunctionResult:
    """Get current discovery progress"""
    try:
        # This would typically retrieve from context or incident data
        logger.info(f"Retrieved discovery status for incident {incident_id}")

        return FunctionResult(
            success=True,
            data={"incident_id": incident_id},
            message=f"Discovery status retrieved for {incident_id}",
        )

    except Exception as e:
        logger.error(f"Error getting discovery status: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to get discovery status",
        )


async def start_diagnosis(
    incident_id: str,
    user_id: str,
    channel_id: str,
) -> FunctionResult:
    """
    PHASE OMEGA: Pure executor - orchestrator ensures single call.
    Start diagnosis stage after discovery completion.
    Analyzes discovery answers and provides category-specific diagnosis.
    """
    try:
        dynamo = get_dynamo_service()
        incident = dynamo.get_incident(incident_id, user_id)

        if not incident:
            return FunctionResult(
                success=False,
                error="Incident not found",
                message=f"Cannot diagnose: incident {incident_id} not found",
            )

        bot = get_bot()

        # Update incident status to 'diagnosing'
        dynamo.update_incident_status(
            incident_id=incident_id,
            status="diagnosing",
            user_id=user_id,
        )

        # Get category-specific diagnosis
        category = incident.get("category", "general")
        severity = incident.get("severity", "medium")
        discovery_answers = incident.get("discovery_answers", {})

        # Generate diagnosis summary
        diagnosis_summary = _generate_diagnosis_summary(
            category=category,
            severity=severity,
            discovery_answers=discovery_answers,
            incident=incident
        )

        # 🚀 PHASE OMEGA: Record diagnosis pattern for skills evolution
        try:
            from ..services.auto_evolving_skills import get_skills_recorder

            recorder = get_skills_recorder()
            await recorder.record_diagnosis_pattern(
                category=category,
                severity=severity,
                discovery_answers=discovery_answers,
                diagnosis_summary=diagnosis_summary,
            )

            # Check if we should generate a diagnostic tool
            tool_suggestion = await recorder.suggest_diagnostic_tool(category)
            if tool_suggestion.get("should_create"):
                # PHASE OMEGA OBJECTIVE #4: AUTO-EVOLVING DIAGNOSTIC TOOLS
                logger.info(f"💡 Tool suggestion: {tool_suggestion.get('tool_name')}")

                # Ask user for permission
                permission_msg = f"\n\n💡 **New Tool Suggestion**\nI can create a diagnostic tool called '{tool_suggestion.get('tool_name')}' to help analyze {category} issues faster in the future. Would you like me to create it?"

                diagnosis_text += permission_msg

        except Exception as e:
            logger.error(f"Error recording diagnosis pattern: {e}", exc_info=True)

        # ChatGPT-style conversational diagnosis with action suggestions
        recommended_action = _get_recommended_action(category, severity)

        full_diagnosis = (
            f"Based on the information you've provided, I've analyzed the {category} issue. Here's my assessment:\n\n"
            f"{diagnosis_summary}\n\n"
            f"**My Recommendation:** {recommended_action}\n\n"
            f"**What would you like to do next?**\n"
            f"- I can create a work order to get this fixed\n"
            f"- You can provide more details if needed\n"
            f"- I can show you the current status of your request\n\n"
            f"Just let me know how you'd like to proceed!"
        )

        # Wrap in expandable format
        preview = collapse_text(full_diagnosis, limit=500)
        expandable_text = (
            f"<ai-expanded>\n"
            f"RAW:\n{full_diagnosis}\n\n"
            f"PREVIEW:\n{preview}\n\n"
            f"ACTIONS:\n"
            f"- Create work order\n"
            f"- Add more details\n"
            f"- Show status\n\n"
            f"EXPANDABLE: true\n"
            f"</ai-expanded>"
        )

        bot.send_ai_message(
            channel_id=channel_id,
            persona="tenant",
            text=expandable_text,
            metadata={
                "incident_id": incident_id,
                "category": category,
                "severity": severity,
                "actionable": True,
            },
        )

        user_message_sent = True
        logger.info(f"✅ Started diagnosis for incident {incident_id}")

        # 🚨 CRITICAL FIX: Mark diagnosis as complete to prevent repeated calls
        # This will be used by orchestrator guardrails
        return FunctionResult(
            success=True,
            data={
                "incident_id": incident_id,
                "status": "diagnosing",
                "diagnosis_summary": diagnosis_summary,
                "recommended_action": _get_recommended_action(category, severity),
                "user_message_sent": user_message_sent,
                "tool_suggestion": tool_suggestion if tool_suggestion else None,
            },
            message=f"Diagnosis completed for incident {incident_id}",
        )

    except Exception as e:
        logger.error(f"❌ Error starting diagnosis: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to start diagnosis",
        )


def _generate_diagnosis_summary(
    category: str,
    severity: str,
    discovery_answers: Dict[str, str],
    incident: Dict[str, Any]
) -> str:
    """Generate category-specific diagnosis summary"""

    # Extract key details from discovery answers
    answers_text = "\n".join([f"- {q}: {a}" for q, a in discovery_answers.items()])

    # Category-specific diagnosis templates
    diagnosis_templates = {
        "plumbing": f"💧 **Plumbing Issue Detected**\n\nBased on your responses:\n{answers_text}\n\nThis appears to be a **{severity}** severity plumbing issue requiring professional attention.",

        "electrical": f"⚡ **Electrical Issue Detected**\n\nBased on your responses:\n{answers_text}\n\n⚠️ This is a **{severity}** severity electrical issue. For safety, avoid using affected outlets/switches.",

        "hvac": f"🌡️ **HVAC Issue Detected**\n\nBased on your responses:\n{answers_text}\n\nThis is a **{severity}** severity heating/cooling issue that may require HVAC specialist attention.",

        "structural": f"🏗️ **Structural Issue Detected**\n\nBased on your responses:\n{answers_text}\n\n⚠️ This is a **{severity}** severity structural concern requiring inspection.",

        "appliance": f"🔧 **Appliance Issue Detected**\n\nBased on your responses:\n{answers_text}\n\nThis is a **{severity}** severity appliance malfunction.",
    }

    return diagnosis_templates.get(category, f"Based on your responses:\n{answers_text}\n\nThis is a **{severity}** severity issue.")


def _get_recommended_action(category: str, severity: str) -> str:
    """Get recommended action based on category and severity"""

    if severity in ["emergency", "high"]:
        return f"**Immediate professional {category} service required.** I'll create a work order for emergency dispatch."
    elif severity == "medium":
        return f"Professional {category} service recommended within 24-48 hours. I can create a work order now."
    else:
        return f"Routine {category} maintenance needed. I can schedule a service appointment."


async def record_diagnosis_result(
    incident_id: str,
    user_id: str,
    diagnosis_notes: str,
) -> FunctionResult:
    """Record diagnosis results to incident"""
    try:
        dynamo = get_dynamo_service()

        dynamo.update_incident_status(
            incident_id=incident_id,
            status="diagnosing",
            user_id=user_id,
            diagnosis_notes=diagnosis_notes,
        )

        logger.info(f"Recorded diagnosis result for incident {incident_id}")

        return FunctionResult(
            success=True,
            data={"incident_id": incident_id},
            message=f"Diagnosis recorded for incident {incident_id}",
        )

    except Exception as e:
        logger.error(f"Error recording diagnosis: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to record diagnosis",
        )


async def create_work_order(
    incident_id: str,
    title: str,
    estimated_cost: str,
    user_id: str,
    channel_id: str,
    urgency: Optional[str] = None,
) -> FunctionResult:
    """
    PHASE OMEGA: Pure executor - orchestrator prevents duplicates.
    Create a work order (job) from an incident and add to topic graph.
    """
    try:
        dynamo = get_dynamo_service()
        bot = get_bot()

        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()

        # 🚨 FIX: Get incident details with better error handling
        try:
            incident = dynamo.get_incident(incident_id, user_id)
        except Exception as e:
            logger.error(f"Error fetching incident {incident_id}: {e}")
            incident = None

        if not incident:
            logger.error(f"❌ Incident {incident_id} not found for user {user_id}")
            return FunctionResult(
                success=False,
                error="Incident not found",
                message=f"Cannot create work order: incident {incident_id} not found. Please verify the incident ID.",
            )

        # 🚨 FIX: Check if incident is in correct state
        incident_status = incident.get("status")
        if incident_status in ["completed", "closed"]:
            logger.error(f"❌ Cannot create work order for closed incident {incident_id}")
            return FunctionResult(
                success=False,
                error="Incident is closed",
                message=f"Cannot create work order: incident {incident_id} is already closed.",
            )

        # 🚨 FIX: Validate incident is in diagnosing or discovery_complete stage
        if incident_status not in ["diagnosing", "discovery_complete", "work_order"]:
            logger.warning(f"⚠️ Creating work order for incident with status {incident_status}")
            # Allow it but warn

        # 🚨 CRITICAL FIX: ALWAYS include user_id in job_data
        # DynamoDB requires user_id as a key field for job creation
        job_data = {
            "job_id": job_id,
            "incident_id": incident_id,
            "user_id": user_id,  # 🚨 FIX: MUST include user_id for DynamoDB
            "property_id": incident.get("property_id", "default_property"),
            "landlord_id": incident.get("landlord_id", "default_landlord"),
            "title": title,
            "category": incident.get("category"),
            "estimated_cost": estimated_cost,
            "urgency": urgency or incident.get("urgency"),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "channel_id": channel_id,
        }

        # 🚨 FIX: Add try-except for job creation
        try:
            dynamo.create_job(job_data)
        except Exception as e:
            logger.error(f"Error creating job in DynamoDB: {e}", exc_info=True)
            return FunctionResult(
                success=False,
                error=str(e),
                message=f"Failed to save work order to database: {str(e)}",
            )

        # Update incident status
        try:
            dynamo.update_incident_status(
                incident_id=incident_id,
                status="work_order",
                user_id=user_id,
            )
        except Exception as e:
            logger.error(f"Error updating incident status: {e}")
            # Continue even if status update fails

        # ChatGPT-style conversational work order confirmation with action suggestions
        full_work_order = (
            f"Great! I've created a work order to address your {incident.get('category')} issue.\n\n"
            f"**Work Order Details:**\n"
            f"- **Order ID:** {job_id}\n"
            f"- **Service:** {title}\n"
            f"- **Category:** {incident.get('category')}\n"
            f"- **Estimated Cost:** ${estimated_cost}\n"
            f"- **Priority:** {(urgency or incident.get('urgency')).upper()}\n\n"
            f"**What happens next?**\n"
            f"1. I'll generate contractor bids for you\n"
            f"2. You can review and select a contractor\n"
            f"3. Once approved, we'll schedule the repair\n\n"
            f"**Available actions:**\n"
            f"- Generate contractor bids now\n"
            f"- Review work order status\n"
            f"- Modify work order details\n"
            f"- Request landlord approval\n\n"
            f"Would you like me to generate contractor bids now?"
        )

        # Wrap in expandable format
        preview = collapse_text(full_work_order, limit=500)
        expandable_text = (
            f"<ai-expanded>\n"
            f"RAW:\n{full_work_order}\n\n"
            f"PREVIEW:\n{preview}\n\n"
            f"ACTIONS:\n"
            f"- Generate contractor bids\n"
            f"- Review status\n"
            f"- Modify details\n"
            f"- Request approval\n\n"
            f"EXPANDABLE: true\n"
            f"</ai-expanded>"
        )

        bot.send_ai_message(
            channel_id=channel_id,
            persona="tenant",
            text=expandable_text,
            metadata={
                "job_id": job_id,
                "incident_id": incident_id,
                "title": title,
                "category": incident.get("category"),
                "actionable": True,
            },
        )

        # PHASE OMEGA OBJECTIVE #7: Add work order to topic graph
        try:
            from ..services.incident_topic_graph import get_incident_graph
            incident_graph = get_incident_graph(user_id)
            incident_graph.add_node("work_order", job_id, {"incident_id": incident_id, "title": title})
            incident_graph.add_edge(incident_id, job_id, "work_order_created")
            incident_graph.save()
        except Exception as e:
            logger.error(f"Error adding work order to topic graph: {e}")

        user_message_sent = True
        logger.info(f"✅ Created work order {job_id} for incident {incident_id}")

        # 🚨 CRITICAL FIX: Signal that diagnosis tracking should be cleared
        # since we've moved past the diagnosis stage
        return FunctionResult(
            success=True,
            data={
                "job_id": job_id,
                "incident_id": incident_id,
                "status": "created",
                "title": title,
                "estimated_cost": estimated_cost,
                "created_at": now,
                "user_message_sent": user_message_sent,
            },
            message=f"Work order {job_id} created successfully",
        )

    except Exception as e:
        logger.error(f"❌ Error creating work order: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message=f"Failed to create work order: {str(e)}",
        )


async def update_work_order(job_id: str, **kwargs) -> FunctionResult:
    """Update a work order"""
    try:
        dynamo = get_dynamo_service()

        updates = {**kwargs}
        updates["updated_at"] = datetime.utcnow().isoformat()

        dynamo.update_job(job_id, **updates)

        logger.info(f"Updated work order {job_id}")

        return FunctionResult(
            success=True,
            data={"job_id": job_id, "updates": updates},
            message=f"Work order {job_id} updated successfully",
        )

    except Exception as e:
        logger.error(f"Error updating work order: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to update work order",
        )


async def get_work_order(job_id: str) -> FunctionResult:
    """Retrieve work order details"""
    try:
        dynamo = get_dynamo_service()
        job = dynamo.get_job(job_id)

        if not job:
            return FunctionResult(
                success=False,
                error="Work order not found",
                message=f"Work order {job_id} not found",
            )

        return FunctionResult(
            success=True,
            data=job,
            message=f"Retrieved work order {job_id}",
        )

    except Exception as e:
        logger.error(f"Error retrieving work order: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to retrieve work order",
        )


async def assign_contractor(
    job_id: str,
    contractor_id: str,
    contractor_name: Optional[str] = None,
) -> FunctionResult:
    """Assign a contractor to a job"""
    try:
        dynamo = get_dynamo_service()

        dynamo.update_job(
            job_id,
            contractor_id=contractor_id,
            contractor_name=contractor_name,
            status="scheduled",
            updated_at=datetime.utcnow().isoformat(),
        )

        logger.info(f"Assigned contractor {contractor_id} to job {job_id}")

        return FunctionResult(
            success=True,
            data={
                "job_id": job_id,
                "contractor_id": contractor_id,
                "contractor_name": contractor_name,
            },
            message=f"Contractor assigned to job {job_id}",
        )

    except Exception as e:
        logger.error(f"Error assigning contractor: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to assign contractor",
        )


async def generate_bids(job_id: str, category: str, channel_id: str) -> FunctionResult:
    """Generate contractor bids for a job"""
    try:
        bot = get_bot()

        # Generate mock bids (in production, this would query real contractors)
        bids = generate_contractor_bids(category)

        # ChatGPT-style conversational bids summary with action suggestions
        full_bids_summary = (
            f"Great news! I've received {len(bids)} contractor bids for your {category} work order.\n\n"
            f"**Top Contractors:**\n\n"
        )

        for i, bid in enumerate(bids[:3], 1):  # Show top 3
            contractor = bid.get('contractor_name', 'Unknown')
            quote = bid.get('quote', 0)
            rating = bid.get('rating', 0)
            full_bids_summary += f"{i}. **{contractor}**\n"
            full_bids_summary += f"   - Quote: ${quote}\n"
            full_bids_summary += f"   - Rating: {'⭐' * int(rating)} ({rating}/5.0)\n\n"

        if len(bids) > 3:
            full_bids_summary += f"*Plus {len(bids) - 3} more contractors available*\n\n"

        full_bids_summary += (
            f"**What would you like to do?**\n"
            f"- Accept one of these bids\n"
            f"- Request more details about a contractor\n"
            f"- See all available bids\n"
            f"- Request landlord approval first\n\n"
            f"Let me know which contractor you'd like to proceed with, or if you need more information!"
        )

        # Wrap in expandable format
        preview = collapse_text(full_bids_summary, limit=500)
        expandable_text = (
            f"<ai-expanded>\n"
            f"RAW:\n{full_bids_summary}\n\n"
            f"PREVIEW:\n{preview}\n\n"
            f"ACTIONS:\n"
            f"- Accept bid\n"
            f"- View contractor details\n"
            f"- See all bids\n"
            f"- Request approval\n\n"
            f"EXPANDABLE: true\n"
            f"</ai-expanded>"
        )

        bot.send_ai_message(
            channel_id=channel_id,
            persona="landlord",
            text=expandable_text,
            metadata={
                "job_id": job_id,
                "bid_count": len(bids),
                "actionable": True,
            },
        )

        logger.info(f"Generated {len(bids)} bids for job {job_id}")

        return FunctionResult(
            success=True,
            data={"job_id": job_id, "bids": bids, "bid_count": len(bids)},
            message=f"Generated {len(bids)} bids for job {job_id}",
        )

    except Exception as e:
        logger.error(f"Error generating bids: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to generate bids",
        )


async def get_bids(job_id: str) -> FunctionResult:
    """Retrieve bids for a job"""
    try:
        dynamo = get_dynamo_service()
        bids = dynamo.list_bids_by_job(job_id)

        return FunctionResult(
            success=True,
            data={"job_id": job_id, "bids": bids, "bid_count": len(bids)},
            message=f"Retrieved {len(bids)} bids for job {job_id}",
        )

    except Exception as e:
        logger.error(f"Error retrieving bids: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to retrieve bids",
        )


async def accept_bid(bid_id: str, job_id: str) -> FunctionResult:
    """Accept a contractor bid"""
    try:
        dynamo = get_dynamo_service()

        # Update bid status
        dynamo.update_bid_status(bid_id, "accepted")

        # Get bid details to assign contractor
        bids = dynamo.list_bids_by_job(job_id)
        accepted_bid = next((b for b in bids if b.get("bid_id") == bid_id), None)

        if accepted_bid:
            # Assign contractor to job
            dynamo.update_job(
                job_id,
                contractor_id=accepted_bid.get("contractor_id"),
                contractor_name=accepted_bid.get("contractor_name"),
                status="scheduled",
            )

        logger.info(f"Accepted bid {bid_id} for job {job_id}")

        return FunctionResult(
            success=True,
            data={"bid_id": bid_id, "job_id": job_id, "status": "accepted"},
            message=f"Bid {bid_id} accepted successfully",
        )

    except Exception as e:
        logger.error(f"Error accepting bid: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to accept bid",
        )


async def request_landlord_approval(
    job_id: str,
    incident_id: str,
    channel_id: str,
) -> FunctionResult:
    """Request landlord approval for a work order"""
    try:
        bot = get_bot()
        dynamo = get_dynamo_service()

        # Get job and incident details
        job = dynamo.get_job(job_id)
        incident = dynamo.get_incident(incident_id, job.get("landlord_id", ""))

        # ChatGPT-style conversational approval request with action suggestions
        full_approval_msg = (
            f"A work order has been created and needs your approval.\n\n"
            f"**Work Order Summary:**\n"
            f"- **Job ID:** {job_id}\n"
            f"- **Service:** {job.get('title')}\n"
            f"- **Category:** {job.get('category')}\n"
            f"- **Estimated Cost:** ${job.get('estimated_cost')}\n"
            f"- **Priority:** {job.get('urgency', 'routine').upper()}\n\n"
            f"**Property Issue:**\n{incident.get('description', 'No description available') if incident else 'Details not available'}\n\n"
            f"**What would you like to do?**\n"
            f"- Approve this work order\n"
            f"- Reject with feedback\n"
            f"- Request more details\n"
            f"- View contractor bids\n\n"
            f"Please review and let me know your decision."
        )

        # Wrap in expandable format
        preview = collapse_text(full_approval_msg, limit=500)
        expandable_text = (
            f"<ai-expanded>\n"
            f"RAW:\n{full_approval_msg}\n\n"
            f"PREVIEW:\n{preview}\n\n"
            f"ACTIONS:\n"
            f"- Approve work order\n"
            f"- Reject with feedback\n"
            f"- Request more details\n"
            f"- View bids\n\n"
            f"EXPANDABLE: true\n"
            f"</ai-expanded>"
        )

        bot.send_ai_message(
            channel_id=channel_id,
            persona="landlord",
            text=expandable_text,
            metadata={
                "job_id": job_id,
                "incident_id": incident_id,
                "actionable": True,
            },
        )

        logger.info(f"Requested landlord approval for job {job_id}")

        return FunctionResult(
            success=True,
            data={"job_id": job_id, "incident_id": incident_id},
            message=f"Approval requested for job {job_id}",
        )

    except Exception as e:
        logger.error(f"Error requesting approval: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to request approval",
        )


async def process_approval_decision(
    job_id: str,
    decision: str,
    reason: Optional[str] = None,
) -> FunctionResult:
    """Process landlord's approval decision"""
    try:
        dynamo = get_dynamo_service()

        if decision == "approved":
            dynamo.update_job(
                job_id,
                status="approved",
                approval_status="approved",
                updated_at=datetime.utcnow().isoformat(),
            )
            message_text = f"Job {job_id} approved"
        else:
            dynamo.update_job(
                job_id,
                status="rejected",
                approval_status="rejected",
                rejection_reason=reason,
                updated_at=datetime.utcnow().isoformat(),
            )
            message_text = f"Job {job_id} rejected"

        logger.info(f"Processed approval decision for job {job_id}: {decision}")

        return FunctionResult(
            success=True,
            data={"job_id": job_id, "decision": decision, "reason": reason},
            message=message_text,
        )

    except Exception as e:
        logger.error(f"Error processing approval decision: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to process approval decision",
        )


async def get_user_incidents(user_id: str, limit: int = 10) -> FunctionResult:
    """Get user's incidents"""
    try:
        dynamo = get_dynamo_service()
        incidents = dynamo.list_incidents_by_tenant(user_id)

        # Limit results
        incidents = incidents[:limit] if incidents else []

        return FunctionResult(
            success=True,
            data={"user_id": user_id, "incidents": incidents, "count": len(incidents)},
            message=f"Retrieved {len(incidents)} incidents for user {user_id}",
        )

    except Exception as e:
        logger.error(f"Error retrieving user incidents: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to retrieve user incidents",
        )


async def get_user_jobs(user_id: str, limit: int = 10) -> FunctionResult:
    """Get user's jobs"""
    try:
        # This would typically query jobs by user_id
        logger.info(f"Retrieved jobs for user {user_id}")

        return FunctionResult(
            success=True,
            data={"user_id": user_id, "jobs": [], "count": 0},
            message=f"Retrieved jobs for user {user_id}",
        )

    except Exception as e:
        logger.error(f"Error retrieving user jobs: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to retrieve user jobs",
        )


async def get_property_info(property_id: str) -> FunctionResult:
    """Get property information"""
    try:
        dynamo = get_dynamo_service()
        property_info = dynamo.get_property(property_id)

        if not property_info:
            return FunctionResult(
                success=False,
                error="Property not found",
                message=f"Property {property_id} not found",
            )

        return FunctionResult(
            success=True,
            data=property_info,
            message=f"Retrieved property {property_id}",
        )

    except Exception as e:
        logger.error(f"Error retrieving property info: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to retrieve property info",
        )


# ==================== PHASE OMEGA: DYNAMIC TOOL FUNCTIONS ====================

async def register_dynamic_tool(
    tool_name: str,
    code: str,
    description: Optional[str] = None,
    category: Optional[str] = None,
) -> FunctionResult:
    """
    Register a new dynamic tool from LLM-generated Python code.

    Args:
        tool_name: Name of the tool (must be valid Python function name)
        code: Python source code containing the function
        description: Description of what the tool does
        category: Category (plumbing, electrical, etc.)

    Returns:
        FunctionResult with registration status
    """
    logger.info(f"🔧 Registering dynamic tool: {tool_name}")

    try:
        from ..dynamic_tools.tool_runtime import get_dynamic_tool_runtime

        runtime = get_dynamic_tool_runtime()

        # Register the tool
        result = runtime.register_tool(
            tool_name=tool_name,
            code=code,
            description=description,
            category=category,
            created_by="llm",
        )

        if result["success"]:
            return FunctionResult(
                success=True,
                data={
                    "tool_id": result["tool_id"],
                    "tool_name": tool_name,
                    "description": result["description"],
                    "metadata": result.get("metadata", {}),
                },
                message=f"✅ Dynamic tool '{tool_name}' registered successfully!",
            )
        else:
            return FunctionResult(
                success=False,
                error=str(result.get("errors", [])),
                message=f"❌ Failed to register tool '{tool_name}': {result.get('errors')}",
            )

    except Exception as e:
        logger.error(f"Error registering dynamic tool: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message=f"Failed to register dynamic tool: {e}",
        )


async def list_dynamic_tools(category: Optional[str] = None) -> FunctionResult:
    """List all registered dynamic tools"""
    logger.info(f"📋 Listing dynamic tools (category={category})")

    try:
        from ..dynamic_tools.tool_runtime import get_dynamic_tool_runtime

        runtime = get_dynamic_tool_runtime()
        tools = runtime.list_tools(category=category)

        return FunctionResult(
            success=True,
            data={
                "tools": tools,
                "count": len(tools),
            },
            message=f"Found {len(tools)} dynamic tools",
        )

    except Exception as e:
        logger.error(f"Error listing dynamic tools: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to list dynamic tools",
        )


# ==================== FUNCTION REGISTRY ====================

def get_function_definitions() -> List[FunctionDefinition]:
    """Get all function definitions for LLM tool calling (built-in + dynamic)"""
    # Built-in functions
    built_in_functions = [
        FunctionDefinition(
            name="create_incident",
            description="Create a new maintenance incident. Use when tenant reports a problem.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Brief title of the incident"},
                    "description": {"type": "string", "description": "Detailed description"},
                    "category": {
                        "type": "string",
                        "enum": ["plumbing", "electrical", "hvac", "appliance", "structural", "other"],
                        "description": "Category of the issue",
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "emergency"],
                        "description": "Severity level",
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["routine", "urgent", "immediate"],
                        "description": "How quickly it needs attention",
                    },
                },
                "required": ["title", "description", "category", "severity", "urgency"],
            },
        ),
        FunctionDefinition(
            name="update_incident",
            description="Update an existing incident's status or details",
            parameters={
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string", "description": "Incident ID to update"},
                    "status": {
                        "type": "string",
                        "enum": ["detected", "discovery", "discovery_complete", "diagnosing", "work_order", "in_progress", "completed"],
                        "description": "New status",
                    },
                },
                "required": ["incident_id"],
            },
        ),
        FunctionDefinition(
            name="get_incident",
            description="Retrieve incident details by ID",
            parameters={
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string", "description": "Incident ID"},
                },
                "required": ["incident_id"],
            },
        ),
        FunctionDefinition(
            name="close_incident",
            description="Mark an incident as resolved and closed",
            parameters={
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string", "description": "Incident ID to close"},
                    "resolution_notes": {"type": "string", "description": "Resolution notes"},
                },
                "required": ["incident_id"],
            },
        ),
        FunctionDefinition(
            name="start_discovery",
            description="Start discovery question flow for an incident",
            parameters={
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string", "description": "Incident ID"},
                    "questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of discovery questions (optional, uses defaults if not provided)",
                    },
                },
                "required": ["incident_id"],
            },
        ),
        FunctionDefinition(
            name="record_discovery_answer",
            description="Record answer to a discovery question",
            parameters={
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string", "description": "Incident ID"},
                    "question_index": {"type": "integer", "description": "Question index (0-based)"},
                    "answer": {"type": "string", "description": "User's answer"},
                    "total_questions": {"type": "integer", "description": "Total number of questions (optional, defaults to 5)"},
                },
                "required": ["incident_id", "question_index", "answer"],
            },
        ),
        FunctionDefinition(
            name="start_diagnosis",
            description="🚨 MANDATORY after discovery_complete: Start diagnosis stage. Analyzes discovery answers and provides category-specific diagnosis. MUST be called when stage=discovery_complete.",
            parameters={
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string", "description": "Incident ID to diagnose"},
                },
                "required": ["incident_id"],
            },
        ),
        FunctionDefinition(
            name="record_diagnosis_result",
            description="Record diagnosis findings and recommendations",
            parameters={
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string", "description": "Incident ID"},
                    "diagnosis_notes": {"type": "string", "description": "Diagnosis notes and findings"},
                },
                "required": ["incident_id", "diagnosis_notes"],
            },
        ),
        FunctionDefinition(
            name="create_work_order",
            description="Create a work order (job) from an incident. Use after diagnosis is complete.",
            parameters={
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string", "description": "Incident ID"},
                    "title": {"type": "string", "description": "Work order title"},
                    "estimated_cost": {"type": "string", "description": "Estimated cost (e.g., '250.00')"},
                    "urgency": {"type": "string", "enum": ["routine", "urgent", "immediate"]},
                },
                "required": ["incident_id", "title", "estimated_cost"],
            },
        ),
        FunctionDefinition(
            name="update_work_order",
            description="Update a work order status or details",
            parameters={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID"},
                    "status": {
                        "type": "string",
                        "enum": ["created", "approved", "scheduled", "in_progress", "completed"],
                    },
                },
                "required": ["job_id"],
            },
        ),
        FunctionDefinition(
            name="get_work_order",
            description="Retrieve work order details",
            parameters={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID"},
                },
                "required": ["job_id"],
            },
        ),
        FunctionDefinition(
            name="request_landlord_approval",
            description="Submit work order for landlord approval",
            parameters={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID"},
                    "incident_id": {"type": "string", "description": "Related incident ID"},
                },
                "required": ["job_id", "incident_id"],
            },
        ),
        FunctionDefinition(
            name="process_approval_decision",
            description="Process landlord's approval or rejection decision",
            parameters={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID"},
                    "decision": {"type": "string", "enum": ["approved", "rejected"]},
                    "reason": {"type": "string", "description": "Reason for decision (optional)"},
                },
                "required": ["job_id", "decision"],
            },
        ),
        FunctionDefinition(
            name="generate_bids",
            description="Generate contractor bids for a job",
            parameters={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID"},
                    "category": {"type": "string", "description": "Job category"},
                },
                "required": ["job_id", "category"],
            },
        ),
        FunctionDefinition(
            name="get_user_incidents",
            description="List all incidents for a user",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "limit": {"type": "integer", "description": "Max results (default 10)"},
                },
                "required": ["user_id"],
            },
        ),
        FunctionDefinition(
            name="register_dynamic_tool",
            description="Register a new dynamic tool from LLM-generated Python code. Use when user asks to create a diagnostic tool or analyzer.",
            parameters={
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string", "description": "Name of the tool (valid Python function name)"},
                    "code": {"type": "string", "description": "Python source code containing the function"},
                    "description": {"type": "string", "description": "Description of what the tool does"},
                    "category": {
                        "type": "string",
                        "enum": ["plumbing", "electrical", "hvac", "appliance", "structural", "general"],
                        "description": "Category of the tool",
                    },
                },
                "required": ["tool_name", "code"],
            },
        ),
        FunctionDefinition(
            name="list_dynamic_tools",
            description="List all registered dynamic tools, optionally filtered by category.",
            parameters={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional category filter",
                    },
                },
                "required": [],
            },
        ),
    ]

    # 🚀 PHASE OMEGA: Add dynamic tools to function definitions
    try:
        from ..dynamic_tools.tool_loader import get_dynamic_tool_loader

        loader = get_dynamic_tool_loader()
        dynamic_tools = loader.get_dynamic_function_definitions()

        logger.info(f"📦 Loaded {len(dynamic_tools)} dynamic tool definitions")

        return built_in_functions + dynamic_tools
    except Exception as e:
        logger.error(f"Error loading dynamic tools: {e}", exc_info=True)
        return built_in_functions


# Function name to implementation mapping
FUNCTION_IMPLEMENTATIONS = {
    "create_incident": create_incident,
    "update_incident": update_incident,
    "get_incident": get_incident,
    "close_incident": close_incident,
    "start_discovery": start_discovery,
    "record_discovery_answer": record_discovery_answer,
    "get_discovery_status": get_discovery_status,
    "start_diagnosis": start_diagnosis,  # 🚨 NEW: Diagnosis stage
    "record_diagnosis_result": record_diagnosis_result,  # 🚨 NEW: Record diagnosis
    "create_work_order": create_work_order,
    "update_work_order": update_work_order,
    "get_work_order": get_work_order,
    "assign_contractor": assign_contractor,
    "generate_bids": generate_bids,
    "get_bids": get_bids,
    "accept_bid": accept_bid,
    "request_landlord_approval": request_landlord_approval,
    "process_approval_decision": process_approval_decision,
    "get_user_incidents": get_user_incidents,
    "get_user_jobs": get_user_jobs,
    "get_property_info": get_property_info,
    # PHASE OMEGA: Dynamic tool management
    "register_dynamic_tool": register_dynamic_tool,
    "list_dynamic_tools": list_dynamic_tools,
}


async def execute_function(
    function_name: str,
    arguments: Dict[str, Any],
    context: Dict[str, Any],
) -> FunctionResult:
    """Execute a function by name with given arguments"""

    # Strip "functions." prefix if LLM added it
    if function_name and function_name.startswith("functions."):
        function_name = function_name.replace("functions.", "", 1)

    # 🚀 PHASE OMEGA: Check if this is a dynamic tool
    try:
        from ..dynamic_tools.tool_loader import get_dynamic_tool_loader
        from ..dynamic_tools.tool_runtime import get_dynamic_tool_runtime

        runtime = get_dynamic_tool_runtime()
        loader = get_dynamic_tool_loader()

        # If tool exists in dynamic registry, execute it
        if function_name in runtime.tools:
            logger.info(f"🔧 Executing dynamic tool: {function_name}")
            result = await loader.execute_dynamic_tool(
                function_name, arguments, context
            )

            # 🚀 PHASE OMEGA: Record dynamic tool execution for skills evolution
            try:
                from ..services.auto_evolving_skills import get_skills_recorder

                recorder = get_skills_recorder()
                await recorder.record_tool_execution(
                    tool_name=function_name,
                    arguments=arguments,
                    result=result.data if result.success else None,
                    success=result.success,
                    user_id=context.get("user_id"),
                )

            except Exception as e:
                logger.error(f"Error recording tool execution: {e}", exc_info=True)

            return result

    except Exception as e:
        logger.error(f"Error checking dynamic tools: {e}", exc_info=True)

    # Dynamic tool sandbox: Check if function is registered dynamic tool
    # STRICT: Only return success for tools that ACTUALLY EXIST
    # Do NOT mask hallucinations - let them fail properly
    if function_name and function_name not in FUNCTION_IMPLEMENTATIONS:
        # Check if it's a registered dynamic tool
        from ..dynamic_tools.tool_runtime import get_dynamic_tool_runtime
        runtime = get_dynamic_tool_runtime()

        if function_name in runtime.tools:
            # Tool exists - this is handled above in the dynamic tools section
            # If we got here, something went wrong - log and fail
            logger.error(f"Dynamic tool {function_name} exists but wasn't executed above")

        # Tool doesn't exist - check if it's an explicit tool generation request
        if function_name.startswith(("generate_tool_", "create_tool_", "register_tool_")):
            logger.info(f"🔧 Tool generation request: {function_name}")
            return FunctionResult(
                success=True,
                data={
                    "type": "tool_generation_request",
                    "tool_name": function_name,
                    "arguments": arguments,
                },
                message=f"Tool generation request captured: {function_name}",
            )

        # Not a dynamic tool, not a generation request - this is a hallucination
        # DO NOT return success - let it fail properly

    if function_name not in FUNCTION_IMPLEMENTATIONS:
        logger.warning(f"Unknown function requested: {function_name}")
        available = list(FUNCTION_IMPLEMENTATIONS.keys())
        return FunctionResult(
            success=False,
            error=f"Function {function_name} not found",
            data={"available_functions": available[:10]},
            message=f"Unknown function: {function_name}. Available: {', '.join(available[:5])}...",
        )

    func = FUNCTION_IMPLEMENTATIONS[function_name]

    # ========== CRITICAL: Aggressive kwargs filtering ==========
    # MUST strip ALL metadata fields that don't exist in function signature
    # Common metadata to strip: channel_id, stage, persona, model, context, etc.

    try:
        sig = inspect.signature(func)
        valid_params = set(sig.parameters.keys())

        # Inject context fields ONLY if function signature accepts them
        if "user_id" in valid_params and "user_id" not in arguments:
            arguments["user_id"] = context.get("user_id")
        if "channel_id" in valid_params and "channel_id" not in arguments:
            arguments["channel_id"] = context.get("channel_id")
        if "property_id" in valid_params and "property_id" not in arguments:
            arguments["property_id"] = context.get("property_id")

        # AGGRESSIVE FILTERING: Strip EVERYTHING not in function signature
        filtered_args = {}
        filtered_out = []

        for key, value in arguments.items():
            if key in valid_params:
                filtered_args[key] = value
            else:
                filtered_out.append(key)

        # Also strip common metadata fields from context injection
        metadata_fields = {
            "stage", "persona", "model", "context", "message_id",
            "timestamp", "session_id", "conversation_id", "thread_id",
            "metadata", "routing", "workflow_stage"
        }

        for meta_field in metadata_fields:
            if meta_field in filtered_args and meta_field not in valid_params:
                filtered_out.append(meta_field)
                filtered_args.pop(meta_field, None)

        if filtered_out:
            logger.info(f"🔒 Stripped {len(filtered_out)} metadata fields from {function_name}: {filtered_out}")

        logger.info(f"✅ Executing {function_name} with valid args: {list(filtered_args.keys())}")

    except Exception as e:
        logger.warning(f"⚠️ Could not inspect {function_name} signature: {e}")
        # Fallback: still filter out known metadata fields
        filtered_args = arguments.copy()

        # Strip known metadata even in fallback
        known_metadata = {"stage", "persona", "model", "metadata", "routing"}
        for meta in known_metadata:
            filtered_args.pop(meta, None)

    try:
        result = await func(**filtered_args)
        return result
    except TypeError as e:
        logger.error(f"❌ Function {function_name} argument error: {e}", exc_info=True)
        logger.error(f"   Attempted args: {list(filtered_args.keys())}")
        logger.error(f"   Valid params: {list(valid_params) if 'valid_params' in locals() else 'unknown'}")
        return FunctionResult(
            success=False,
            error=f"Invalid arguments: {str(e)}",
            message=f"Failed to execute {function_name}: invalid arguments",
        )
    except Exception as e:
        logger.error(f"❌ Function {function_name} execution error: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message=f"Failed to execute {function_name}",
        )
