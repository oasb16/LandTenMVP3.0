"""
ResponseHandler - OpenAI Responses API Integration

Replaces dual-agent flow (TenantAgent + Orchestrator) with single unified flow.
Handles empathetic conversation + function calling in one Responses API call.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
import openai

from .conversation_manager import get_conversation_manager
from ..functions.function_registry import execute_function, get_function_definitions
from .stream_bot import get_bot
from .dynamo_service import get_dynamo_service

logger = logging.getLogger(__name__)


class ResponseHandler:
    """
    Handles message processing using OpenAI Responses API.

    Replaces the old dual-agent architecture:
    - OLD: User → TenantAgent (empathy) → Orchestrator (functions) → Execute
    - NEW: User → Single Response (empathy + functions) → Execute tools

    Key Features:
    - Single unified prompt (empathy + function calling)
    - Explicit tool loop management
    - State management via Conversations API
    - Preserves empathetic responses
    """

    def __init__(self):
        """Initialize ResponseHandler"""
        self.openai_client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))
        self.dynamo_service = get_dynamo_service()
        self.conversation_manager = get_conversation_manager(dynamo_service=self.dynamo_service)
        self.bot = get_bot()
        self.prompt_id = os.getenv("LANDTEN_PROMPT_ID")

        # Load enhanced system prompt for auto-tool-generation
        self.system_prompt = self._load_system_prompt()

        # Get available tools for function calling
        raw_functions = get_function_definitions()

        # Convert to Responses API format (flat structure, not nested like Chat Completions)
        self.tools = []
        for func in raw_functions:
            # Convert Pydantic model to dict if needed
            if hasattr(func, 'model_dump'):
                func_dict = func.model_dump()
            elif hasattr(func, 'dict'):
                func_dict = func.dict()
            else:
                # Fallback if not a Pydantic model
                func_dict = {
                    "name": func.name,
                    "description": func.description,
                    "parameters": func.parameters
                }

            # Responses API uses flat format: {type, name, description, parameters}
            # NOT nested like Chat API: {type, function: {name, description, parameters}}
            tool = {
                "type": "function",
                "name": func_dict["name"],
                "description": func_dict["description"],
                "parameters": func_dict["parameters"]
            }
            self.tools.append(tool)

        if not self.prompt_id:
            logger.warning(
                "LANDTEN_PROMPT_ID not set - using local system prompt instead"
            )

        logger.info(f"ResponseHandler initialized with prompt: {self.prompt_id or 'local'}")
        logger.info(f"Loaded {len(self.tools)} tools for function calling")
        logger.info(f"📋 System prompt: {len(self.system_prompt)} chars")

        # DEBUG: Log first tool structure to verify format
        if self.tools:
            import json
            logger.info(f"🔍 DEBUG: First tool structure: {json.dumps(self.tools[0], indent=2)}")

    def _refresh_tools(self):
        """
        Refresh tools list to include newly registered dynamic tools.

        CRITICAL: Must be called after register_dynamic_tool succeeds
        to make the new tool available in the SAME conversation.
        """
        raw_functions = get_function_definitions()

        # Rebuild tools list
        self.tools = []
        for func in raw_functions:
            # Convert Pydantic model to dict if needed
            if hasattr(func, 'model_dump'):
                func_dict = func.model_dump()
            elif hasattr(func, 'dict'):
                func_dict = func.dict()
            else:
                func_dict = {
                    "name": func.name,
                    "description": func.description,
                    "parameters": func.parameters
                }

            # Responses API uses flat format
            tool = {
                "type": "function",
                "name": func_dict["name"],
                "description": func_dict["description"],
                "parameters": func_dict["parameters"]
            }
            self.tools.append(tool)

        logger.info(f"🔄 Tools refreshed: {len(self.tools)} tools now available")

    def _load_system_prompt(self) -> str:
        """Load system prompt from file or use default"""
        from pathlib import Path

        prompt_path = Path(__file__).parent.parent.parent / "system_prompts" / "tenant_agent_prompt.txt"

        if prompt_path.exists():
            try:
                with open(prompt_path, "r") as f:
                    prompt = f.read()
                logger.info(f"✅ Loaded system prompt from {prompt_path}")
                return prompt
            except Exception as e:
                logger.error(f"Failed to load system prompt: {e}")

        # Fallback to inline prompt
        return """You are PropertyHelper, an empathetic AI assistant for property maintenance.

