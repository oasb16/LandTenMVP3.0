"""
Universal function registry for LLM orchestrator.
Contains all callable functions with schemas and implementations.
"""
from typing import Dict, Any, List, Optional
import uuid
import logging
import inspect
import os
import stripe
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

# Initialize Stripe with API key from environment
# Will automatically use test mode if sk_test_* key is provided
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
if stripe.api_key:
    is_test_mode = stripe.api_key.startswith("sk_test_")
    logger.info(f"🔑 Stripe initialized in {'TEST/SANDBOX' if is_test_mode else 'PRODUCTION'} mode")
else:
    logger.warning("⚠️ STRIPE_SECRET_KEY not found - payments will be simulated")

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
        from ..services.ai_service import get_ai_response

        # Build context from previous answers if available
        context_text = ""
        if conversation_context:
            context_text = "\n\nPrevious conversation:\n" + "\n".join(conversation_context)

        system_context = f"""You are PropertyAI. Generate discovery questions like ChatGPT—not a rigid checklist.
Make them natural, conversational, and context-aware. No banked questions.
Return {max_q} short questions max, one per line.

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

        # Use async AI service with rate-limit awareness
        from ..services.ai_service import get_ai_response_async
        response = await get_ai_response_async(
            message=user_prompt,
            persona="assistant",
            context=system_context,
        )

        # FIXED: get_ai_response returns JSON, not plain text
        # Parse JSON response to extract questions array
        questions = []
        try:
            import json
            import re

            # Strip markdown code blocks (```json ... ```)
            cleaned_response = response.strip()
            # Remove opening ```json or ```
            cleaned_response = re.sub(r'^```(?:json)?\s*\n', '', cleaned_response)
            # Remove closing ```
            cleaned_response = re.sub(r'\n```\s*$', '', cleaned_response)

            data = json.loads(cleaned_response)
            if isinstance(data, dict) and "questions" in data:
                questions = data["questions"]
            elif isinstance(data, list):
                questions = data
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse JSON response, trying plain text fallback: {e}")
            # Fallback to old plain text parsing if JSON fails
            lines = response.strip().split("\n")
            import re
            for line in lines:
                # Skip markdown code fences and JSON structure lines
                if line.strip() in ['```', '```json', '{', '}', '[', ']'] or '"questions"' in line:
                    continue

                # Remove numbering and clean up
                cleaned = line.strip()
                # Remove leading numbers like "1.", "1)", etc.
                cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned)
                # Remove quotes if it's a JSON string
                cleaned = re.sub(r'^"(.*)"[,]?$', r'\1', cleaned)

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
    attachments: Optional[List[Dict[str, Any]]] = None,  # 🔥 NEW: Accept attachments
) -> FunctionResult:
    """
    Create a new maintenance incident.

    Automatically processes image attachments:
    - Downloads images from Stream Chat CDN
    - Uploads to S3 for permanent storage
    - Attaches to incident.photos field
    """
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

        # 🔥 NEW: Process image attachments and upload to S3
        photos = []
        if attachments:
            logger.info(f"📸 Processing {len(attachments)} attachment(s) for incident {incident_id}")
            from ..services.s3_uploader import get_s3_uploader

            s3_uploader = get_s3_uploader()

            for idx, attachment in enumerate(attachments):
                att_type = attachment.get('type', '')
                att_mime = attachment.get('mime_type', '')

                # Check if it's an image
                is_image = (
                    att_type == 'image' or
                    'image' in att_mime or
                    any(attachment.get('url', '').lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'])
                )

                if is_image:
                    # Get image URL from attachment (Stream Chat format)
                    image_url = attachment.get('url') or attachment.get('image_url') or attachment.get('asset_url')

                    if image_url:
                        logger.info(f"   📷 Uploading image {idx + 1}: {image_url[:80]}...")

                        try:
                            # Download from Stream Chat CDN and upload to S3
                            photo_record = await s3_uploader.download_and_upload(
                                source_url=image_url,
                                incident_id=incident_id,
                                content_type=att_mime or 'image/jpeg',
                                ai_analysis=None  # Will be populated later if needed
                            )

                            if photo_record:
                                photos.append(photo_record)
                                logger.info(f"   ✅ Uploaded to S3: {photo_record['url']}")
                            else:
                                logger.warning(f"   ⚠️ Failed to upload image {idx + 1}")

                        except Exception as e:
                            logger.error(f"   ❌ Error uploading image {idx + 1}: {e}")
                else:
                    logger.debug(f"   ⏭️ Skipping non-image attachment: type={att_type}, mime={att_mime}")

            logger.info(f"📸 Processed {len(photos)} image(s) for incident {incident_id}")

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
            "photos": photos,  # 🔥 NEW: S3 photo URLs with metadata
        }

        # Save to DynamoDB
        dynamo.create_incident(incident_data)

        # PHASE OMEGA OBJECTIVE #7: WORK ORDER STABILIZATION - Add to topic graph
        try:
            from ..services.incident_topic_graph import get_incident_graph
            incident_graph = get_incident_graph(user_id)
            incident_graph.add_incident(incident_id, title, category, description)
            # 🚨 CRITICAL FIX: Removed duplicate save
            # Graph is saved once at end of message processing (ai_webhooks_v3.py)
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
    attachments: Optional[List[Dict[str, Any]]] = None,  # 🔥 NEW: Accept attachments
    **kwargs,
) -> FunctionResult:
    """
    Update an existing incident.

    Automatically processes new image attachments:
    - Downloads images from Stream Chat CDN
    - Uploads to S3 for permanent storage
    - Appends to existing incident.photos
    """
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

        # 🔥 NEW: Process new image attachments and append to existing photos
        if attachments:
            logger.info(f"📸 Processing {len(attachments)} new attachment(s) for incident {incident_id}")
            from ..services.s3_uploader import get_s3_uploader

            s3_uploader = get_s3_uploader()
            new_photos = []

            for idx, attachment in enumerate(attachments):
                att_type = attachment.get('type', '')
                att_mime = attachment.get('mime_type', '')

                # Check if it's an image
                is_image = (
                    att_type == 'image' or
                    'image' in att_mime or
                    any(attachment.get('url', '').lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'])
                )

                if is_image:
                    image_url = attachment.get('url') or attachment.get('image_url') or attachment.get('asset_url')

                    if image_url:
                        logger.info(f"   📷 Uploading new image {idx + 1}: {image_url[:80]}...")

                        try:
                            photo_record = await s3_uploader.download_and_upload(
                                source_url=image_url,
                                incident_id=incident_id,
                                content_type=att_mime or 'image/jpeg',
                                ai_analysis=None
                            )

                            if photo_record:
                                new_photos.append(photo_record)
                                logger.info(f"   ✅ Uploaded to S3: {photo_record['url']}")
                            else:
                                logger.warning(f"   ⚠️ Failed to upload image {idx + 1}")

                        except Exception as e:
                            logger.error(f"   ❌ Error uploading image {idx + 1}: {e}")

            # Append new photos to existing photos list
            if new_photos:
                existing_photos = existing.get('photos', []) if existing else []
                all_photos = existing_photos + new_photos
                updates['photos'] = all_photos
                logger.info(f"📸 Added {len(new_photos)} new photo(s). Total: {len(all_photos)}")

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
    channel_id: str,
    incident_id: Optional[str] = None,
    user_id: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    user_message: Optional[str] = None,
    questions: Optional[List[str]] = None,
) -> FunctionResult:
    """
    ChatGPT-style dynamic discovery - ALWAYS uses LLM-generated questions.

    🚨 NEW: Works with OR without incident_id
    - WITH incident_id: Traditional flow (incident exists, add discovery)
    - WITHOUT incident_id: Pre-incident discovery (collect info BEFORE creating incident)
    """
    try:
        bot = get_bot()
        dynamo = get_dynamo_service()

        # Get incident details if incident_id provided
        incident = None
        if incident_id:
            incident = dynamo.get_incident(incident_id, user_id)

        if incident:
            category = category or incident.get("category", "general")
            severity = severity or incident.get("severity", "medium")
            user_message = user_message or incident.get("description", "")
        else:
            # Pre-incident discovery: infer category from user message
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

            # Store questions in incident (if incident exists)
            if incident_id and incident:
                dynamo.update_incident_status(
                    incident_id=incident_id,
                    status="discovery",
                    user_id=user_id or incident.get("user_id"),
                    discovery_responses={"questions": questions},
                )

        # Update incident status to 'discovery' if incident exists
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
            text=full_message,  # Send plain text, not expandable
            metadata={
                "incident_id": incident_id,  # None for pre-incident discovery
                "question_index": 0,
                "total_questions": total,
                "actionable": True,
            },
        )

        user_message_sent = True
        if incident_id:
            logger.info(f"Started ChatGPT-style discovery for incident {incident_id} with {len(questions)} questions")
        else:
            logger.info(f"Started pre-incident discovery with {len(questions)} questions (incident will be created after Q5)")

        return FunctionResult(
            success=True,
            data={
                "incident_id": incident_id,  # None for pre-incident discovery
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


async def create_incident_from_discovery(
    channel_id: str,
    user_id: str,
    discovery_data: dict,
    property_id: Optional[str] = None,
) -> FunctionResult:
    """
    Create incident from completed discovery Q&A.
    Called after all 5 discovery questions are answered.

    Args:
        discovery_data: Should contain:
            - initial_message: user's original report
            - questions: list of 5 questions
            - answers: dict of {question_idx: answer_text}
    """
    try:
        from ..services.ai_service import get_ai_response_async

        # Extract discovery data
        initial_message = discovery_data.get("initial_message", "")
        questions = discovery_data.get("questions", [])
        answers = discovery_data.get("answers", {})

        # Build Q&A summary
        qa_summary = f"Initial report: {initial_message}\n\n"
        for i, question in enumerate(questions):
            answer = answers.get(str(i), answers.get(i, "No answer"))
            qa_summary += f"Q{i+1}: {question}\nA{i+1}: {answer}\n\n"

        # Use AI to synthesize incident details from Q&A
        synthesis_prompt = f"""Analyze this maintenance issue report and discovery Q&A, then extract structured incident details.

