"""
Auto-Evolving Skills - System learns from repeated patterns and creates new dynamic tools.
Makes the agent grow intelligence over time.
"""
import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter
from datetime import datetime, timedelta

from ..dynamic_tools.tool_runtime import get_dynamic_tool_runtime

logger = logging.getLogger(__name__)


class PatternDetector:
    """
    Detects repeated patterns in user interactions.

    Tracks:
    - Repeated issue types
    - Common question patterns
    - Frequent diagnosis scenarios
    - Recurring solutions
    """

    def __init__(self):
        self.incident_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.threshold_for_skill_creation = 3  # Create skill after 3 similar incidents

    def record_incident(
        self,
        category: str,
        title: str,
        description: str,
        discovery_answers: Dict[str, str],
        diagnosis: Optional[str] = None,
    ):
        """Record incident for pattern detection"""
        incident_record = {
            "category": category,
            "title": title,
            "description": description,
            "discovery_answers": discovery_answers,
            "diagnosis": diagnosis,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Index by category
        self.incident_patterns[category].append(incident_record)

        logger.debug(f"📊 Recorded incident pattern: {category}")

        # Check if pattern threshold reached
        self._check_for_skill_creation(category)

    def _check_for_skill_creation(self, category: str):
        """Check if we should create a new skill for this category"""
        incidents = self.incident_patterns[category]

        if len(incidents) < self.threshold_for_skill_creation:
            return

        # Analyze recent incidents (last 30 days)
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        recent_incidents = [
            inc for inc in incidents
            if datetime.fromisoformat(inc["timestamp"]) > cutoff_date
        ]

        if len(recent_incidents) < self.threshold_for_skill_creation:
            return

        # Check for common patterns
        pattern = self._extract_pattern(recent_incidents)

        if pattern:
            logger.info(f"🔍 Pattern detected in {category}: {pattern}")
            # Trigger skill creation
            self._suggest_skill_creation(category, pattern, recent_incidents)

    def _extract_pattern(self, incidents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extract common pattern from incidents"""
        # Extract keywords from titles
        title_words = []
        for inc in incidents:
            words = inc["title"].lower().split()
            title_words.extend(words)

        # Find most common words (excluding stopwords)
        word_counts = Counter(title_words)
        stopwords = {"the", "a", "an", "is", "in", "on", "at", "to", "and"}
        common_words = [
            word for word, count in word_counts.most_common(5)
            if word not in stopwords and len(word) > 3
        ]

        if not common_words:
            return None

        # Check if diagnosis is similar
        diagnoses = [inc.get("diagnosis") for inc in incidents if inc.get("diagnosis")]

        return {
            "common_keywords": common_words,
            "incident_count": len(incidents),
            "diagnoses": diagnoses,
        }

    def _suggest_skill_creation(
        self,
        category: str,
        pattern: Dict[str, Any],
        incidents: List[Dict[str, Any]],
    ):
        """Suggest creating a new dynamic skill for this pattern"""
        skill_name = f"analyze_{category}_{pattern['common_keywords'][0]}_issue"

        logger.info(f"💡 Suggesting new skill: {skill_name}")

        # Create skill metadata
        skill_suggestion = {
            "skill_name": skill_name,
            "category": category,
            "pattern": pattern,
            "source_incidents": [inc["title"] for inc in incidents],
            "suggested_at": datetime.utcnow().isoformat(),
        }

        # Store suggestion (in production, this would trigger LLM to generate the skill)
        logger.info(f"✨ Skill suggestion created: {skill_suggestion}")

        return skill_suggestion


class SkillEvolutionEngine:
    """
    Generates new dynamic tools based on detected patterns.

    Workflow:
    1. Detect pattern (PatternDetector)
    2. Generate skill code (LLM)
    3. Validate and register (DynamicToolRuntime)
    4. Track usage and effectiveness
    """

    def __init__(self):
        self.pattern_detector = PatternDetector()
        self.runtime = get_dynamic_tool_runtime()
        self.generated_skills: Dict[str, Dict[str, Any]] = {}

    async def record_and_analyze(
        self,
        incident: Dict[str, Any],
    ):
        """Record incident and analyze for skill evolution"""
        category = incident.get("category", "general")
        title = incident.get("title", "")
        description = incident.get("description", "")
        discovery_answers = incident.get("discovery_answers", {})
        diagnosis = incident.get("diagnosis_notes")

        # Record pattern
        self.pattern_detector.record_incident(
            category=category,
            title=title,
            description=description,
            discovery_answers=discovery_answers,
            diagnosis=diagnosis,
        )

        logger.info(f"📈 Recorded incident for evolution tracking: {category}")

    async def generate_skill_from_pattern(
        self,
        pattern: Dict[str, Any],
        category: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a new dynamic skill from detected pattern.

        Args:
            pattern: Detected pattern dict
            category: Category (plumbing, electrical, etc.)

        Returns:
            Generated skill metadata
        """
        skill_name = f"analyze_{category}_{pattern['common_keywords'][0]}"

        logger.info(f"🔧 Generating skill: {skill_name}")

        # Generate skill code (simplified - in production, use LLM)
        skill_code = self._generate_skill_code_template(skill_name, category, pattern)

        # Register skill
        result = self.runtime.register_tool(
            tool_name=skill_name,
            code=skill_code,
            description=f"Analyzes {category} issues related to {', '.join(pattern['common_keywords'])}",
            category=category,
            created_by="auto_evolution",
        )

        if result["success"]:
            self.generated_skills[skill_name] = {
                "pattern": pattern,
                "category": category,
                "created_at": datetime.utcnow().isoformat(),
                "usage_count": 0,
            }

            logger.info(f"✅ Skill generated and registered: {skill_name}")
            return result
        else:
            logger.error(f"❌ Failed to generate skill: {result.get('errors')}")
            return None

    async def record_discovery_pattern(
        self,
        category: str,
        severity: str,
        user_message: str,
        questions_generated: List[str],
    ):
        """
        Record discovery question pattern for skill evolution.

        Args:
            category: Incident category
            severity: Severity level
            user_message: User's initial message
            questions_generated: List of generated discovery questions
        """
        logger.debug(f"📊 Recording discovery pattern: {category}/{severity}")
        # Store pattern for future analysis
        # In production, this would feed into pattern detection
        pass

    async def record_diagnosis_pattern(
        self,
        category: str,
        severity: str,
        discovery_answers: Dict[str, str],
        diagnosis_summary: str,
    ):
        """
        Record diagnosis pattern for skill evolution.

        Args:
            category: Incident category
            severity: Severity level
            discovery_answers: Answers from discovery phase
            diagnosis_summary: Generated diagnosis summary
        """
        logger.debug(f"📊 Recording diagnosis pattern: {category}/{severity}")
        # Store pattern for future analysis
        # In production, this would feed into pattern detection
        pass

    async def suggest_diagnostic_tool(self, category: str) -> Dict[str, Any]:
        """
        Suggest creating a diagnostic tool for a category.

        Args:
            category: Category to analyze

        Returns:
            Dict with should_create (bool), tool_name (str), reason (str)
        """
        # Check if we have enough patterns for this category
        incidents = self.pattern_detector.incident_patterns.get(category, [])

        if len(incidents) >= self.pattern_detector.threshold_for_skill_creation:
            pattern = self.pattern_detector._extract_pattern(incidents)
            if pattern:
                tool_name = f"diagnose_{category}_{pattern['common_keywords'][0]}"
                return {
                    "should_create": True,
                    "tool_name": tool_name,
                    "reason": f"Detected {len(incidents)} similar {category} incidents",
                    "pattern": pattern,
                }

        return {
            "should_create": False,
            "tool_name": None,
            "reason": "Not enough patterns detected yet",
        }

    async def record_tool_execution(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        success: bool,
        user_id: str,
    ):
        """
        Record dynamic tool execution for tracking and improvement.

        Args:
            tool_name: Name of executed tool
            arguments: Arguments passed to tool
            result: Result returned by tool
            success: Whether execution succeeded
            user_id: User who triggered execution
        """
        logger.debug(f"📊 Recording tool execution: {tool_name} (success={success})")

        # Update usage stats if tool is in generated_skills
        if tool_name in self.generated_skills:
            self.generated_skills[tool_name]["usage_count"] += 1
            self.generated_skills[tool_name]["last_used_at"] = datetime.utcnow().isoformat()

            if not success:
                # Track failures for potential improvement
                if "failures" not in self.generated_skills[tool_name]:
                    self.generated_skills[tool_name]["failures"] = []
                self.generated_skills[tool_name]["failures"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "arguments": arguments,
                    "user_id": user_id,
                })

    def _generate_skill_code_template(
        self,
        skill_name: str,
        category: str,
        pattern: Dict[str, Any]
    ) -> str:
        """Generate Python code for skill (template)"""
        keywords = pattern.get("common_keywords", [])

        code = f'''def {skill_name}(description: str, symptoms: str) -> dict:
    """
    Analyzes {category} issues related to {', '.join(keywords)}.

    Auto-generated skill based on {pattern.get("incident_count", 0)} similar incidents.
    """
    import re

    # Keyword detection
    keywords = {keywords}
    found_keywords = [kw for kw in keywords if kw in description.lower()]

    # Severity assessment (simplified)
    severity = "medium"
    if any(word in description.lower() for word in ["emergency", "flooding", "sparks"]):
        severity = "high"
    elif any(word in description.lower() for word in ["minor", "small", "slight"]):
        severity = "low"

    return {{
        "category": "{category}",
        "detected_keywords": found_keywords,
        "severity": severity,
        "confidence": len(found_keywords) / len(keywords) if keywords else 0.5,
        "recommendation": "Professional {category} service recommended",
    }}
'''
        return code


# Singleton
_skill_evolution_engine = None


def get_skill_evolution_engine() -> SkillEvolutionEngine:
    """Get singleton instance"""
    global _skill_evolution_engine
    if _skill_evolution_engine is None:
        _skill_evolution_engine = SkillEvolutionEngine()
    return _skill_evolution_engine


# Alias for backward compatibility
def get_skills_recorder() -> SkillEvolutionEngine:
    """Alias for get_skill_evolution_engine() for backward compatibility"""
    return get_skill_evolution_engine()
