"""
Dynamic Discovery Question Generator - Generates category-specific discovery questions on the fly.
No more hardcoded Q1-Q5. Questions are tailored to each incident.
"""
import os
import logging
from typing import List, Dict, Any
from openai import OpenAI

from ..config.settings import settings

logger = logging.getLogger(__name__)


class DynamicDiscoveryGenerator:
    """
    Generates adaptive discovery questions based on:
    - Incident category
    - Incident severity
    - User's initial description
    - Known symptom patterns
    """

    def __init__(self):
        self._openai_client: OpenAI = None
        self.model = "gpt-4o"
        self.temperature = 0.3

    def _get_openai_client(self) -> OpenAI:
        """Lazy OpenAI client initialization"""
        if self._openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
            self._openai_client = OpenAI(api_key=api_key)
        return self._openai_client

    async def generate_questions(
        self,
        category: str,
        severity: str,
        user_message: str,
        max_questions: int = 5,
    ) -> List[str]:
        """
        Generate adaptive discovery questions.

        Args:
            category: Incident category (plumbing, electrical, etc.)
            severity: Severity level (low, medium, high, emergency)
            user_message: User's initial description
            max_questions: Number of questions to generate (default 5)

        Returns:
            List of discovery questions
        """
        logger.info(f"🔍 Generating dynamic discovery questions for {category}/{severity}")

        client = self._get_openai_client()

        # Build category-specific guidance
        category_context = self._get_category_context(category)

        system_prompt = f"""You are a property maintenance expert specializing in {category} issues.

Generate {max_questions} specific, actionable discovery questions to diagnose the issue described by the user.

Guidelines:
1. Ask about observable details (what they see, hear, smell)
2. Progress from basic to detailed (location → symptoms → severity → impact)
3. Be specific to {category} category
4. Keep questions short and clear (one question at a time)
5. Don't ask for information already provided
6. Don't ask the user to perform technical diagnostics

Category-specific context:
{category_context}

Severity level: {severity}

Output ONLY the questions, one per line, numbered 1-{max_questions}.
No explanations, no preamble, just the questions.
"""

        user_prompt = f"""User reported issue: "{user_message}"

Generate {max_questions} discovery questions to diagnose this {category} issue.
"""

        try:
            response = client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            response_text = response.choices[0].message.content

            # Parse questions from response
            questions = self._parse_questions(response_text, max_questions)

            logger.info(f"✅ Generated {len(questions)} discovery questions")
            return questions

        except Exception as e:
            logger.error(f"❌ Failed to generate questions: {e}", exc_info=True)
            # Fallback to generic questions
            return self._get_fallback_questions(category, max_questions)

    def _get_category_context(self, category: str) -> str:
        """Get category-specific diagnostic guidance"""
        contexts = {
            "plumbing": """
Focus on:
- Location and type of leak (drip vs stream vs flooding)
- Water pressure issues
- Drainage problems
- Water color/smell
- Sounds (gurgling, hammering)
- Recent changes or events
""",
            "electrical": """
Focus on:
- Specific outlets/fixtures affected
- Breaker status (tripped or not)
- Burning smell or sparks
- Flickering vs total failure
- Recent usage or events
- Safety hazards
""",
            "hvac": """
Focus on:
- Temperature issues (too hot/cold/not changing)
- Airflow strength
- Strange sounds or smells
- Thermostat display
- When issue started
- Indoor vs outdoor unit
""",
            "appliance": """
Focus on:
- Appliance age and model
- Specific symptoms (noise, not starting, leaking)
- Error codes displayed
- Recent changes in performance
- Impact on daily routine
- Safety concerns
""",
            "structural": """
Focus on:
- Location and extent of damage
- When damage was noticed
- Progressive or sudden
- Water involvement
- Safety risks (falling hazards, access issues)
- Weather or event triggers
""",
            "mechanical": """
Focus on:
- What's not moving properly
- Sounds (grinding, clicking, squealing)
- Stuck vs loose vs misaligned
- Recent weather or usage changes
- Safety and security implications
""",
        }

        return contexts.get(category, "Focus on detailed symptom description and impact.")

    def _parse_questions(self, response_text: str, max_questions: int) -> List[str]:
        """Parse questions from LLM response"""
        lines = response_text.strip().split('\n')
        questions = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Remove number prefix if present (e.g., "1. " or "1) ")
            import re
            cleaned = re.sub(r'^\d+[\.\)]\s*', '', line)

            if cleaned and len(cleaned) > 10:  # Sanity check
                questions.append(cleaned)

            if len(questions) >= max_questions:
                break

        # If parsing failed, split by newline
        if not questions:
            questions = [l.strip() for l in lines if len(l.strip()) > 10][:max_questions]

        return questions

    def _get_fallback_questions(self, category: str, max_questions: int) -> List[str]:
        """Fallback questions if generation fails"""
        fallback_sets = {
            "plumbing": [
                "Where exactly is the leak located?",
                "Is it actively dripping or flowing water right now?",
                "When did you first notice this issue?",
                "Is there any water damage visible?",
                "Is the water clear or discolored?",
            ],
            "electrical": [
                "Which outlets or fixtures are affected?",
                "Did you check if the circuit breaker tripped?",
                "Is there any burning smell or visible sparks?",
                "When did this issue start?",
                "Does the problem happen constantly or intermittently?",
            ],
            "hvac": [
                "Is the system making any unusual noises?",
                "What temperature is it compared to what it should be?",
                "Is any air coming out of the vents?",
                "When did you first notice the problem?",
                "Does the thermostat display show any errors?",
            ],
        }

        questions = fallback_sets.get(category, [
            "Can you describe the issue in more detail?",
            "Where is this problem located?",
            "When did it start?",
            "How severe is it right now?",
            "Is there any safety concern?",
        ])

        return questions[:max_questions]


# Singleton instance
_dynamic_discovery_generator = None


def get_dynamic_discovery_generator() -> DynamicDiscoveryGenerator:
    """Get singleton instance"""
    global _dynamic_discovery_generator
    if _dynamic_discovery_generator is None:
        _dynamic_discovery_generator = DynamicDiscoveryGenerator()
    return _dynamic_discovery_generator
