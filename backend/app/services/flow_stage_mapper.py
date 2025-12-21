"""
Flow Stage Mapper - Normalizes old stage strings to new FlowStage enum values

This module provides backward compatibility between the old string-based stage system
and the new FlowStage enum system. It prevents crashes when old stage names are
encountered in the context.

Example old stage names that need normalization:
- "general.chat" → FlowStage.IDLE
- "incident.active" → FlowStage.DISCOVERY
- "job.request" → FlowStage.JOB
"""

import logging
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class FlowStage(str, Enum):
    """Flow stages - must match intent_classifier.FlowStage"""
    IDLE = "idle"
    DISCOVERY = "discovery"
    JOB_READY = "job-ready"
    APPROVAL_PENDING = "approval_pending"
    JOB = "job"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAID = "paid"


class FlowStageMapper:
    """
    Maps old string-based stage names to new FlowStage enum values.

    Provides backward compatibility for existing contexts that use old stage names.
    """

    # Complete mapping from old stage names to new FlowStage enum
    STAGE_MAP = {
        # Old V1 stage names
        "general.chat": FlowStage.IDLE,
        "idle": FlowStage.IDLE,

        # Incident stages
        "incident.active": FlowStage.DISCOVERY,
        "incident.report": FlowStage.DISCOVERY,
        "incident.followup": FlowStage.DISCOVERY,

        # Discovery stages
        "discovery": FlowStage.DISCOVERY,
        "discovery.response": FlowStage.DISCOVERY,
        "discovery.continue": FlowStage.DISCOVERY,

        # Job-ready stage
        "job-ready": FlowStage.JOB_READY,
        "job_ready": FlowStage.JOB_READY,

        # Job stages
        "job": FlowStage.JOB,
        "job.request": FlowStage.JOB,
        "job.inquiry": FlowStage.JOB,
        "job.status": FlowStage.JOB,

        # Approval stages
        "approval": FlowStage.APPROVAL_PENDING,
        "approval_pending": FlowStage.APPROVAL_PENDING,
        "approval.request": FlowStage.APPROVAL_PENDING,
        "approval.decision": FlowStage.APPROVAL_PENDING,

        # In progress
        "in_progress": FlowStage.IN_PROGRESS,
        "in-progress": FlowStage.IN_PROGRESS,

        # Completion stages
        "completion": FlowStage.COMPLETED,
        "completed": FlowStage.COMPLETED,
        "completion.confirmation": FlowStage.COMPLETED,

        # Paid
        "paid": FlowStage.PAID,

        # Bids (map to JOB for now)
        "bids": FlowStage.JOB,
        "bids.request": FlowStage.JOB,
        "bids.compare": FlowStage.JOB,
    }

    @classmethod
    def normalize(cls, stage_str: Optional[str]) -> FlowStage:
        """
        Normalize a stage string to a FlowStage enum value.

        Args:
            stage_str: Stage string from old system (e.g., "general.chat", "incident.active")

        Returns:
            FlowStage enum value

        Examples:
            >>> FlowStageMapper.normalize("general.chat")
            FlowStage.IDLE

            >>> FlowStageMapper.normalize("incident.active")
            FlowStage.DISCOVERY

            >>> FlowStageMapper.normalize("job.request")
            FlowStage.JOB
        """
        # Handle None or empty string
        if not stage_str:
            logger.debug("[flow-stage-mapper] Empty stage string, defaulting to IDLE")
            return FlowStage.IDLE

        # Check if already a FlowStage enum
        if isinstance(stage_str, FlowStage):
            return stage_str

        # Convert to lowercase for case-insensitive matching
        stage_lower = stage_str.lower().strip()

        # Try direct mapping first
        if stage_lower in cls.STAGE_MAP:
            normalized = cls.STAGE_MAP[stage_lower]
            # Only log at INFO if the stage is actually changing (normalization occurred)
            if stage_lower != normalized.value:
                logger.info("[flow-stage-mapper] Normalized '%s' → %s", stage_str, normalized.value)
            else:
                logger.debug("[flow-stage-mapper] Stage '%s' already normalized", stage_str)
            return normalized

        # Try to match as FlowStage value directly
        try:
            # Check if it's already a valid FlowStage value
            for stage in FlowStage:
                if stage.value == stage_lower:
                    logger.debug("[flow-stage-mapper] '%s' is already a valid FlowStage", stage_str)
                    return stage
        except Exception:
            pass

        # Fallback to IDLE for unknown stages
        logger.warning(
            "[flow-stage-mapper] Unknown stage '%s', defaulting to IDLE. "
            "Consider adding to STAGE_MAP if this is a valid stage.",
            stage_str
        )
        return FlowStage.IDLE

    @classmethod
    def normalize_to_string(cls, stage_str: Optional[str]) -> str:
        """
        Normalize a stage string and return its string value.

        Args:
            stage_str: Stage string from old system

        Returns:
            Normalized stage string (FlowStage.value)
        """
        normalized_enum = cls.normalize(stage_str)
        return normalized_enum.value

    @classmethod
    def is_valid_stage(cls, stage_str: str) -> bool:
        """
        Check if a stage string is valid (either in map or is a FlowStage value).

        Args:
            stage_str: Stage string to check

        Returns:
            True if valid, False otherwise
        """
        if not stage_str:
            return False

        stage_lower = stage_str.lower().strip()

        # Check if in mapping
        if stage_lower in cls.STAGE_MAP:
            return True

        # Check if it's a valid FlowStage value
        for stage in FlowStage:
            if stage.value == stage_lower:
                return True

        return False


# Convenience function for quick access
def normalize_stage(stage_str: Optional[str]) -> FlowStage:
    """Convenience function to normalize a stage string."""
    return FlowStageMapper.normalize(stage_str)


__all__ = ["FlowStage", "FlowStageMapper", "normalize_stage"]
