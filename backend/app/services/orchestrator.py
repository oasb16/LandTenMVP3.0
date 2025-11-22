"""
LLM Orchestrator Engine - Core intelligence layer.
Handles all LLM interactions for intent classification, function selection, and response generation.
"""
from typing import Dict, Any, List, Optional
import json
import os
from pathlib import Path
import anthropic
from ..models.orchestrator_schemas import (
    MetaContext,
    OrchestratorOutput,
    FunctionDefinition,
    FunctionResult,
    ContextUpdates,
    FunctionCall,
)
from ..config.settings import settings
from ..utils.logging import get_logger

logger = get_logger(__name__)


class LLMOrchestrator:
    """
    Universal LLM orchestrator that handles all reasoning, intent classification,
    function selection, and context management through LLM prompting.
    """

    def __init__(self):
        self.anthropic_client = None
        self.system_prompt = self._load_system_prompt()
        self.model = getattr(settings, "ORCHESTRATOR_MODEL", "claude-3-5-sonnet-20241022")
        self.temperature = getattr(settings, "ORCHESTRATOR_TEMPERATURE", 0.3)
        self.max_tokens = 4096

    def _get_anthropic_client(self) -> anthropic.Anthropic:
        """Lazy Anthropic client initialization"""
        if self.anthropic_client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY") or settings.OPENAI_API_KEY
            self.anthropic_client = anthropic.Anthropic(api_key=api_key)
        return self.anthropic_client

    def _load_system_prompt(self) -> str:
        """Load the universal orchestrator system prompt"""
        try:
            prompt_path = Path(__file__).parent.parent.parent / "system_prompts" / "orchestrator_prompt.txt"

            if prompt_path.exists():
                with open(prompt_path, "r") as f:
                    return f.read()
            else:
                logger.warning(f"System prompt not found at {prompt_path}, using fallback")
                return self._get_fallback_prompt()

        except Exception as e:
            logger.error(f"Error loading system prompt: {e}", exc_info=True)
            return self._get_fallback_prompt()

    def _get_fallback_prompt(self) -> str:
        """Fallback system prompt if file not found"""
        return """
You are the LandTen AI Orchestrator. Analyze user messages, select appropriate functions,
and manage conversation context. Always respond with valid JSON in this format:

{
  "intent": "<intent>",
  "reasoning": "<your reasoning>",
  "context_updates": {},
  "function_call": {"name": "<function_name or null>", "arguments": {}},
  "response_to_user": "<message or null>"
}
"""

    def _build_tools_for_anthropic(self, functions: List[FunctionDefinition]) -> List[Dict[str, Any]]:
        """Convert function definitions to Anthropic tool format"""
        tools = []

        for func_def in functions:
            tool = {
                "name": func_def.name,
                "description": func_def.description,
                "input_schema": func_def.parameters,
            }
            tools.append(tool)

        return tools

    def _format_meta_context(self, meta_context: MetaContext) -> str:
        """Format meta-context for LLM consumption"""
        context_dict = {
            "persona": meta_context.persona,
            "stage": meta_context.stage,
            "active_incident_id": meta_context.active_incident_id,
            "active_job_id": meta_context.active_job_id,
            "discovery": {
                "question_index": meta_context.discovery.question_index,
                "questions": meta_context.discovery.questions,
                "answers": meta_context.discovery.answers,
            },
            "last_intent": meta_context.last_intent,
            "last_user_message": meta_context.last_user_message,
            "conversation_history": [
                {"role": msg.role, "text": msg.text, "timestamp": msg.timestamp}
                for msg in meta_context.conversation_history[-5:]  # Last 5 messages
            ],
            "entities": meta_context.entities,
            "metadata": meta_context.metadata,
        }

        return json.dumps(context_dict, indent=2)

    def _format_function_result(self, function_result: FunctionResult) -> str:
        """Format function execution result for LLM"""
        result_dict = {
            "success": function_result.success,
            "data": function_result.data,
            "error": function_result.error,
            "message": function_result.message,
        }

        return json.dumps(result_dict, indent=2)

    def _parse_orchestrator_output(self, response_text: str) -> OrchestratorOutput:
        """Parse LLM response into OrchestratorOutput"""
        try:
            # Try to extract JSON from response
            response_text = response_text.strip()

            # Handle markdown code blocks
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])

            response_json = json.loads(response_text)

            # Build context updates
            context_updates_data = response_json.get("context_updates", {})
            context_updates = ContextUpdates(**context_updates_data)

            # Build function call
            function_call_data = response_json.get("function_call", {})
            function_call = FunctionCall(**function_call_data)

            # Build orchestrator output
            output = OrchestratorOutput(
                intent=response_json.get("intent", "unknown"),
                reasoning=response_json.get("reasoning", ""),
                context_updates=context_updates,
                function_call=function_call,
                response_to_user=response_json.get("response_to_user"),
            )

            return output

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response text: {response_text}")

            # Return fallback output
            return OrchestratorOutput(
                intent="general.chat",
                reasoning="Failed to parse LLM response",
                context_updates=ContextUpdates(),
                function_call=FunctionCall(name=None, arguments={}),
                response_to_user="I'm having trouble processing that request. Could you please rephrase?",
            )

        except Exception as e:
            logger.error(f"Error parsing orchestrator output: {e}", exc_info=True)

            return OrchestratorOutput(
                intent="error",
                reasoning=f"Error: {str(e)}",
                context_updates=ContextUpdates(),
                function_call=FunctionCall(name=None, arguments={}),
                response_to_user="I encountered an error processing your request. Please try again.",
            )

    async def run(
        self,
        user_message: str,
        meta_context: MetaContext,
        available_functions: List[FunctionDefinition],
        function_result: Optional[FunctionResult] = None,
    ) -> OrchestratorOutput:
        """
        Main orchestrator entry point.
        Sends user message + context to LLM, receives structured output.
        """
        try:
            client = self._get_anthropic_client()

            # Build user message content
            user_content_parts = []

            # Add meta-context
            user_content_parts.append(f"**Meta-Context:**\n```json\n{self._format_meta_context(meta_context)}\n```")

            # Add function result if this is a multi-turn call
            if function_result:
                user_content_parts.append(
                    f"\n**Function Result:**\n```json\n{self._format_function_result(function_result)}\n```"
                )
                user_content_parts.append(
                    "\nThe function has been executed. Based on the result, decide the next action."
                )

            # Add user message
            user_content_parts.append(f"\n**User Message:** {user_message}")

            user_content = "\n".join(user_content_parts)

            # Build tools
            tools = self._build_tools_for_anthropic(available_functions)

            # Call Anthropic API
            logger.info(f"Calling orchestrator LLM for intent: {meta_context.last_intent or 'initial'}")

            # Create messages
            messages = [{"role": "user", "content": user_content}]

            # Add conversation history for context
            for msg in meta_context.conversation_history[-3:]:
                if msg.role == "user":
                    messages.insert(0, {"role": "user", "content": msg.text})
                elif msg.role == "assistant":
                    messages.insert(0, {"role": "assistant", "content": msg.text})

            # Ensure messages alternate and start with user
            if messages and messages[0]["role"] != "user":
                messages = messages[1:]

            # Call Claude with tool use
            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self.system_prompt,
                messages=[messages[-1]],  # Use only the latest message with full context
                tools=tools,
            )

            # Extract response
            if response.content:
                # Check if response contains tool use
                tool_use = None
                text_content = ""

                for block in response.content:
                    if block.type == "tool_use":
                        tool_use = block
                    elif block.type == "text":
                        text_content += block.text

                # If tool use detected, build function call
                if tool_use:
                    logger.info(f"LLM selected tool: {tool_use.name}")

                    output = OrchestratorOutput(
                        intent=meta_context.last_intent or "unknown",
                        reasoning=text_content or f"Selected function {tool_use.name}",
                        context_updates=ContextUpdates(),
                        function_call=FunctionCall(
                            name=tool_use.name,
                            arguments=tool_use.input,
                        ),
                        response_to_user=None,
                    )

                    return output

                # Otherwise, try to parse text content as JSON
                else:
                    output = self._parse_orchestrator_output(text_content)
                    logger.info(f"LLM intent: {output.intent}, function: {output.function_call.name or 'none'}")
                    return output

            else:
                logger.warning("Empty response from LLM")
                return OrchestratorOutput(
                    intent="unknown",
                    reasoning="Empty LLM response",
                    context_updates=ContextUpdates(),
                    function_call=FunctionCall(name=None, arguments={}),
                    response_to_user="I didn't quite catch that. Could you please try again?",
                )

        except anthropic.RateLimitError as e:
            logger.error(f"Anthropic rate limit exceeded: {e}")
            return OrchestratorOutput(
                intent="error",
                reasoning="Rate limit exceeded",
                context_updates=ContextUpdates(),
                function_call=FunctionCall(name=None, arguments={}),
                response_to_user="I'm experiencing high demand right now. Please try again in a moment.",
            )

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}", exc_info=True)
            return OrchestratorOutput(
                intent="error",
                reasoning=f"API error: {str(e)}",
                context_updates=ContextUpdates(),
                function_call=FunctionCall(name=None, arguments={}),
                response_to_user="I'm having trouble connecting to my intelligence system. Please try again.",
            )

        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            return OrchestratorOutput(
                intent="error",
                reasoning=f"Error: {str(e)}",
                context_updates=ContextUpdates(),
                function_call=FunctionCall(name=None, arguments={}),
                response_to_user="I encountered an unexpected error. Please try again or contact support.",
            )

    async def run_simple(
        self,
        user_message: str,
        context_summary: str = "",
    ) -> str:
        """
        Simplified orchestrator for direct Q&A without function calling.
        Used for meta-questions or general chat.
        """
        try:
            client = self._get_anthropic_client()

            messages = []

            if context_summary:
                messages.append({
                    "role": "user",
                    "content": f"Context: {context_summary}\n\nUser: {user_message}",
                })
            else:
                messages.append({"role": "user", "content": user_message})

            response = client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=self.temperature,
                system="You are a helpful property maintenance assistant. Provide clear, concise responses.",
                messages=messages,
            )

            if response.content and len(response.content) > 0:
                return response.content[0].text

            return "I'm not sure how to respond to that."

        except Exception as e:
            logger.error(f"Simple orchestrator error: {e}", exc_info=True)
            return "I'm having trouble processing that request. Please try again."


# Singleton instance
_orchestrator = None


def get_orchestrator() -> LLMOrchestrator:
    """Get singleton instance of LLMOrchestrator"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = LLMOrchestrator()
    return _orchestrator
