"""
Dynamic Incident Cards - LLM generates visually rich incident cards as structured JSON.
Cards include collapsible sections, progress indicators, and color-coded severity.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DynamicIncidentCardGenerator:
    """
    Generates rich, structured incident cards from incident data.

    Card features:
    - Collapsible description sections
    - Expandable Q&A blocks
    - Inline diagnosis blocks
    - Color-coded severity indicators
    - Progress bars for discovery/workflow stages
    - Timeline visualization
    """

    def generate_incident_card(
        self,
        incident: Dict[str, Any],
        include_discovery: bool = False,
        include_diagnosis: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a rich incident card from incident data.

        Args:
            incident: Incident data dict
            include_discovery: Include discovery Q&A section
            include_diagnosis: Include diagnosis section

        Returns:
            Structured card JSON
        """
        incident_id = incident.get("incident_id", "unknown")
        title = incident.get("title", "Untitled Incident")
        category = incident.get("category", "general")
        severity = incident.get("severity", "medium")
        status = incident.get("status", "detected")
        description = incident.get("description", "")

        # Build card structure
        card = {
            "type": "incident_card",
            "incident_id": incident_id,
            "header": self._build_header(title, incident_id, severity, status),
            "sections": [],
            "actions": self._build_actions(status, incident_id),
            "metadata": {
                "category": category,
                "created_at": incident.get("created_at"),
                "updated_at": incident.get("updated_at"),
            },
        }

        # Section 1: Description (collapsible)
        if description:
            card["sections"].append({
                "type": "collapsible",
                "title": "📄 Issue Description",
                "collapsed": len(description) > 200,
                "content": description,
            })

        # Section 2: Discovery Q&A (if included)
        if include_discovery:
            discovery_section = self._build_discovery_section(incident)
            if discovery_section:
                card["sections"].append(discovery_section)

        # Section 3: Diagnosis (if included)
        if include_diagnosis:
            diagnosis_section = self._build_diagnosis_section(incident)
            if diagnosis_section:
                card["sections"].append(diagnosis_section)

        # Section 4: Progress/Timeline
        timeline_section = self._build_timeline_section(incident)
        if timeline_section:
            card["sections"].append(timeline_section)

        return card

    def _build_header(
        self,
        title: str,
        incident_id: str,
        severity: str,
        status: str,
    ) -> Dict[str, Any]:
        """Build card header with severity color coding"""
        severity_colors = {
            "low": "green",
            "medium": "yellow",
            "high": "orange",
            "emergency": "red",
        }

        status_emojis = {
            "detected": "🔍",
            "discovery": "❓",
            "discovery_complete": "✅",
            "diagnosing": "🔬",
            "work_order": "🔧",
            "scheduling": "📅",
            "in_progress": "⚙️",
            "completed": "✅",
        }

        return {
            "title": title,
            "incident_id": incident_id,
            "severity": {
                "level": severity,
                "color": severity_colors.get(severity, "gray"),
                "label": severity.upper(),
            },
            "status": {
                "stage": status,
                "emoji": status_emojis.get(status, "📋"),
                "label": status.replace("_", " ").title(),
            },
        }

    def _build_discovery_section(self, incident: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build expandable discovery Q&A section"""
        discovery_answers = incident.get("discovery_answers", {})

        if not discovery_answers:
            return None

        # Convert discovery answers to Q&A pairs
        qa_pairs = []
        for key, answer in discovery_answers.items():
            question_num = key.replace("q", "")
            qa_pairs.append({
                "question": f"Q{int(question_num) + 1}",  # Q1, Q2, etc.
                "answer": answer,
            })

        return {
            "type": "expandable",
            "title": "❓ Discovery Questions",
            "expanded": False,
            "content": {
                "type": "qa_list",
                "items": qa_pairs,
            },
        }

    def _build_diagnosis_section(self, incident: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build diagnosis result section with color-coded severity"""
        diagnosis_notes = incident.get("diagnosis_notes")

        if not diagnosis_notes:
            return None

        return {
            "type": "highlighted",
            "title": "🔬 Diagnosis",
            "highlight_color": "blue",
            "content": diagnosis_notes,
        }

    def _build_timeline_section(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """Build timeline/progress section"""
        status = incident.get("status", "detected")

        # Define workflow stages
        stages = [
            {"key": "detected", "label": "Reported"},
            {"key": "discovery", "label": "Gathering Info"},
            {"key": "diagnosing", "label": "Diagnosing"},
            {"key": "work_order", "label": "Work Order"},
            {"key": "in_progress", "label": "In Progress"},
            {"key": "completed", "label": "Completed"},
        ]

        # Calculate progress
        status_index = next((i for i, s in enumerate(stages) if s["key"] == status), 0)
        progress_percentage = int((status_index / (len(stages) - 1)) * 100)

        # Mark completed stages
        for i, stage in enumerate(stages):
            stage["completed"] = i <= status_index
            stage["current"] = i == status_index

        return {
            "type": "progress",
            "title": "📊 Status",
            "progress": progress_percentage,
            "stages": stages,
        }

    def _build_actions(self, status: str, incident_id: str) -> List[Dict[str, Any]]:
        """Build available actions based on status"""
        actions = []

        # Status-specific actions
        if status == "diagnosing":
            actions.append({
                "type": "button",
                "label": "Create Work Order",
                "action": "create_work_order",
                "incident_id": incident_id,
            })

        if status in ["work_order", "scheduling"]:
            actions.append({
                "type": "button",
                "label": "View Work Order",
                "action": "view_work_order",
                "incident_id": incident_id,
            })

        # Always available
        actions.append({
            "type": "link",
            "label": "View Full Details",
            "action": "view_incident",
            "incident_id": incident_id,
        })

        return actions


# Singleton
_dynamic_incident_card_generator = None


def get_dynamic_incident_card_generator() -> DynamicIncidentCardGenerator:
    """Get singleton instance"""
    global _dynamic_incident_card_generator
    if _dynamic_incident_card_generator is None:
        _dynamic_incident_card_generator = DynamicIncidentCardGenerator()
    return _dynamic_incident_card_generator


# Alias for backward compatibility
def get_card_generator() -> DynamicIncidentCardGenerator:
    """Alias for get_dynamic_incident_card_generator() for backward compatibility"""
    return get_dynamic_incident_card_generator()
