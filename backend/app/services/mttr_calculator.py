"""
MTTR Calculator - Mean Time To Repair Calculation & Analytics

This service calculates and tracks MTTR metrics for incidents:
- Calculate MTTR for resolved incidents
- Store MTTR events in DynamoDB
- Compare against target SLAs
- Generate analytics and reports
- Track performance by category, severity, property

MTTR = Time from incident creation to resolution

Target MTTR by Severity:
- Emergency: 4 hours
- High: 24 hours
- Medium: 72 hours (3 days)
- Low: 168 hours (7 days)
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class MTTRCalculator:
    """Calculates and tracks Mean Time To Repair metrics."""

    # Target MTTR in hours by severity
    TARGET_MTTR = {
        "emergency": 4,
        "high": 24,
        "medium": 72,
        "low": 168
    }

    def __init__(self):
        """Initialize MTTR calculator."""
        logger.info("[mttr] MTTR Calculator initialized")

    def calculate_mttr(
        self,
        incident: Dict[str, Any]
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Calculate MTTR for a resolved incident.

        Args:
            incident: Incident data with created_at and resolved_at

        Returns:
            Tuple of (success, mttr_data, error_message)
        """
        incident_id = incident.get("incident_id")
        created_at = incident.get("created_at")
        resolved_at = incident.get("resolved_at")
        severity = incident.get("severity", "medium")
        category = incident.get("category", "general")

        if not created_at or not resolved_at:
            logger.error(
                "[mttr] Cannot calculate MTTR for incident %s: missing timestamps",
                incident_id
            )
            return False, None, "Missing created_at or resolved_at timestamp"

        try:
            logger.info(
                "[mttr] Calculating MTTR | incident=%s severity=%s category=%s",
                incident_id,
                severity,
                category
            )

            # Parse timestamps
            created = self._parse_timestamp(created_at)
            resolved = self._parse_timestamp(resolved_at)

            # Calculate duration in hours
            duration = (resolved - created).total_seconds() / 3600
            mttr_hours = round(duration, 2)

            # Get target MTTR for this severity
            target_hours = self.TARGET_MTTR.get(severity, 72)

            # Check if target was met
            met_target = mttr_hours <= target_hours

            # Calculate performance metrics
            if met_target:
                performance_percent = 100.0
            else:
                performance_percent = (target_hours / mttr_hours) * 100

            # Create MTTR event record
            mttr_event = {
                "event_id": f"MTTR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{incident_id[:8]}",
                "incident_id": incident_id,
                "category": category,
                "severity": severity,
                "mttr_hours": Decimal(str(mttr_hours)),
                "target_hours": Decimal(str(target_hours)),
                "met_target": met_target,
                "performance_percent": Decimal(str(round(performance_percent, 2))),
                "created_at": created_at,
                "resolved_at": resolved_at,
                "recorded_at": datetime.utcnow().isoformat() + "Z",
                "metadata": {
                    "property_id": incident.get("property_id"),
                    "landlord_id": incident.get("landlord_id"),
                    "job_id": incident.get("job_id")
                }
            }

            logger.info(
                "[mttr] ✅ MTTR calculated | incident=%s | %.2f hours (target: %.2f) | met=%s",
                incident_id,
                mttr_hours,
                target_hours,
                met_target
            )

            return True, mttr_event, None

        except Exception as e:
            logger.error(
                "[mttr] ❌ Failed to calculate MTTR for incident %s: %s",
                incident_id,
                str(e)
            )
            return False, None, str(e)

    def calculate_aggregate_mttr(
        self,
        incidents: list
    ) -> Dict[str, Any]:
        """
        Calculate aggregate MTTR statistics for a set of incidents.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Dictionary with aggregate statistics
        """
        logger.info("[mttr] Calculating aggregate MTTR for %d incidents", len(incidents))

        mttr_values = []
        by_category = {}
        by_severity = {}
        total_met_target = 0

        for incident in incidents:
            success, mttr_data, _ = self.calculate_mttr(incident)

            if not success:
                continue

            mttr_hours = float(mttr_data["mttr_hours"])
            category = mttr_data["category"]
            severity = mttr_data["severity"]
            met_target = mttr_data["met_target"]

            mttr_values.append(mttr_hours)

            # Track by category
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(mttr_hours)

            # Track by severity
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(mttr_hours)

            if met_target:
                total_met_target += 1

        if not mttr_values:
            return {
                "total_incidents": 0,
                "average_mttr_hours": 0,
                "median_mttr_hours": 0,
                "min_mttr_hours": 0,
                "max_mttr_hours": 0,
                "target_met_rate": 0
            }

        # Calculate statistics
        mttr_values.sort()
        avg_mttr = sum(mttr_values) / len(mttr_values)
        median_mttr = mttr_values[len(mttr_values) // 2]
        target_met_rate = (total_met_target / len(mttr_values)) * 100

        # Category averages
        category_averages = {
            cat: sum(vals) / len(vals)
            for cat, vals in by_category.items()
        }

        # Severity averages
        severity_averages = {
            sev: sum(vals) / len(vals)
            for sev, vals in by_severity.items()
        }

        stats = {
            "total_incidents": len(mttr_values),
            "average_mttr_hours": round(avg_mttr, 2),
            "median_mttr_hours": round(median_mttr, 2),
            "min_mttr_hours": round(min(mttr_values), 2),
            "max_mttr_hours": round(max(mttr_values), 2),
            "target_met_rate": round(target_met_rate, 2),
            "by_category": category_averages,
            "by_severity": severity_averages
        }

        logger.info(
            "[mttr] Aggregate MTTR: avg=%.2fh median=%.2fh met_rate=%.1f%%",
            avg_mttr,
            median_mttr,
            target_met_rate
        )

        return stats

    def get_performance_summary(
        self,
        property_id: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get MTTR performance summary with optional filters.

        Args:
            property_id: Optional property filter
            category: Optional category filter
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Performance summary dictionary
        """
        # This would query the mttr_events table
        # For now, return placeholder
        logger.info(
            "[mttr] Getting performance summary | property=%s category=%s",
            property_id,
            category
        )

        return {
            "period": {"start": start_date, "end": end_date},
            "filters": {"property_id": property_id, "category": category},
            "summary": {
                "total_incidents": 0,
                "average_mttr": 0,
                "target_met_rate": 0
            }
        }

    def _parse_timestamp(self, timestamp: str) -> datetime:
        """Parse ISO timestamp string to datetime object."""
        # Handle both with and without 'Z' suffix
        if timestamp.endswith("Z"):
            timestamp = timestamp[:-1]

        try:
            return datetime.fromisoformat(timestamp)
        except ValueError:
            # Try alternate formats
            return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")


# Singleton instance
_mttr_calculator: Optional[MTTRCalculator] = None


def get_mttr_calculator() -> MTTRCalculator:
    """Get or create the singleton MTTRCalculator instance."""
    global _mttr_calculator

    if _mttr_calculator is None:
        _mttr_calculator = MTTRCalculator()

    return _mttr_calculator
