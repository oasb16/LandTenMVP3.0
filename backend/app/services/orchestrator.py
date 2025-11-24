"""
LLM Orchestrator Engine - Core intelligence layer for HYBRID MODE.
Handles all LLM interactions for intent classification, function selection, and response generation.
Supports both JSON tool calls and natural language responses.
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

    Operates in HYBRID MODE:
    - Outputs JSON for tool calls (incident creation, discovery, work orders)
    - Outputs natural language for greetings, clarifications, general chat
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
You are the LandTen V3 Orchestrator operating in HYBRID MODE.

For maintenance tasks → output JSON with tool calls
For conversation → output natural language

Always output EITHER:
1. Valid JSON: {"intent": "...", "function": "...", "arguments": {...}}
2. Natural text: "Hi! How can I help you today?"

NEVER mix both modes.
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
        """
        Format meta-context for LLM consumption.
        Enhanced for HYBRID MODE with complete incident state.
        """

        # Enhanced context with full incident state for topic locking
        context_dict = {
            "persona": meta_context.persona,
            "stage": meta_context.stage,
            "active_incident_id": meta_context.active_incident_id,
            "active_job_id": meta_context.active_job_id,

            # Discovery state
            "discovery": {
                "incident_id": meta_context.discovery.incident_id if hasattr(meta_context.discovery, "incident_id") else None,
                "question_index": meta_context.discovery.question_index,
                "questions": meta_context.discovery.questions,
                "answers": meta_context.discovery.answers,
                "is_active": meta_context.stage == "discovery" and meta_context.active_incident_id is not None,
            },

            "last_intent": meta_context.last_intent,
            "last_user_message": meta_context.last_user_message,

            # CRITICAL: Active incident metadata for topic locking
            "metadata": {
                "active_incident_status": meta_context.metadata.get("active_incident_status"),
                "active_incident_category": meta_context.metadata.get("active_incident_category"),
                "active_incident_title": meta_context.metadata.get("active_incident_title"),
                "active_incident_description": meta_context.metadata.get("active_incident_description"),
                "property_id": meta_context.metadata.get("property_id"),
            },

            "conversation_history": [
                {"role": msg.role, "text": msg.text, "timestamp": msg.timestamp}
                for msg in meta_context.conversation_history[-5:]  # Last 5 messages
            ],

            "entities": meta_context.entities,
            "user_id": meta_context.user_id,
            "channel_id": meta_context.channel_id,
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

    def _parse_orchestrator_output(self, response_text: str, retry_count: int = 0) -> OrchestratorOutput:
        """
        Parse LLM response into OrchestratorOutput with HYBRID MODE support.

        HYBRID MODE: Response can be EITHER:
        1. JSON (for tool calls) - parse as structured output
        2. Natural language (for conversation) - treat as natural response
        """
        try:
            response_text = response_text.strip()

            # === HYBRID MODE DETECTION ===
            # If response looks like JSON, parse it as a tool call
            # If response is natural language, treat it as conversational response

            is_json = response_text.startswith("{") or response_text.startswith("```")

            # If NOT JSON, check if it's intentional natural language
            if not is_json:
                # Check for natural language patterns
                natural_indicators = [
                    response_text.lower().startswith(("hi", "hello", "i ", "that ", "got it", "sure", "we're")),
                    "?" in response_text,
                    len(response_text.split()) > 3 and not response_text.startswith("{"),
                ]

                if any(natural_indicators):
                    logger.info(f"✅ Detected natural language response: {response_text[:100]}")
                    return OrchestratorOutput(
                        intent="general.chat",
                        reasoning="Natural language response detected",
                        context_updates=ContextUpdates(),
                        function_call=FunctionCall(name=None, arguments={}),
                        response_to_user=response_text,
                    )
                else:
                    # Ambiguous - might be malformed JSON
                    logger.warning(f"⚠️ Ambiguous response (not JSON, not natural): {response_text[:100]}")
                    raise ValueError(f"Response is neither valid JSON nor natural language: {response_text[:50]}")

            # === JSON PARSING MODE ===
            # Handle markdown code blocks
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                # Strip ```json or ``` from first line
                if lines[0].strip() in ["```json", "```"]:
                    response_text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            response_json = json.loads(response_text)

            # Validate required fields exist
            if "intent" not in response_json:
                logger.warning("Missing 'intent' in LLM response, defaulting to 'unknown'")
                response_json["intent"] = "unknown"

            # Support multiple JSON formats
            # Format 1: {"intent": "...", "function": "...", "arguments": {...}}
            # Format 2: {"intent": "...", "function_call": {"name": "...", "arguments": {...}}}

            if "function_call" in response_json and isinstance(response_json["function_call"], dict):
                # Format 2
                function_call_data = response_json["function_call"]
                function_call = FunctionCall(**function_call_data)
            elif "function" in response_json:
                # Format 1
                function_name = response_json.get("function")
                if function_name == "none" or function_name is None:
                    function_call = FunctionCall(name=None, arguments={})
                else:
                    function_call = FunctionCall(
                        name=function_name,
                        arguments=response_json.get("arguments", {})
                    )
            else:
                # No function specified
                function_call = FunctionCall(name=None, arguments={})

            # Build context updates
            context_updates_data = response_json.get("context_updates", {})
            context_updates = ContextUpdates(**context_updates_data) if context_updates_data else ContextUpdates()

            # Build orchestrator output
            output = OrchestratorOutput(
                intent=response_json.get("intent", "unknown"),
                reasoning=response_json.get("reasoning", ""),
                context_updates=context_updates,
                function_call=function_call,
                response_to_user=response_json.get("response_to_user"),
            )

            logger.info(f"✅ Parsed JSON successfully: intent={output.intent}, function={output.function_call.name or 'none'}")
            return output

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"❌ Parsing failed: {e}")
            logger.error(f"Response text: {response_text[:500]}")

            # Return error state - do NOT fall back to general.chat
            return OrchestratorOutput(
                intent="json_parse_error",
                reasoning=f"LLM failed to output valid response (attempt {retry_count + 1})",
                context_updates=ContextUpdates(),
                function_call=FunctionCall(name=None, arguments={}),
                response_to_user="I'm having trouble processing that request. Could you please rephrase it?",
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

    def _is_garbage_input(self, user_message: str) -> bool:
        """
        🚨 FIX: Enhanced garbage input detection for HYBRID MODE.
        Returns True if input should be rejected as garbage.
        """
        message_lower = user_message.lower().strip()
        message_clean = user_message.strip()

        # Check for greetings (NOT garbage, but should not trigger incidents)
        greeting_patterns = ["hi", "hello", "hey", "sup", "ok", "thanks", "yes", "no", "k", "lol", "yo"]
        if message_lower in greeting_patterns:
            return False  # Greetings are valid, not garbage

        # 🚨 FIX: Enhanced garbage detection patterns
        garbage_checks = [
            len(message_clean) < 3,  # Too short
            all(c in "!?.,;:'\"-_()[]{}/" for c in message_clean),  # All punctuation

            # 🚨 NEW: Detect random keyboard mashing (like "asdafd")
            len(set(message_clean.lower())) <= 4 and len(message_clean) >= 4,  # Limited char variety

            # 🚨 NEW: Detect repeated patterns ("why why why why")
            len(message_clean.split()) > 2 and len(set(message_clean.split())) == 1,  # All same word

            # 🚨 NEW: Detect gibberish (no vowels or only vowels)
            len(message_clean) > 5 and not any(c in 'aeiou' for c in message_lower),  # No vowels
            len(message_clean) > 5 and all(c in 'aeiou ' for c in message_lower),  # Only vowels

            # 🚨 NEW: Detect single-character spam ("...", "???")
            len(message_clean) > 3 and len(set(message_clean)) == 1,  # All same char
        ]

        # Check for maintenance keywords to override garbage detection
        maintenance_keywords = [
            "leak", "broken", "clog", "drip", "smell", "noise", "crack", "malfunction",
            "issue", "problem", "repair", "fix", "stopped", "won't", "doesn't", "can't",
            "flooding", "sparking", "burning", "sink", "toilet", "fridge", "heater",
            "ac", "door", "window", "outlet", "breaker", "emergency", "urgent", "garage"
        ]
        has_maintenance_keyword = any(keyword in message_lower for keyword in maintenance_keywords)

        # If garbage AND no maintenance keywords → it's garbage
        if any(garbage_checks) and not has_maintenance_keyword:
            logger.info(f"🗑️ Garbage detected: '{user_message[:50]}'")
            return True

        return False

    def _handle_stage_transitions(
        self,
        output: OrchestratorOutput,
        meta_context: MetaContext,
    ) -> OrchestratorOutput:
        """
        PHASE OMEGA OBJECTIVE #2: CANONICAL STAGE ROUTING
        All stage transitions happen here - single source of truth
        """
        function_name = output.function_call.name
        current_stage = meta_context.stage

        # Stage transition rules
        stage_transitions = {
            "create_incident": "detected",
            "start_discovery": "discovery",
            "start_diagnosis": "diagnosing",
            "create_work_order": "work_order",
        }

        # Apply stage transition if function triggers one
        if function_name in stage_transitions:
            new_stage = stage_transitions[function_name]
            if current_stage != new_stage:
                logger.info(f"🔄 Stage transition: {current_stage} → {new_stage} (triggered by {function_name})")
                output.context_updates.stage = new_stage

        return output

    def _handle_auto_evolving_tools(
        self,
        output: OrchestratorOutput,
        meta_context: MetaContext,
    ) -> OrchestratorOutput:
        """
        PHASE OMEGA OBJECTIVE #4: AUTO-EVOLVING DIAGNOSTIC TOOLS
        Check if diagnosis suggested a new tool and prompt user for permission
        """
        # Check if start_diagnosis was called
        if output.function_call.name == "start_diagnosis":
            # Mark that we should check for tool suggestions after diagnosis
            if not output.context_updates.metadata:
                output.context_updates.metadata = {}
            output.context_updates.metadata["check_tool_suggestion"] = True

        return output

    def _apply_guardrails(
        self,
        output: OrchestratorOutput,
        meta_context: MetaContext,
    ) -> OrchestratorOutput:
        """
        PHASE OMEGA: Enhanced guardrails with de-duplication
        """

        # PHASE OMEGA OBJECTIVE #5: DISCOVERY DE-DUPLICATION
        if output.function_call.name == "start_discovery":
            incident = None
            try:
                from ..services.dynamo_service import get_dynamo_service
                dynamo = get_dynamo_service()
                incident = dynamo.get_incident(
                    meta_context.active_incident_id,
                    meta_context.user_id
                )
            except Exception as e:
                logger.error(f"Error checking incident status: {e}")

            if incident:
                incident_status = incident.get("status")
                if incident_status in ["discovery", "discovery_complete", "diagnosing", "work_order"]:
                    logger.warning(f"🛑 GUARDRAIL: Blocked duplicate start_discovery (status={incident_status})")
                    return OrchestratorOutput(
                        intent="general.chat",
                        reasoning=f"Discovery already started/completed for this incident",
                        context_updates=ContextUpdates(),
                        function_call=FunctionCall(name=None, arguments={}),
                        response_to_user="I'm already gathering information about this issue. What else would you like me to know?",
                    )

        # PHASE OMEGA OBJECTIVE #6: DIAGNOSIS DE-DUPLICATION
        if output.function_call.name == "start_diagnosis":
            # Check if stage is correct
            if meta_context.stage not in ["discovery_complete", "diagnosing"]:
                logger.warning(f"🛑 GUARDRAIL: Blocked start_diagnosis in stage {meta_context.stage}")
                return OrchestratorOutput(
                    intent="general.chat",
                    reasoning=f"Cannot diagnose - wrong stage: {meta_context.stage}",
                    context_updates=ContextUpdates(),
                    function_call=FunctionCall(name=None, arguments={}),
                    response_to_user="Let's complete the discovery questions first before diagnosing the issue.",
                )

            # Check if already diagnosing
            if meta_context.stage == "diagnosing":
                logger.warning(f"🛑 GUARDRAIL: Blocked duplicate start_diagnosis")
                return OrchestratorOutput(
                    intent="create_work_order",
                    reasoning=f"Diagnosis already complete",
                    context_updates=ContextUpdates(stage="work_order"),
                    function_call=FunctionCall(
                        name="create_work_order",
                        arguments={
                            "incident_id": meta_context.active_incident_id,
                            "title": f"Repair for {meta_context.active_incident_id}",
                            "estimated_cost": "250.00",
                        },
                    ),
                    response_to_user=None,
                )

        # GUARDRAIL #1: discovery_complete MUST trigger start_diagnosis
        if meta_context.stage == "discovery_complete":
            if output.function_call.name == "create_incident":
                logger.warning(f"🛑 GUARDRAIL ACTIVATED: Blocked create_incident during discovery_complete")
                logger.warning(f"   Original intent: {output.intent}")
                logger.warning(f"   Overriding to: start_diagnosis")

                return OrchestratorOutput(
                    intent="start_diagnosis",
                    reasoning=f"GUARDRAIL OVERRIDE: discovery_complete stage requires diagnosis, not incident creation. Original: {output.reasoning}",
                    context_updates=ContextUpdates(stage="diagnosing"),
                    function_call=FunctionCall(
                        name="start_diagnosis",
                        arguments={"incident_id": meta_context.active_incident_id},
                    ),
                    response_to_user=None,
                )

            elif output.function_call.name is None and output.intent == "general.chat":
                logger.warning(f"🛑 GUARDRAIL ACTIVATED: Blocked general.chat during discovery_complete")
                logger.warning(f"   Overriding to: start_diagnosis")

                return OrchestratorOutput(
                    intent="start_diagnosis",
                    reasoning=f"GUARDRAIL OVERRIDE: discovery_complete requires diagnosis, not chat",
                    context_updates=ContextUpdates(stage="diagnosing"),
                    function_call=FunctionCall(
                        name="start_diagnosis",
                        arguments={"incident_id": meta_context.active_incident_id},
                    ),
                    response_to_user=None,
                )

        # GUARDRAIL #2: diagnosing stage MUST NOT create new incidents
        if meta_context.stage == "diagnosing":
            if output.function_call.name == "create_incident":
                logger.warning(f"🛑 GUARDRAIL ACTIVATED: Blocked create_incident during diagnosing")
                logger.warning(f"   Active incident: {meta_context.active_incident_id}")
                logger.warning(f"   Overriding to: record_diagnosis_result")

                # Extract title/description from attempted incident creation
                attempted_args = output.function_call.arguments or {}
                diagnosis_notes = f"User provided: {attempted_args.get('title', '')} - {attempted_args.get('description', '')}"

                return OrchestratorOutput(
                    intent="record_diagnosis_result",
                    reasoning=f"GUARDRAIL OVERRIDE: diagnosing stage, treating as additional diagnosis info",
                    context_updates=ContextUpdates(),
                    function_call=FunctionCall(
                        name="record_diagnosis_result",
                        arguments={
                            "incident_id": meta_context.active_incident_id,
                            "diagnosis_notes": diagnosis_notes,
                        },
                    ),
                    response_to_user=None,
                )

        # GUARDRAIL #3: discovery stage MUST record answers, not create incidents
        if meta_context.stage == "discovery":
            if output.function_call.name == "create_incident":
                logger.warning(f"🛑 GUARDRAIL ACTIVATED: Blocked create_incident during discovery")
                logger.warning(f"   Active incident: {meta_context.active_incident_id}")
                logger.warning(f"   Overriding to: record_discovery_answer")

                # Extract description from attempted incident creation
                attempted_args = output.function_call.arguments or {}
                answer_text = attempted_args.get('description', attempted_args.get('title', 'Yes'))

                return OrchestratorOutput(
                    intent="record_discovery_answer",
                    reasoning=f"GUARDRAIL OVERRIDE: discovery stage, treating as discovery answer",
                    context_updates=ContextUpdates(),
                    function_call=FunctionCall(
                        name="record_discovery_answer",
                        arguments={
                            "incident_id": meta_context.active_incident_id,
                            "question_index": meta_context.discovery.question_index,
                            "answer": answer_text,
                        },
                    ),
                    response_to_user=None,
                )

        # 🚨 GUARDRAIL #4: TOPIC SHIFT DETECTION - Allow new incident when user mentions unrelated issue
        # If user mentions a NEW maintenance issue while in post-discovery stages, allow topic switch
        if meta_context.active_incident_id and meta_context.stage in ["discovery_complete", "diagnosing", "work_order"]:
            # Check if LLM detected create_incident intent (topic shift detected)
            if output.function_call.name == "create_incident":
                # This is likely a new unrelated issue - allow it
                logger.warning(f"🔄 TOPIC SHIFT DETECTED: New incident while in {meta_context.stage}")
                logger.warning(f"   Previous incident: {meta_context.active_incident_id}")
                logger.warning(f"   User message: {meta_context.last_user_message[:80]}")
                logger.warning(f"   Allowing topic switch to create new incident")

                # Clear previous incident context to allow new incident
                output.context_updates = ContextUpdates(
                    active_incident_id=None,  # Clear previous incident
                    stage="idle",  # Reset to idle for new incident
                )

                return output

        # No guardrails triggered - return original output
        return output

    async def run(
        self,
        user_message: str,
        meta_context: MetaContext,
        available_functions: List[FunctionDefinition],
        function_result: Optional[FunctionResult] = None,
    ) -> OrchestratorOutput:
        """
        Main orchestrator entry point for HYBRID MODE.

        Sends user message + context to LLM, receives either:
        - JSON with tool call (for maintenance tasks)
        - Natural language text (for conversation)
        """
        try:
            # 🚀 PHASE OMEGA: Multi-Agent Pipeline Integration
            agent_response = None
            try:
                from ..agents.agent_router import get_agent_router

                agent_router = get_agent_router()
                agent_context = {
                    "stage": meta_context.stage,
                    "active_incident_id": meta_context.active_incident_id,
                    "persona": meta_context.persona,
                    "metadata": meta_context.metadata,
                }

                agent_response = await agent_router.route(
                    message=user_message,
                    context=agent_context,
                )

                logger.info(f"🤖 Agent router: {agent_response.get('agent_type', 'unknown')}")

                if agent_response and agent_response.get("structured_output"):
                    structured = agent_response["structured_output"]
                    if structured.get("function_call"):
                        logger.info(f"🎯 Agent pre-selected function: {structured['function_call']}")

            except Exception as e:
                logger.error(f"Agent router error: {e}", exc_info=True)
                agent_response = None

            # 🚀 PHASE OMEGA: Topic Graph Integration
            topic_shift_detected = False
            incident_graph_context = None
            try:
                from ..services.incident_topic_graph import get_incident_graph

                if meta_context.active_incident_id:
                    incident_graph = get_incident_graph(meta_context.user_id)

                    shift_result = incident_graph.detect_topic_shift(
                        user_message=user_message,
                        current_incident_id=meta_context.active_incident_id
                    )

                    topic_shift_detected = shift_result.get("is_shift", False)

                    if topic_shift_detected:
                        logger.info(f"🔀 Topic shift detected: {shift_result.get('reason')}")
                        incident_graph_context = shift_result

            except Exception as e:
                logger.error(f"Topic graph error: {e}", exc_info=True)

            client = self._get_openai_client()

            # 🚨 CRITICAL PRE-FLIGHT CHECK: Garbage input filter
            if self._is_garbage_input(user_message):
                logger.info(f"🗑️ Garbage input detected: {user_message[:50]}")
                return OrchestratorOutput(
                    intent="garbage_input",
                    reasoning="Input is too short, greeting, or nonsense without maintenance keywords",
                    context_updates=ContextUpdates(),
                    function_call=FunctionCall(name=None, arguments={}),
                    response_to_user="I didn't quite catch that—could you describe what's going on at the property?",
                )

            # 🚨 CRITICAL PRE-FLIGHT CHECK: Load active incident data for topic locking
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
                        meta_context.metadata["active_incident_status"] = "completed"
                        meta_context.metadata["active_incident_category"] = incident.get("category")
                        meta_context.metadata["active_incident_title"] = incident.get("title")
                    elif incident:
                        meta_context.metadata["active_incident_status"] = incident.get("status")
                        meta_context.metadata["active_incident_category"] = incident.get("category")
                        meta_context.metadata["active_incident_title"] = incident.get("title")
                        meta_context.metadata["active_incident_description"] = incident.get("description", "")[:200]

                        logger.info(f"📌 Active incident context: {incident.get('title')} ({incident.get('status')})")

                except Exception as e:
                    logger.error(f"Error checking active incident status: {e}")

            # Build user message content
            user_content_parts = []

            # Add agent response as context enhancement if available
            if agent_response and agent_response.get("agent_response"):
                user_content_parts.append(
                    f"**🤖 Specialized Agent Input ({agent_response.get('agent_type')}):**\n{agent_response.get('agent_response')}\n"
                )

            # Add topic shift detection results
            if topic_shift_detected and incident_graph_context:
                user_content_parts.append(
                    f"**🔀 Topic Shift Detected:** User may be discussing a different incident. Details: {incident_graph_context.get('reason')}\n"
                )

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

            # 🚨 CRITICAL: Add discovery flow detection hints
            if meta_context.stage == "discovery" and meta_context.active_incident_id:
                user_content = (
                    f"🔍 **DISCOVERY MODE ACTIVE**\n"
                    f"Incident {meta_context.active_incident_id} is in discovery.\n"
                    f"Question index: {meta_context.discovery.question_index}\n"
                    f"If user sends text answer → call record_discovery_answer\n"
                    f"If user mentions NEW issue → pause discovery, create new incident\n\n"
                    + user_content
                )

            # 🚨 CRITICAL: Add discovery_complete → diagnosing mandatory flow hint
            if meta_context.stage == "discovery_complete" and meta_context.active_incident_id:
                user_content = (
                    f"🔬 **DISCOVERY COMPLETE → DIAGNOSIS REQUIRED**\n"
                    f"Incident {meta_context.active_incident_id} has completed discovery.\n"
                    f"YOU MUST CALL: start_diagnosis\n"
                    f"DO NOT call create_incident\n"
                    f"DO NOT respond with general.chat\n"
                    f"MANDATORY ACTION: call start_diagnosis immediately\n\n"
                    + user_content
                )

            # 🚨 CRITICAL: Add diagnosing stage hint
            if meta_context.stage == "diagnosing" and meta_context.active_incident_id:
                user_content = (
                    f"🩺 **DIAGNOSING MODE ACTIVE**\n"
                    f"Incident {meta_context.active_incident_id} is being diagnosed.\n"
                    f"🚨 CRITICAL RULES:\n"
                    f"  - If user says 'yes', 'ok', 'sure' → call create_work_order\n"
                    f"  - If user says 'no' → respond with general.chat\n"
                    f"  - If user provides details → call record_diagnosis_result\n"
                    f"  - DO NOT call create_incident\n"
                    f"  - DO NOT call start_diagnosis again\n\n"
                    + user_content
                )

            # Build tools
            tools = self._build_tools_for_openai(available_functions)

            # Call OpenAI API
            logger.info(f"Calling orchestrator LLM (HYBRID MODE) for intent: {meta_context.last_intent or 'initial'}")

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
                tools=tools if tools else None,
            )

            # Extract response
            message = response.choices[0].message

            # Check if response contains tool calls (OpenAI native tool calling)
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                logger.info(f"🔧 LLM selected tool: {tool_call.function.name}")

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

                # 🚨 CRITICAL GUARDRAIL: Override incorrect LLM decisions
                # PHASE OMEGA: Apply stage transitions
                output = self._handle_stage_transitions(output, meta_context)
                output = self._apply_guardrails(output, meta_context)
                output = self._handle_auto_evolving_tools(output, meta_context)

                return output

            # Otherwise, parse text content (could be JSON or natural language)
            elif message.content:
                output = self._parse_orchestrator_output(message.content)
                logger.info(f"📋 LLM intent: {output.intent}, function: {output.function_call.name or 'none'}")

                # 🚨 CRITICAL GUARDRAIL: Override incorrect LLM decisions
                # PHASE OMEGA: Apply stage transitions
                output = self._handle_stage_transitions(output, meta_context)
                output = self._apply_guardrails(output, meta_context)
                output = self._handle_auto_evolving_tools(output, meta_context)

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


async def record_agent_interaction(
    user_id: str,
    agent_type: str,
    user_message: str,
    agent_response: str,
    outcome: str,
) -> None:
    """
    🚀 PHASE OMEGA: Record agent interactions for auto-evolving skills
    """
    try:
        from ..services.auto_evolving_skills import get_skills_recorder

        recorder = get_skills_recorder()

        await recorder.record_interaction(
            user_id=user_id,
            agent_type=agent_type,
            user_message=user_message,
            agent_response=agent_response,
            outcome=outcome,
        )

        # Check if pattern detected and new skill should be created
        pattern_result = await recorder.detect_pattern(user_id)

        if pattern_result.get("pattern_detected"):
            logger.info(f"🎓 Pattern detected: {pattern_result.get('pattern_type')}")

            # Generate new skill/tool
            skill_result = await recorder.generate_skill(
                pattern_type=pattern_result["pattern_type"],
                examples=pattern_result.get("examples", []),
            )

            if skill_result.get("success"):
                logger.info(f"✨ Auto-generated skill: {skill_result.get('skill_name')}")

    except Exception as e:
        logger.error(f"Error recording agent interaction: {e}", exc_info=True)


# Singleton instance
_orchestrator = None


def get_orchestrator() -> LLMOrchestrator:
    """Get singleton instance of LLMOrchestrator"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = LLMOrchestrator()
    return _orchestrator
