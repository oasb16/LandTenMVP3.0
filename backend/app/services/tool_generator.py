"""
Tool Generator - LLM generates Python code for dynamic tools.

PHASE OMEGA: Real LLM-driven code generation, validation, and registration.
"""
import logging
from typing import Dict, Any, Optional, List
from openai import OpenAI

logger = logging.getLogger(__name__)


class ToolGenerator:
    """
    Generates Python code for dynamic tools using LLM.

    PHASE OMEGA: Automatically creates tools based on patterns and requests.
    """

    def __init__(self, model: str = "gpt-4o"):
        """
        Initialize tool generator.

        Args:
            model: OpenAI model to use for code generation
        """
        self.model = model
        self.client = None

    def _get_client(self) -> OpenAI:
        """Get or create OpenAI client"""
        if self.client is None:
            self.client = OpenAI()
        return self.client

    async def generate_tool_from_pattern(
        self,
        pattern: Dict[str, Any],
        tool_name: str,
        tool_purpose: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a Python tool from a detected pattern.

        Args:
            pattern: Pattern data (from auto_evolving_skills)
            tool_name: Name for the generated tool
            tool_purpose: Description of what the tool should do

        Returns:
            Dict with code, description, category, or None on error
        """
        try:
            # Build prompt for LLM
            prompt = self._build_code_generation_prompt(
                pattern=pattern,
                tool_name=tool_name,
                tool_purpose=tool_purpose,
            )

            client = self._get_client()

            # Call LLM to generate code
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert Python code generator specializing in creating safe, deterministic utility functions.

CRITICAL RULES:
1. ONLY generate pure functions with no side effects
2. NO imports outside: math, statistics, datetime, decimal, re, json, typing, collections, itertools, functools
3. NO file I/O, NO network access, NO subprocess calls
4. NO global variables, NO async functions
5. Include comprehensive docstring with Args and Returns
6. Function must be self-contained and testable
7. Use type hints for all parameters and return values
8. Return JSON-serializable data only

Your code will be validated by a security sandbox before execution."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Low temperature for consistent, safe code
                max_tokens=1500,
            )

            code = response.choices[0].message.content

            # Extract code block if wrapped in markdown
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()

            # Validate code is not empty
            if not code or len(code) < 20:
                logger.error("Generated code is too short or empty")
                return None

            logger.info(f"✅ Generated tool code for {tool_name} ({len(code)} chars)")

            return {
                "code": code,
                "tool_name": tool_name,
                "description": tool_purpose,
                "category": pattern.get("category", "general"),
                "pattern": pattern,
            }

        except Exception as e:
            logger.error(f"Error generating tool code: {e}", exc_info=True)
            return None

    async def generate_diagnostic_tool(
        self,
        category: str,
        symptom_maps: Dict[str, List[str]],
        tool_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a diagnostic tool based on symptom → diagnosis mappings.

        Args:
            category: Incident category (plumbing, electrical, etc.)
            symptom_maps: Dict of symptom_key → list of diagnoses
            tool_name: Optional custom tool name

        Returns:
            Dict with code, description, category, or None on error
        """
        if not tool_name:
            tool_name = f"diagnose_{category.lower().replace(' ', '_')}"

        # Build pattern summary
        pattern = {
            "category": category,
            "symptom_maps": symptom_maps,
            "num_symptoms": len(symptom_maps),
        }

        # Create tool purpose
        tool_purpose = f"Diagnose {category} issues based on symptoms and discovery answers. Returns most likely diagnosis with confidence score."

        # Build custom prompt for diagnostic tool
        prompt = f"""Create a Python function called `{tool_name}` that diagnoses {category} issues.

INPUTS: The function should accept a dictionary of symptoms/answers (Dict[str, str])

KNOWN PATTERNS (use these to inform the diagnosis logic):
{self._format_symptom_maps(symptom_maps)}

REQUIREMENTS:
- Function signature: def {tool_name}(symptoms: Dict[str, str]) -> Dict[str, Any]
- Analyze symptoms and return diagnosis with confidence
- Return format: {{"diagnosis": str, "confidence": float, "reasoning": str}}
- Use keyword matching and pattern recognition
- Confidence should be 0.0 to 1.0

Generate ONLY the function code, no other text."""

        try:
            client = self._get_client()

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Python developer creating diagnostic tools. Generate safe, pure functions only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1500,
            )

            code = response.choices[0].message.content

            # Extract code
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()

            if not code or len(code) < 20:
                logger.error("Generated diagnostic code is too short")
                return None

            logger.info(f"✅ Generated diagnostic tool: {tool_name}")

            return {
                "code": code,
                "tool_name": tool_name,
                "description": tool_purpose,
                "category": category,
                "pattern": pattern,
            }

        except Exception as e:
            logger.error(f"Error generating diagnostic tool: {e}", exc_info=True)
            return None

    def _build_code_generation_prompt(
        self,
        pattern: Dict[str, Any],
        tool_name: str,
        tool_purpose: str,
    ) -> str:
        """Build prompt for code generation"""
        prompt = f"""Create a Python function called `{tool_name}`.

PURPOSE: {tool_purpose}

PATTERN DATA:
{self._format_pattern(pattern)}

REQUIREMENTS:
- Function must be pure (no side effects)
- Only use allowed imports: math, statistics, datetime, decimal, re, json, typing, collections, itertools, functools
- Include complete docstring with Args and Returns sections
- Use type hints
- Return JSON-serializable data
- Be deterministic (same input = same output)

Generate ONLY the function code, no other text."""
        return prompt

    def _format_pattern(self, pattern: Dict[str, Any]) -> str:
        """Format pattern data for prompt"""
        lines = []
        for key, value in pattern.items():
            if key in ["created_at", "last_updated_at", "timestamp"]:
                continue  # Skip timestamps
            if isinstance(value, (list, dict)):
                lines.append(f"- {key}: {len(value)} items")
            else:
                lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def _format_symptom_maps(self, symptom_maps: Dict[str, List[str]]) -> str:
        """Format symptom maps for prompt"""
        lines = []
        for symptom, diagnoses in list(symptom_maps.items())[:10]:  # Limit to 10 examples
            # Count diagnosis frequency
            diagnosis_counts = {}
            for d in diagnoses:
                diagnosis_counts[d] = diagnosis_counts.get(d, 0) + 1

            most_common = max(diagnosis_counts.items(), key=lambda x: x[1])[0]
            lines.append(f"- {symptom} → {most_common} ({diagnosis_counts[most_common]} times)")

        return "\n".join(lines)

    async def validate_and_register_tool(
        self,
        tool_code: str,
        tool_name: str,
        description: str,
        category: str = "generated",
    ) -> Dict[str, Any]:
        """
        Validate generated code and register it as a dynamic tool.

        Args:
            tool_code: Python code for the tool
            tool_name: Name of the tool
            description: Tool description
            category: Tool category

        Returns:
            Dict with success (bool), tool_id (str), errors (list)
        """
        try:
            from ..dynamic_tools.tool_runtime import get_dynamic_tool_runtime

            runtime = get_dynamic_tool_runtime()

            # Register tool (this will validate it automatically)
            result = runtime.register_tool(
                tool_name=tool_name,
                code=tool_code,
                description=description,
                category=category,
                created_by="llm_auto_generator",
            )

            if result["success"]:
                logger.info(f"🎉 LLM-generated tool registered successfully: {tool_name}")
                return {
                    "success": True,
                    "tool_id": result.get("tool_id"),
                    "tool_name": tool_name,
                    "errors": [],
                }
            else:
                logger.error(f"❌ Tool validation failed: {result.get('errors')}")
                return {
                    "success": False,
                    "tool_id": None,
                    "tool_name": tool_name,
                    "errors": result.get("errors", []),
                }

        except Exception as e:
            logger.error(f"Error validating/registering tool: {e}", exc_info=True)
            return {
                "success": False,
                "tool_id": None,
                "tool_name": tool_name,
                "errors": [str(e)],
            }


# Singleton instance
_tool_generator: Optional[ToolGenerator] = None


def get_tool_generator() -> ToolGenerator:
    """Get singleton instance of ToolGenerator"""
    global _tool_generator
    if _tool_generator is None:
        _tool_generator = ToolGenerator()
    return _tool_generator
