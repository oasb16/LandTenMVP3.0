"""
AI Support Analytics Tracker

Tracks key metrics for the Amazon-style AI Support flow:
- Flow completion rates (sessions reaching resolution vs dropoffs)
- Common issues by persona and category
- User satisfaction (implicit from action selections)
- Stage transition times
- Persona-specific performance metrics
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class AnalyticsEvent:
    """Represents a single analytics event."""

    def __init__(
        self,
        event_type: str,
        channel_id: str,
        user_id: str,
        persona: str,
        **kwargs
    ):
        self.event_type = event_type
        self.channel_id = channel_id
        self.user_id = user_id
        self.persona = persona
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.metadata = kwargs


class AnalyticsTracker:
    """
    Tracks and aggregates analytics for AI Support sessions.

    In production, this would persist to DynamoDB or a time-series database.
    For now, maintains in-memory statistics.
    """

    def __init__(self):
        # Event storage (in-memory)
        self._events: List[AnalyticsEvent] = []

        # Aggregated metrics
        self._session_stages: Dict[str, List[str]] = defaultdict(list)  # channel_id -> [stages]
        self._session_start_times: Dict[str, datetime] = {}  # channel_id -> start_time
        self._stage_entry_times: Dict[str, datetime] = {}  # channel_id -> last_stage_time

        # Counters for quick aggregation
        self._total_sessions = 0
        self._completed_sessions = 0
        self._cta_selections = Counter()  # cta_id -> count
        self._item_selections = Counter()  # item_id -> count
        self._reason_selections = Counter()  # reason -> count
        self._resolution_actions = Counter()  # action_id -> count
        self._persona_sessions = Counter()  # persona -> count
        self._dropoff_stages = Counter()  # stage -> count

    def track_event(
        self,
        event_type: str,
        channel_id: str,
        user_id: str,
        persona: str,
        **kwargs
    ):
        """
        Track an analytics event.

        Event types:
        - session_start: User initialized AI Support
        - stage_transition: User moved between stages
        - cta_selected: User selected a CTA
        - item_selected: User selected an item
        - reason_selected: User selected a reason
        - diagnosis_started: Diagnosis chat began
        - diagnosis_completed: LLM finished diagnosis
        - resolution_shown: Resolution panel displayed
        - action_taken: User clicked a resolution action
        - session_completed: User finished flow
        - session_abandoned: User left without completing
        """
        event = AnalyticsEvent(
            event_type=event_type,
            channel_id=channel_id,
            user_id=user_id,
            persona=persona,
            **kwargs
        )

        self._events.append(event)

        # Update aggregated metrics
        self._update_metrics(event)

        logger.info(f"[Analytics] {event_type} | persona={persona} | channel={channel_id}")

    def _update_metrics(self, event: AnalyticsEvent):
        """Update aggregated metrics based on event."""
        channel_id = event.channel_id
        event_type = event.event_type
        persona = event.persona

        if event_type == "session_start":
            self._total_sessions += 1
            self._persona_sessions[persona] += 1
            self._session_start_times[channel_id] = datetime.now(timezone.utc)
            self._session_stages[channel_id] = ["intro"]

        elif event_type == "stage_transition":
            from_stage = event.metadata.get("from_stage")
            to_stage = event.metadata.get("to_stage")

            if to_stage:
                self._session_stages[channel_id].append(to_stage)

            # Track time in previous stage
            if channel_id in self._stage_entry_times:
                time_in_stage = (datetime.now(timezone.utc) - self._stage_entry_times[channel_id]).total_seconds()
                logger.debug(f"Time in {from_stage}: {time_in_stage:.2f}s")

            self._stage_entry_times[channel_id] = datetime.now(timezone.utc)

        elif event_type == "cta_selected":
            cta_id = event.metadata.get("cta_id")
            if cta_id:
                self._cta_selections[cta_id] += 1

        elif event_type == "item_selected":
            item_id = event.metadata.get("item_id")
            if item_id:
                self._item_selections[item_id] += 1

        elif event_type == "reason_selected":
            reason = event.metadata.get("reason")
            if reason:
                self._reason_selections[reason] += 1

        elif event_type == "action_taken":
            action_id = event.metadata.get("action_id")
            if action_id:
                self._resolution_actions[action_id] += 1

        elif event_type == "session_completed":
            self._completed_sessions += 1

        elif event_type == "session_abandoned":
            # Track which stage user dropped off at
            if channel_id in self._session_stages:
                last_stage = self._session_stages[channel_id][-1]
                self._dropoff_stages[last_stage] += 1

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics for all AI Support sessions.

        Returns aggregated metrics for dashboard display.
        """
        completion_rate = (
            (self._completed_sessions / self._total_sessions * 100)
            if self._total_sessions > 0
            else 0
        )

        return {
            "total_sessions": self._total_sessions,
            "completed_sessions": self._completed_sessions,
            "completion_rate": round(completion_rate, 2),
            "persona_breakdown": dict(self._persona_sessions),
            "top_ctas": self._cta_selections.most_common(5),
            "top_items": self._item_selections.most_common(5),
            "top_reasons": self._reason_selections.most_common(10),
            "top_actions": self._resolution_actions.most_common(10),
            "dropoff_stages": dict(self._dropoff_stages),
            "total_events": len(self._events)
        }

    def get_persona_stats(self, persona: str) -> Dict[str, Any]:
        """Get statistics for a specific persona."""
        # Filter events by persona
        persona_events = [e for e in self._events if e.persona == persona]

        # Count sessions and completions
        sessions = len([e for e in persona_events if e.event_type == "session_start"])
        completions = len([e for e in persona_events if e.event_type == "session_completed"])

        completion_rate = (
            (completions / sessions * 100) if sessions > 0 else 0
        )

        # Most common reasons for this persona
        reasons = Counter()
        for event in persona_events:
            if event.event_type == "reason_selected":
                reason = event.metadata.get("reason")
                if reason:
                    reasons[reason] += 1

        # Most common actions for this persona
        actions = Counter()
        for event in persona_events:
            if event.event_type == "action_taken":
                action_id = event.metadata.get("action_id")
                if action_id:
                    actions[action_id] += 1

        return {
            "persona": persona,
            "total_sessions": sessions,
            "completed_sessions": completions,
            "completion_rate": round(completion_rate, 2),
            "top_reasons": reasons.most_common(5),
            "top_actions": actions.most_common(5),
            "total_events": len(persona_events)
        }

    def get_issue_trends(self) -> Dict[str, Any]:
        """
        Analyze issue trends across all sessions.

        Returns insights about common problems and patterns.
        """
        # Group reasons by frequency
        total_reasons = sum(self._reason_selections.values())

        reason_percentages = {}
        for reason, count in self._reason_selections.most_common():
            percentage = (count / total_reasons * 100) if total_reasons > 0 else 0
            reason_percentages[reason] = {
                "count": count,
                "percentage": round(percentage, 2)
            }

        # Analyze CTA to reason patterns
        cta_reason_pairs = []
        for event in self._events:
            if event.event_type == "reason_selected":
                # Find the CTA from the same channel
                channel_id = event.channel_id
                cta_events = [
                    e for e in self._events
                    if e.channel_id == channel_id and e.event_type == "cta_selected"
                ]
                if cta_events:
                    cta_id = cta_events[-1].metadata.get("cta_id")
                    reason = event.metadata.get("reason")
                    cta_reason_pairs.append((cta_id, reason))

        cta_reason_counts = Counter(cta_reason_pairs)

        return {
            "total_issues_reported": total_reasons,
            "reason_breakdown": reason_percentages,
            "top_issue_patterns": [
                {"cta": cta, "reason": reason, "count": count}
                for (cta, reason), count in cta_reason_counts.most_common(10)
            ]
        }

    def get_satisfaction_metrics(self) -> Dict[str, Any]:
        """
        Calculate implicit satisfaction metrics based on user actions.

        Satisfaction indicators:
        - High: "done", "issue_resolved" actions
        - Medium: Successful submissions ("create_incident", "submit_bid")
        - Low: "contact_support", "request_more_info"
        - Negative: Session abandonment
        """
        satisfied_actions = ["done", "issue_resolved"]
        neutral_actions = ["create_incident", "submit_bid", "approve_work"]
        unsatisfied_actions = ["contact_support", "contact_emergency", "escalate"]

        satisfied_count = sum(
            self._resolution_actions[action]
            for action in satisfied_actions
        )

        neutral_count = sum(
            self._resolution_actions[action]
            for action in neutral_actions
        )

        unsatisfied_count = sum(
            self._resolution_actions[action]
            for action in unsatisfied_actions
        )

        total_actions = sum(self._resolution_actions.values())
        abandoned_sessions = self._total_sessions - self._completed_sessions

        return {
            "satisfied_users": satisfied_count,
            "neutral_users": neutral_count,
            "unsatisfied_users": unsatisfied_count,
            "abandoned_sessions": abandoned_sessions,
            "total_resolved": total_actions,
            "satisfaction_score": self._calculate_satisfaction_score(
                satisfied_count, neutral_count, unsatisfied_count, abandoned_sessions
            )
        }

    def _calculate_satisfaction_score(
        self,
        satisfied: int,
        neutral: int,
        unsatisfied: int,
        abandoned: int
    ) -> float:
        """
        Calculate overall satisfaction score (0-100).

        Weighted: Satisfied = 100, Neutral = 70, Unsatisfied = 30, Abandoned = 0
        """
        total = satisfied + neutral + unsatisfied + abandoned
        if total == 0:
            return 0.0

        weighted_sum = (
            satisfied * 100 +
            neutral * 70 +
            unsatisfied * 30 +
            abandoned * 0
        )

        return round(weighted_sum / total, 2)

    def clear_analytics(self):
        """Clear all analytics data (useful for testing)."""
        self._events.clear()
        self._session_stages.clear()
        self._session_start_times.clear()
        self._stage_entry_times.clear()
        self._total_sessions = 0
        self._completed_sessions = 0
        self._cta_selections.clear()
        self._item_selections.clear()
        self._reason_selections.clear()
        self._resolution_actions.clear()
        self._persona_sessions.clear()
        self._dropoff_stages.clear()
        logger.info("[Analytics] All analytics data cleared")


# Singleton instance
_analytics_tracker: Optional[AnalyticsTracker] = None


def get_analytics_tracker() -> AnalyticsTracker:
    """Get or create analytics tracker instance."""
    global _analytics_tracker
    if _analytics_tracker is None:
        _analytics_tracker = AnalyticsTracker()
    return _analytics_tracker
