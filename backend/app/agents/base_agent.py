"""
Base Agent - Parent class for all specialized agents.
Provides common functionality for LLM interaction.
"""
import os
import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from openai import OpenAI

from ..config.settings import settings
from ..services.openai_wrapper import get_openai_wrapper, RateLimitExceeded

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all specialized agents.

    Each agent has:
    - Unique system prompt defining its role
    - Access to the same LLM
    - Specialized knowledge and capabilities
    """

    def __init__(
        self,
        agent_name: str,
        model: str = "gpt-4o",
        temperature: float = 0.3,
    ):
        self.agent_name = agent_name
        self.model = model
        self.temperature = temperature
        self._openai_client: Optional[OpenAI] = None

        # Load system prompt for this agent
        self.system_prompt = self._load_system_prompt()

    @abstractmethod
    def _load_system_prompt(self) -> str:
        """Load agent-specific system prompt"""
        pass

    def _get_openai_client(self) -> OpenAI:
        """Lazy OpenAI client initialization"""
        if self._openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
            self._openai_client = OpenAI(api_key=api_key)
        return self._openai_client

    async def process(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Process a message through this agent.

        Args:
            user_message: The message to process
            context: Optional context dict
            conversation_history: Optional list of previous messages

        Returns:
            dict with agent response and metadata
        """
        logger.info(f"🤖 [{self.agent_name}] Processing message")

        client = self._get_openai_client()

        # Build messages
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)

        # Add context if provided
        if context:
            context_str = self._format_context(context)
            messages.append({
                "role": "user",
                "content": f"**Context:**\n{context_str}\n\n**User Message:**\n{user_message}"
            })
        else:
            messages.append({"role": "user", "content": user_message})

        # Call LLM (via rate-limit-aware wrapper)
        try:
            openai_wrapper = get_openai_wrapper()
            response = await openai_wrapper.chat_completion(
                model=self.model,
                max_tokens=2048,
                temperature=self.temperature,
                messages=messages,
            )

            response_text = response.choices[0].message.content

            logger.info(f"✅ [{self.agent_name}] Response generated")

            return {
                "success": True,
                "agent": self.agent_name,
                "response": response_text,
                "metadata": {
                    "model": self.model,
                    "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else None,
                },
            }

        except RateLimitExceeded as e:
            logger.error(f"⛔ [{self.agent_name}] Rate limit exceeded: {e}")
            return {
                "success": False,
                "agent": self.agent_name,
                "error": "rate_limit_exceeded",
                "message": "I'm experiencing high demand right now. Please try again in a moment.",
            }

        except Exception as e:
            logger.error(f"❌ [{self.agent_name}] Error: {e}", exc_info=True)
            return {
                "success": False,
                "agent": self.agent_name,
                "error": str(e),
            }

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dict for LLM consumption"""
        lines = []
        for key, value in context.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)
