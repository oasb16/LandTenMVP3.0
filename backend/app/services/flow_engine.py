"""
Flow Engine — orchestrates conversation stage transitions.
Determines next stage based on context, intent, persona, and policies.
"""

import logging
from typing import Dict, Any

from app.services.policy_validator import validate_action, PolicyValidationResult

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
    """Decide what flow stage should follow current intent."""
    lowered = message.lower()

    if "photo" in lowered or "picture" in lowered:
        return "discovery.response"
    if intent == "incident.report":
        return "discovery.response"
    if intent == "discovery.response" and "approve" in lowered:
        return "approval.decision"
    if intent == "job.request" and any(keyword in lowered for keyword in ["bid", "quote", "contractor"]):
        return "bids.request"

    options = FLOW_GRAPH.get(intent, [])
    if options:
        return options[0]
    return "general.chat"


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
