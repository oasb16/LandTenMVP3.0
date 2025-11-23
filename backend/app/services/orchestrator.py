"""
LLM Orchestrator Engine - Core intelligence layer.
Handles all LLM interactions for intent classification, function selection, and response generation.
"""
from typing import Dict, Any, List, Optional
import json
import os
import logging
from pathlib import Path
from openai import OpenAI
from ..models.orchestrator_schemas import (
    MetaContext,
    OrchestratorOutput,
    FunctionDefinition,
    FunctionResult,
    ContextUpdates,
    FunctionCall,
)
from ..config.settings import settings

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    """
    Universal LLM orchestrator that handles all reasoning, intent classification,
    function selection, and context management through LLM prompting.
    """

    def __init__(self):
        self.openai_client = None
        self.system_prompt = self._load_system_prompt()
        self.model = getattr(settings, "ORCHESTRATOR_MODEL", "gpt-4o")
        self.temperature = getattr(settings, "ORCHESTRATOR_TEMPERATURE", 0.3)
        self.max_tokens = 4096

    def _get_openai_client(self) -> OpenAI:
        """Lazy OpenAI client initialization"""
        if self.openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
            self.openai_client = OpenAI(api_key=api_key)
        return self.openai_client

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

    def _build_tools_for_openai(self, functions: List[FunctionDefinition]) -> List[Dict[str, Any]]:
        """Convert function definitions to OpenAI tool format"""
        tools = []

        for func_def in functions:
            tool = {
                "type": "function",
                "function": {
                    "name": func_def.name,
                    "description": func_def.description,
                    "parameters": func_def.parameters,
                },
            }
            tools.append(tool)

        return tools

    def _format_meta_context(self, meta_context: MetaContext) -> str:
        """Format meta-context for LLM consumption"""

        # Enhanced context with discovery state detection
        context_dict = {
            "persona": meta_context.persona,
            "stage": meta_context.stage,
            "active_incident_id": meta_context.active_incident_id,
            "active_job_id": meta_context.active_job_id,
            "discovery": {
                "incident_id": meta_context.discovery.incident_id if hasattr(meta_context.discovery, "incident_id") else None,
                "question_index": meta_context.discovery.question_index,
                "questions": meta_context.discovery.questions,
                "answers": meta_context.discovery.answers,
                "is_active": meta_context.stage == "discovery" and meta_context.active_incident_id is not None,
            },
            "last_intent": meta_context.last_intent,
            "last_user_message": meta_context.last_user_message,

            # CRITICAL: Add incident status hint to prevent updates to closed incidents
            "active_incident_status": None,  # Will be populated if incident is loaded

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

            # Handle case where LLM returns natural language instead of JSON
            if not response_text.startswith("{") and not response_text.startswith("```"):
                logger.warning(f"LLM returned non-JSON response: {response_text[:100]}")
                # Try to recover by treating it as general.chat
                return OrchestratorOutput(
                    intent="general.chat",
                    reasoning="LLM returned natural language instead of structured output",
                    context_updates=ContextUpdates(),
                    function_call=FunctionCall(name=None, arguments={}),
                    response_to_user=response_text,
                )

            # Handle markdown code blocks
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                # Strip ```json or ``` from first line
                if lines[0].strip() in ["```json", "```"]:
                    response_text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

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

            # CRITICAL FIX: Don't default to general.chat for valid maintenance requests
            # Instead, ask user to rephrase
            return OrchestratorOutput(
                intent="parse_error",
                reasoning="Failed to parse LLM response",
                context_updates=ContextUpdates(),
                function_call=FunctionCall(name=None, arguments={}),
                response_to_user="I'm having trouble understanding that. Could you please describe your maintenance issue more clearly?",
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
            client = self._get_openai_client()

            # CRITICAL PRE-FLIGHT CHECK: If active_incident_id exists, check if it's closed
            if meta_context.active_incident_id:
                try:
                    from ..services.dynamo_service import get_dynamo_service
                    dynamo = get_dynamo_service()
                    incident = dynamo.get_incident(
                        meta_context.active_incident_id,
                        meta_context.user_id
                    )

                    if incident and incident.get("status") == "completed":
                        logger.info(f"⚠️ Active incident {meta_context.active_incident_id} is closed")
                        # Inject into context
                        meta_context.metadata["active_incident_status"] = "completed"
                    elif incident:
                        meta_context.metadata["active_incident_status"] = incident.get("status")
                        meta_context.metadata["active_incident_category"] = incident.get("category")
                        meta_context.metadata["active_incident_title"] = incident.get("title")

                except Exception as e:
                    logger.error(f"Error checking active incident status: {e}")

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

            # CRITICAL: Add discovery flow detection hints
            if meta_context.stage == "discovery" and meta_context.active_incident_id:
                user_content = (
                    f"🔍 **DISCOVERY MODE ACTIVE**\n"
                    f"Incident {meta_context.active_incident_id} is in discovery.\n"
                    f"Question index: {meta_context.discovery.question_index}\n"
                    f"If user sends text answer → call record_discovery_answer\n"
                    f"If user mentions NEW issue → pause discovery, create new incident\n\n"
                    + user_content
                )

            # Build tools
            tools = self._build_tools_for_openai(available_functions)

            # Call OpenAI API
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

            # Insert system prompt as first message
            messages.insert(0, {"role": "system", "content": self.system_prompt})

            # Call OpenAI with tool use
            response = client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=messages,
                tools=tools,
            )

            # Extract response
            message = response.choices[0].message

            # Check if response contains tool calls
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                logger.info(f"LLM selected tool: {tool_call.function.name}")

                # Parse function arguments
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                # Extract intent from reasoning or default to function name
                intent = meta_context.last_intent or tool_call.function.name.replace("_", ".")

                output = OrchestratorOutput(
                    intent=intent,
                    reasoning=message.content or f"Selected function {tool_call.function.name}",
                    context_updates=ContextUpdates(),
                    function_call=FunctionCall(
                        name=tool_call.function.name,
                        arguments=arguments,
                    ),
                    response_to_user=None,
                )

                return output

            # Otherwise, try to parse text content as JSON
            elif message.content:
                output = self._parse_orchestrator_output(message.content)
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
            client = self._get_openai_client()

            messages = [
                {"role": "system", "content": "You are a helpful property maintenance assistant. Provide clear, concise responses."}
            ]

            if context_summary:
                messages.append({
                    "role": "user",
                    "content": f"Context: {context_summary}\n\nUser: {user_message}",
                })
            else:
                messages.append({"role": "user", "content": user_message})

            response = client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                temperature=self.temperature,
                messages=messages,
            )

            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content

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
