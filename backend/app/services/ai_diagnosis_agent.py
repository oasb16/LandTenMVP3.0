"""
AI Diagnosis Agent - LLM-powered troubleshooting assistant

Uses OpenAI GPT-4 to intelligently diagnose maintenance issues through
conversation with users. Provides smart troubleshooting suggestions and
determines when enough information has been gathered for resolution.
"""
import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class DiagnosisAgent:
    """
    LLM-powered diagnosis agent for intelligent troubleshooting.

    Maintains conversation context and uses GPT-4 to:
    - Ask clarifying questions about the issue
    - Provide troubleshooting suggestions
    - Determine when diagnosis is complete
    - Generate actionable summaries for resolution
    """

    def __init__(self):
        """Initialize OpenAI client and configuration."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))

        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set - diagnosis agent will use fallback mode")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=self.api_key)

        # Conversation histories keyed by channel_id
        self._conversations: Dict[str, List[Dict[str, str]]] = {}

    def _get_system_prompt(self, persona: str, context: Dict[str, Any]) -> str:
        """
        Generate system prompt based on persona and session context.
        """
        cta = context.get("selected_cta", "maintenance")
        item = context.get("selected_item_id", "unknown")
        reason = context.get("selected_reason", "an issue")

        base_prompt = f"""You are an AI support agent for LandTen, a property management platform.

User Role: {persona}
Issue Category: {cta}
Affected Item: {item}
Initial Complaint: {reason}

Your task is to diagnose the problem through intelligent conversation:

1. Ask 2-3 clarifying questions to understand:
   - When did the issue start?
   - How severe is it? (safety concern, inconvenience, cosmetic)
   - Has anything changed recently?
   - Any visible damage or unusual sounds/smells?

2. Provide helpful troubleshooting suggestions when appropriate:
   - Safe, simple checks the user can perform
   - Common causes and quick fixes
   - When to escalate to emergency services

3. Determine when you have enough information:
   - After gathering key details, indicate diagnosis is complete
   - Prepare a concise summary of the issue
   - Recommend appropriate next actions

Guidelines:
- Keep responses concise (2-3 sentences max)
- Be empathetic and professional
- Focus on gathering actionable information
- Don't make the user repeat themselves
- Signal completion with "DIAGNOSIS_COMPLETE:" followed by your summary

Remember: You're helping {persona}s resolve property issues efficiently."""

        return base_prompt

    async def send_message(
        self,
        channel_id: str,
        user_message: str,
        persona: str,
        session_context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """
        Process user message and generate AI response.

        Args:
            channel_id: Stream channel ID for conversation tracking
            user_message: Latest message from user
            persona: User's role (tenant, landlord, etc.)
            session_context: Session state with selected items/reasons

        Returns:
            Tuple of (ai_response, is_diagnosis_complete)
        """
        # Fallback mode if OpenAI not configured
        if not self.client:
            return self._fallback_response(user_message, persona)

        try:
            # Get or initialize conversation history
            if channel_id not in self._conversations:
                system_prompt = self._get_system_prompt(persona, session_context)
                self._conversations[channel_id] = [
                    {"role": "system", "content": system_prompt}
                ]

            # Add user message to history
            self._conversations[channel_id].append({
                "role": "user",
                "content": user_message
            })

            # Get AI response
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self._conversations[channel_id],
                temperature=self.temperature,
                max_tokens=300
            )

            ai_message = response.choices[0].message.content

            # Add AI response to history
            self._conversations[channel_id].append({
                "role": "assistant",
                "content": ai_message
            })

            # Check if diagnosis is complete
            is_complete = "DIAGNOSIS_COMPLETE:" in ai_message

            # Extract summary if complete (remove the marker)
            if is_complete:
                ai_message = ai_message.replace("DIAGNOSIS_COMPLETE:", "").strip()

            logger.info(f"[Diagnosis Agent] Generated response for {channel_id}, complete={is_complete}")

            return ai_message, is_complete

        except Exception as e:
            logger.error(f"Error in diagnosis agent: {e}", exc_info=True)
            return self._fallback_response(user_message, persona)

    def _fallback_response(self, user_message: str, persona: str) -> Tuple[str, bool]:
        """
        Simple fallback responses when LLM is unavailable.
        Returns (response, is_complete) tuple.
        """
        # After any message, transition to resolution
        response = (
            "Thank you for providing those details. "
            "Based on what you've shared, I have enough information to help you proceed. "
            "DIAGNOSIS_COMPLETE: User reported issue with detailed context."
        )
        return response, True

    def get_conversation_summary(self, channel_id: str) -> str:
        """
        Generate a summary of the conversation for resolution context.
        """
        if channel_id not in self._conversations:
            return "No conversation history available."

        # Extract user messages only
        user_messages = [
            msg["content"]
            for msg in self._conversations[channel_id]
            if msg["role"] == "user"
        ]

        if not user_messages:
            return "No user messages in conversation."

        return "\n".join(f"- {msg}" for msg in user_messages)

    def clear_conversation(self, channel_id: str):
        """Clear conversation history for a channel."""
        if channel_id in self._conversations:
            del self._conversations[channel_id]
            logger.info(f"Cleared diagnosis conversation for {channel_id}")

    def start_diagnosis(
        self,
        channel_id: str,
        persona: str,
        session_context: Dict[str, Any]
    ) -> str:
        """
        Start a new diagnosis session with initial greeting.

        Returns initial AI message to user.
        """
        reason = session_context.get("selected_reason", "your issue")
        item = session_context.get("selected_item_id", "item")

        # Initialize conversation with system prompt
        system_prompt = self._get_system_prompt(persona, session_context)
        self._conversations[channel_id] = [
            {"role": "system", "content": system_prompt}
        ]

        # Generate contextual greeting
        greeting = (
            f"I understand you're experiencing: **{reason}** with your {item}. "
            f"Let me ask a few questions to better understand the situation."
        )

        return greeting


# Singleton instance
_diagnosis_agent: Optional[DiagnosisAgent] = None


def get_diagnosis_agent() -> DiagnosisAgent:
    """Get or create diagnosis agent instance."""
    global _diagnosis_agent
    if _diagnosis_agent is None:
        _diagnosis_agent = DiagnosisAgent()
    return _diagnosis_agent
