"""
AI Reasoning Engine V2 - Flow-State Aware Intent Detection & Response Planning

This is a complete rewrite of the AI reasoning engine that:
- Integrates with the multi-layer intent classifier
- Respects flow state and prevents invalid transitions
- Never falls back to generic responses during active flows
- Enforces stage-aware intent classification
- Provides deterministic forward progression

Architecture:
    Layer 1: Raw Intent Detection (OpenAI or rule-based)
    Layer 2: Flow State Override (via intent_classifier)
    Layer 3: Safety Guard (via intent_classifier)
    Layer 4: Short Message Resolver (via intent_classifier)
    Layer 5: Response Planning (this module)

This ensures the AI never misroutes messages and maintains flow consistency.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from openai import OpenAI

from .intent_classifier import get_intent_classifier, FlowStage

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    """Supported intent types for the PropertyAI system."""
    # Incident-related
    INCIDENT_REPORT = "incident.report"
    INCIDENT_FOLLOWUP = "incident.followup"

    # Discovery-related
    DISCOVERY_RESPONSE = "discovery.response"
    DISCOVERY_CONTINUE = "discovery.continue"

    # Job-related
    JOB_REQUEST = "job.request"
    JOB_INQUIRY = "job.inquiry"
    JOB_STATUS = "job.status"

    # Bid-related
    BIDS_REQUEST = "bids.request"
    BIDS_COMPARE = "bids.compare"

    # Approval-related
    APPROVAL_REQUEST = "approval.request"
    APPROVAL_DECISION = "approval.decision"

    # General
    GENERAL_CHAT = "general.chat"
    GREETING = "greeting"
    HELP = "help"
    UNCLEAR = "unclear"


class CardType(str, Enum):
    """Card types that can be dynamically generated."""
    INCIDENT = "incident"
    DISCOVERY = "discovery"
    JOB = "job"
    BIDS = "bids"
    APPROVAL = "approval"
    COMPLETION = "completion"
    GENERAL = "general"
    NONE = "none"


class AIReasoningV2:
    """
    Flow-state aware AI Reasoning Engine.

    This class integrates with the multi-layer intent classifier to provide
    context-aware, stage-respecting intent detection and response planning.
    """

    def __init__(self):
        """Initialize the AI Reasoning Engine V2."""
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))

        # Initialize OpenAI client
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client: Optional[OpenAI] = None
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info(f"[ai-reasoning-v2] Initialized with model: {self.model}")
            except Exception as exc:
                logger.error(f"[ai-reasoning-v2] Failed to initialize OpenAI client: {exc}")
        else:
            logger.warning("[ai-reasoning-v2] OPENAI_API_KEY not set - using heuristic reasoning only")

        # Initialize intent classifier
        self.intent_classifier = get_intent_classifier()

    def infer_intent_with_flow_awareness(
        self,
        message: str,
        context: Dict[str, Any],
        persona: str
    ) -> Dict[str, Any]:
        """
        Infer user intent with full flow state awareness.

        This method:
        1. Detects raw intent from OpenAI or rules
        2. Applies multi-layer intent classification
        3. Respects flow state and prevents invalid transitions
        4. Returns final intent with full metadata

        Args:
            message: The user's message text
            context: Current conversation context (MUST include flow_state)
            persona: User's persona (tenant, landlord, contractor)

        Returns:
            Dictionary containing:
            {
                "intent": Final intent after all layers,
                "raw_intent": Original intent before flow state processing,
                "confidence": float (0-1),
                "entities": dict of extracted entities,
                "metadata": dict of classification metadata,
                "stage": current flow stage,
                "reasoning": explanation of classification
            }
        """
        logger.info(
            "[ai-reasoning-v2] ========== Starting Intent Inference ==========\n"
            "  Message: %s\n"
            "  Persona: %s\n"
            "  Flow Stage: %s\n"
            "  Active Incident: %s\n"
            "  Active Job: %s",
            message[:100],
            persona,
            context.get("flow_state", {}).get("stage", "idle"),
            context.get("active_incident_id") or context.get("active_incident"),
            context.get("active_job_id") or context.get("active_job")
        )

        # STEP 1: Get raw intent from OpenAI or rules
        raw_intent_result = self._detect_raw_intent(message, context, persona)
        raw_intent = raw_intent_result["intent"]
        entities = raw_intent_result.get("entities", {})
        confidence = raw_intent_result.get("confidence", 0.5)

        logger.info(
            "[ai-reasoning-v2] LAYER 1 - Raw Intent Detection:\n"
            "  Raw Intent: %s (confidence: %.2f)\n"
            "  Entities: %s",
            raw_intent,
            confidence,
            entities
        )

        # STEP 2: Apply multi-layer intent classification
        final_intent, classification_metadata = self.intent_classifier.classify_with_context(
            message=message,
            raw_intent=raw_intent,
            context=context,
            persona=persona
        )

        logger.info(
            "[ai-reasoning-v2] LAYERS 2-4 - Multi-Layer Classification:\n"
            "  Raw Intent: %s\n"
            "  Final Intent: %s\n"
            "  Layers Applied: %d\n"
            "  Override Reason: %s",
            raw_intent,
            final_intent,
            len(classification_metadata.get("layers_applied", [])),
            classification_metadata.get("layers_applied", [{}])[-1].get("override_reason", "none")
        )

        # STEP 3: Validate intent transition
        flow_state = context.get("flow_state", {})
        stage = flow_state.get("stage", "idle")
        previous_intent = context.get("active_intent", "idle")

        logger.info(
            "[ai-reasoning-v2] Intent Transition:\n"
            "  Previous: %s\n"
            "  New: %s\n"
            "  Stage: %s",
            previous_intent,
            final_intent,
            stage
        )

        # STEP 4: Extract entities if needed
        if not entities or self._should_reextract_entities(final_intent, entities):
            entities = self.extract_entities(message, final_intent, persona)
            logger.info("[ai-reasoning-v2] Entities extracted: %s", entities)

        # STEP 5: Build final result
        result = {
            "intent": final_intent,
            "raw_intent": raw_intent,
            "confidence": confidence,
            "entities": entities,
            "metadata": classification_metadata,
            "stage": stage,
            "reasoning": self._build_reasoning_summary(
                message, raw_intent, final_intent, classification_metadata
            )
        }

        logger.info(
            "[ai-reasoning-v2] ========== Intent Inference Complete ==========\n"
            "  Final Intent: %s\n"
            "  Stage: %s\n"
            "  Confidence: %.2f",
            final_intent,
            stage,
            confidence
        )

        return result

    def generate_contextual_response(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any],
        persona: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Generate a contextual response based on intent and flow state.

        This method:
        1. Checks flow state to determine appropriate response
        2. Uses stage-specific response templates
        3. Never generates generic fallback during active flows
        4. Returns structured response plan

        Args:
            intent: The classified intent
            entities: Extracted entities
            context: Current conversation context
            persona: User's persona
            message: Original user message

        Returns:
            Dictionary containing:
            {
                "response_text": The text to send to user,
                "card_type": Card type to generate (if any),
                "actions": List of suggested actions,
                "metadata": Metadata to attach to message,
                "context_updates": Updates to apply to context
            }
        """
        flow_state = context.get("flow_state", {})
        stage = flow_state.get("stage", "idle")
        last_ai_prompt = flow_state.get("last_ai_prompt", "")

        logger.info(
            "[ai-reasoning-v2] Generating contextual response:\n"
            "  Intent: %s\n"
            "  Stage: %s\n"
            "  Last AI Prompt: %s",
            intent,
            stage,
            last_ai_prompt[:50] if last_ai_prompt else "none"
        )

        # STAGE-SPECIFIC RESPONSE GENERATION
        response = self._generate_stage_specific_response(
            intent=intent,
            stage=stage,
            entities=entities,
            context=context,
            persona=persona,
            message=message,
            last_ai_prompt=last_ai_prompt
        )

        logger.info(
            "[ai-reasoning-v2] Response generated:\n"
            "  Text: %s\n"
            "  Card: %s",
            response["response_text"][:100],
            response["card_type"]
        )

        return response

    def post_process_reasoning(
        self,
        message: str,
        context: Dict[str, Any],
        persona: str,
    ) -> Dict[str, Any]:
        """
        Main entry point for AI reasoning - produces complete reasoning bundle.

        This is the primary method called by the webhook handler. It:
        1. Infers intent with flow awareness
        2. Generates contextual response
        3. Returns structured reasoning bundle

        Args:
            message: User message text
            context: Full conversation context
            persona: User persona

        Returns:
            Dictionary containing:
            {
                "intent": final intent,
                "summary": short summary,
                "reply": response text,
                "entities": extracted entities,
                "actions": suggested actions,
                "persona": persona,
                "reasoning": full reasoning metadata
            }
        """
        # Explicit V2 logging for confirmation
        logger.info(
            "[ai-reasoning-v2] ========== START V2 PIPELINE ==========\n"
            "  Message: %s\n"
            "  Persona: %s\n"
            "  Flow Stage: %s",
            message[:100],
            persona,
            context.get("flow_state", {}).get("stage", "idle")
        )

        # STEP 1: Infer intent with flow awareness
        intent_result = self.infer_intent_with_flow_awareness(message, context, persona)

        # STEP 2: Generate contextual response
        response = self.generate_contextual_response(
            intent=intent_result["intent"],
            entities=intent_result["entities"],
            context=context,
            persona=persona,
            message=message
        )

        # STEP 3: Build final reasoning bundle
        result = {
            "intent": intent_result["intent"],
            "summary": self._generate_summary(message, intent_result["intent"], intent_result["entities"]),
            "reply": response["response_text"],
            "entities": intent_result["entities"],
            "actions": response.get("actions", []),
            "persona": persona,
            "reasoning": {
                "raw_intent": intent_result["raw_intent"],
                "final_intent": intent_result["intent"],
                "stage": intent_result["stage"],
                "layers_applied": intent_result["metadata"].get("layers_applied", []),
                "confidence": intent_result["confidence"]
            }
        }

        logger.info(
            "[ai-reasoning-v2] Post-processing complete:\n"
            "  Intent: %s\n"
            "  Summary: %s\n"
            "  Reply: %s",
            result["intent"],
            result["summary"],
            result["reply"][:100]
        )

        return result

    def _detect_raw_intent(
        self,
        message: str,
        context: Dict[str, Any],
        persona: str
    ) -> Dict[str, Any]:
        """
        Detect raw intent using OpenAI or rule-based fallback.

        This is Layer 1 of the intent classification pipeline.
        """
        # Build context summary
        context_summary = self._build_context_summary(context)

        # Try OpenAI classification first
        if self.client:
            try:
                prompt = self._create_intent_prompt(message, context_summary, persona)
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=[
                        {"role": "system", "content": self._get_intent_system_prompt(persona)},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                )

                result = json.loads(response.choices[0].message.content)
                return self._normalize_intent_result(result)

            except Exception as e:
                logger.error(f"[ai-reasoning-v2] OpenAI classification failed: {e}")
                return self._fallback_intent_detection(message, context, persona)
        else:
            # No OpenAI client - use rules
            return self._fallback_intent_detection(message, context, persona)

    def _fallback_intent_detection(
        self,
        message: str,
        context: Dict[str, Any],
        persona: str
    ) -> Dict[str, Any]:
        """
        Rule-based intent detection when OpenAI is unavailable.

        This provides deterministic classification based on keywords and context.
        """
        message_lower = message.lower()

        # Check for high-priority incident keywords
        high_priority_keywords = ["incident", "emergency", "urgent", "flood", "burst", "gas leak", "fire"]
        if any(keyword in message_lower for keyword in high_priority_keywords):
            return {
                "intent": Intent.INCIDENT_REPORT.value,
                "confidence": 0.9,
                "entities": self._extract_entities_fallback(message),
                "reasoning": "Fallback: high-priority incident keyword detected"
            }

        # Check for greeting
        greeting_words = ["hello", "hi", "hey", "good morning", "good afternoon"]
        if any(word in message_lower for word in greeting_words):
            return {
                "intent": Intent.GREETING.value,
                "confidence": 0.8,
                "entities": {},
                "reasoning": "Fallback: greeting detected"
            }

        # Check for incident keywords
        incident_keywords = ["leak", "broken", "damage", "not working", "issue", "problem", "repair"]
        if any(keyword in message_lower for keyword in incident_keywords):
            # Check if there's an active incident - then it's a followup
            if context.get("active_incident_id") or context.get("active_incident"):
                return {
                    "intent": Intent.INCIDENT_FOLLOWUP.value,
                    "confidence": 0.7,
                    "entities": {},
                    "reasoning": "Fallback: incident keywords + active incident = followup"
                }
            else:
                return {
                    "intent": Intent.INCIDENT_REPORT.value,
                    "confidence": 0.8,
                    "entities": self._extract_entities_fallback(message),
                    "reasoning": "Fallback: incident keywords detected"
                }

        # Check for job-related keywords
        job_keywords = ["job", "work order", "repair", "fix"]
        if any(keyword in message_lower for keyword in job_keywords):
            return {
                "intent": Intent.JOB_INQUIRY.value,
                "confidence": 0.6,
                "entities": {},
                "reasoning": "Fallback: job keywords detected"
            }

        # Check for bid-related keywords
        bid_keywords = ["bid", "quote", "contractor", "estimate"]
        if any(keyword in message_lower for keyword in bid_keywords):
            return {
                "intent": Intent.BIDS_REQUEST.value,
                "confidence": 0.6,
                "entities": {},
                "reasoning": "Fallback: bid keywords detected"
            }

        # Check for approval keywords
        approval_keywords = ["approve", "accept", "ok", "yes", "reject", "deny"]
        if any(keyword in message_lower for keyword in approval_keywords):
            return {
                "intent": Intent.APPROVAL_DECISION.value,
                "confidence": 0.7,
                "entities": {},
                "reasoning": "Fallback: approval keywords detected"
            }

        # Default to general chat
        return {
            "intent": Intent.GENERAL_CHAT.value,
            "confidence": 0.5,
            "entities": {},
            "reasoning": "Fallback: no specific intent detected"
        }

    def _extract_entities_fallback(self, message: str) -> Dict[str, Any]:
        """Extract entities using rule-based approach."""
        message_lower = message.lower()
        entities: Dict[str, Any] = {}

        # Category detection
        if any(keyword in message_lower for keyword in ["water", "leak", "flood", "pipe", "faucet", "toilet"]):
            entities["category"] = "plumbing"
        elif any(keyword in message_lower for keyword in ["electric", "outlet", "power", "light", "switch"]):
            entities["category"] = "electrical"
        elif any(keyword in message_lower for keyword in ["heat", "ac", "hvac", "thermostat", "furnace"]):
            entities["category"] = "hvac"
        elif any(keyword in message_lower for keyword in ["fridge", "stove", "oven", "dishwasher", "appliance"]):
            entities["category"] = "appliance"
        else:
            entities["category"] = "general"

        # Severity detection
        if any(keyword in message_lower for keyword in ["emergency", "flood", "burst", "fire", "gas"]):
            entities["severity"] = "emergency"
        elif any(keyword in message_lower for keyword in ["urgent", "bad", "severe", "major"]):
            entities["severity"] = "high"
        elif any(keyword in message_lower for keyword in ["minor", "small", "slight"]):
            entities["severity"] = "low"
        else:
            entities["severity"] = "medium"

        # Location detection
        for loc in ["kitchen", "bathroom", "basement", "ceiling", "living room", "bedroom", "garage"]:
            if loc in message_lower:
                entities["location"] = loc
                break

        return entities

    def _generate_stage_specific_response(
        self,
        intent: str,
        stage: str,
        entities: Dict[str, Any],
        context: Dict[str, Any],
        persona: str,
        message: str,
        last_ai_prompt: str
    ) -> Dict[str, Any]:
        """
        Generate response based on current stage.

        This prevents generic fallback during active flows.
        """
        # DISCOVERY STAGE - Always acknowledge answers
        if stage == FlowStage.DISCOVERY.value:
            return {
                "response_text": "Thanks for that information. I'm recording your response.",
                "card_type": CardType.DISCOVERY.value,
                "actions": ["continue_discovery"],
                "metadata": {"stage": stage},
                "context_updates": {}
            }

        # JOB-READY STAGE - Prompt for job creation
        if stage == FlowStage.JOB_READY.value:
            if intent == Intent.JOB_REQUEST.value:
                return {
                    "response_text": "Perfect. I'll move ahead with creating a work order.",
                    "card_type": CardType.JOB.value,
                    "actions": ["create_job"],
                    "metadata": {"stage": stage},
                    "context_updates": {}
                }
            else:
                return {
                    "response_text": "I've gathered the details. Would you like me to create a work order?",
                    "card_type": CardType.NONE.value,
                    "actions": ["prompt_job_creation"],
                    "metadata": {"stage": stage},
                    "context_updates": {}
                }

        # APPROVAL_PENDING STAGE - Handle approval decision
        if stage == FlowStage.APPROVAL_PENDING.value:
            if intent == Intent.APPROVAL_DECISION.value:
                if any(word in message.lower() for word in ["yes", "approve", "ok", "accept"]):
                    return {
                        "response_text": "Great! I've recorded your approval and will proceed with the work order.",
                        "card_type": CardType.APPROVAL.value,
                        "actions": ["process_approval"],
                        "metadata": {"stage": stage, "decision": "approved"},
                        "context_updates": {"approval_status": "approved"}
                    }
                else:
                    return {
                        "response_text": "I've recorded your decision. The work order will not proceed.",
                        "card_type": CardType.APPROVAL.value,
                        "actions": ["process_rejection"],
                        "metadata": {"stage": stage, "decision": "rejected"},
                        "context_updates": {"approval_status": "rejected"}
                    }
            else:
                return {
                    "response_text": "I'm waiting for your approval decision. Would you like to approve or reject this work order?",
                    "card_type": CardType.NONE.value,
                    "actions": ["await_approval"],
                    "metadata": {"stage": stage},
                    "context_updates": {}
                }

        # JOB STAGE - Job is in progress
        if stage == FlowStage.JOB.value:
            return {
                "response_text": "Your work order is currently in progress. Let me know if you need an update.",
                "card_type": CardType.JOB.value,
                "actions": ["check_job_status"],
                "metadata": {"stage": stage},
                "context_updates": {}
            }

        # IDLE STAGE - Handle new intents
        if stage == FlowStage.IDLE.value:
            if intent == Intent.INCIDENT_REPORT.value:
                return {
                    "response_text": "I've detected an issue. Let me help you create an incident report.",
                    "card_type": CardType.INCIDENT.value,
                    "actions": ["create_incident"],
                    "metadata": {"stage": stage},
                    "context_updates": {}
                }
            elif intent == Intent.GREETING.value:
                greetings = {
                    "tenant": "Hello! I'm your PropertyAI assistant. How can I help you today?",
                    "landlord": "Hello! I'm here to help you manage your properties. What would you like to do?",
                    "contractor": "Hello! I'm here to help you with your work orders. What do you need?"
                }
                return {
                    "response_text": greetings.get(persona, "Hello! How can I help you?"),
                    "card_type": CardType.NONE.value,
                    "actions": [],
                    "metadata": {"stage": stage},
                    "context_updates": {}
                }
            else:
                return {
                    "response_text": "I'm here to help! What can I assist you with?",
                    "card_type": CardType.NONE.value,
                    "actions": [],
                    "metadata": {"stage": stage},
                    "context_updates": {}
                }

        # DEFAULT - Return generic response
        return {
            "response_text": "I understand. How else can I help you?",
            "card_type": CardType.NONE.value,
            "actions": [],
            "metadata": {"stage": stage},
            "context_updates": {}
        }

    def extract_entities(
        self,
        message: str,
        intent: str,
        persona: str
    ) -> Dict[str, Any]:
        """Extract structured entities from a message."""
        if not self.client:
            return self._extract_entities_fallback(message)

        prompt = f"""
        Extract relevant entities from this message:
        Message: "{message}"
        Intent: {intent}
        Persona: {persona}

        Return a JSON object with extracted entities such as:
        - category (plumbing, electrical, hvac, appliance, general)
        - severity (low, medium, high, emergency)
        - urgency (routine, urgent, immediate)
        - location (kitchen, bathroom, bedroom, etc.)
        - symptoms (list of symptoms)
        - cost_estimate (if mentioned)
        - timeline (if mentioned)

        Only include entities that are clearly present in the message.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": "You are a precise entity extraction system."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            entities = json.loads(response.choices[0].message.content)
            logger.debug(f"[ai-reasoning-v2] Extracted entities: {entities}")
            return entities

        except Exception as e:
            logger.error(f"[ai-reasoning-v2] Entity extraction failed: {e}")
            return self._extract_entities_fallback(message)

    # ============================================================================
    # Helper Methods
    # ============================================================================

    def _build_context_summary(self, context: Dict[str, Any]) -> str:
        """Build a concise summary of the conversation context."""
        parts = []

        flow_state = context.get("flow_state") or {}
        stage = flow_state.get("stage", "idle")
        if stage != "idle":
            parts.append(f"Current stage: {stage}")

        if context.get("active_incident_id") or context.get("active_incident"):
            parts.append(f"Active incident: {context.get('active_incident_id') or context.get('active_incident')}")

        if context.get("active_job_id") or context.get("active_job"):
            parts.append(f"Active job: {context.get('active_job_id') or context.get('active_job')}")

        question_index = flow_state.get("question_index")
        if question_index is not None:
            parts.append(f"Question index: {question_index}")

        last_ai_prompt = flow_state.get("last_ai_prompt")
        if last_ai_prompt:
            parts.append(f"Last AI prompt: {last_ai_prompt[:50]}")

        return "\n".join(parts) if parts else "No active flow"

    def _create_intent_prompt(
        self,
        message: str,
        context_summary: str,
        persona: str
    ) -> str:
        """Create the prompt for intent classification."""
        return f"""
        Classify the intent of this user message in a property management context.

        USER PERSONA: {persona}
        USER MESSAGE: "{message}"

        CONTEXT:
        {context_summary}

        Possible intents:
        - incident.report: User is reporting a new property issue
        - incident.followup: User is providing more info about existing incident
        - discovery.response: User is answering a discovery question
        - job.request: User is requesting work to be done
        - job.inquiry: User is asking about a job
        - bids.request: User wants to see contractor bids
        - approval.decision: User is approving/rejecting something
        - general.chat: General conversation
        - greeting: User is greeting
        - help: User needs help

        Return a JSON object with:
        {{
            "intent": "intent.type",
            "confidence": 0.0-1.0,
            "entities": {{}},
            "reasoning": "why you chose this intent"
        }}
        """

    def _get_intent_system_prompt(self, persona: str) -> str:
        """Get the system prompt for intent classification."""
        return f"""
        You are an intelligent property management assistant that classifies user intents.
        You are currently assisting a {persona}.

        Your job is to:
        1. Understand the user's intent from their message
        2. Consider the conversation context
        3. Extract relevant entities
        4. Be precise and context-aware

        Always return valid JSON.
        """

    def _normalize_intent_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate intent classification result."""
        return {
            "intent": result.get("intent", Intent.UNCLEAR.value),
            "confidence": float(result.get("confidence", 0.5)),
            "entities": result.get("entities", {}),
            "reasoning": result.get("reasoning", "")
        }

    def _should_reextract_entities(self, intent: str, entities: Dict[str, Any]) -> bool:
        """Determine if entities should be re-extracted."""
        # If intent is incident-related but no category, re-extract
        if intent in [Intent.INCIDENT_REPORT.value, Intent.INCIDENT_FOLLOWUP.value]:
            if not entities.get("category"):
                return True

        return False

    def _build_reasoning_summary(
        self,
        message: str,
        raw_intent: str,
        final_intent: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Build a human-readable reasoning summary."""
        if raw_intent == final_intent:
            return f"Intent '{final_intent}' detected and validated"
        else:
            layers = metadata.get("layers_applied", [])
            last_layer = layers[-1] if layers else {}
            reason = last_layer.get("override_reason", "unknown")
            return f"Intent '{raw_intent}' overridden to '{final_intent}': {reason}"

    def _generate_summary(self, message: str, intent: str, entities: Dict[str, Any]) -> str:
        """Generate a short summary of the message."""
        category = entities.get("category", "")
        if intent == Intent.INCIDENT_REPORT.value and category:
            return f"{category.capitalize()} issue reported"
        elif intent == Intent.DISCOVERY_RESPONSE.value:
            return "Discovery question answered"
        elif intent == Intent.JOB_REQUEST.value:
            return "Work order requested"
        elif intent == Intent.APPROVAL_DECISION.value:
            return "Approval decision made"
        else:
            return message[:50] + "..." if len(message) > 50 else message


# Singleton instance
_ai_reasoning_v2: Optional[AIReasoningV2] = None


def get_ai_reasoning_v2() -> AIReasoningV2:
    """Get or create the singleton AIReasoningV2 instance."""
    global _ai_reasoning_v2

    if _ai_reasoning_v2 is None:
        _ai_reasoning_v2 = AIReasoningV2()

    return _ai_reasoning_v2
