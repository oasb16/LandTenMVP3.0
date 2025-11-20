"""
Discovery Manager - Orchestrates Information Gathering Flows

This service manages the discovery process for incidents:
- Load category-specific discovery questions
- Track progress through discovery flow
- Validate user responses
- Store answers in context
- Determine when discovery is complete
- Generate discovery progress cards
- Transition to job creation when ready

Features:
- Category-specific question banks
- Progress tracking
- Answer validation
- Dynamic question selection based on previous answers
- Photo upload prompts
- DIY triage logic
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from .context_manager import get_context_manager
from .card_builder import CardBuilder

logger = logging.getLogger(__name__)


class DiscoveryManager:
    """Manages discovery flow orchestration."""

    def __init__(self):
        """Initialize discovery manager with question banks."""
        self.context_manager = get_context_manager()
        self.card_builder = CardBuilder()
        self.question_banks = self._load_question_banks()

    def _load_question_banks(self) -> Dict[str, List[str]]:
        """
        Load discovery question banks for each category.

        In production, this would load from JSON config files.
        For MVP, using hardcoded questions.
        """
        return {
            "plumbing": [
                "Is water currently leaking or flowing?",
                "Where exactly is the issue located (kitchen, bathroom, etc.)?",
                "Have you tried turning off the water supply valve?",
                "Is there visible water damage to walls, ceiling, or floor?",
                "When did you first notice the problem?",
                "Can you describe the severity (small drip vs. large leak)?"
            ],
            "electrical": [
                "Is the electrical issue causing a safety hazard (sparks, burning smell)?",
                "Which room or area is affected?",
                "Have you checked the circuit breaker panel?",
                "Are any outlets or switches warm to the touch?",
                "When did the problem start?",
                "Is power completely out or just flickering?"
            ],
            "hvac": [
                "Is your heating or cooling system not working at all, or working poorly?",
                "What temperature is it currently inside?",
                "Have you checked/replaced the air filter recently?",
                "Do you hear any unusual sounds from the unit?",
                "When was your last HVAC maintenance?",
                "Is the thermostat set correctly?"
            ],
            "appliance": [
                "Which appliance is having issues?",
                "What exactly is the problem (not starting, making noise, leaking)?",
                "How old is the appliance?",
                "Is it under warranty?",
                "Have you tried unplugging and restarting it?",
                "Are there any error codes displayed?"
            ],
            "general": [
                "Can you describe the issue in detail?",
                "Where in the property is the problem located?",
                "Is this creating any safety hazards?",
                "How urgent is this repair (immediate, this week, routine)?",
                "Do you have photos of the issue?",
                "When did you first notice the problem?"
            ]
        }

    def start_discovery(
        self,
        user_id: str,
        channel_id: str,
        incident_id: str,
        category: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Start discovery flow for an incident.

        Args:
            user_id: User ID
            channel_id: Stream channel ID
            incident_id: Incident ID
            category: Incident category

        Returns:
            Tuple of (success, first_question, error_message)
        """
        logger.info(
            "[discovery] Starting discovery | user=%s incident=%s category=%s",
            user_id,
            incident_id,
            category
        )

        try:
            # Initialize discovery state in context
            discovery_state = {
                "active": True,
                "incident_id": incident_id,
                "category": category,
                "question_index": 0,
                "total_questions": len(self.question_banks.get(category, self.question_banks["general"])),
                "answers": {},
                "started_at": None,
                "completed_at": None
            }

            # Update context
            success = self.context_manager.update_context(
                user_id,
                channel_id,
                {
                    "flow_state": {
                        "stage": "discovery",
                        "discovery": discovery_state,
                        "incident_id": incident_id
                    }
                }
            )

            if not success:
                return False, None, "Failed to update context"

            # Get first question
            first_question = self.get_next_question(user_id, channel_id, category)

            logger.info(
                "[discovery] ✅ Discovery started | question_index=0 | total=%d",
                discovery_state["total_questions"]
            )

            return True, first_question, None

        except Exception as e:
            logger.error("[discovery] ❌ Failed to start discovery: %s", str(e))
            return False, None, str(e)

    def get_next_question(
        self,
        user_id: str,
        channel_id: str,
        category: str
    ) -> Optional[str]:
        """
        Get the next discovery question.

        Args:
            user_id: User ID
            channel_id: Channel ID
            category: Incident category

        Returns:
            Next question text or None if discovery complete
        """
        context = self.context_manager.get_context(user_id, channel_id)
        if not context:
            logger.error("[discovery] No context found for user %s", user_id)
            return None

        flow_state = context.get("flow_state", {})
        discovery_state = flow_state.get("discovery", {})

        question_index = discovery_state.get("question_index", 0)
        questions = self.question_banks.get(category, self.question_banks["general"])

        if question_index >= len(questions):
            logger.info("[discovery] All questions answered | user=%s", user_id)
            return None

        question = questions[question_index]

        logger.info(
            "[discovery] Next question %d/%d: %s",
            question_index + 1,
            len(questions),
            question[:50]
        )

        return question

    def record_answer(
        self,
        user_id: str,
        channel_id: str,
        answer: str
    ) -> Tuple[bool, bool, Optional[str]]:
        """
        Record a discovery answer and advance to next question.

        Args:
            user_id: User ID
            channel_id: Channel ID
            answer: User's answer

        Returns:
            Tuple of (success, is_complete, error_message)
        """
        logger.info(
            "[discovery] Recording answer | user=%s | answer=%s",
            user_id,
            answer[:100]
        )

        try:
            context = self.context_manager.get_context(user_id, channel_id)
            if not context:
                return False, False, "No context found"

            flow_state = context.get("flow_state", {})
            discovery_state = flow_state.get("discovery", {})

            question_index = discovery_state.get("question_index", 0)
            answers = discovery_state.get("answers", {})

            # Store answer
            answers[f"q{question_index}"] = answer

            # Advance to next question
            next_index = question_index + 1
            total_questions = discovery_state.get("total_questions", 4)

            is_complete = next_index >= total_questions

            # Update discovery state
            discovery_state["question_index"] = next_index
            discovery_state["answers"] = answers

            if is_complete:
                discovery_state["active"] = False
                discovery_state["completed_at"] = None
                flow_state["stage"] = "job-ready"

            # Update context
            success = self.context_manager.update_context(
                user_id,
                channel_id,
                {"flow_state": flow_state}
            )

            if not success:
                return False, False, "Failed to update context"

            logger.info(
                "[discovery] ✅ Answer recorded | progress=%d/%d | complete=%s",
                next_index,
                total_questions,
                is_complete
            )

            return True, is_complete, None

        except Exception as e:
            logger.error("[discovery] ❌ Failed to record answer: %s", str(e))
            return False, False, str(e)

    def get_discovery_progress(
        self,
        user_id: str,
        channel_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get current discovery progress.

        Args:
            user_id: User ID
            channel_id: Channel ID

        Returns:
            Discovery progress data or None
        """
        context = self.context_manager.get_context(user_id, channel_id)
        if not context:
            return None

        flow_state = context.get("flow_state", {})
        discovery_state = flow_state.get("discovery", {})

        question_index = discovery_state.get("question_index", 0)
        total_questions = discovery_state.get("total_questions", 4)
        answers = discovery_state.get("answers", {})

        progress_percent = (question_index / total_questions * 100) if total_questions > 0 else 0

        return {
            "active": discovery_state.get("active", False),
            "question_index": question_index,
            "total_questions": total_questions,
            "progress_percent": progress_percent,
            "answers": answers,
            "is_complete": question_index >= total_questions
        }

    def generate_discovery_card(
        self,
        user_id: str,
        channel_id: str,
        incident_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a discovery progress card.

        Args:
            user_id: User ID
            channel_id: Channel ID
            incident_id: Incident ID

        Returns:
            Card data or None
        """
        progress = self.get_discovery_progress(user_id, channel_id)
        if not progress:
            return None

        card = self.card_builder.discovery_card(
            incident_id=incident_id,
            questions_asked=progress["question_index"],
            questions_total=progress["total_questions"],
            current_question=None,
            answers=progress["answers"],
            images_uploaded=0  # TODO: track photo uploads
        )

        return card

    def validate_answer(self, question: str, answer: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a discovery answer.

        Args:
            question: The question being answered
            answer: User's answer

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic validation
        if not answer or len(answer.strip()) == 0:
            return False, "Please provide an answer"

        if len(answer) > 1000:
            return False, "Answer too long (max 1000 characters)"

        # Question-specific validation could go here
        # For example, Yes/No questions should only accept yes/no

        return True, None


# Singleton instance
_discovery_manager: Optional[DiscoveryManager] = None


def get_discovery_manager() -> DiscoveryManager:
    """Get or create the singleton DiscoveryManager instance."""
    global _discovery_manager

    if _discovery_manager is None:
        _discovery_manager = DiscoveryManager()

    return _discovery_manager
