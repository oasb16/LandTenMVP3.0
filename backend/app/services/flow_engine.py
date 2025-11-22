"""
Flow Engine — orchestrates conversation stage transitions.
Determines next stage based on context, intent, persona, and policies.
"""

import logging
from typing import Dict, Any

from ..services.policy_validator import validate_action, PolicyValidationResult

logger = logging.getLogger(__name__)

FLOW_GRAPH: Dict[str, list[str]] = {
    "incident.report": ["discovery.response", "incident.followup", "diy.suggestion"],
    "discovery.response": ["job.request", "incident.followup"],
    "job.request": ["approval.decision", "bids.request"],
    "approval.decision": ["completion.confirmation"],
}

STAGE_POLICY_ACTION = {
    "approval.decision": "approve_job",
    "job.request": "create_job",
    "bids.request": "view_bids",
    "incident.followup": "incident.followup",
    "diy.suggestion": "diy.suggestion",
}


def determine_next_stage(context: Dict[str, Any], intent: str, message: str, persona: str) -> str:
    """
    Decide what flow stage should follow current intent.

    Maps intents to stages according to AI Reasoning V2 pipeline.
    """
    lowered = message.lower()

    # SPECIAL CASE: meta.info_request and general.chat during active flows
    # These should preserve the current stage, not force to idle
    current_stage = context.get("flow_state", {}).get("stage", "idle")

    if intent == "meta.info_request":
        # Meta questions during active flows should NOT change the stage
        logger.info("[flow-engine] Intent 'meta.info_request' → Preserving current stage '%s'", current_stage)
        return current_stage

    if intent == "general.chat" and current_stage not in ["idle", "general.chat"]:
        # General chat during active flows should preserve the flow
        # (This is now classified correctly by intent_classifier, but we add safety here)
        logger.info("[flow-engine] Intent 'general.chat' in active flow → Preserving current stage '%s'", current_stage)
        return current_stage

    # Intent to stage mapping (aligned with ai_reasoning_v2 and intent_classifier)
    intent_to_stage_map = {
        # Incident starts discovery
        "incident.report": "discovery",
        "incident.followup": "discovery",

        # Discovery responses stay in discovery
        "discovery.response": "discovery",
        "discovery.continue": "discovery",

        # Job request goes to job (or approval if needed)
        "job.request": "job",
        "job.inquiry": "job",
        "job.status": "job",

        # Bids
        "bids.request": "bids",
        "bids.compare": "bids",

        # Approval
        "approval.request": "approval_pending",
        "approval.decision": "job",  # After approval, go to job

        # General - go to idle only if not in active flow
        "general.chat": "idle",
        "greeting": "idle",
        "help": "idle",
        "unclear": "idle",
    }

    # Get the stage from mapping
    next_stage = intent_to_stage_map.get(intent)

    if next_stage:
        logger.info("[flow-engine] Intent '%s' → Stage '%s'", intent, next_stage)
        return next_stage

    # Fallback: return intent as stage name
    logger.warning("[flow-engine] No mapping for intent '%s', using as stage", intent)
    return intent


def process_transition(
    user_id: str,
    channel_id: str,
    persona: str,
    intent: str,
    message: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate policy, compute next stage, and return updated flow package.
    """
    next_stage = determine_next_stage(context, intent, message, persona)
    action_name = STAGE_POLICY_ACTION.get(next_stage, next_stage)
    validation: PolicyValidationResult = validate_action(persona, action_name, context)

    logger.info(
        "[flow-engine] Transition: %s → %s | allowed=%s",
        intent,
        next_stage,
        validation.allowed,
    )

    return {
        "next_stage": next_stage,
        "allowed": validation.allowed,
        "violation_message": validation.message,
    }
