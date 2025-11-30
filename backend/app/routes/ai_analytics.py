"""
AI Support Analytics Routes

Provides endpoints for viewing and analyzing AI Support flow metrics:
- Overall statistics
- Persona-specific performance
- Issue trends and patterns
- User satisfaction metrics
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from ..services.ai_support_analytics import get_analytics_tracker

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/ai/analytics/summary")
async def get_analytics_summary():
    """
    Get overall analytics summary for AI Support sessions.

    Returns:
        - Total sessions, completion rate
        - Persona breakdown
        - Top CTAs, items, reasons, actions
        - Dropoff stages
    """
    try:
        tracker = get_analytics_tracker()
        summary = tracker.get_summary_stats()

        return {
            "success": True,
            "data": summary
        }

    except Exception as e:
        logger.error(f"Error fetching analytics summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch analytics summary")


@router.get("/ai/analytics/persona/{persona}")
async def get_persona_analytics(persona: str):
    """
    Get analytics for a specific persona.

    Args:
        persona: User role (tenant, landlord, contractor, property_manager)

    Returns:
        - Sessions and completion rate for persona
        - Top reasons and actions
        - Persona-specific metrics
    """
    try:
        # Validate persona
        valid_personas = ["tenant", "landlord", "contractor", "property_manager"]
        if persona not in valid_personas:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid persona. Must be one of: {', '.join(valid_personas)}"
            )

        tracker = get_analytics_tracker()
        stats = tracker.get_persona_stats(persona)

        return {
            "success": True,
            "data": stats
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching persona analytics for {persona}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch persona analytics")


@router.get("/ai/analytics/trends")
async def get_issue_trends():
    """
    Get issue trends and patterns across all sessions.

    Returns:
        - Total issues reported
        - Breakdown by reason (with percentages)
        - Common CTA → reason patterns
    """
    try:
        tracker = get_analytics_tracker()
        trends = tracker.get_issue_trends()

        return {
            "success": True,
            "data": trends
        }

    except Exception as e:
        logger.error(f"Error fetching issue trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch issue trends")


@router.get("/ai/analytics/satisfaction")
async def get_satisfaction_metrics():
    """
    Get user satisfaction metrics based on implicit signals.

    Returns:
        - Satisfied, neutral, unsatisfied counts
        - Abandoned sessions
        - Overall satisfaction score (0-100)

    Satisfaction is inferred from resolution actions:
    - High: "done", "issue_resolved"
    - Medium: "create_incident", "submit_bid", "approve_work"
    - Low: "contact_support", "contact_emergency", "escalate"
    - Negative: Session abandonment
    """
    try:
        tracker = get_analytics_tracker()
        satisfaction = tracker.get_satisfaction_metrics()

        return {
            "success": True,
            "data": satisfaction
        }

    except Exception as e:
        logger.error(f"Error fetching satisfaction metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch satisfaction metrics")


@router.get("/ai/analytics/dashboard")
async def get_full_dashboard():
    """
    Get complete analytics dashboard data (all metrics in one call).

    Returns comprehensive analytics including:
    - Summary statistics
    - All persona breakdowns
    - Issue trends
    - Satisfaction metrics
    """
    try:
        tracker = get_analytics_tracker()

        # Gather all metrics
        summary = tracker.get_summary_stats()
        trends = tracker.get_issue_trends()
        satisfaction = tracker.get_satisfaction_metrics()

        # Get stats for each persona
        personas = ["tenant", "landlord", "contractor", "property_manager"]
        persona_stats = {
            persona: tracker.get_persona_stats(persona)
            for persona in personas
        }

        return {
            "success": True,
            "data": {
                "summary": summary,
                "trends": trends,
                "satisfaction": satisfaction,
                "personas": persona_stats
            }
        }

    except Exception as e:
        logger.error(f"Error fetching full dashboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard data")


@router.delete("/ai/analytics/clear")
async def clear_analytics():
    """
    Clear all analytics data (useful for testing/development).

    ⚠️ WARNING: This deletes all collected analytics!
    In production, this should be protected by admin authentication.
    """
    try:
        tracker = get_analytics_tracker()
        tracker.clear_analytics()

        return {
            "success": True,
            "message": "All analytics data cleared"
        }

    except Exception as e:
        logger.error(f"Error clearing analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clear analytics")
