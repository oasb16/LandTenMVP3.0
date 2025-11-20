"""
Bid Generator Service - Generates Contractor Bids for Jobs

This service generates mock contractor bids based on job category, severity, and location.
In production, this would integrate with real contractor databases and pricing APIs.

Features:
- Generate 3-5 contractor bids per job
- Price estimation based on category and severity
- ETA calculation based on urgency
- Contractor rating generation (for MVP, uses mock data)
- Distance calculation (mock for MVP)
"""

import random
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


class BidGenerator:
    """Generates contractor bids for maintenance jobs."""

    def __init__(self):
        """Initialize the bid generator with contractor database."""
        self.contractors_db = self._load_contractor_database()

    def _load_contractor_database(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load mock contractor database organized by category.

        In production, this would query a real contractor database.
        """
        return {
            "plumbing": [
                {
                    "contractor_id": "contractor-plumb-001",
                    "name": "RapidFix Plumbing",
                    "rating": 4.8,
                    "reviews_count": 247,
                    "base_rate": 150,
                    "response_time_hours": 2,
                    "specialties": ["emergency", "leak repair", "pipe replacement"],
                    "service_area_miles": 15
                },
                {
                    "contractor_id": "contractor-plumb-002",
                    "name": "Prime Contractors",
                    "rating": 4.6,
                    "reviews_count": 189,
                    "base_rate": 175,
                    "response_time_hours": 4,
                    "specialties": ["general plumbing", "fixture installation"],
                    "service_area_miles": 20
                },
                {
                    "contractor_id": "contractor-plumb-003",
                    "name": "SafeHome Plumbing Pros",
                    "rating": 4.9,
                    "reviews_count": 312,
                    "base_rate": 200,
                    "response_time_hours": 1,
                    "specialties": ["emergency", "water damage", "leak repair"],
                    "service_area_miles": 10
                },
                {
                    "contractor_id": "contractor-plumb-004",
                    "name": "Budget Plumbing Services",
                    "rating": 4.3,
                    "reviews_count": 95,
                    "base_rate": 125,
                    "response_time_hours": 8,
                    "specialties": ["general plumbing", "routine maintenance"],
                    "service_area_miles": 25
                },
                {
                    "contractor_id": "contractor-plumb-005",
                    "name": "24/7 Plumbing Solutions",
                    "rating": 4.7,
                    "reviews_count": 201,
                    "base_rate": 165,
                    "response_time_hours": 3,
                    "specialties": ["emergency", "24/7 service"],
                    "service_area_miles": 12
                }
            ],
            "electrical": [
                {
                    "contractor_id": "contractor-elec-001",
                    "name": "Bright Spark Electric",
                    "rating": 4.9,
                    "reviews_count": 278,
                    "base_rate": 180,
                    "response_time_hours": 2,
                    "specialties": ["emergency", "wiring", "panel upgrades"],
                    "service_area_miles": 15
                },
                {
                    "contractor_id": "contractor-elec-002",
                    "name": "PowerUp Electrical",
                    "rating": 4.5,
                    "reviews_count": 142,
                    "base_rate": 150,
                    "response_time_hours": 6,
                    "specialties": ["general electrical", "outlets", "switches"],
                    "service_area_miles": 20
                },
                {
                    "contractor_id": "contractor-elec-003",
                    "name": "Master Electricians",
                    "rating": 4.8,
                    "reviews_count": 324,
                    "base_rate": 220,
                    "response_time_hours": 1,
                    "specialties": ["emergency", "commercial", "residential"],
                    "service_area_miles": 10
                }
            ],
            "hvac": [
                {
                    "contractor_id": "contractor-hvac-001",
                    "name": "CoolBreeze HVAC",
                    "rating": 4.7,
                    "reviews_count": 195,
                    "base_rate": 200,
                    "response_time_hours": 4,
                    "specialties": ["AC repair", "heating", "maintenance"],
                    "service_area_miles": 18
                },
                {
                    "contractor_id": "contractor-hvac-002",
                    "name": "Climate Control Experts",
                    "rating": 4.9,
                    "reviews_count": 267,
                    "base_rate": 250,
                    "response_time_hours": 2,
                    "specialties": ["emergency", "installation", "repair"],
                    "service_area_miles": 12
                },
                {
                    "contractor_id": "contractor-hvac-003",
                    "name": "Affordable Heating & Cooling",
                    "rating": 4.4,
                    "reviews_count": 118,
                    "base_rate": 175,
                    "response_time_hours": 8,
                    "specialties": ["routine service", "filter replacement"],
                    "service_area_miles": 25
                }
            ],
            "appliance": [
                {
                    "contractor_id": "contractor-appl-001",
                    "name": "Appliance Rescue",
                    "rating": 4.6,
                    "reviews_count": 156,
                    "base_rate": 140,
                    "response_time_hours": 4,
                    "specialties": ["refrigerator", "dishwasher", "washer/dryer"],
                    "service_area_miles": 20
                },
                {
                    "contractor_id": "contractor-appl-002",
                    "name": "Fix-It-Fast Appliance",
                    "rating": 4.8,
                    "reviews_count": 223,
                    "base_rate": 160,
                    "response_time_hours": 2,
                    "specialties": ["emergency", "all appliances"],
                    "service_area_miles": 15
                }
            ],
            "general": [
                {
                    "contractor_id": "contractor-gen-001",
                    "name": "HandyPro Services",
                    "rating": 4.5,
                    "reviews_count": 189,
                    "base_rate": 100,
                    "response_time_hours": 6,
                    "specialties": ["general repairs", "maintenance"],
                    "service_area_miles": 20
                },
                {
                    "contractor_id": "contractor-gen-002",
                    "name": "Property Care Solutions",
                    "rating": 4.7,
                    "reviews_count": 234,
                    "base_rate": 120,
                    "response_time_hours": 4,
                    "specialties": ["property maintenance", "repairs"],
                    "service_area_miles": 18
                }
            ]
        }

    def generate_bids(
        self,
        job_id: str,
        category: str,
        severity: str,
        urgency: str,
        description: str,
        property_location: Optional[Dict[str, float]] = None,
        num_bids: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate contractor bids for a job.

        Args:
            job_id: Unique job identifier
            category: Job category (plumbing, electrical, hvac, etc.)
            severity: Severity level (low, medium, high, emergency)
            urgency: Urgency level (routine, urgent, immediate)
            description: Job description for context
            property_location: Optional lat/lng for distance calculation
            num_bids: Number of bids to generate (default 3, max 5)

        Returns:
            List of bid dictionaries with contractor info and quotes
        """
        logger.info(
            "[bid-generator] Generating %d bids for job %s | category=%s severity=%s",
            num_bids,
            job_id,
            category,
            severity
        )

        # Get contractors for this category
        contractors = self.contractors_db.get(category.lower(), self.contractors_db["general"])

        # Select best matching contractors
        selected_contractors = self._select_contractors(
            contractors,
            severity,
            urgency,
            num_bids
        )

        # Generate bids
        bids = []
        for idx, contractor in enumerate(selected_contractors):
            bid = self._generate_bid(
                job_id,
                contractor,
                category,
                severity,
                urgency,
                description,
                property_location,
                idx
            )
            bids.append(bid)

        # Sort by quote (lowest first)
        bids.sort(key=lambda x: x["quote"])

        logger.info(
            "[bid-generator] ✅ Generated %d bids for job %s | quotes: %s",
            len(bids),
            job_id,
            [f"${b['quote']}" for b in bids]
        )

        return bids

    def _select_contractors(
        self,
        contractors: List[Dict[str, Any]],
        severity: str,
        urgency: str,
        num_bids: int
    ) -> List[Dict[str, Any]]:
        """
        Select best matching contractors based on severity and urgency.

        For emergency/high severity, prioritize fast response times.
        For routine, include budget options.
        """
        # Score contractors
        scored = []
        for contractor in contractors:
            score = contractor["rating"] * 10  # Base score from rating

            # Bonus for fast response on urgent jobs
            if urgency in ["immediate", "urgent"] and contractor["response_time_hours"] <= 2:
                score += 15

            # Bonus for specialties matching severity
            if severity in ["emergency", "high"] and "emergency" in contractor["specialties"]:
                score += 10

            scored.append((score, contractor))

        # Sort by score (highest first)
        scored.sort(key=lambda x: x[0], reverse=True)

        # Return top N contractors
        selected = [contractor for _, contractor in scored[:num_bids]]

        # If not enough, add random ones
        if len(selected) < num_bids:
            remaining = [c for c in contractors if c not in selected]
            selected.extend(random.sample(remaining, min(num_bids - len(selected), len(remaining))))

        return selected

    def _generate_bid(
        self,
        job_id: str,
        contractor: Dict[str, Any],
        category: str,
        severity: str,
        urgency: str,
        description: str,
        property_location: Optional[Dict[str, float]],
        bid_index: int
    ) -> Dict[str, Any]:
        """Generate a single bid from a contractor."""

        # Calculate quote
        base_rate = contractor["base_rate"]
        quote = self._calculate_quote(base_rate, severity, urgency, category)

        # Calculate ETA
        eta = self._calculate_eta(contractor["response_time_hours"], urgency)

        # Calculate distance (mock)
        distance = self._calculate_distance(contractor["service_area_miles"])

        # Generate bid ID
        bid_id = f"BID-{datetime.now().strftime('%Y%m%d%H%M%S')}-{bid_index}"

        return {
            "bid_id": bid_id,
            "job_id": job_id,
            "contractor_id": contractor["contractor_id"],
            "contractor_name": contractor["name"],
            "contractor_email": f"{contractor['contractor_id']}@landten-contractors.com",
            "contractor_phone": f"+1-555-{random.randint(1000, 9999)}",
            "quote": float(quote),
            "eta": eta,
            "availability": self._generate_availability(urgency),
            "rating": float(contractor["rating"]),
            "reviews_count": contractor["reviews_count"],
            "distance": distance,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "specialties": contractor["specialties"],
                "response_time_hours": contractor["response_time_hours"],
                "service_area_miles": contractor["service_area_miles"]
            }
        }

    def _calculate_quote(
        self,
        base_rate: float,
        severity: str,
        urgency: str,
        category: str
    ) -> Decimal:
        """Calculate bid quote based on base rate and job parameters."""

        # Start with base rate
        quote = Decimal(str(base_rate))

        # Severity multiplier
        severity_multipliers = {
            "low": Decimal("1.0"),
            "medium": Decimal("1.3"),
            "high": Decimal("1.6"),
            "emergency": Decimal("2.0")
        }
        quote *= severity_multipliers.get(severity, Decimal("1.0"))

        # Urgency premium
        urgency_premiums = {
            "routine": Decimal("0"),
            "urgent": Decimal("25"),
            "immediate": Decimal("50")
        }
        quote += urgency_premiums.get(urgency, Decimal("0"))

        # Add some randomness for variation (±10%)
        variation = Decimal(str(random.uniform(-0.1, 0.1)))
        quote += quote * variation

        # Round to nearest $5
        quote = (quote / Decimal("5")).quantize(Decimal("1")) * Decimal("5")

        return quote

    def _calculate_eta(self, response_time_hours: int, urgency: str) -> str:
        """Calculate estimated time of arrival."""

        if urgency == "immediate":
            if response_time_hours <= 2:
                return "Within 2 hours"
            elif response_time_hours <= 4:
                return "Same day"
            else:
                return "Next business day"

        elif urgency == "urgent":
            if response_time_hours <= 4:
                return "Same day"
            elif response_time_hours <= 8:
                return "Next business day"
            else:
                return "Within 48 hours"

        else:  # routine
            if response_time_hours <= 8:
                return "Within 2 days"
            else:
                return "Within 1 week"

    def _generate_availability(self, urgency: str) -> str:
        """Generate availability text."""

        now = datetime.now()

        if urgency == "immediate":
            return f"Available now"
        elif urgency == "urgent":
            tomorrow = now + timedelta(days=1)
            return f"Available {tomorrow.strftime('%A, %I:%M %p')}"
        else:
            next_week = now + timedelta(days=random.randint(2, 7))
            return f"Available {next_week.strftime('%A, %B %d')}"

    def _calculate_distance(self, service_area_miles: int) -> str:
        """Calculate distance to property (mock)."""

        # Generate random distance within service area
        distance = random.uniform(0.5, service_area_miles * 0.8)
        return f"{distance:.1f} mi"


# Singleton instance
_bid_generator: Optional[BidGenerator] = None


def get_bid_generator() -> BidGenerator:
    """Get or create the singleton BidGenerator instance."""
    global _bid_generator

    if _bid_generator is None:
        _bid_generator = BidGenerator()

    return _bid_generator
