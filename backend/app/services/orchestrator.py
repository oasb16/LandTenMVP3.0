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
from ..services.openai_wrapper import get_openai_wrapper, RateLimitExceeded

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

        # 🚨 CRITICAL FIX: Hard token budgets to prevent TPM explosions
        self.MAX_INPUT_TOKENS = 10000  # Hard limit on input tokens
        self.MAX_SYSTEM_PROMPT_TOKENS = 3000  # Trim system prompt if longer
        self.MAX_CONVERSATION_MESSAGES = 3  # Last N messages only
        self.MAX_DISCOVERY_HINT_TOKENS = 300  # Limit hint verbosity

    def _get_openai_client(self) -> OpenAI:
        """Lazy OpenAI client initialization with retry configuration"""
        if self.openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
            # FIXED: Configure max_retries to prevent Heroku H12 timeout
            # max_retries=2 with exponential backoff (~1s, ~2s) keeps total under 5s
            self.openai_client = OpenAI(
                api_key=api_key,
                max_retries=2,  # Limit retries to prevent 30s+ webhook timeout
                timeout=25.0,   # Fail fast if single request takes > 25s
            )
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

    def _estimate_token_count(self, text: str) -> int:
        """
        🚨 CRITICAL FIX: Accurate token estimation for budget enforcement.
        Uses character-based heuristic: ~4 chars per token for English.
        """
        return len(text) // 4

    def _trim_to_token_budget(self, text: str, max_tokens: int) -> str:
        """
        🚨 CRITICAL FIX: Trim text to fit within token budget.
        Truncates from the middle to preserve beginning and end context.
        """
        estimated_tokens = self._estimate_token_count(text)

        if estimated_tokens <= max_tokens:
            return text

        # Truncate to fit budget (preserve beginning + end)
        target_chars = max_tokens * 4
        if len(text) <= target_chars:
            return text

        # Keep first 60% and last 20%, trim middle
        keep_start = int(target_chars * 0.6)
        keep_end = int(target_chars * 0.2)

        trimmed = text[:keep_start] + f"\n\n[... {estimated_tokens - max_tokens} tokens trimmed ...]\n\n" + text[-keep_end:]

        logger.warning(f"⚠️ Trimmed text from {estimated_tokens} to ~{max_tokens} tokens")
        return trimmed

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
                "incident_id": meta_context.discovery.incident_id if (meta_context.discovery and hasattr(meta_context.discovery, "incident_id")) else None,
                "question_index": meta_context.discovery.question_index if meta_context.discovery else 0,
                "questions": meta_context.discovery.questions if meta_context.discovery else [],
                "answers": meta_context.discovery.answers if meta_context.discovery else {},
                # is_active should be True when stage is "discovery" or when there are questions in progress
                # This supports both pre-incident discovery (incident_id=None) and incident-based discovery
                "is_active": meta_context.stage == "discovery" or (meta_context.discovery and len(meta_context.discovery.questions) > 0),
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

            # 🚨 FIX: Extract JSON from response even if there's explanatory text before it
            # LLM sometimes outputs: "explanation text\n```json\n{...}\n```"
            json_block_match = None
            if "```json" in response_text or "```\n{" in response_text:
                import re
                # Extract JSON from code block
                json_block_pattern = r'```(?:json)?\s*\n([\s\S]*?)\n```'
                match = re.search(json_block_pattern, response_text)
                if match:
                    json_block_match = match.group(1).strip()
                    logger.info(f"📦 Extracted JSON from code block (ignoring explanatory text)")
                    response_text = json_block_match

            is_json = response_text.startswith("{") or json_block_match is not None

            # If NOT JSON, check if it's intentional natural language
            if not is_json:
                # Check for natural language patterns
                natural_indicators = [
                    response_text.lower().startswith(("hi", "hello", "that ", "got it", "sure", "we're")),
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
            # Handle markdown code blocks at start of response
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

    def _determine_next_action(
        self,
        meta_context: MetaContext,
        user_message: str,
        agent_structured_output: Optional[Dict[str, Any]] = None,
    ) -> Optional[OrchestratorOutput]:
        """
        PHASE OMEGA: Single Flow Engine - State Machine for all transitions.
        Decides the next action based on current stage WITHOUT calling LLM.

        Returns OrchestratorOutput if action is determined, None if LLM call needed.
        """
        stage = meta_context.stage
        incident_id = meta_context.active_incident_id

        logger.info(f"🎯 State machine check: stage={stage}, incident={incident_id}")

        # STATE: discovery_complete → MUST call start_diagnosis
        if stage == "discovery_complete" and incident_id:
            logger.info(f"✅ State machine: discovery_complete → start_diagnosis")
            return OrchestratorOutput(
                intent="start_diagnosis",
                reasoning="State machine: discovery_complete requires diagnosis",
                context_updates=ContextUpdates(stage="diagnosing"),
                function_call=FunctionCall(
                    name="start_diagnosis",
                    arguments={"incident_id": incident_id},
                ),
                response_to_user=None,
            )

        # STATE: diagnosing + user approval ("yes", "ok", "sure") → create_work_order
        if stage == "diagnosing" and incident_id:
            user_lower = user_message.lower().strip()
            approval_keywords = ["yes", "ok", "sure", "proceed", "go ahead", "create it", "sounds good"]

            if any(keyword in user_lower for keyword in approval_keywords):
                logger.info(f"✅ State machine: diagnosing + approval → create_work_order")
                return OrchestratorOutput(
                    intent="create_work_order",
                    reasoning="State machine: user approved work order creation",
                    context_updates=ContextUpdates(stage="work_order"),
                    function_call=FunctionCall(
                        name="create_work_order",
                        arguments={
                            "incident_id": incident_id,
                            "title": f"Repair for incident {incident_id}",
                            "estimated_cost": "250.00",
                        },
                    ),
                    response_to_user=None,
                )

        # No state machine action determined - proceed to LLM
        return None

    def _should_skip_llm(self, agent_response: Optional[Dict[str, Any]]) -> bool:
        """
        PHASE OMEGA: Check if we should skip LLM call.
        Returns True if agent provided structured output with function call.
        """
        if not agent_response:
            return False

        structured = agent_response.get("structured_output")
        if structured and structured.get("function_call"):
            logger.info(f"⚡ Skipping LLM - agent provided function: {structured['function_call']}")
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
            # Check if this is for the SAME incident or a NEW issue
            # If incident_id is in arguments and matches active_incident_id, it's a duplicate
            # If no incident_id in arguments, it's a NEW issue (pre-incident discovery) - allow it
            requested_incident_id = output.function_call.arguments.get("incident_id")

            # Only block if trying to restart discovery for the SAME incident
            if requested_incident_id and requested_incident_id == meta_context.active_incident_id:
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
                        logger.warning(f"🛑 GUARDRAIL: Blocked duplicate start_discovery for incident {requested_incident_id} (status={incident_status})")
                        return OrchestratorOutput(
                            intent="general.chat",
                            reasoning=f"Discovery already started/completed for this incident",
                            context_updates=ContextUpdates(),
                            function_call=FunctionCall(name=None, arguments={}),
                            response_to_user="I'm already gathering information about this issue. What else would you like me to know?",
                        )
            else:
                # No incident_id or different incident_id - this is a NEW issue, allow it
                if not requested_incident_id:
                    logger.info("✅ Allowing pre-incident discovery for NEW issue")
                else:
                    logger.info(f"✅ Allowing discovery for different incident {requested_incident_id}")

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
            # 🚨 CRITICAL FIX: Removed agent router call from orchestrator to prevent double-invocation
            # Agent routing is now handled ONLY in ai_webhooks_v3.py (handle_new_message_background)
            # This eliminates the circular dependency:
            #   OLD: webhook → agent router → orchestrator → agent router (DUPLICATE!)
            #   NEW: webhook → agent router OR orchestrator (SINGLE PATH)

            # 🚨 CRITICAL FIX: Topic graph integration moved to webhook layer to prevent duplicate calls
            # All topic detection now happens in handle_new_message_background() BEFORE calling orchestrator

            # 🚀 PHASE OMEGA: State Machine Pre-flight Check
            # Check if state machine can determine next action without LLM
            state_machine_output = self._determine_next_action(
                meta_context=meta_context,
                user_message=user_message,
                agent_structured_output=None,  # No agent pre-processing in orchestrator
            )

            if state_machine_output:
                logger.info(f"⚡ State machine decided action: {state_machine_output.function_call.name}")
                # Apply stage transitions
                state_machine_output = self._handle_stage_transitions(state_machine_output, meta_context)
                state_machine_output = self._apply_guardrails(state_machine_output, meta_context)
                return state_machine_output

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

            # 🚨 CRITICAL FIX: Removed agent response injection to prevent token explosion
            # Agent routing happens BEFORE orchestrator, not INSIDE it

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

            # 🚨 CRITICAL FIX: Shortened stage hints to reduce token usage (500+ → 100 tokens each)
            if meta_context.stage == "discovery" and meta_context.active_incident_id:
                user_content = (
                    f"🔍 Discovery Q{meta_context.discovery.question_index} for {meta_context.active_incident_id}. "
                    f"Record answer or create new incident if topic shift.\n"
                    + user_content
                )

            if meta_context.stage == "discovery_complete" and meta_context.active_incident_id:
                user_content = (
                    f"🔬 Discovery done for {meta_context.active_incident_id}. "
                    f"MUST call start_diagnosis.\n"
                    + user_content
                )

            if meta_context.stage == "diagnosing" and meta_context.active_incident_id:
                user_content = (
                    f"🩺 Diagnosing {meta_context.active_incident_id}. "
                    f"User approval → create_work_order. User details → record_diagnosis_result.\n"
                    + user_content
                )

            # Build tools
            tools = self._build_tools_for_openai(available_functions)

            # Call OpenAI API
            logger.info(f"Calling orchestrator LLM (HYBRID MODE) for intent: {meta_context.last_intent or 'initial'}")

            # 🚨 CRITICAL FIX: Apply token budgets to prevent TPM explosion
            # Trim system prompt if too verbose
            trimmed_system_prompt = self._trim_to_token_budget(
                self.system_prompt,
                self.MAX_SYSTEM_PROMPT_TOKENS
            )

            # Create messages
            messages = [{"role": "user", "content": user_content}]

            # Add conversation history for context (LIMIT TO LAST N MESSAGES)
            history_messages = meta_context.conversation_history[-self.MAX_CONVERSATION_MESSAGES:]
            for msg in history_messages:
                if msg.role == "user":
                    # Trim long user messages to prevent token explosion
                    trimmed_text = self._trim_to_token_budget(msg.text, 500)
                    messages.insert(0, {"role": "user", "content": trimmed_text})
                elif msg.role == "assistant":
                    # Trim long assistant messages
                    trimmed_text = self._trim_to_token_budget(msg.text, 500)
                    messages.insert(0, {"role": "assistant", "content": trimmed_text})

            # Ensure messages alternate and start with user
            if messages and messages[0]["role"] != "user":
                messages = messages[1:]

            # Insert system prompt as first message (with trimming applied)
            messages.insert(0, {"role": "system", "content": trimmed_system_prompt})

            # 🚨 CRITICAL FIX: Final safety check - estimate total input tokens
            total_input_text = "".join([m["content"] for m in messages])
            total_input_tokens = self._estimate_token_count(total_input_text)

            if total_input_tokens > self.MAX_INPUT_TOKENS:
                logger.error(
                    f"🚨 Input token budget exceeded: {total_input_tokens}/{self.MAX_INPUT_TOKENS} "
                    f"- further trimming conversation history"
                )
                # Emergency trim: reduce conversation history to 1 message
                messages = [
                    messages[0],  # Keep system prompt
                    messages[-1],  # Keep current user message only
                ]
                total_input_tokens = self._estimate_token_count("".join([m["content"] for m in messages]))
                logger.warning(f"⚠️ Emergency trim applied, new total: {total_input_tokens} tokens")

            logger.info(f"📊 Input tokens: ~{total_input_tokens}, Max output: {self.max_tokens}")

            # Call OpenAI with tool use (via rate-limit-aware wrapper)
            try:
                openai_wrapper = get_openai_wrapper()
                logger.info(f"messages being sent to LLM: {messages}")
                response = await openai_wrapper.chat_completion(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=messages,
                    tools=tools if tools else None,
                )
            except RateLimitExceeded as e:
                from ..utils.creative_messages import get_rate_limit_message

                logger.error(f"⛔ Rate limit exceeded in orchestrator: {e}")

                # Check if this is urgent based on incident urgency
                is_urgent = meta_context.metadata.get("urgency") in ["high", "emergency", "urgent"]
                persona = meta_context.persona or "tenant"

                return OrchestratorOutput(
                    intent="rate_limited",
                    reasoning=f"Rate limit exceeded: {str(e)}",
                    context_updates=ContextUpdates(),
                    function_call=FunctionCall(name=None, arguments={}),
                    response_to_user=get_rate_limit_message(persona, urgent=is_urgent),
                )

            # Extract response
            message = response.choices[0].message
            logger.info("Orchestrator LLM response received")
            logger.info(f"Response content: {message}")

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

            # Use wrapper for rate-limit awareness
            try:
                openai_wrapper = get_openai_wrapper()
                logger.info("Calling simple orchestrator LLM")
                logger.info(f"messages being sent : {messages}")
                response = await openai_wrapper.chat_completion(
                    model=self.model,
                    max_tokens=1024,
                    temperature=self.temperature,
                    messages=messages,
                )

                if response.choices and response.choices[0].message.content:
                    logger.info("Simple orchestrator LLM response received")
                    logger.info(f"Response content: {response.choices[0].message.content}")
                    return response.choices[0].message.content

                return "I'm not sure how to respond to that."

            except RateLimitExceeded:
                from ..utils.creative_messages import get_rate_limit_message
                return get_rate_limit_message("tenant", urgent=False)

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