CRITICAL: When users describe maintenance problems, ALWAYS use diagnostic tools:
1. Check if tool exists (diagnose_water_leak, estimate_hvac_repair, schedule_preventive_maintenance)
2. If exists: USE IT IMMEDIATELY with the symptom data
3. If not: Generate new tool using register_dynamic_tool, then use it
4. Enhance your response with tool data (cost, urgency, severity)

Example:
User: "Brown water dripping from ceiling"
You: Call diagnose_water_leak(leak_location="bathroom ceiling", water_color="brown", flow_rate="dripping")
Then: Use result to provide specific diagnosis, cost, and urgency
"""

    async def process_message(
        self,
        channel_id: str,
        user_id: str,
        message: str,
        persona: str = "tenant"
    ) -> Dict[str, Any]:
        """
        Process user message using Responses API.

        This is the main entry point that replaces the old dual-agent flow.

        Flow:
        1. Get or create conversation
        2. Call Responses API with user message
        3. Extract assistant message + tool calls
        4. Send assistant message to user FIRST (preserve empathy!)
        5. If tool calls exist, execute them in a loop
        6. Update conversation state

        Args:
            channel_id: Slack channel ID
            user_id: User identifier
            message: User's message text
            persona: User role (tenant, landlord, contractor)

        Returns:
            dict: Result with success, message, tool_calls_executed, etc.
        """
        try:
            logger.info(f"Processing message for channel: {channel_id}, user: {user_id}")

            # 1. Get or create conversation
            conversation_id = await self.conversation_manager.get_or_create_conversation(
                channel_id=channel_id,
                user_id=user_id,
                persona=persona
            )

            logger.info(f"Using conversation: {conversation_id}")

            # 2. Prepare input items with system prompt injection
            # Inject auto-tool-generation instructions into first user message
            enhanced_message = f"""<system_context>
{self.system_prompt}
</system_context>

<user_message>
{message}
</user_message>

