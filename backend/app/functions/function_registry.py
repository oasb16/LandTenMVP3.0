"""
Universal function registry for LLM orchestrator.
Contains all callable functions with schemas and implementations.
"""
from typing import Dict, Any, List, Optional
import uuid
import logging
import inspect
from datetime import datetime
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
from ..utils.discovery_questions import (
    get_discovery_questions,
    get_first_discovery_question,
    should_ask_discovery_questions,
)
from collections import defaultdict

logger = logging.getLogger(__name__)

# ==================== DISCOVERY QUESTIONS ====================

DEFAULT_DISCOVERY_QUESTIONS = [
    "Is the issue still occurring right now?",
    "Where exactly is the problem located in your unit?",
    "When did you first notice this issue?",
    "Are there any safety hazards (water near electricity, gas smell, etc.)?",
]

# Global incident deduplication cache (incident fingerprints)
# Maps user_id -> set of incident fingerprints (title+category+severity hash)
_recent_incidents = defaultdict(set)

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
        # IDEMPOTENCY CHECK: Prevent duplicate incident creation
        # Check if user already has an active incident in the same category
        dynamo = get_dynamo_service()

        logger.info(f"🔍 Checking for duplicate incidents for user {user_id} in category {category}")
        recent_incidents = dynamo.list_incidents_by_tenant(user_id)

        # Check for active incidents in same category
        for inc in recent_incidents:
            inc_status = inc.get("status")
            inc_category = inc.get("category")
            inc_id = inc.get("incident_id")
            inc_title = inc.get("title", "")

            # Skip completed incidents
            if inc_status == "completed":
                continue

            # Check if same category
            if inc_category == category:
                # Check if title is very similar (simple keyword match)
                title_words = set(title.lower().split())
                inc_title_words = set(inc_title.lower().split())
                common_words = title_words.intersection(inc_title_words)

                # If > 50% overlap in meaningful words, likely duplicate
                min_len = min(len(title_words), len(inc_title_words))
                if min_len > 0 and len(common_words) / min_len > 0.5:
                    logger.warning(f"⚠️ Duplicate incident detected: {inc_id} (status={inc_status})")
                    return FunctionResult(
                        success=False,
                        error="Duplicate incident",
                        data={
                            "incident_id": inc_id,
                            "status": inc_status,
                            "title": inc_title,
                            "category": inc_category
                        },
                        message=f"You already have an open {category} incident ({inc_id}): '{inc_title}'. Are you providing more details about that issue, or is this a different problem?",
                    )

                # Same category, but different specific issue
                # Log but allow creation
                logger.info(f"ℹ️ Creating new {category} incident despite existing {inc_id} (different specific issue)")

        # Use fingerprinting as backup check
        import hashlib
        fingerprint = hashlib.md5(
            f"{title.lower().strip()}:{category}:{severity}".encode()
        ).hexdigest()[:8]

        # Mark fingerprint as recent (prevent rapid duplicates)
        _recent_incidents[user_id].add(fingerprint)

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

        # Send incident card with collapsed description
        collapsed_description = collapse_text(description, limit=300)

        incident_card_text = (
            f"📄 **Incident Reported**\n\n"
            f"**Incident ID:** {incident_id}\n"
            f"**Title:** {title}\n"
            f"**Category:** {category}\n"
            f"**Severity:** {severity}\n"
            f"**Urgency:** {urgency}\n\n"
            f"**Details:**\n{collapsed_description}\n\n"
            f"---\nWe'll gather more details to resolve this quickly."
        )

        bot.send_ai_message(
            channel_id=channel_id,
            persona="tenant",
            text=incident_card_text,
            metadata={
                "incident_id": incident_id,
                "type": "incident_created",
                "category": category,
                "severity": severity,
                "urgency": urgency,
                "title": title,
                "success": True,
            },
        )

        # CRITICAL FIX: Only send first discovery question if appropriate
        # DO NOT send if orchestrator will handle it (prevents duplicates)
        # Check if we should auto-start discovery
        auto_start_discovery = should_ask_discovery_questions(category, severity)

        if auto_start_discovery:
            logger.info(f"✅ Auto-starting discovery for incident {incident_id}")

            first_question = get_first_discovery_question(category, severity, description)
            discovery_text = format_discovery_progress(
                question_index=0,
                total_questions=5,  # Default to 5 questions
                current_question=first_question,
            )
            bot.send_ai_message(
                channel_id=channel_id,
                persona="tenant",
                text=discovery_text,
                metadata={
                    "incident_id": incident_id,
                    "type": "discovery_question",
                    "question_index": 0,
                },
            )

            # Update incident status to 'discovery' immediately
            dynamo.update_incident_status(
                incident_id=incident_id, status="discovery", user_id=user_id
            )

            # CRITICAL: Return flag indicating discovery was auto-started
            # This prevents the orchestrator from calling start_discovery again
            return FunctionResult(
                success=True,
                data={
                    "incident_id": incident_id,
                    "status": "discovery",  # Changed from "detected"
                    "title": title,
                    "category": category,
                    "severity": severity,
                    "urgency": urgency,
                    "created_at": now,
                    "discovery_auto_started": True,  # Flag for orchestrator
                },
                message=f"Incident {incident_id} created and discovery started automatically",
            )

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
    category: Optional[str] = None,
    severity: Optional[str] = None,
    user_message: Optional[str] = None,
    questions: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> FunctionResult:
    """Start discovery question flow with category-specific questions"""
    try:
        bot = get_bot()
        dynamo = get_dynamo_service()

        # Get incident details if category/severity not provided
        incident = dynamo.get_incident(incident_id, user_id)

        # Check if incident is closed/resolved
        if incident and incident.get("status") == "completed":
            logger.info(f"⚠️ Cannot start discovery for closed incident {incident_id}")
            return FunctionResult(
                success=False,
                error="Incident is already closed",
                message="This incident has been resolved. Please create a new incident if you have a new issue.",
            )

        # Check if discovery already in progress (status = discovery or work_order)
        if incident and incident.get("status") in ["discovery", "work_order"]:
            logger.info(f"ℹ️ Discovery already started for incident {incident_id}")

        if incident:
            category = category or incident.get("category", "general")
            severity = severity or incident.get("severity", "medium")
            user_message = user_message or incident.get("description", "")
        else:
            category = category or "general"
            severity = severity or "medium"
            user_message = user_message or ""

        # Update incident status to 'discovery' if not already
        if incident and incident.get("status") not in ["discovery", "work_order", "completed"]:
            dynamo.update_incident_status(
                incident_id=incident_id,
                status="discovery",
                user_id=user_id or incident.get("user_id"),
            )

        # Get adaptive questions based on category and severity
        discovery_questions = questions or get_discovery_questions(
            category=category,
            severity=severity,
            user_message=user_message or "",
            max_questions=5,
        )

        if not discovery_questions:
            discovery_questions = DEFAULT_DISCOVERY_QUESTIONS

        # Send discovery question with progress bar
        total = len(discovery_questions)
        filled = 1
        empty = total - filled
        progress_bar = "▓" * filled + "░" * empty

        discovery_text = (
            f"🔍 **Discovery Question**\n\n"
            f"Progress: [{progress_bar}] 1/{total}\n\n"
            f"**Q1:** {discovery_questions[0]}\n\n"
            f"Please answer to help us understand the issue better."
        )

        bot.send_ai_message(
            channel_id=channel_id,
            persona="tenant",
            text=discovery_text,
            metadata={
                "incident_id": incident_id,
                "type": "discovery_question",
                "question_index": 0,
                "total_questions": len(discovery_questions),
            },
        )

        logger.info(f"Started discovery for incident {incident_id} with {len(discovery_questions)} questions")

        return FunctionResult(
            success=True,
            data={
                "incident_id": incident_id,
                "questions": discovery_questions,
                "current_question": discovery_questions[0],
                "question_index": 0,
                "total_questions": len(discovery_questions),
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
    """Record a discovery answer and send next question"""
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

        # Determine total questions
        if total_questions is None:
            total_questions = 5  # Default

        # CRITICAL FIX: Save answer to DynamoDB incident
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

        # Acknowledge answer progress
        progress_msg = f"✅ Answer recorded ({next_index}/{total_questions})"
        if next_index < total_questions:
            progress_msg += f"\n\nNext question coming..."
        else:
            progress_msg += f"\n\n🎯 Discovery complete! Creating work order..."

        bot.send_ai_message(
            channel_id=channel_id,
            persona="tenant",
            text=progress_msg,
            metadata={"incident_id": incident_id, "question_index": next_index},
        )

        # Check if discovery is complete
        if next_index >= total_questions:
            logger.info(f"✅ Discovery completed for incident {incident_id}")

            # CRITICAL FIX: Transition incident status to 'discovery_complete'
            dynamo.update_incident_status(
                incident_id=incident_id,
                status="discovery_complete",
                user_id=user_id,
            )

            return FunctionResult(
                success=True,
                data={
                    "incident_id": incident_id,
                    "question_index": question_index,
                    "answer": answer,
                    "discovery_complete": True,
                },
                message="Discovery questions completed",
            )

        # CRITICAL: Automatically send next question
        # Get discovery questions from context or generate new ones
        category = incident.get("category", "general")
        severity = incident.get("severity", "medium")
        description = incident.get("description", "")

        from ..utils.discovery_questions import get_discovery_questions
        questions = get_discovery_questions(category, severity, description, max_questions=total_questions)

        if next_index < len(questions):
            next_question = questions[next_index]

            # Send next discovery question
            from ..utils.message_cards import format_discovery_progress
            discovery_text = format_discovery_progress(
                question_index=next_index,
                total_questions=total_questions,
                current_question=next_question,
            )

            bot.send_ai_message(
                channel_id=channel_id,
                persona="tenant",
                text=discovery_text,
                metadata={
                    "incident_id": incident_id,
                    "type": "discovery_question",
                    "question_index": next_index,
                },
            )

            logger.info(f"✅ Sent discovery question {next_index+1}/{total_questions} for incident {incident_id}")
        else:
            logger.warning(f"⚠️ No question available for index {next_index}")

        # Send next question
        logger.info(f"Recorded discovery answer {question_index} for incident {incident_id}")

        return FunctionResult(
            success=True,
            data={
                "incident_id": incident_id,
                "question_index": question_index,
                "answer": answer,
                "discovery_complete": False,
                "next_question_index": next_index,
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


async def create_work_order(
    incident_id: str,
    title: str,
    estimated_cost: str,
    user_id: str,
    channel_id: str,
    urgency: Optional[str] = None,
) -> FunctionResult:
    """Create a work order (job) from an incident"""
    try:
        dynamo = get_dynamo_service()
        bot = get_bot()

        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()

        # Get incident details
        incident = dynamo.get_incident(incident_id, user_id)
        if not incident:
            return FunctionResult(
                success=False,
                error="Incident not found",
                message=f"Cannot create work order: incident {incident_id} not found",
            )

        job_data = {
            "job_id": job_id,
            "incident_id": incident_id,
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

        # Save to DynamoDB
        dynamo.create_job(job_data)

        # Update incident status
        dynamo.update_incident_status(
            incident_id=incident_id,
            status="work_order",
            user_id=user_id,
        )

        # Send beautifully formatted work order card
        work_order_text = format_work_order_card({
            "job_id": job_id,
            "title": title,
            "category": incident.get("category"),
            "estimated_cost": estimated_cost,
            "urgency": urgency or incident.get("urgency"),
        })

        bot.send_ai_message(
            channel_id=channel_id,
            persona="tenant",
            text=work_order_text,
            metadata={
                "job_id": job_id,
                "incident_id": incident_id,
                "type": "work_order",
                "title": title,
                "category": incident.get("category"),
            },
        )

        logger.info(f"Created work order {job_id} for incident {incident_id}")

        return FunctionResult(
            success=True,
            data={
                "job_id": job_id,
                "incident_id": incident_id,
                "status": "created",
                "title": title,
                "estimated_cost": estimated_cost,
                "created_at": now,
            },
            message=f"Work order {job_id} created successfully",
        )

    except Exception as e:
        logger.error(f"Error creating work order: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message="Failed to create work order",
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

        # Send bids notification
        bids_summary = f"📊 Received {len(bids)} Contractor Bids\n\n"
        for i, bid in enumerate(bids[:3], 1):  # Show top 3
            bids_summary += f"{i}. {bid.get('contractor_name', 'Unknown')} - ${bid.get('quote', 0)} (⭐ {bid.get('rating', 0)})\n"
        if len(bids) > 3:
            bids_summary += f"\n+{len(bids) - 3} more bids available"

        bot.send_ai_message(
            channel_id=channel_id,
            persona="landlord",
            text=bids_summary,
            metadata={"job_id": job_id, "bid_count": len(bids), "type": "bids"},
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

        # Send approval request to landlord
        approval_msg = f"📋 **Approval Required**\n\n**Job:** {job.get('title')}\n**Category:** {job.get('category')}\n**Estimated Cost:** ${job.get('estimated_cost')}\n**Urgency:** {job.get('urgency')}\n\nPlease review and approve or reject this work order."

        bot.send_ai_message(
            channel_id=channel_id,
            persona="landlord",
            text=approval_msg,
            metadata={"job_id": job_id, "incident_id": incident_id, "type": "approval_request"},
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


# ==================== FUNCTION REGISTRY ====================

def get_function_definitions() -> List[FunctionDefinition]:
    """Get all function definitions for LLM tool calling"""
    return [
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
                        "enum": ["detected", "discovery", "work_order", "in_progress", "completed"],
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
            name="create_work_order",
            description="Create a work order (job) from an incident. Use after discovery is complete.",
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
    ]


# Function name to implementation mapping
FUNCTION_IMPLEMENTATIONS = {
    "create_incident": create_incident,
    "update_incident": update_incident,
    "get_incident": get_incident,
    "close_incident": close_incident,
    "start_discovery": start_discovery,
    "record_discovery_answer": record_discovery_answer,
    "get_discovery_status": get_discovery_status,
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

    # Dynamic tool sandbox: ONLY trigger for explicit dynamic tool patterns
    # Must be VERY specific to avoid treating normal functions as dynamic tools
    if function_name and (
        function_name not in FUNCTION_IMPLEMENTATIONS and (
            function_name.startswith(("run_code", "eval_js", "exec_python", "execute_code",
                                     "sandbox_", "plugin_", "dynamic_tool_")) or
            # Also catch common LLM hallucinations
            function_name.startswith(("get_incident_by_", "search_", "find_",
                                     "query_", "lookup_", "fetch_"))
        )
    ):
        logger.info(f"Dynamic tool sandbox triggered for: {function_name}")
        logger.warning(f"⚠️ LLM hallucinated unknown function: {function_name}")
        return FunctionResult(
            success=True,
            data={
                "type": "dynamic_tool_request",
                "tool_idea": function_name,
                "arguments": arguments,
                "context": context,
            },
            error=None,
            message=f"Dynamic tool request captured: {function_name}",
        )

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