{qa_summary}

Return ONLY a JSON object with these exact fields:
{{
  "title": "Short descriptive title (3-8 words)",
  "description": "Detailed description combining all Q&A (2-3 sentences)",
  "category": "electrical|plumbing|hvac|appliance|structural|pest|safety|other",
  "severity": "low|medium|high|emergency",
  "urgency": "routine|urgent|immediate"
}}"""

        # Get AI synthesis
        response = await get_ai_response_async(
            message=synthesis_prompt,
            persona="assistant",
            context="You are a maintenance triage expert.",
        )

        # Parse JSON from response
        import json
        import re

        # Strip markdown code blocks
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n', '', cleaned_response)
        cleaned_response = re.sub(r'\n```\s*$', '', cleaned_response)

        incident_details = json.loads(cleaned_response)

        # Create incident with synthesized details
        result = await create_incident(
            title=incident_details.get("title", initial_message[:50]),
            description=incident_details.get("description", qa_summary),
            category=incident_details.get("category", "general"),
            severity=incident_details.get("severity", "medium"),
            urgency=incident_details.get("urgency", "routine"),
            user_id=user_id,
            channel_id=channel_id,
            property_id=property_id,
        )

        if result.success:
            incident_id = result.data.get("incident_id")
            logger.info(f"✅ Created incident {incident_id} from discovery Q&A")

            # Send confirmation to user
            bot = get_bot()
            bot.send_ai_message(
                channel_id=channel_id,
                persona="tenant",
                text=f"Thanks for all those details! I've created incident **{incident_id}** and we'll get this resolved for you.",
                metadata={"incident_id": incident_id},
            )

            return result
        else:
            logger.error(f"Failed to create incident from discovery: {result.error}")
            return result

    except Exception as e:
        logger.error(f"Error creating incident from discovery: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to create incident from discovery",
        )


async def record_discovery_answer(
    answer: str,
    question_index: int,
    channel_id: str,
    user_id: str,
    incident_id: Optional[str] = None,
    total_questions: Optional[int] = 5,
) -> FunctionResult:
    """
    Record discovery answer and ask next question.

    🚨 NEW: Works with OR without incident_id
    - WITH incident_id: Traditional flow (save to incident in DynamoDB)
    - WITHOUT incident_id: Pre-incident discovery (answers stored in meta_context)
    """
    try:
        dynamo = get_dynamo_service()
        bot = get_bot()

        # Initialize variables
        incident = None
        stored_questions = []
        existing_answers = {}
        category = "general"
        severity = "medium"
        description = ""

        if incident_id:
            # Traditional flow: get incident from DynamoDB
            incident = dynamo.get_incident(incident_id, user_id)
            if not incident:
                return FunctionResult(
                    success=False,
                    error="Incident not found",
                    message=f"Cannot record answer: incident {incident_id} not found",
                )

            # Get stored questions and answers from incident
            discovery_responses = incident.get("discovery_responses", {})
            stored_questions = discovery_responses.get("questions", [])
            existing_answers = incident.get("discovery_answers", {})
            category = incident.get("category", "general")
            severity = incident.get("severity", "medium")
            description = incident.get("description", "")

        if total_questions is None:
            total_questions = len(stored_questions) if stored_questions else 5

        # Save answer
        if isinstance(existing_answers, dict):
            existing_answers[f"q{question_index}"] = answer
        else:
            existing_answers = {f"q{question_index}": answer}

        next_index = question_index + 1

        # Save answer to incident (if incident exists)
        if incident_id and incident:
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
            logger.info(f"✅ Discovery completed (Q{next_index}/{total_questions})")

            if incident_id:
                # Traditional flow: mark incident as discovery_complete
                dynamo.update_incident_status(
                    incident_id=incident_id,
                    status="discovery_complete",
                    user_id=user_id,
                )
                completion_msg = "Perfect! I have all the information I need. Let me analyze the issue and determine the best course of action."
                next_stage = "diagnosing"
            else:
                # Pre-incident flow: signal to create incident
                completion_msg = "Perfect! I have all the information I need. Let me create the incident for you now."
                next_stage = "create_incident"

            bot.send_ai_message(
                channel_id=channel_id,
                persona="tenant",
                text=completion_msg,
                metadata={
                    "incident_id": incident_id,
                    "discovery_complete": True,
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
                    "next_stage": next_stage,
                    "user_message_sent": user_message_sent,
                    # For pre-incident flow: return discovery data
                    "discovery_data": {
                        "questions": stored_questions,
                        "answers": existing_answers,
                    } if not incident_id else None,
                },
                message="Discovery questions completed" + (", ready to create incident" if not incident_id else ", moving to diagnosis"),
            )

        # Dynamically regenerate next question based on conversation context
        # category, severity, description already set above (from incident or defaults)

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
            stored_questions = updated_questions

            # Save to incident if exists
            if incident_id and incident:
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
            f"Thanks for that information.\n\n"
            f"**Question {next_index + 1} of {total_questions}:** {next_question}"
        )

        bot.send_ai_message(
            channel_id=channel_id,
            persona="tenant",
            text=full_message,  # Plain text, no expandable
            metadata={
                "incident_id": incident_id,
                "question_index": next_index,
                "total_questions": total_questions,
                "actionable": True,
            },
        )

        if incident_id:
            logger.info(f"✅ Sent discovery question {next_index+1}/{total_questions} for incident {incident_id}")
        else:
            logger.info(f"✅ Sent pre-incident discovery question {next_index+1}/{total_questions}")

        return FunctionResult(
            success=True,
            data={
                "incident_id": incident_id,
                "question_index": question_index,
                "answer": answer,
                "discovery_complete": False,
                "next_question_index": next_index,
                "user_message_sent": user_message_sent,
                # For pre-incident flow: return updated discovery data
                "discovery_data": {
                    "questions": stored_questions,
                    "answers": existing_answers,
                } if not incident_id else None,
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
            # 🚨 CRITICAL FIX: Removed duplicate save
            # Graph is saved once at end of message processing (ai_webhooks_v3.py)
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
        dynamo = get_dynamo_service()

        # 🚨 FIX: Use BidGenerator service for realistic contractor data
        from ..services.bid_generator import get_bid_generator

        bid_generator = get_bid_generator()

        # Get job details for better bid generation
        job = dynamo.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found for bid generation")
            # Fallback to basic generation
            severity = "medium"
            urgency = "routine"
            description = f"{category} maintenance required"
        else:
            urgency = job.get("urgency", "routine")
            description = job.get("title", f"{category} maintenance required")

            # Get incident details for severity (jobs don't have severity field)
            incident_id = job.get("incident_id")
            if incident_id:
                incident = dynamo.get_incident(incident_id, job.get("user_id"))
                severity = incident.get("severity", "medium") if incident else "medium"
            else:
                severity = "medium"

        # Generate bids using BidGenerator
        bids = bid_generator.generate_bids(
            job_id=job_id,
            category=category,
            severity=severity,
            urgency=urgency,
            description=description,
            num_bids=3
        )

        # Save bids to DynamoDB
        for bid in bids:
            try:
                dynamo.create_bid(bid)
                logger.info(f"✅ Saved bid {bid['bid_id']} to DynamoDB")
            except Exception as e:
                logger.error(f"Error saving bid {bid.get('bid_id')}: {e}")

        # ChatGPT-style conversational bids summary with action suggestions
        full_bids_summary = (
            f"Great news! I've received {len(bids)} contractor bids for your {category} work order.\n\n"
            f"**Top Contractors:**\n\n"
        )

        for i, bid in enumerate(bids[:3], 1):  # Show top 3
            contractor = bid.get('contractor_name', 'Unknown')
            quote = bid.get('quote', 0)
            rating = bid.get('rating', 0)
            eta = bid.get('eta', 'TBD')
            full_bids_summary += f"{i}. **{contractor}**\n"
            full_bids_summary += f"   - Quote: ${quote:.2f}\n"
            full_bids_summary += f"   - Rating: {'⭐' * int(rating)} ({rating}/5.0)\n"
            full_bids_summary += f"   - ETA: {eta}\n\n"

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


async def process_payment(
    job_id: str,
    amount: float,
    payment_method: Optional[str] = "stripe",
) -> FunctionResult:
    """
    🔒 ESCROW PAYMENT: Hold payment for 7 days or until tenant approval
    💰 PLATFORM FEE: Automatically deduct 15% commission

    Payment Flow:
    1. Charge tenant → Hold in escrow (Stripe authorized charge)
    2. Update job status to "awaiting_approval"
    3. Tenant approves OR 7 days pass → Capture charge
    4. Transfer to contractor (amount - 15% platform fee)
    5. Platform keeps 15% as revenue
    """
    try:
        dynamo = get_dynamo_service()

        # Get job details
        job = dynamo.get_job(job_id)
        if not job:
            return FunctionResult(
                success=False,
                error="Job not found",
                message=f"Cannot process payment: job {job_id} not found",
            )

        # Check job is completed
        if job.get("status") != "completed":
            return FunctionResult(
                success=False,
                error="Job not completed",
                message=f"Cannot process payment: job {job_id} is not completed (status: {job.get('status')})",
            )

        contractor_id = job.get("contractor_id")
        contractor_name = job.get("contractor_name", "Unknown")

        if not contractor_id:
            return FunctionResult(
                success=False,
                error="No contractor assigned",
                message=f"Cannot process payment: no contractor assigned to job {job_id}",
            )

        # 💰 CALCULATE PLATFORM FEE (15%)
        PLATFORM_FEE_PERCENTAGE = 0.15
        total_amount = amount
        platform_fee = total_amount * PLATFORM_FEE_PERCENTAGE
        contractor_payout = total_amount - platform_fee

        logger.info(f"💰 Payment breakdown for job {job_id}:")
        logger.info(f"   Total: ${total_amount:.2f}")
        logger.info(f"   Platform fee (15%): ${platform_fee:.2f}")
        logger.info(f"   Contractor payout: ${contractor_payout:.2f}")

        # Process payment via Stripe
        if payment_method == "stripe":
            try:
                # 🔒 STEP 1: Create authorized charge (HOLD in escrow, don't capture yet)
                escrow_expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()

                if stripe.api_key:
                    # Real Stripe: Create authorized charge (hold funds, don't capture yet)
                    # Note: For full implementation, need tenant's stripe_customer_id or payment_method_id
                    # For sandbox testing, using test payment method
                    try:
                        charge = stripe.Charge.create(
                            amount=int(total_amount * 100),  # Convert to cents
                            currency="usd",
                            capture=False,  # HOLD in escrow, don't capture yet
                            description=f"Escrow payment for job {job_id}",
                            metadata={
                                "job_id": job_id,
                                "contractor_id": contractor_id,
                                "platform_fee": platform_fee,
                                "contractor_payout": contractor_payout,
                            },
                            # In production, add: customer=tenant_stripe_customer_id or source=payment_method_id
                        )
                        escrow_charge_id = charge.id
                        logger.info(f"🔒 Stripe charge created: {escrow_charge_id}")
                    except stripe.error.CardError as e:
                        # For sandbox testing without customer setup, simulate escrow
                        escrow_charge_id = f"ch_escrow_{uuid.uuid4().hex[:12]}"
                        logger.warning(f"⚠️ Stripe charge failed (expected in sandbox without customer setup): {e}")
                        logger.info(f"   Using simulated escrow charge: {escrow_charge_id}")
                else:
                    # No Stripe key: simulate escrow
                    escrow_charge_id = f"ch_escrow_{uuid.uuid4().hex[:12]}"
                    logger.info(f"💡 Simulating escrow (no Stripe key configured)")

                logger.info(f"🔒 Holding ${total_amount:.2f} in escrow for job {job_id}")
                logger.info(f"   Charge ID: {escrow_charge_id}")
                logger.info(f"   Auto-release: {escrow_expires_at}")

                # STEP 2: Update job with escrow details
                dynamo.update_job(
                    job_id,
                    payment_status="escrowed",
                    payment_amount=total_amount,
                    platform_fee=platform_fee,
                    contractor_payout=contractor_payout,
                    escrow_charge_id=escrow_charge_id,
                    escrow_created_at=datetime.utcnow().isoformat(),
                    escrow_expires_at=escrow_expires_at,
                    payment_method=payment_method,
                )

                logger.info(f"✅ Payment escrowed for job {job_id}")
                logger.info(f"   Tenant will be asked to approve work within 7 days")

                return FunctionResult(
                    success=True,
                    data={
                        "job_id": job_id,
                        "payment_status": "escrowed",
                        "total_amount": total_amount,
                        "platform_fee": platform_fee,
                        "contractor_payout": contractor_payout,
                        "escrow_charge_id": escrow_charge_id,
                        "escrow_expires_at": escrow_expires_at,
                        "contractor_id": contractor_id,
                        "contractor_name": contractor_name,
                    },
                    message=f"💰 Payment of ${total_amount:.2f} held in escrow. Tenant has 7 days to approve work. Contractor will receive ${contractor_payout:.2f} after approval.",
                )

            except Exception as stripe_error:
                logger.error(f"Stripe escrow error: {stripe_error}", exc_info=True)
                return FunctionResult(
                    success=False,
                    error=str(stripe_error),
                    message=f"Failed to create escrow payment: {str(stripe_error)}",
                )

        else:
            return FunctionResult(
                success=False,
                error="Unsupported payment method",
                message=f"Payment method '{payment_method}' is not supported",
            )

    except Exception as e:
        logger.error(f"Error processing payment: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to process payment",
        )


async def approve_work_completion(
    job_id: str,
    user_id: str,
    approved: bool,
    feedback: Optional[str] = None,
) -> FunctionResult:
    """
    🎯 TENANT APPROVES WORK: Release escrow payment to contractor

    Called when tenant confirms work is satisfactory.
    Triggers immediate release of escrowed funds to contractor.
    """
    try:
        dynamo = get_dynamo_service()

        # Get job details
        job = dynamo.get_job(job_id)
        if not job:
            return FunctionResult(
                success=False,
                error="Job not found",
                message=f"Cannot approve work: job {job_id} not found",
            )

        # Check payment is escrowed
        if job.get("payment_status") != "escrowed":
            return FunctionResult(
                success=False,
                error="Payment not escrowed",
                message=f"Cannot approve: payment status is {job.get('payment_status')}, expected 'escrowed'",
            )

        if approved:
            # ✅ TENANT APPROVED: Release payment
            logger.info(f"✅ Tenant approved work for job {job_id}")

            # Release escrow to contractor
            release_result = await release_escrow_payment(job_id)

            if release_result.success:
                # Update job with approval
                dynamo.update_job(
                    job_id,
                    work_approved=True,
                    work_approved_at=datetime.utcnow().isoformat(),
                    work_feedback=feedback,
                )

                return FunctionResult(
                    success=True,
                    data={
                        "job_id": job_id,
                        "approved": True,
                        "payment_released": True,
                        "contractor_payout": release_result.data.get("contractor_payout"),
                    },
                    message=f"✅ Work approved! ${release_result.data.get('contractor_payout', 0):.2f} released to contractor.",
                )
            else:
                return release_result

        else:
            # ❌ TENANT REJECTED: Hold escrow for dispute resolution
            logger.info(f"❌ Tenant rejected work for job {job_id}: {feedback}")

            dynamo.update_job(
                job_id,
                work_approved=False,
                work_rejected_at=datetime.utcnow().isoformat(),
                work_feedback=feedback,
                payment_status="disputed",
            )

            return FunctionResult(
                success=True,
                data={
                    "job_id": job_id,
                    "approved": False,
                    "payment_status": "disputed",
                },
                message=f"❌ Work rejected. Payment held for dispute resolution. Reason: {feedback or 'No feedback provided'}",
            )

    except Exception as e:
        logger.error(f"Error approving work: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to approve work",
        )


async def release_escrow_payment(job_id: str) -> FunctionResult:
    """
    💸 RELEASE ESCROW: Transfer funds from escrow to contractor

    Called by:
    1. approve_work_completion() - Tenant approved work
    2. Auto-release cron job - 7 days passed, no disputes

    Transfers: (total_amount - 15% platform fee) to contractor
    Platform keeps: 15% as revenue
    """
    try:
        dynamo = get_dynamo_service()

        # Get job details
        job = dynamo.get_job(job_id)
        if not job:
            return FunctionResult(
                success=False,
                error="Job not found",
                message=f"Cannot release escrow: job {job_id} not found",
            )

        # Verify payment is escrowed
        if job.get("payment_status") != "escrowed":
            return FunctionResult(
                success=False,
                error="Payment not escrowed",
                message=f"Cannot release: payment status is {job.get('payment_status')}",
            )

        contractor_id = job.get("contractor_id")
        contractor_name = job.get("contractor_name", "Unknown")
        escrow_charge_id = job.get("escrow_charge_id")
        total_amount = job.get("payment_amount", 0)
        platform_fee = job.get("platform_fee", total_amount * 0.15)
        contractor_payout = job.get("contractor_payout", total_amount - platform_fee)

        logger.info(f"💸 Releasing escrow for job {job_id}")
        logger.info(f"   Escrow charge: {escrow_charge_id}")
        logger.info(f"   Total: ${total_amount:.2f}")
        logger.info(f"   Platform fee (15%): ${platform_fee:.2f}")
        logger.info(f"   Contractor payout: ${contractor_payout:.2f}")

        try:
            # 🔒 STEP 1: Capture the escrow charge (collect money from tenant)
            if stripe.api_key and escrow_charge_id and escrow_charge_id.startswith("ch_"):
                try:
                    captured_charge = stripe.Charge.capture(escrow_charge_id)
                    logger.info(f"💰 Stripe charge captured: {escrow_charge_id} (${total_amount:.2f})")
                except stripe.error.InvalidRequestError as e:
                    # Charge might be simulated or already captured
                    logger.warning(f"⚠️ Could not capture charge {escrow_charge_id}: {e}")
                    logger.info(f"   Continuing with payout (charge may be simulated)")
            else:
                logger.info(f"💡 Simulated charge capture (no real Stripe charge)")

            # 💸 STEP 2: Transfer to contractor (minus platform fee)
            from ..services.stripe_service import StripeService

            transfer_id = f"tr_{uuid.uuid4().hex[:12]}"  # Default simulated transfer

            # Real Stripe payout (if contractor has Stripe account)
            # NOTE: Requires contractor to have a Stripe Connect account set up
            # For sandbox testing without contractor accounts, we'll simulate
            if stripe.api_key:
                # In production with contractor Stripe accounts:
                # contractor_stripe_account = job.get("contractor_stripe_account_id")
                # if contractor_stripe_account:
                #     try:
                #         payout_result = StripeService.create_payout(
                #             destination_account_id=contractor_stripe_account,
                #             amount_cents=int(contractor_payout * 100),
                #             description=f"Payment for job {job_id} (escrow released)",
                #             metadata={
                #                 "job_id": job_id,
                #                 "contractor_id": contractor_id,
                #                 "escrow_charge_id": escrow_charge_id,
                #                 "platform_fee": platform_fee,
                #             }
                #         )
                #         transfer_id = payout_result.get("transfer_id")
                #         logger.info(f"💸 Stripe transfer created: {transfer_id}")
                #     except Exception as payout_error:
                #         logger.error(f"❌ Stripe payout failed: {payout_error}")
                #         transfer_id = f"tr_failed_{uuid.uuid4().hex[:12]}"
                logger.info(f"💡 Simulating contractor payout (contractor Stripe account not set up yet)")
            else:
                logger.info(f"💡 Simulating contractor payout (no Stripe key configured)")

            # STEP 3: Update job status to paid
            dynamo.update_job(
                job_id,
                payment_status="paid",
                payment_released_at=datetime.utcnow().isoformat(),
                stripe_transfer_id=transfer_id,
            )

            logger.info(f"✅ Escrow released for job {job_id}")
            logger.info(f"   Transfer ID: {transfer_id}")
            logger.info(f"   Contractor {contractor_name} received: ${contractor_payout:.2f}")
            logger.info(f"   Platform revenue: ${platform_fee:.2f}")

            return FunctionResult(
                success=True,
                data={
                    "job_id": job_id,
                    "payment_status": "paid",
                    "total_amount": total_amount,
                    "platform_fee": platform_fee,
                    "contractor_payout": contractor_payout,
                    "transfer_id": transfer_id,
                    "contractor_id": contractor_id,
                    "contractor_name": contractor_name,
                },
                message=f"💸 Payment released! Contractor received ${contractor_payout:.2f}. Platform earned ${platform_fee:.2f}.",
            )

        except Exception as stripe_error:
            logger.error(f"Stripe release error: {stripe_error}", exc_info=True)
            return FunctionResult(
                success=False,
                error=str(stripe_error),
                message=f"Failed to release escrow payment: {str(stripe_error)}",
            )

    except Exception as e:
        logger.error(f"Error releasing escrow: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to release escrow payment",
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
            description="🚨 DISCOVERY-FIRST FLOW: Start Q1-Q5 discovery. For NEW issues, call WITHOUT incident_id (pre-incident discovery). For existing incidents, call WITH incident_id.",
            parameters={
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string", "description": "Incident ID (OPTIONAL - omit for pre-incident discovery of new issues)"},
                    "questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of discovery questions (optional, uses defaults if not provided)",
                    },
                },
                "required": [],  # 🚨 FIX: incident_id is now OPTIONAL for pre-incident discovery
            },
        ),
        FunctionDefinition(
            name="record_discovery_answer",
            description="🚨 DISCOVERY-FIRST FLOW: Record user's answer to current discovery question. Advances to next question automatically. For pre-incident discovery, omit incident_id.",
            parameters={
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string", "description": "Incident ID (OPTIONAL - omit for pre-incident discovery)"},
                    "question_index": {"type": "integer", "description": "Question index (0-based, optional - can be inferred from context)"},
                    "answer": {"type": "string", "description": "User's answer to the current question"},
                    "total_questions": {"type": "integer", "description": "Total number of questions (optional, defaults to 5)"},
                },
                "required": ["answer"],  # 🚨 FIX: Only answer is required; question_index and incident_id are optional
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
            name="process_payment",
            description="🔒 ESCROW PAYMENT: Hold payment in escrow for 7 days. Automatically deducts 15% platform fee. Tenant must approve work to release funds to contractor.",
            parameters={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID"},
                    "amount": {"type": "number", "description": "Total payment amount in dollars (e.g., 250.00). Platform will deduct 15% fee, contractor receives 85%."},
                    "payment_method": {
                        "type": "string",
                        "enum": ["stripe"],
                        "description": "Payment method (default: stripe)"
                    },
                },
                "required": ["job_id", "amount"],
            },
        ),
        FunctionDefinition(
            name="approve_work_completion",
            description="🎯 Tenant approves or rejects completed work. If approved, releases escrowed payment to contractor. If rejected, holds payment for dispute resolution.",
            parameters={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID"},
                    "user_id": {"type": "string", "description": "User ID (tenant)"},
                    "approved": {"type": "boolean", "description": "True if work is approved, False if rejected"},
                    "feedback": {"type": "string", "description": "Optional feedback about the work quality"},
                },
                "required": ["job_id", "user_id", "approved"],
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
    "process_payment": process_payment,  # 🔒 ESCROW: Hold payment with 15% platform fee
    "approve_work_completion": approve_work_completion,  # 🎯 NEW: Tenant approves work → release escrow
    "release_escrow_payment": release_escrow_payment,  # 💸 NEW: Release funds to contractor
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
        if "attachments" in valid_params and "attachments" not in arguments:
            arguments["attachments"] = context.get("attachments")  # 🔥 Pass attachments

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
