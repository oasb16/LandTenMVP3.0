"""
AI Reasoning Engine - Intelligent Intent Detection & Policy-Bounded Reasoning

This module provides the core intelligence for the PropertyAI system:
- Intent classification from free-form user messages
- Entity extraction (category, severity, urgency, etc.)
- Context-aware next action prediction
- Policy-bounded creative response generation
- Dynamic card type determination

This is the "brain" that transforms rigid button flows into adaptive conversations.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from openai import OpenAI

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


class AIReasoning:
    """
    AI Reasoning Engine for intelligent intent detection and response planning.

    This class uses LLMs to:
    1. Classify user intent from free-form text
    2. Extract relevant entities
    3. Determine appropriate next actions
    4. Decide what card type to generate
    5. Plan conversation flow
    """

    def __init__(self):
        """Initialize the AI Reasoning Engine."""
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))

        # Initialize OpenAI client (1.x interface)
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client: Optional[OpenAI] = None
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info(f"AIReasoning initialized with model: {self.model}")
            except Exception as exc:  # pragma: no cover - network path
                logger.error(f"Failed to initialise OpenAI client: {exc}")
        else:
            logger.warning("OPENAI_API_KEY not set - using heuristic reasoning fallback")
            logger.info(f"AIReasoning initialized with model: {self.model} (fallback mode)")

    def infer_intent(
        self,
        message: str,
        context: Dict[str, Any],
        persona: str
    ) -> Dict[str, Any]:
        """
        Infer user intent from a message using LLM reasoning.

        Args:
            message: The user's message text
            context: Current conversation context
            persona: User's persona (tenant, landlord, contractor)

        Returns:
            Dictionary containing:
            {
                "intent": Intent enum value,
                "confidence": float (0-1),
                "entities": dict of extracted entities,
                "next_actions": list of suggested actions,
                "card_type": CardType enum value,
                "reasoning": explanation of classification
            }
        """
        # Build context summary for the LLM
        context_summary = self._build_context_summary(context)

        # Create intent classification prompt
        prompt = self._create_intent_prompt(message, context_summary, persona)

        if not self.client:
            return self._fallback_intent_detection(message, context, persona)

        try:
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
            normalized_result = self._normalize_intent_result(result)

            logger.info(
                "[ai-reasoning] Intent detected: %s (confidence %.2f)",
                normalized_result["intent"],
                normalized_result["confidence"],
            )
            return normalized_result

        except Exception as e:  # pragma: no cover - network failure
            logger.error(f"Error in intent inference: {e}")
            return self._fallback_intent_detection(message, context, persona)

    def generate_response_plan(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any],
        persona: str
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive response plan based on intent and context.

        Args:
            intent: The detected intent
            entities: Extracted entities
            context: Current conversation context
            persona: User's persona

        Returns:
            Dictionary containing:
            {
                "response_type": "card|message|hybrid",
                "card_type": CardType value if card needed,
                "message_text": str,
                "actions": list of action buttons,
                "metadata": dict of metadata to attach,
                "should_update_context": bool,
                "context_updates": dict of context updates
            }
        """
        prompt = self._create_response_plan_prompt(intent, entities, context, persona)

        if not self.client:
            return self._fallback_response_plan(intent, entities, persona)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": self._get_response_planning_system_prompt(persona)},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return self._normalize_response_plan(result)

        except Exception as e:  # pragma: no cover - network failure
            logger.error(f"Error in response planning: {e}")
            return self._fallback_response_plan(intent, entities, persona)

    def extract_entities(
        self,
        message: str,
        intent: str,
        persona: str
    ) -> Dict[str, Any]:
        """
        Extract structured entities from a message.

        Args:
            message: The user's message
            intent: The detected intent
            persona: User's persona

        Returns:
            Dictionary of extracted entities
        """
        prompt = f"""
        Extract relevant entities from this message:
        Message: "{message}"
        Intent: {intent}
        Persona: {persona}

        Return a JSON object with extracted entities such as:
        - category (plumbing, electrical, hvac, etc.)
        - severity (low, medium, high, emergency)
        - urgency (routine, urgent, immediate)
        - location (kitchen, bathroom, bedroom, etc.)
        - symptoms (list of symptoms)
        - cost_estimate (if mentioned)
        - timeline (if mentioned)
        - contractor_name (if mentioned)

        Only include entities that are clearly present in the message.
        """

        if not self.client:
            return self._fallback_entity_extraction(message)

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
            logger.debug(f"[ai-reasoning] Extracted entities: {entities}")
            return entities

        except Exception as e:  # pragma: no cover - network failure
            logger.error(f"Error in entity extraction: {e}")
            return self._fallback_entity_extraction(message)

    def _build_context_summary(self, context: Dict[str, Any]) -> str:
        """Build a concise summary of the conversation context."""
        parts = []

        if context.get("flow_type"):
            parts.append(f"Current flow: {context['flow_type']}")

        if context.get("active_incident_id"):
            parts.append(f"Active incident: {context['active_incident_id']}")

        if context.get("active_job_id"):
            parts.append(f"Active job: {context['active_job_id']}")

        if context.get("last_intent"):
            parts.append(f"Last intent: {context['last_intent']}")

        flow_state = context.get("flow_state") or {}
        if flow_state.get("stage") and flow_state.get("stage") != "idle":
            parts.append(
                f"Flow stage: {flow_state.get('stage')} (question_index={flow_state.get('question_index')})"
            )

        # Add last few messages
        history = context.get("conversation_history", [])
        if history:
            recent = history[-3:]  # Last 3 messages
            parts.append(f"Recent conversation ({len(recent)} messages):")
            for msg in recent:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:100]  # Truncate long messages
                parts.append(f"  {role}: {content}")

        return "\n".join(parts) if parts else "No prior context"

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
        - incident.report: User is reporting a new property issue/problem
        - incident.followup: User is providing more info about an existing incident
        - discovery.response: User is answering a discovery question
        - discovery.continue: User wants to continue the discovery process
        - job.request: User is requesting work to be done
        - job.inquiry: User is asking about a job
        - job.status: User wants to know job status
        - bids.request: User wants to see contractor bids
        - bids.compare: User is comparing bids
        - approval.request: User needs approval for something
        - approval.decision: User is approving/rejecting something
        - general.chat: General conversation
        - greeting: User is greeting
        - help: User needs help
        - unclear: Intent is unclear

        Return a JSON object with:
        {{
            "intent": "intent.type",
            "confidence": 0.0-1.0,
            "entities": {{}},
            "reasoning": "why you chose this intent",
            "card_type": "incident|discovery|job|bids|approval|general|none",
            "next_actions": ["action1", "action2"]
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
        4. Suggest appropriate next actions
        5. Determine if a card should be shown

        Be precise and context-aware. Consider:
        - What the user said
        - What happened before (context)
        - What persona they are (tenant/landlord/contractor)
        - What makes sense as the next step

        Always return valid JSON.
        """

    def _get_response_planning_system_prompt(self, persona: str) -> str:
        """Get the system prompt for response planning."""
        return f"""
        You are an intelligent response planner for a property management AI assistant.
        You are planning responses for a {persona}.

        Your job is to:
        1. Decide what type of response to send (card, message, or both)
        2. Determine what information to include
        3. Suggest action buttons if appropriate
        4. Plan context updates
        5. Ensure responses are helpful and professional

        Be creative but bounded by policies:
        - Tenants: Help with issues, provide guidance, be empathetic
        - Landlords: Focus on efficiency, cost management, approvals
        - Contractors: Focus on job details, requirements, scheduling

        Always return valid JSON.
        """

    def _create_response_plan_prompt(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any],
        persona: str
    ) -> str:
        """Create the prompt for response planning."""
        return f"""
        Plan an appropriate response for this situation:

        INTENT: {intent}
        ENTITIES: {json.dumps(entities, indent=2)}
        PERSONA: {persona}
        CONTEXT: {self._build_context_summary(context)}

        Generate a response plan as JSON:
        {{
            "response_type": "card|message|hybrid",
            "card_type": "incident|discovery|job|bids|approval|completion|general|none",
            "message_text": "the message to send to the user",
            "actions": [
                {{"name": "action_name", "label": "Button Label", "value": "action:name:params"}}
            ],
            "metadata": {{"key": "value"}},
            "should_update_context": true|false,
            "context_updates": {{"field": "value"}}
        }}
        """

    def post_process_reasoning(
        self,
        message: str,
        context: Dict[str, Any],
        persona: str,
    ) -> Dict[str, Any]:
        """
        Produce a structured reasoning bundle and conversational reply.
        """
        summary = self.summarize_conversation(context.get("conversation", [])[-5:])
        prompt = self._create_reasoning_prompt(message, context, persona, summary)
        suggested_intent = self.infer_followup_intent(message, context)

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=[
                        {"role": "system", "content": self._get_reasoning_system_prompt(persona)},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                payload = json.loads(response.choices[0].message.content)
                normalized = self._normalize_reasoning_output(payload, message, persona)
                if suggested_intent and suggested_intent != Intent.GENERAL_CHAT.value:
                    normalized["intent"] = suggested_intent
                logger.info(
                    "[ai-reasoning] intent=%s summary=%s",
                    normalized["intent"],
                    normalized["summary"],
                )
                return normalized
            except Exception as exc:  # pragma: no cover - network failure
                logger.error(f"Error in post_process_reasoning: {exc}")

        return self._fallback_reasoning(message, context, persona, suggested_intent)

    def _create_reasoning_prompt(
        self,
        message: str,
        context: Dict[str, Any],
        persona: str,
        conversation_summary: str,
    ) -> str:
        return f"""
        Analyse the latest message and respond with JSON:
        {{
            "intent": "intent.label",
            "summary": "Short plain-language summary",
            "reply": "Natural assistant reply for the user",
            "entities": {{"category": "...", "severity": "...", "location": "..."}},
            "actions": ["next_step_1", "next_step_2"]
        }}

        Persona: {persona}
        Context summary: {self._build_context_summary(context)}
        Conversation recap: {conversation_summary}
        Message: "{message}"
        """

    def summarize_conversation(self, history: List[Dict[str, Any]]) -> str:
        if not history:
            return "No prior messages."
        lines = []
        for item in history:
            role = item.get("role", "user")
            text = item.get("text") or item.get("content") or ""
            lines.append(f"{role}: {text}")
        return " | ".join(lines)

    def infer_followup_intent(self, message: str, context: Dict[str, Any]) -> str:
        message_lower = message.lower()
        flow_state = context.get("flow_state", {}) or {}
        stage = flow_state.get("stage") or "idle"
        active_intent = context.get("active_intent")

        if "approve" in message_lower and stage in {"job", "approval"}:
            return Intent.APPROVAL_DECISION.value

        if active_intent == Intent.INCIDENT_REPORT.value:
            return Intent.DISCOVERY_RESPONSE.value

        if stage in {"discovery", "job-ready"}:
            if any(token in message_lower for token in ["yes", "please", "do it", "create"]):
                return Intent.JOB_REQUEST.value
            return Intent.DISCOVERY_RESPONSE.value

        if stage == "job":
            return Intent.JOB_STATUS.value

        return Intent.GENERAL_CHAT.value

    @staticmethod
    def _get_reasoning_system_prompt(persona: str) -> str:
        tones = {
            "tenant": "empathetic and reassuring",
            "landlord": "confident and decisive",
            "contractor": "practical and collaborative",
        }
        tone = tones.get(persona, "professional and helpful")
        return (
            "You are PropertyAI, an intelligent property management assistant. "
            f"Adopt a {tone} tone and NEVER return unstructured text – only a JSON object as requested."
        )

    def _normalize_reasoning_output(
        self,
        payload: Dict[str, Any],
        message: str,
        persona: str,
    ) -> Dict[str, Any]:
        intent = payload.get("intent") or Intent.GENERAL_CHAT.value
        entities = payload.get("entities") or {}
        summary = payload.get("summary") or message
        reply = payload.get("reply") or "I'm here to help. Could you share a little more detail?"
        actions = payload.get("actions") or []

        return {
            "intent": intent,
            "summary": summary,
            "reply": reply,
            "entities": entities,
            "actions": actions,
            "persona": persona,
        }

    def _normalize_intent_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate intent classification result."""
        return {
            "intent": result.get("intent", Intent.UNCLEAR.value),
            "confidence": float(result.get("confidence", 0.5)),
            "entities": result.get("entities", {}),
            "next_actions": result.get("next_actions", []),
            "card_type": result.get("card_type", CardType.NONE.value),
            "reasoning": result.get("reasoning", "")
        }

    def _normalize_response_plan(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate response plan result."""
        return {
            "response_type": result.get("response_type", "message"),
            "card_type": result.get("card_type", CardType.NONE.value),
            "message_text": result.get("message_text", ""),
            "actions": result.get("actions", []),
            "metadata": result.get("metadata", {}),
            "should_update_context": result.get("should_update_context", True),
            "context_updates": result.get("context_updates", {})
        }

    def _fallback_reasoning(
        self,
        message: str,
        context: Dict[str, Any],
        persona: str,
        suggested_intent: str,
    ) -> Dict[str, Any]:
        """
        Deterministic reasoning when LLM is unavailable.

        Protects high-confidence incident signals from being downgraded.
        """
        message_lower = message.lower()
        for loc in ["kitchen", "bathroom", "basement", "ceiling", "living room", "bedroom"]:
            if loc in message_lower:
                location = loc
                break
        else:
            location = None

        # High-priority incident keywords - preserve intent with high confidence
        high_priority_keywords = ["incident", "emergency", "urgent", "flood", "burst", "gas leak"]
        has_high_priority = any(keyword in message_lower for keyword in high_priority_keywords)

        # Standard incident keywords
        incident_keywords = ["water", "leak", "broken", "damage", "not working", "pipe", "electrical"]
        has_incident_signal = any(keyword in message_lower for keyword in incident_keywords)

        # Priority 1: If suggested_intent is already INCIDENT_REPORT, preserve it
        if suggested_intent == Intent.INCIDENT_REPORT.value:
            summary = "Maintenance incident reported."
            reply = "I understand — I've logged this as an incident and will help you through the next steps."
            entities = self._fallback_entity_extraction(message)
            actions = ["create_incident", "start_discovery"]
            intent = Intent.INCIDENT_REPORT.value

        # Priority 2: High-priority incident keywords override suggested intent
        elif has_high_priority or (has_incident_signal and suggested_intent == Intent.GENERAL_CHAT.value):
            summary = "High-priority incident detected."
            reply = "I've detected a potential incident that needs attention. Let me help you get this resolved."
            entities = self._fallback_entity_extraction(message)
            if entities.get("category") == "plumbing":
                entities["severity"] = "high"
            actions = ["create_incident", "start_discovery"]
            intent = Intent.INCIDENT_REPORT.value

        # Priority 3: Respect suggested_intent for flow continuity
        elif suggested_intent == Intent.DISCOVERY_RESPONSE.value:
            summary = "Continuing discovery for the active incident."
            reply = "Thanks — I'm tracking that. I'll keep guiding you through the next questions."
            entities = self._fallback_entity_extraction(message)
            actions = ["continue_discovery"]
            intent = suggested_intent

        elif suggested_intent == Intent.JOB_REQUEST.value:
            summary = "Tenant requested a work order."
            reply = "Understood. I'll move ahead with preparing a work order so we can dispatch help."
            entities = self._fallback_entity_extraction(message)
            actions = ["create_job"]
            intent = suggested_intent

        elif suggested_intent == Intent.APPROVAL_DECISION.value:
            summary = "User wants to make an approval decision."
            reply = "Let me record that decision and make sure the right person is notified."
            entities = {}
            actions = ["approval_decision"]
            intent = suggested_intent

        # Priority 4: Detect incident from keywords even without suggested_intent
        elif has_incident_signal:
            summary = "Maintenance issue detected from keywords."
            reply = "I've picked up on a potential issue. Let me help you document this properly."
            entities = self._fallback_entity_extraction(message)
            actions = ["create_incident", "start_discovery"]
            intent = Intent.INCIDENT_REPORT.value

        # Priority 5: Default to general chat
        else:
            summary = "General assistance requested."
            reply = "I'm on it. Could you share a little more about what's happening?"
            entities = {}
            actions = ["clarify"]
            intent = Intent.GENERAL_CHAT.value

        return {
            "intent": intent,
            "summary": summary,
            "reply": reply,
            "entities": entities,
            "actions": actions,
            "persona": persona,
        }

    @staticmethod
    def _fallback_entity_extraction(message: str) -> Dict[str, Any]:
        message_lower = message.lower()
        entities: Dict[str, Any] = {}

        if any(keyword in message_lower for keyword in ["water", "leak", "flood", "pipe"]):
            entities["category"] = "plumbing"
            entities["severity"] = "high" if "everywhere" in message_lower or "flood" in message_lower else "medium"

        for loc in ["kitchen", "bathroom", "basement", "ceiling", "living room", "bedroom"]:
            if loc in message_lower:
                entities["location"] = loc
                break

        return entities

    def _analyze_message_fallback(self, message: str) -> Dict[str, Any]:
        """Lightweight analysis that complements intent detection for fallback mode.

        Returns ai_analysis with category, severity, urgency and a suggested next_action.
        """
        entities = self._fallback_entity_extraction(message)
        msg = message.lower()
        ai_analysis: Dict[str, Any] = {
            "category": entities.get("category", "general"),
            "severity": entities.get("severity", "medium"),
            "urgency": entities.get("urgency", "routine"),
            "next_action": "respond_general",
        }

        if any(k in msg for k in ["emergency", "fire", "gas", "flood", "burst"]):
            ai_analysis.update({"urgency": "immediate", "severity": "high", "next_action": "create_incident"})
        elif any(k in msg for k in ["leak", "water", "broken", "not working"]):
            ai_analysis.update({"urgency": "urgent", "next_action": "start_discovery"})
        elif any(k in msg for k in ["rent", "payment", "bill"]):
            ai_analysis.update({"category": "finance", "next_action": "show_payment_info"})

        return ai_analysis

    def _fallback_intent_detection(
        self,
        message: str,
        context: Dict[str, Any],
        persona: str
    ) -> Dict[str, Any]:
        """
        Fallback rule-based intent detection when LLM fails.
        This ensures the system degrades gracefully.

        High-confidence incident signals take priority over generic classification.
        """
        message_lower = message.lower()

        # High-priority incident keywords - these should never be downgraded
        high_priority_keywords = ["incident", "emergency", "urgent", "flood", "burst", "gas leak"]
        has_high_priority = any(keyword in message_lower for keyword in high_priority_keywords)

        # Standard incident keywords
        incident_keywords = ["leak", "broken", "damage", "not working", "issue", "problem", "repair needed"]
        has_incident_signal = any(keyword in message_lower for keyword in incident_keywords)

        # If high-priority incident keyword detected, ALWAYS classify as incident
        if has_high_priority:
            return {
                "intent": Intent.INCIDENT_REPORT.value,
                "confidence": 0.9,  # High confidence
                "entities": self._fallback_entity_extraction(message),
                "next_actions": ["create_incident", "start_discovery"],
                "card_type": CardType.INCIDENT.value,
                "reasoning": "Fallback: HIGH PRIORITY incident keyword detected - preserving intent"
            }

        # Greeting detection (only if no incident signals)
        greeting_words = ["hello", "hi", "hey", "good morning", "good afternoon"]
        if any(word in message_lower for word in greeting_words) and not has_incident_signal:
            return {
                "intent": Intent.GREETING.value,
                "confidence": 0.7,
                "entities": {},
                "next_actions": ["respond_friendly"],
                "card_type": CardType.NONE.value,
                "reasoning": "Fallback: detected greeting"
            }

        # Standard incident detection
        if has_incident_signal:
            # Check if we have an active incident - then it's a followup
            if context.get("active_incident_id") or context.get("active_incident"):
                return {
                    "intent": Intent.INCIDENT_FOLLOWUP.value,
                    "confidence": 0.7,
                    "entities": {},
                    "next_actions": ["continue_discovery"],
                    "card_type": CardType.DISCOVERY.value,
                    "reasoning": "Fallback: incident keywords + existing incident = followup"
                }
            else:
                return {
                    "intent": Intent.INCIDENT_REPORT.value,
                    "confidence": 0.8,  # Strong confidence for incident keywords
                    "entities": self._fallback_entity_extraction(message),
                    "next_actions": ["create_incident", "start_discovery"],
                    "card_type": CardType.INCIDENT.value,
                    "reasoning": "Fallback: detected incident keywords"
                }

        # Job-related keywords
        job_keywords = ["job", "work order", "repair", "fix"]
        if any(keyword in message_lower for keyword in job_keywords):
            return {
                "intent": Intent.JOB_INQUIRY.value,
                "confidence": 0.6,
                "entities": {},
                "next_actions": ["show_job_info"],
                "card_type": CardType.JOB.value,
                "reasoning": "Fallback: detected job keywords"
            }

        # Bid-related keywords
        bid_keywords = ["bid", "quote", "contractor", "estimate"]
        if any(keyword in message_lower for keyword in bid_keywords):
            return {
                "intent": Intent.BIDS_REQUEST.value,
                "confidence": 0.6,
                "entities": {},
                "next_actions": ["show_bids"],
                "card_type": CardType.BIDS.value,
                "reasoning": "Fallback: detected bid keywords"
            }

        # Default to general chat
        ai_analysis = self._analyze_message_fallback(message)
        return {
            "intent": Intent.GENERAL_CHAT.value,
            "confidence": 0.5,
            "entities": {},
            "next_actions": ["respond_general"],
            "card_type": CardType.NONE.value,
            "reasoning": "Fallback: no specific intent detected",
            "ai_analysis": ai_analysis,
        }

    def _fallback_response_plan(
        self,
        intent: str,
        entities: Dict[str, Any],
        persona: str
    ) -> Dict[str, Any]:
        """
        Fallback response planning when LLM fails.
        """
        return {
            "response_type": "message",
            "card_type": CardType.NONE.value,
            "message_text": "I understand you're trying to tell me something. Could you provide more details?",
            "actions": [],
            "metadata": {"intent": intent},
            "should_update_context": True,
            "context_updates": {"last_intent": intent}
        }


# Singleton instance
_ai_reasoning: Optional[AIReasoning] = None


def get_ai_reasoning() -> AIReasoning:
    """Get or create the singleton AIReasoning instance."""
    global _ai_reasoning

    if _ai_reasoning is None:
        _ai_reasoning = AIReasoning()

    return _ai_reasoning
