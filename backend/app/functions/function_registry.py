"""
Universal function registry for LLM orchestrator.
Contains all callable functions with schemas and implementations.
"""
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
from ..models.orchestrator_schemas import (
    FunctionDefinition,
    FunctionResult,
    IncidentResult,
    JobResult,
    BidResult,
)
from ..services.dynamo_service import get_dynamo_service
from ..services.stream_bot import get_stream_bot
from ..services.card_builder import (
    incident_card,
    discovery_card,
    work_order_card,
    bids_card,
    completion_card,
)
from ..services.incident_flow import generate_contractor_bids
from ..utils.logging import get_logger

logger = get_logger(__name__)

# ==================== DISCOVERY QUESTIONS ====================

DEFAULT_DISCOVERY_QUESTIONS = [
    "Is the issue still occurring right now?",
    "Where exactly is the problem located in your unit?",
    "When did you first notice this issue?",
    "Are there any safety hazards (water near electricity, gas smell, etc.)?",
]

# ==================== FUNCTION IMPLEMENTATIONS ====================


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
        dynamo = get_dynamo_service()
        bot = get_stream_bot()

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
            "media_urls": [],
        }

        # Save to DynamoDB
        await dynamo.create_incident(incident_data)

        # Send incident card to Stream Chat
        await bot.send_incident_card(
            channel_id=channel_id,
            incident_id=incident_id,
            title=title,
            category=category,
            severity=severity,
            urgency=urgency,
            description=description,
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

        updates = {}
        if status:
            updates["status"] = status
        updates.update(kwargs)
        updates["updated_at"] = datetime.utcnow().isoformat()

        await dynamo.update_incident_status(
            incident_id=incident_id,
            status=status or "detected",
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
        incident = await dynamo.get_incident(incident_id, user_id)

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

        await dynamo.update_incident_status(
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
    questions: Optional[List[str]] = None,
) -> FunctionResult:
    """Start discovery question flow"""
    try:
        bot = get_stream_bot()

        discovery_questions = questions or DEFAULT_DISCOVERY_QUESTIONS

        # Send discovery card with first question
        await bot.send_discovery_card(
            channel_id=channel_id,
            incident_id=incident_id,
            question=discovery_questions[0],
            question_index=0,
            total_questions=len(discovery_questions),
        )

        logger.info(f"Started discovery for incident {incident_id}")

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
    total_questions: int,
) -> FunctionResult:
    """Record a discovery answer and send next question"""
    try:
        bot = get_stream_bot()
        next_index = question_index + 1

        # Update discovery card with answer
        await bot.update_discovery_progress(
            channel_id=channel_id,
            incident_id=incident_id,
            answered=next_index,
            total=total_questions,
        )

        # Check if discovery is complete
        if next_index >= total_questions:
            logger.info(f"Discovery completed for incident {incident_id}")
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
            message=f"Discovery answer {question_index} recorded",
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
        bot = get_stream_bot()

        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()

        # Get incident details
        incident = await dynamo.get_incident(incident_id, user_id)
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
        await dynamo.create_job(job_data)

        # Update incident status
        await dynamo.update_incident_status(
            incident_id=incident_id,
            status="work_order",
            user_id=user_id,
        )

        # Send work order card
        await bot.send_work_order_card(
            channel_id=channel_id,
            job_id=job_id,
            incident_id=incident_id,
            title=title,
            category=incident.get("category"),
            estimated_cost=estimated_cost,
            urgency=urgency or incident.get("urgency"),
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

        await dynamo.update_job(job_id, **updates)

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
        job = await dynamo.get_job(job_id)

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

        await dynamo.update_job(
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
        bot = get_stream_bot()

        # Generate mock bids (in production, this would query real contractors)
        bids = generate_contractor_bids(category)

        # Send bids card
        await bot.send_bids_card(
            channel_id=channel_id,
            job_id=job_id,
            bids=bids,
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
        bids = await dynamo.list_bids_by_job(job_id)

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
        await dynamo.update_bid_status(bid_id, "accepted")

        # Get bid details to assign contractor
        bids = await dynamo.list_bids_by_job(job_id)
        accepted_bid = next((b for b in bids if b.get("bid_id") == bid_id), None)

        if accepted_bid:
            # Assign contractor to job
            await dynamo.update_job(
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
        bot = get_stream_bot()
        dynamo = get_dynamo_service()

        # Get job and incident details
        job = await dynamo.get_job(job_id)
        incident = await dynamo.get_incident(incident_id, job.get("landlord_id", ""))

        # Send approval request to landlord
        await bot.send_approval_request(
            channel_id=channel_id,
            job_id=job_id,
            incident_id=incident_id,
            title=job.get("title"),
            category=job.get("category"),
            estimated_cost=job.get("estimated_cost"),
            urgency=job.get("urgency"),
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
            await dynamo.update_job(
                job_id,
                status="approved",
                approval_status="approved",
                updated_at=datetime.utcnow().isoformat(),
            )
            message_text = f"Job {job_id} approved"
        else:
            await dynamo.update_job(
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
        incidents = await dynamo.list_incidents_by_tenant(user_id)

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
        property_info = await dynamo.get_property(property_id)

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
    if function_name not in FUNCTION_IMPLEMENTATIONS:
        return FunctionResult(
            success=False,
            error=f"Function {function_name} not found",
            message=f"Unknown function: {function_name}",
        )

    func = FUNCTION_IMPLEMENTATIONS[function_name]

    # Inject context fields into arguments
    arguments["user_id"] = context.get("user_id")
    arguments["channel_id"] = context.get("channel_id")

    try:
        result = await func(**arguments)
        return result
    except TypeError as e:
        logger.error(f"Function {function_name} argument error: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=f"Invalid arguments: {str(e)}",
            message=f"Failed to execute {function_name}: invalid arguments",
        )
    except Exception as e:
        logger.error(f"Function {function_name} execution error: {e}", exc_info=True)
        return FunctionResult(
            success=False,
            error=str(e),
            message=f"Failed to execute {function_name}",
        )
