"""
Flow State Machine - Strict State Transition Validation

This module enforces strict state transitions and prevents invalid flow progressions.
It works in conjunction with the intent classifier to ensure flow consistency.

Valid Flow Stages:
    idle → discovery → job-ready → approval_pending → job → in_progress → completed → paid → idle

State Transition Rules:
    - Discovery must complete before job creation
    - Approval must precede job start (if required)
    - Jobs cannot skip stages
    - No backwards transitions (except terminal → idle)
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

logger = logging.getLogger(__name__)


class FlowStage(str, Enum):
    """Valid flow stages in the maintenance workflow."""
    IDLE = "idle"
    DISCOVERY = "discovery"
    JOB_READY = "job-ready"
    APPROVAL_PENDING = "approval_pending"
    JOB = "job"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAID = "paid"


class TransitionReason(str, Enum):
    """Reasons for transition success or failure."""
    VALID = "valid_transition"
    INVALID = "invalid_transition"
    BLOCKED = "blocked_by_rules"
    ALREADY_AT_STAGE = "already_at_stage"
    MISSING_PREREQUISITE = "missing_prerequisite"


# Valid state transitions (from → to)
VALID_TRANSITIONS: Dict[FlowStage, List[FlowStage]] = {
    FlowStage.IDLE: [
        FlowStage.DISCOVERY,  # Start discovery after incident report
    ],
    FlowStage.DISCOVERY: [
        FlowStage.JOB_READY,  # Discovery complete
        FlowStage.IDLE,  # Cancel/abort discovery
    ],
    FlowStage.JOB_READY: [
        FlowStage.APPROVAL_PENDING,  # Need approval
        FlowStage.JOB,  # Auto-approved or no approval needed
        FlowStage.IDLE,  # Cancel job creation
    ],
    FlowStage.APPROVAL_PENDING: [
        FlowStage.JOB,  # Approved
        FlowStage.IDLE,  # Rejected
    ],
    FlowStage.JOB: [
        FlowStage.IN_PROGRESS,  # Contractor starts work
        FlowStage.IDLE,  # Job cancelled
    ],
    FlowStage.IN_PROGRESS: [
        FlowStage.COMPLETED,  # Work finished
        FlowStage.IDLE,  # Job cancelled mid-work
    ],
    FlowStage.COMPLETED: [
        FlowStage.PAID,  # Payment processed
        FlowStage.IDLE,  # Payment failed/cancelled
    ],
    FlowStage.PAID: [
        FlowStage.IDLE,  # Return to idle after payment
    ],
}


# Prerequisites for each stage (what must be present in context)
STAGE_PREREQUISITES: Dict[FlowStage, List[str]] = {
    FlowStage.DISCOVERY: ["active_incident_id"],
    FlowStage.JOB_READY: ["active_incident_id"],
    FlowStage.APPROVAL_PENDING: ["active_job_id"],
    FlowStage.JOB: ["active_job_id"],
    FlowStage.IN_PROGRESS: ["active_job_id"],
    FlowStage.COMPLETED: ["active_job_id"],
    FlowStage.PAID: ["active_job_id"],
}


def validate_transition(
    current_stage: str,
    new_stage: str,
    context: Optional[Dict[str, Any]] = None
) -> Tuple[bool, TransitionReason, Optional[str]]:
    """
    Validate if a stage transition is allowed.

    Args:
        current_stage: Current flow stage
        new_stage: Proposed new stage
        context: Optional context for prerequisite checking

    Returns:
        Tuple of (is_valid, reason, error_message)
    """
    # Normalize stage strings
    try:
        current = FlowStage(current_stage)
        new = FlowStage(new_stage)
    except ValueError as e:
        return False, TransitionReason.INVALID, f"Invalid stage: {e}"

    # Check if already at target stage
    if current == new:
        logger.debug(f"[flow-state-machine] Already at stage '{current_stage}'")
        return True, TransitionReason.ALREADY_AT_STAGE, None

    # Check if transition is in allowed list
    allowed_transitions = VALID_TRANSITIONS.get(current, [])

    if new not in allowed_transitions:
        error_msg = (
            f"Cannot transition from '{current_stage}' to '{new_stage}'. "
            f"Allowed transitions: {[s.value for s in allowed_transitions]}"
        )
        logger.warning(f"[flow-state-machine] ❌ {error_msg}")
        return False, TransitionReason.INVALID, error_msg

    # Check prerequisites if context provided
    if context:
        is_valid, error_msg = _check_prerequisites(new, context)
        if not is_valid:
            logger.warning(f"[flow-state-machine] ❌ Prerequisite check failed: {error_msg}")
            return False, TransitionReason.MISSING_PREREQUISITE, error_msg

    logger.info(f"[flow-state-machine] ✅ Valid transition: {current_stage} → {new_stage}")
    return True, TransitionReason.VALID, None


def _check_prerequisites(stage: FlowStage, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Check if context has required prerequisites for a stage.

    Args:
        stage: Target stage
        context: Context dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    required = STAGE_PREREQUISITES.get(stage, [])

    for prereq in required:
        value = context.get(prereq)
        if not value:
            return False, f"Missing prerequisite '{prereq}' for stage '{stage.value}'"

    return True, None


def get_next_stage_for_intent(
    intent: str,
    current_stage: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Determine next stage based on intent and current stage.

    This method provides intelligent stage progression based on intent classification.

    Args:
        intent: Detected intent
        current_stage: Current flow stage
        context: Optional context for decision-making

    Returns:
        Next stage
    """
    # Intent to stage mapping
    intent_stage_map = {
        # Incident starts discovery
        "incident.report": FlowStage.DISCOVERY.value,

        # Discovery responses stay in discovery
        "discovery.response": FlowStage.DISCOVERY.value,
        "discovery.continue": FlowStage.DISCOVERY.value,

        # Job request transitions to approval or job
        "job.request": _determine_job_stage(context),

        # Approval decision transitions to job or idle
        "approval.decision": _determine_approval_result_stage(context),

        # Job status checks stay in current job stage
        "job.status": current_stage if "job" in current_stage else FlowStage.JOB.value,
        "job.inquiry": current_stage if "job" in current_stage else FlowStage.JOB.value,
    }

    next_stage = intent_stage_map.get(intent, current_stage)

    logger.debug(
        f"[flow-state-machine] Intent '{intent}' in stage '{current_stage}' → '{next_stage}'"
    )

    return next_stage


