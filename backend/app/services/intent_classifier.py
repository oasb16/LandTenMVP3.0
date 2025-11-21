"""
Flow-Aware Intent Classifier - Multi-Layer Intent Detection with State Guards

This module provides context-aware intent classification that respects flow state,
prevents invalid transitions, and disambiguates short messages.

Architecture:
    Layer 1: Raw Intent Detection (OpenAI or rule-based)
    Layer 2: Flow State Override (force discovery.response if in discovery)
    Layer 3: Safety Guard (prevent incident.report if active incident)
    Layer 4: Short Message Resolver (disambiguate "yes", "ok", etc.)

This ensures the AI never misroutes messages and maintains flow consistency.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class FlowStage(str, Enum):
    """Flow stages with strict intent rules."""
    IDLE = "idle"
    DISCOVERY = "discovery"
    JOB_READY = "job-ready"
    APPROVAL_PENDING = "approval_pending"
    JOB = "job"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAID = "paid"


class IntentClassifier:
    """Multi-layer intent classifier with flow state awareness."""

    # Affirmative/negative word detection
    AFFIRMATIVE_WORDS = {
        "yes", "yeah", "yep", "yup", "sure", "okay", "ok", "correct",
        "right", "go ahead", "sounds good", "do it", "proceed", "continue",
        "affirmative", "absolutely", "definitely"
    }

    NEGATIVE_WORDS = {
        "no", "nope", "nah", "cancel", "stop", "never mind", "don't",
        "negative", "reject", "decline"
    }

    # Flow state rules
    FLOW_STATE_RULES = {
        FlowStage.DISCOVERY: {
            "allowed_intents": ["discovery.response", "discovery.continue"],
            "blocked_intents": ["incident.report", "general.chat", "greeting"],
            "default_override": "discovery.response",
            "description": "In discovery - all messages are answers"
        },
        FlowStage.JOB_READY: {
            "allowed_intents": ["job.request", "discovery.response", "general.chat"],
            "blocked_intents": ["incident.report"],
            "affirmative_override": "job.request",
            "description": "Ready for job creation"
        },
        FlowStage.APPROVAL_PENDING: {
            "allowed_intents": ["approval.decision"],
            "blocked_intents": ["incident.report", "job.request", "general.chat"],
            "affirmative_override": "approval.decision",
            "negative_override": "approval.decision",
            "description": "Waiting for approval decision"
        },
        FlowStage.JOB: {
            "allowed_intents": ["job.status", "job.inquiry", "general.chat"],
            "blocked_intents": ["incident.report"],
            "description": "Job in progress"
        },
        FlowStage.IDLE: {
            "allowed_intents": ["incident.report", "greeting", "help", "general.chat"],
            "blocked_intents": [],
            "description": "No active flow"
        }
    }

    def classify_with_context(
        self,
        message: str,
        raw_intent: str,
        context: Dict[str, Any],
        persona: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Multi-layer intent classification with flow state awareness.

        Args:
            message: User message text
            raw_intent: Base intent from AI or rules
            context: Full conversation context
            persona: User persona

        Returns:
            Tuple of (final_intent, metadata)
            metadata contains: layer, override_reason, confidence
        """
        message_lower = message.lower().strip()

        # Get flow state
        flow_state = context.get("flow_state", {})
        stage = flow_state.get("stage", "idle")
        active_incident = context.get("active_incident_id") or context.get("active_incident")
        active_job = context.get("active_job_id") or context.get("active_job")
        last_ai_prompt = flow_state.get("last_ai_prompt", "")

        logger.info(
            "[intent-classifier] LAYER 1 - Raw intent: %s | stage: %s | active_incident: %s",
            raw_intent,
            stage,
            active_incident
        )

        # LAYER 2: Flow State Override
        layer2_intent, layer2_metadata = self._apply_flow_state_override(
            raw_intent=raw_intent,
            message=message_lower,
            stage=stage,
            flow_state=flow_state
        )

        logger.info(
            "[intent-classifier] LAYER 2 - Flow override: %s → %s | reason: %s",
            raw_intent,
            layer2_intent,
            layer2_metadata.get("override_reason", "none")
        )

        # LAYER 3: Safety Guard
        layer3_intent, layer3_metadata = self._apply_safety_guard(
            intent=layer2_intent,
            active_incident=active_incident,
            active_job=active_job,
            stage=stage
        )

        logger.info(
            "[intent-classifier] LAYER 3 - Safety guard: %s → %s | reason: %s",
            layer2_intent,
            layer3_intent,
            layer3_metadata.get("override_reason", "none")
        )

        # LAYER 4: Short Message Resolver
        layer4_intent, layer4_metadata = self._resolve_short_message(
            message=message_lower,
            intent=layer3_intent,
            last_ai_prompt=last_ai_prompt,
            stage=stage,
            flow_state=flow_state
        )

        logger.info(
            "[intent-classifier] LAYER 4 - Short message resolver: %s → %s | reason: %s",
            layer3_intent,
            layer4_intent,
            layer4_metadata.get("override_reason", "none")
        )

        # Combine metadata
        final_metadata = {
            "raw_intent": raw_intent,
            "final_intent": layer4_intent,
            "stage": stage,
            "layers_applied": [
                layer2_metadata,
                layer3_metadata,
                layer4_metadata
            ],
            "active_incident": active_incident,
            "active_job": active_job
        }

        logger.info(
            "[intent-classifier] ✅ FINAL INTENT: %s (from %s) | stage: %s",
            layer4_intent,
            raw_intent,
            stage
        )

        return layer4_intent, final_metadata

    def _apply_flow_state_override(
        self,
        raw_intent: str,
        message: str,
        stage: str,
        flow_state: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Apply flow state rules to override intent."""

        # Get stage rules
        stage_rules = self.FLOW_STATE_RULES.get(FlowStage(stage), self.FLOW_STATE_RULES[FlowStage.IDLE])

        # Check if intent is blocked
        if raw_intent in stage_rules.get("blocked_intents", []):
            default = stage_rules.get("default_override", "general.chat")
            return default, {
                "layer": "flow_state_override",
                "override_reason": f"Intent '{raw_intent}' blocked in stage '{stage}', using default '{default}'",
                "applied": True
            }

        # Check if intent is not allowed
        allowed = stage_rules.get("allowed_intents", [])
        if allowed and raw_intent not in allowed:
            default = stage_rules.get("default_override", raw_intent)
            return default, {
                "layer": "flow_state_override",
                "override_reason": f"Intent '{raw_intent}' not allowed in stage '{stage}', using default '{default}'",
                "applied": True
            }

        # No override needed
        return raw_intent, {
            "layer": "flow_state_override",
            "override_reason": "No override needed",
            "applied": False
        }

    def _apply_safety_guard(
        self,
        intent: str,
        active_incident: Optional[str],
        active_job: Optional[str],
        stage: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Prevent invalid state transitions."""

        # RULE: Cannot create new incident if one is active
        if intent == "incident.report" and active_incident:
            return "incident.followup", {
                "layer": "safety_guard",
                "override_reason": f"Cannot create new incident - active incident {active_incident} exists",
                "applied": True
            }

        # RULE: Cannot create job if one is active
        if intent == "job.request" and active_job and stage not in ["job-ready", "idle"]:
            return "job.inquiry", {
                "layer": "safety_guard",
                "override_reason": f"Cannot create new job - active job {active_job} exists",
                "applied": True
            }

        # No safety override needed
        return intent, {
            "layer": "safety_guard",
            "override_reason": "No safety override needed",
            "applied": False
        }

    def _resolve_short_message(
        self,
        message: str,
        intent: str,
        last_ai_prompt: str,
        stage: str,
        flow_state: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Disambiguate short messages like 'yes', 'ok', 'approve'."""

        message_lower = message.lower().strip()

        # Check if message is short affirmative
        is_affirmative = (
            message_lower in self.AFFIRMATIVE_WORDS or
            len(message.split()) <= 2
        )

        # Check if message is negative
        is_negative = message_lower in self.NEGATIVE_WORDS

        if not is_affirmative and not is_negative:
            # Not a short message
            return intent, {
                "layer": "short_message_resolver",
                "override_reason": "Not a short message",
                "applied": False
            }

        # Get stage rules
        stage_rules = self.FLOW_STATE_RULES.get(FlowStage(stage), {})

        # AFFIRMATIVE RESOLUTION
        if is_affirmative:
            # Check for affirmative_override in stage rules
            if "affirmative_override" in stage_rules:
                override_intent = stage_rules["affirmative_override"]
                return override_intent, {
                    "layer": "short_message_resolver",
                    "override_reason": f"Affirmative '{message}' in stage '{stage}' → '{override_intent}'",
                    "applied": True
                }

            # Check last AI prompt for context
            if last_ai_prompt:
                if "create a work order" in last_ai_prompt.lower() or "create job" in last_ai_prompt.lower():
                    return "job.request", {
                        "layer": "short_message_resolver",
                        "override_reason": f"Affirmative to job creation prompt",
                        "applied": True
                    }

                if "approve" in last_ai_prompt.lower():
                    return "approval.decision", {
                        "layer": "short_message_resolver",
                        "override_reason": f"Affirmative to approval prompt",
                        "applied": True
                    }

        # NEGATIVE RESOLUTION
        if is_negative:
            if "negative_override" in stage_rules:
                override_intent = stage_rules["negative_override"]
                return override_intent, {
                    "layer": "short_message_resolver",
                    "override_reason": f"Negative '{message}' in stage '{stage}' → '{override_intent}' (rejected)",
                    "applied": True,
                    "decision": "rejected"
                }

        # No override
        return intent, {
            "layer": "short_message_resolver",
            "override_reason": "No disambiguation needed",
            "applied": False
        }


# Singleton instance
_intent_classifier: Optional[IntentClassifier] = None


def get_intent_classifier() -> IntentClassifier:
    """Get or create the singleton IntentClassifier instance."""
    global _intent_classifier

    if _intent_classifier is None:
        _intent_classifier = IntentClassifier()

    return _intent_classifier
