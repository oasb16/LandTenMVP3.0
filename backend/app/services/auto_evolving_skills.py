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