def _determine_job_stage(context: Optional[Dict[str, Any]]) -> str:
    """
    Determine if job should go to approval_pending or directly to job.

    Args:
        context: Context with job info

    Returns:
        Stage: approval_pending or job
    """
    if not context:
        return FlowStage.JOB.value

    # Check if approval is required
    requires_approval = context.get("requires_approval", False)

    # Check cost threshold
    estimated_cost = context.get("estimated_cost", 0)
    approval_threshold = context.get("approval_threshold", 500)

    if requires_approval or estimated_cost > approval_threshold:
        return FlowStage.APPROVAL_PENDING.value
    else:
        return FlowStage.JOB.value


def _determine_approval_result_stage(context: Optional[Dict[str, Any]]) -> str:
    """
    Determine next stage after approval decision.

    Args:
        context: Context with approval result

    Returns:
        Stage: job (if approved) or idle (if rejected)
    """
    if not context:
        return FlowStage.IDLE.value

    approval_status = context.get("approval_status", "pending")

    if approval_status == "approved":
        return FlowStage.JOB.value
    else:
        return FlowStage.IDLE.value


def can_start_new_incident(context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Check if a new incident can be started.

    Rules:
    - Cannot start new incident if one is active
    - Cannot start new incident during discovery
    - Can start if idle or previous incident completed

    Args:
        context: Current context

    Returns:
        Tuple of (can_start, reason)
    """
    flow_state = context.get("flow_state", {})
    stage = flow_state.get("stage", "idle")
    active_incident = context.get("active_incident_id") or context.get("active_incident")

    # Check if currently in a flow
    if stage not in [FlowStage.IDLE.value, FlowStage.COMPLETED.value, FlowStage.PAID.value]:
        return False, f"Cannot start new incident - currently in stage '{stage}'"

    # Check if incident is active
    if active_incident:
        return False, f"Cannot start new incident - incident '{active_incident}' is active"

    return True, None


def can_start_new_job(context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Check if a new job can be started.

    Rules:
    - Cannot start new job if one is active
    - Must be in job-ready stage
    - Must have completed discovery

    Args:
        context: Current context

    Returns:
        Tuple of (can_start, reason)
    """
    flow_state = context.get("flow_state", {})
    stage = flow_state.get("stage", "idle")
    active_job = context.get("active_job_id") or context.get("active_job")

    # Check if job is active
    if active_job and stage not in [FlowStage.IDLE.value, FlowStage.JOB_READY.value]:
        return False, f"Cannot start new job - job '{active_job}' is active in stage '{stage}'"

    # Check if in correct stage
    if stage not in [FlowStage.JOB_READY.value, FlowStage.IDLE.value]:
        return False, f"Cannot start job - must be in 'job-ready' stage (currently '{stage}')"

    # Check if discovery completed
    question_index = flow_state.get("question_index")
    if stage == FlowStage.JOB_READY.value and question_index is None:
        return False, "Cannot start job - discovery not completed"

    return True, None


def get_stage_description(stage: str) -> str:
    """
    Get a human-readable description of a stage.

    Args:
        stage: Flow stage

    Returns:
        Description string
    """
    descriptions = {
        FlowStage.IDLE.value: "No active flow",
        FlowStage.DISCOVERY.value: "Gathering information about the incident",
        FlowStage.JOB_READY.value: "Ready to create work order",
        FlowStage.APPROVAL_PENDING.value: "Waiting for landlord approval",
        FlowStage.JOB.value: "Job created, awaiting contractor assignment",
        FlowStage.IN_PROGRESS.value: "Contractor is working on the job",
        FlowStage.COMPLETED.value: "Work completed, awaiting payment",
        FlowStage.PAID.value: "Job paid, incident resolved",
    }

    return descriptions.get(stage, f"Unknown stage: {stage}")


def get_allowed_intents_for_stage(stage: str) -> List[str]:
    """
    Get list of allowed intents for a given stage.

    This mirrors the FLOW_STATE_RULES from intent_classifier.py.

    Args:
        stage: Flow stage

    Returns:
        List of allowed intent strings
    """
    stage_intent_map = {
        FlowStage.IDLE.value: [
            "incident.report",
            "greeting",
            "help",
            "general.chat"
        ],
        FlowStage.DISCOVERY.value: [
            "discovery.response",
            "discovery.continue"
        ],
        FlowStage.JOB_READY.value: [
            "job.request",
            "discovery.response",
            "general.chat"
        ],
        FlowStage.APPROVAL_PENDING.value: [
            "approval.decision"
        ],
        FlowStage.JOB.value: [
            "job.status",
            "job.inquiry",
            "general.chat"
        ],
        FlowStage.IN_PROGRESS.value: [
            "job.status",
            "general.chat"
        ],
        FlowStage.COMPLETED.value: [
            "approval.decision",  # Approve completion
            "general.chat"
        ],
        FlowStage.PAID.value: [
            "general.chat"
        ],
    }

    return stage_intent_map.get(stage, ["general.chat"])


# Export key functions
__all__ = [
    "FlowStage",
    "TransitionReason",
    "validate_transition",
    "get_next_stage_for_intent",
    "can_start_new_incident",
    "can_start_new_job",
    "get_stage_description",
    "get_allowed_intents_for_stage",
]