REMEMBER: Use diagnostic tools proactively. Check if diagnose_* tools exist, or generate new ones with register_dynamic_tool."""

            input_items = [
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": enhanced_message
                        }
                    ]
                }
            ]

            # 3. Handle tool loop (call Response API + execute tools repeatedly)
            result = await self.handle_tool_loop(
                conversation_id=conversation_id,
                prompt_id=self.prompt_id,
                input_items=input_items,
                channel_id=channel_id,
                user_id=user_id,
                max_iterations=5
            )

            logger.info(f"Message processing complete: {result.get('tool_calls_executed', 0)} tool calls executed")

            return {
                "success": True,
                "conversation_id": conversation_id,
                "tool_calls_executed": result.get("tool_calls_executed", 0),
                "final_message": result.get("final_message"),
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "tool_calls_executed": 0
            }

    async def handle_tool_loop(
        self,
        conversation_id: str,
        prompt_id: str,
        input_items: List[Dict[str, Any]],
        channel_id: str,
        user_id: str,
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Handle explicit tool loop for Responses API.

        Responses API doesn't auto-loop like Assistants did, so we must:
        1. Call responses.create()
        2. Check for tool calls
        3. If tool calls exist, execute them
        4. Add tool outputs as new input items
        5. Repeat until no more tool calls (or max iterations reached)

        Args:
            conversation_id: OpenAI Conversation ID
            prompt_id: Prompt ID from dashboard
            input_items: Initial input items (user message or tool outputs)
            channel_id: Slack channel ID
            user_id: User identifier
            max_iterations: Maximum tool loop iterations (default: 5)

        Returns:
            dict: Result with tool_calls_executed count and final_message
        """
        iteration = 0
        total_tool_calls = 0
        current_input = input_items
        final_message = None

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Tool loop iteration {iteration}/{max_iterations}")

            # Call Responses API with tools enabled
            try:
                response = self.openai_client.responses.create(
                    prompt={"id": prompt_id},
                    conversation=conversation_id,
                    input=current_input,
                    tools=self.tools  # ✅ CRITICAL: Enable function calling
                )

                logger.info(f"Response received: {response.id}")

            except Exception as e:
                logger.error(f"Responses API error: {e}", exc_info=True)

                # Provide user-friendly error messages based on error type
                error_message = "I encountered an error processing your request. Please try again."

                # Check for OpenAI quota/billing errors
                if "insufficient_quota" in str(e).lower() or "429" in str(e):
                    error_message = (
                        "I'm currently unable to process requests due to API quota limits. "
                        "This is a temporary issue with the OpenAI service. "
                        "Please try again in a few minutes or contact support if this persists."
                    )
                    logger.error("⚠️ OpenAI quota exceeded - check billing at platform.openai.com")

                # Send error message to user
                self.bot.send_ai_message(
                    channel_id=channel_id,
                    persona="tenant",
                    text=error_message,
                    metadata={"error": str(e)}
                )
                break

            # Extract response content
            content = await self.extract_response_content(response)

            # Check for tool calls FIRST
            tool_calls = content.get("tool_calls", [])

            # Send assistant message if:
            # - This is the first iteration (initial user-facing response), OR
            # - No more tool calls (final diagnostic response with data)
            should_send_message = (
                content.get("assistant_message") and
                (iteration == 1 or not tool_calls)  # First iteration OR final response
            )

            if should_send_message:
                final_message = content["assistant_message"]
                self.bot.send_ai_message(
                    channel_id=channel_id,
                    persona="tenant",
                    text=final_message,
                    metadata={"response_id": response.id}
                )
                logger.info(f"Sent assistant message to user (iteration {iteration})")
            elif content.get("assistant_message"):
                logger.info(f"Skipping intermediate assistant message (tool output processing)")

            if not tool_calls:
                # No more tool calls - we're done
                logger.info(f"No tool calls in response, loop complete")
                break

            logger.info(f"Found {len(tool_calls)} tool calls to execute")

            # DEBUG: Log tool calls to verify IDs
            for tc in tool_calls:
                logger.info(f"  - Tool call ID: {tc.get('id')}, function: {tc.get('function', {}).get('name')}")

            # Execute tool calls
            tool_outputs = await self.execute_tool_calls(
                tool_calls=tool_calls,
                context={
                    "channel_id": channel_id,
                    "user_id": user_id,
                    "conversation_id": conversation_id
                }
            )

            total_tool_calls += len(tool_calls)

            # Prepare next iteration input (tool outputs)
            current_input = tool_outputs

            # DEBUG: Log tool outputs to verify format
            logger.info(f"🔍 DEBUG: Sending {len(tool_outputs)} tool outputs:")
            for output in tool_outputs:
                logger.info(f"  - call_id: {output.get('call_id')}, type: {output.get('type')}")

        if iteration >= max_iterations:
            logger.warning(f"Tool loop reached max iterations ({max_iterations})")
            self.bot.send_ai_message(
                channel_id=channel_id,
                persona="tenant",
                text="I'm processing your request. This might take a moment...",
                metadata={"max_iterations_reached": True}
            )

        return {
            "tool_calls_executed": total_tool_calls,
            "final_message": final_message,
            "iterations": iteration
        }

    async def execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute tool calls and convert results to tool_output items.

        Integrates with existing function_registry.execute_function().

        Args:
            tool_calls: List of tool call objects from Response
            context: Execution context (channel_id, user_id, etc.)

        Returns:
            list: Tool output items ready for next Responses API call
        """
        tool_outputs = []

        for tool_call in tool_calls:
            try:
                # Extract function details
                tool_call_id = tool_call.get("id")
                function_name = tool_call.get("function", {}).get("name")
                arguments_str = tool_call.get("function", {}).get("arguments", "{}")

                # Parse arguments
                try:
                    arguments = json.loads(arguments_str)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse arguments: {arguments_str}")
                    arguments = {}

                logger.info(f"Executing tool: {function_name} with args: {arguments}")

                # Execute function via function_registry
                result = await execute_function(
                    function_name=function_name,
                    arguments=arguments,
                    context=context
                )

                # Convert FunctionResult to function_call_output format (Responses API)
                output_data = {
                    "success": result.success,
                    "data": result.data,
                    "message": result.message,
                    "error": result.error
                }

                tool_outputs.append({
                    "type": "function_call_output",  # Responses API format
                    "call_id": tool_call_id,  # Responses API uses 'call_id' not 'tool_call_id'
                    "output": json.dumps(output_data)
                })

                logger.info(f"Tool {function_name} executed: success={result.success}")

                # 🔄 CRITICAL: If register_dynamic_tool was called, refresh tools list
                # This makes the new tool available in the SAME conversation
                if function_name == "register_dynamic_tool" and result.success:
                    logger.info("🔄 Refreshing tools after register_dynamic_tool...")
                    self._refresh_tools()
                    logger.info(f"✅ New tool is now available for immediate use")

            except Exception as e:
                logger.error(f"Error executing tool call: {e}", exc_info=True)

                # Add error output
                tool_outputs.append({
                    "type": "function_call_output",  # Responses API format
                    "call_id": tool_call.get("id"),  # Responses API uses 'call_id' not 'tool_call_id'
                    "output": json.dumps({
                        "success": False,
                        "error": str(e),
                        "message": "Tool execution failed"
                    })
                })

        return tool_outputs

    async def extract_response_content(
        self,
        response: Any
    ) -> Dict[str, Any]:
        """
        Extract assistant message and tool calls from Response object.

        Args:
            response: OpenAI Response object

        Returns:
            dict: {
                "assistant_message": str or None,
                "tool_calls": list of tool call objects
            }
        """
        content = {
            "assistant_message": None,
            "tool_calls": []
        }

        # Iterate through output items
        for item in response.output:
            # Extract assistant messages
            if item.type == "message" and item.role == "assistant":
                # Get text from content
                if item.content and len(item.content) > 0:
                    for content_item in item.content:
                        if hasattr(content_item, "text"):
                            content["assistant_message"] = content_item.text
                            break
                        elif content_item.get("type") == "text":
                            content["assistant_message"] = content_item.get("text", "")
                            break

            # Extract tool calls (Responses API uses flat format: item.name, not item.function.name)
            elif item.type == "function_call" or hasattr(item, "name"):
                # DEBUG: Log available fields on the item
                logger.info(f"🔍 DEBUG: Function call item fields: {dir(item)}")
                logger.info(f"🔍 DEBUG: item.id = {item.id}")
                if hasattr(item, 'call_id'):
                    logger.info(f"🔍 DEBUG: item.call_id = {item.call_id}")

                content["tool_calls"].append({
                    "id": item.call_id,  # Responses API uses call_id (not id)
                    "type": "function",
                    "function": {
                        "name": item.name,  # Flat format in Responses API
                        "arguments": item.arguments  # Flat format in Responses API
                    }
                })

        return content


# Singleton instance
_response_handler = None


def get_response_handler():
    """Get or create ResponseHandler singleton"""
    global _response_handler
    if _response_handler is None:
        _response_handler = ResponseHandler()
    return _response_handler
