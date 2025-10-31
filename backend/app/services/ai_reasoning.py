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

import openai

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

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            openai.api_key = api_key
        else:
            logger.warning("OPENAI_API_KEY not set - AI reasoning will be limited")

        logger.info(f"AIReasoning initialized with model: {self.model}")

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

        try:
            # Call OpenAI for intent classification
            response = openai.ChatCompletion.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": self._get_intent_system_prompt(persona)},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            # Parse response
            result = json.loads(response.choices[0].message.content)

            # Validate and normalize
            normalized_result = self._normalize_intent_result(result)

            logger.info(f"[ai-reasoning] Intent detected: {normalized_result['intent']} "
                       f"(confidence: {normalized_result['confidence']:.2f})")

            return normalized_result

        except Exception as e:
            logger.error(f"Error in intent inference: {e}")
            # Fallback to rule-based classification
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

        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": self._get_response_planning_system_prompt(persona)},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return self._normalize_response_plan(result)

        except Exception as e:
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

        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                temperature=0.1,  # Lower temperature for entity extraction
                messages=[
                    {"role": "system", "content": "You are a precise entity extraction system."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            entities = json.loads(response.choices[0].message.content)
            logger.debug(f"[ai-reasoning] Extracted entities: {entities}")
            return entities

        except Exception as e:
            logger.error(f"Error in entity extraction: {e}")
            return {}

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

    def _fallback_intent_detection(
        self,
        message: str,
        context: Dict[str, Any],
        persona: str
    ) -> Dict[str, Any]:
        """
        Fallback rule-based intent detection when LLM fails.
        This ensures the system degrades gracefully.
        """
        message_lower = message.lower()

        # Greeting detection
        greeting_words = ["hello", "hi", "hey", "good morning", "good afternoon"]
        if any(word in message_lower for word in greeting_words):
            return {
                "intent": Intent.GREETING.value,
                "confidence": 0.7,
                "entities": {},
                "next_actions": ["respond_friendly"],
                "card_type": CardType.NONE.value,
                "reasoning": "Fallback: detected greeting"
            }

        # Incident keywords
        incident_keywords = ["leak", "broken", "damage", "not working", "issue", "problem"]
        if any(keyword in message_lower for keyword in incident_keywords):
            # Check if we have an active incident - then it's a followup
            if context.get("active_incident_id"):
                return {
                    "intent": Intent.INCIDENT_FOLLOWUP.value,
                    "confidence": 0.6,
                    "entities": {},
                    "next_actions": ["continue_discovery"],
                    "card_type": CardType.DISCOVERY.value,
                    "reasoning": "Fallback: incident keywords + existing incident = followup"
                }
            else:
                return {
                    "intent": Intent.INCIDENT_REPORT.value,
                    "confidence": 0.6,
                    "entities": {},
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
        return {
            "intent": Intent.GENERAL_CHAT.value,
            "confidence": 0.5,
            "entities": {},
            "next_actions": ["respond_general"],
            "card_type": CardType.NONE.value,
            "reasoning": "Fallback: no specific intent detected"
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
