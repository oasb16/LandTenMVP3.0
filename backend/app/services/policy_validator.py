"""
Policy Validator - Persona-Based Policy Enforcement Layer

This module enforces company policies and persona-specific boundaries on all AI actions.
It ensures that AI creativity is bounded by business rules, compliance requirements,
and role-based permissions.

Features:
- Persona-specific policy enforcement (tenant, landlord, contractor)
- Action authorization checks
- Cost threshold validation
- Approval workflow enforcement
- Compliance and safety checks
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class Persona(str, Enum):
    """User personas with different policy boundaries."""
    TENANT = "tenant"
    LANDLORD = "landlord"
    CONTRACTOR = "contractor"


class PolicyViolation(Exception):
    """Raised when an action violates a policy."""
    pass


@dataclass
class PolicyValidationResult:
    allowed: bool
    message: Optional[str] = None


class PolicyValidator:
    """
    Validates actions against persona-specific policies.

    This class ensures that the AI agent operates within defined boundaries
    and doesn't perform unauthorized actions or violate business rules.
    """

    def __init__(self):
        """Initialize the policy validator with predefined policies."""
        self.policies = self._load_policies()
        logger.info("PolicyValidator initialized")

    def _load_policies(self) -> Dict[str, Dict[str, Any]]:
        """
        Load persona-specific policies.

        Returns:
            Dictionary of policies keyed by persona
        """
        return {
            Persona.TENANT.value: {
                "allowed_intents": [
                    "incident.report",
                    "incident.followup",
                    "discovery.response",
                "discovery.continue",
                "job.request",
                "job.inquiry",
                "job.status",
                    "general.chat",
                    "greeting",
                    "help"
                ],
                "forbidden_actions": [
                    "approve_job",
                    "approve_contractor",
                    "create_job_without_incident",
                    "modify_cost",
                    "assign_contractor",
                    "cancel_job"
                ],
                "can_create_incident": True,
                "can_approve_work": False,
                "can_view_bids": False,
                "can_request_maintenance": True,
                "requires_landlord_approval": True,
                "max_auto_approve_amount": 0,  # Tenants can't auto-approve
                "data_access": {
                    "can_view_own_incidents": True,
                    "can_view_all_incidents": False,
                    "can_view_jobs": True,
                    "can_view_bids": False,
                    "can_view_costs": False
                },
                "message_guidelines": {
                    "tone": "friendly, helpful, empathetic",
                    "can_provide_diy_tips": True,
                    "can_provide_cost_estimates": False,
                    "must_include_safety_warnings": True
                }
            },
            Persona.LANDLORD.value: {
                "allowed_intents": [
                    "incident.report",
                    "incident.followup",
                    "job.request",
                    "job.inquiry",
                    "job.status",
                    "bids.request",
                    "bids.compare",
                    "approval.request",
                    "approval.decision",
                    "general.chat",
                    "greeting",
                    "help"
                ],
                "forbidden_actions": [
                    # Landlords can do most things
                ],
                "can_create_incident": True,
                "can_approve_work": True,
                "can_view_bids": True,
                "can_request_maintenance": True,
                "requires_landlord_approval": False,
                "max_auto_approve_amount": 500,  # Can auto-approve up to $500
                "data_access": {
                    "can_view_own_incidents": True,
                    "can_view_all_incidents": True,
                    "can_view_jobs": True,
                    "can_view_bids": True,
                    "can_view_costs": True
                },
                "message_guidelines": {
                    "tone": "professional, efficient, business-focused",
                    "can_provide_diy_tips": False,
                    "can_provide_cost_estimates": True,
                    "must_include_safety_warnings": False
                }
            },
            Persona.CONTRACTOR.value: {
                "allowed_intents": [
                    "job.inquiry",
                    "job.status",
                    "bids.request",
                    "general.chat",
                    "greeting",
                    "help"
                ],
                "forbidden_actions": [
                    "create_incident",
                    "approve_job",
                    "approve_contractor",
                    "modify_job",
                    "view_other_bids"
                ],
                "can_create_incident": False,
                "can_approve_work": False,
                "can_view_bids": False,  # Can only see their own bid
                "can_request_maintenance": False,
                "requires_landlord_approval": True,
                "max_auto_approve_amount": 0,
                "data_access": {
                    "can_view_own_incidents": False,
                    "can_view_all_incidents": False,
                    "can_view_jobs": True,  # Only assigned jobs
                    "can_view_bids": False,  # Only their own
                    "can_view_costs": True  # Their quotes
                },
                "message_guidelines": {
                    "tone": "professional, focused on job details",
                    "can_provide_diy_tips": False,
                    "can_provide_cost_estimates": True,
                    "must_include_safety_warnings": True
                }
            }
        }

    def validate_intent(self, intent: str, persona: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a persona is allowed to perform an intent.

        Args:
            intent: The intent to validate
            persona: The user's persona

        Returns:
            Tuple of (is_valid, error_message)
        """
        if persona not in self.policies:
            return False, f"Unknown persona: {persona}"

        policy = self.policies[persona]
        allowed_intents = policy.get("allowed_intents", [])

        if intent in allowed_intents:
            return True, None

        # Check if this is a forbidden intent with a custom message
        message = self._get_violation_message(intent, persona)
        return False, message

    def validate_action(self, action: str, persona: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a persona is allowed to perform an action.

        Args:
            action: The action to validate
            persona: The user's persona

        Returns:
            Tuple of (is_valid, error_message)
        """
        if persona not in self.policies:
            return False, f"Unknown persona: {persona}"

        policy = self.policies[persona]
        forbidden_actions = policy.get("forbidden_actions", [])

        if action in forbidden_actions:
            message = self._get_violation_message(action, persona)
            return False, message

        return True, None



    def validate_cost_approval(
        self,
        cost: float,
        persona: str
    ) -> Tuple[bool, str]:
        """
        Validate if a persona can approve a cost.

        Args:
            cost: The cost amount
            persona: The user's persona

        Returns:
            Tuple of (can_auto_approve, approval_type)
            approval_type can be: "auto-approve", "recommended-review", "manual-approval"
        """
        if persona not in self.policies:
            return False, "manual-approval"

        policy = self.policies[persona]

        if not policy.get("can_approve_work", False):
            return False, "manual-approval"

        max_auto = policy.get("max_auto_approve_amount", 0)

        if cost <= max_auto:
            return True, "auto-approve"
        elif cost <= max_auto * 2:
            return False, "recommended-review"
        else:
            return False, "manual-approval"

    def can_access_data(
        self,
        persona: str,
        data_type: str,
        resource_owner: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Check if a persona can access a specific data type.

        Args:
            persona: The user's persona
            data_type: Type of data (e.g., "incidents", "jobs", "bids", "costs")
            resource_owner: Optional owner ID of the resource
            user_id: Optional current user ID

        Returns:
            True if access is allowed
        """
        if persona not in self.policies:
            return False

        policy = self.policies[persona]
        data_access = policy.get("data_access", {})

        # Map data_type to policy keys
        access_key_map = {
            "incidents": "can_view_all_incidents" if not resource_owner or resource_owner != user_id else "can_view_own_incidents",
            "jobs": "can_view_jobs",
            "bids": "can_view_bids",
            "costs": "can_view_costs"
        }

        access_key = access_key_map.get(data_type, data_type)
        return data_access.get(access_key, False)

    def get_message_guidelines(self, persona: str) -> Dict[str, Any]:
        """
        Get message generation guidelines for a persona.

        Args:
            persona: The user's persona

        Returns:
            Dictionary of message guidelines
        """
        if persona not in self.policies:
            return {}

        return self.policies[persona].get("message_guidelines", {})

    def _get_violation_message(self, intent_or_action: str, persona: str) -> str:
        """
        Get a user-friendly violation message.

        Args:
            intent_or_action: The intent or action that was attempted
            persona: The user's persona

        Returns:
            Friendly error message
        """
        messages = {
            Persona.TENANT.value: {
                "approve_job": "I appreciate your initiative, but job approvals need to be handled by your landlord. I've notified them of your request!",
                "approve_contractor": "I can't approve contractors directly, but I'll make sure your landlord sees the best options.",
                "create_job_without_incident": "Let's start by reporting the issue first, then we can create a work order.",
                "modify_cost": "Cost adjustments require landlord approval. I'll help you communicate your concerns.",
                "default": "I'd love to help with that, but it requires landlord authorization. Let me assist with what I can do for you instead!"
            },
            Persona.CONTRACTOR.value: {
                "create_incident": "As a contractor, you can respond to jobs rather than create incidents. Let me show you your active jobs!",
                "approve_job": "Job approvals are handled by landlords. I can help you with job details and scheduling instead.",
                "view_other_bids": "For fairness, contractors can only see their own bids. Want to review yours?",
                "default": "That action requires landlord permissions. Let me help you with contractor-specific tasks instead!"
            },
            Persona.LANDLORD.value: {
                "default": "Something went wrong with that action. Let me help you try another approach."
            }
        }

        persona_messages = messages.get(persona, {})
        return persona_messages.get(intent_or_action, persona_messages.get("default", "That action isn't allowed by your account type."))

    def validate_response(
        self,
        response_plan: Dict[str, Any],
        persona: str,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate an entire response plan before execution.

        Args:
            response_plan: The planned response
            persona: The user's persona
            context: Current conversation context

        Returns:
            Tuple of (is_valid, error_message, modified_plan)
        """
        # Extract actions from the plan
        actions = response_plan.get("actions", [])

        # Validate each action
        for action in actions:
            action_name = action.get("name", "")
            is_valid, error = self.validate_action(action_name, persona)

            if not is_valid:
                logger.warning(f"[policy-validator] Action '{action_name}' blocked for {persona}: {error}")
                # Remove forbidden action
                modified_plan = response_plan.copy()
                modified_plan["actions"] = [a for a in actions if a.get("name") != action_name]
                return False, error, modified_plan

        # Check cost approval if applicable
        if "cost" in response_plan.get("metadata", {}):
            cost = float(response_plan["metadata"]["cost"])
            can_approve, approval_type = self.validate_cost_approval(cost, persona)

            if not can_approve and approval_type == "manual-approval":
                # Modify the plan to require landlord approval
                modified_plan = response_plan.copy()
                modified_plan["metadata"]["requires_approval"] = True
                modified_plan["metadata"]["approval_type"] = approval_type
                return True, None, modified_plan

        return True, None, response_plan

    def get_persona_capabilities(self, persona: str) -> Dict[str, Any]:
        """
        Get a summary of what a persona can and cannot do.

        Args:
            persona: The user's persona

        Returns:
            Dictionary of capabilities
        """
        if persona not in self.policies:
            return {}

        policy = self.policies[persona]

        return {
            "persona": persona,
            "allowed_intents": policy.get("allowed_intents", []),
            "forbidden_actions": policy.get("forbidden_actions", []),
            "can_create_incident": policy.get("can_create_incident", False),
            "can_approve_work": policy.get("can_approve_work", False),
            "can_view_bids": policy.get("can_view_bids", False),
            "max_auto_approve_amount": policy.get("max_auto_approve_amount", 0),
            "data_access": policy.get("data_access", {}),
            "message_guidelines": policy.get("message_guidelines", {})
        }


# Singleton instance
_policy_validator: Optional[PolicyValidator] = None


def get_policy_validator() -> PolicyValidator:
    """Get or create the singleton PolicyValidator instance."""
    global _policy_validator

    if _policy_validator is None:
        _policy_validator = PolicyValidator()

    return _policy_validator


def validate_action(persona: str, action: str, context: Optional[Dict[str, Any]] = None) -> PolicyValidationResult:
    validator = get_policy_validator()
    allowed, message = validator.validate_action(action, persona)
    return PolicyValidationResult(allowed=allowed, message=message)
