"""
Contractor Gamification & Retention Models

This module defines the psychological hooks and engagement systems that make
contractors sticky and drive network effects.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class ContractorLevel(str, Enum):
    """Contractor levels - creates aspirational ladder"""
    BRONZE = "bronze"  # 0-10 jobs
    SILVER = "silver"  # 11-50 jobs
    GOLD = "gold"  # 51-100 jobs
    PLATINUM = "platinum"  # 101-250 jobs
    DIAMOND = "diamond"  # 251-500 jobs
    ELITE = "elite"  # 500+ jobs


class BadgeType(str, Enum):
    """Achievement badges - social proof and gamification"""
    # Verification Badges
    VERIFIED_LICENSE = "verified_license"
    VERIFIED_IDENTITY = "verified_identity"
    VERIFIED_INSURANCE = "verified_insurance"
    BACKGROUND_CHECK = "background_check"

    # Performance Badges
    FAST_RESPONDER = "fast_responder"  # Responds to jobs in <15 min
    QUALITY_PRO = "quality_pro"  # 4.8+ rating, 20+ reviews
    DEADLINE_MASTER = "deadline_master"  # Completes 95% on time
    CUSTOMER_FAVORITE = "customer_favorite"  # 4.9+ rating

    # Volume Badges
    FIRST_JOB = "first_job"
    TEN_JOBS = "ten_jobs"
    FIFTY_JOBS = "fifty_jobs"
    HUNDRED_JOBS = "hundred_jobs"

    # Social Badges
    TEAM_PLAYER = "team_player"  # Partners with other contractors
    MENTOR = "mentor"  # Helps new contractors
    REFERRAL_CHAMPION = "referral_champion"  # Referred 5+ contractors

    # Financial Badges
    HIGH_EARNER = "high_earner"  # Top 10% in category
    CONSISTENT_EARNER = "consistent_earner"  # 12 weeks consecutive work

    # Special Badges
    EARLY_ADOPTER = "early_adopter"  # Joined in first 1000
    VIP_CONTRACTOR = "vip_contractor"  # Invitation only


class Badge(BaseModel):
    """Individual badge instance"""
    badge_type: BadgeType
    earned_at: datetime
    display_name: str
    description: str
    icon_url: Optional[str] = None
    rarity: str = "common"  # common, rare, epic, legendary


class Achievement(BaseModel):
    """Trackable achievements for gamification"""
    achievement_id: str
    title: str
    description: str
    progress: int = 0
    target: int
    reward_points: int = 0
    reward_badge: Optional[BadgeType] = None
    completed: bool = False
    completed_at: Optional[datetime] = None


class ContractorScore(BaseModel):
    """
    Contractor score (0-100) - drives competitiveness and optimization

    Factors:
    - Profile completeness (20 points)
    - Verification levels (20 points)
    - Response time (15 points)
    - Job completion rate (15 points)
    - Customer ratings (20 points)
    - Platform engagement (10 points)
    """
    total_score: int = Field(ge=0, le=100)

    # Score breakdown
    profile_score: int = 0  # /20
    verification_score: int = 0  # /20
    response_score: int = 0  # /15
    completion_score: int = 0  # /15
    rating_score: int = 0  # /20
    engagement_score: int = 0  # /10

    # Ranking
    percentile: Optional[int] = None  # Top X%
    category_rank: Optional[int] = None  # Rank within category
    zip_rank: Optional[int] = None  # Rank within zip code


class EarningsInsight(BaseModel):
    """Financial analytics to keep contractors engaged"""

    # Current period
    today_earnings: float = 0
    week_earnings: float = 0
    month_earnings: float = 0

    # Projections (aspiration)
    projected_weekly: float = 0
    projected_monthly: float = 0
    projected_annual: float = 0

    # Comparisons (social proof)
    category_average_weekly: float = 0
    top_10_percent_weekly: float = 0
    your_vs_average: float = 0  # Percentage above/below average

    # Insights
    best_earning_day: Optional[str] = None
    best_earning_hour: Optional[str] = None
    average_job_value: float = 0
    highest_paying_client: Optional[str] = None


class StreakTracker(BaseModel):
    """Streak tracking - daily engagement driver"""
    current_streak: int = 0  # Days
    longest_streak: int = 0
    last_activity_date: Optional[datetime] = None

    # Rewards
    streak_milestone_next: int = 7  # Next milestone (7, 14, 30, 60, 90, 180, 365)
    streak_bonus_unlocked: bool = False


class ReferralStats(BaseModel):
    """Viral loop tracking"""
    referral_code: str
    referrals_sent: int = 0
    referrals_signed_up: int = 0
    referrals_active: int = 0  # Completed at least 1 job
    earnings_from_referrals: float = 0

    # Incentives
    bonus_earned: float = 0
    next_bonus_at: int = 3  # Next bonus at X active referrals


class LeaderboardEntry(BaseModel):
    """Leaderboard position - competitive driver"""
    contractor_id: str
    rank: int
    display_name: str
    score: int
    level: ContractorLevel
    jobs_completed: int
    rating: float
    badges_count: int

    # Anonymous display option
    show_name: bool = True


class JobMarketInsights(BaseModel):
    """Real-time market data - creates urgency"""
    jobs_posted_today: int
    jobs_in_your_area: int
    jobs_in_your_category: int
    avg_bid_count: int
    avg_job_value: float

    # Urgency creators
    hot_jobs_expiring_soon: int  # Expiring in <2 hours
    premium_jobs_available: int  # $500+ value

    # Opportunity score (0-100)
    market_heat: int = Field(ge=0, le=100)  # How hot is the market right now


class ContractorGamification(BaseModel):
    """
    Complete gamification profile for a contractor
    Designed to maximize engagement and retention
    """
    contractor_id: str

    # Core gamification
    level: ContractorLevel = ContractorLevel.BRONZE
    score: ContractorScore
    badges: List[Badge] = []
    achievements: List[Achievement] = []

    # Financial hooks
    earnings_insights: EarningsInsight

    # Engagement drivers
    streak: StreakTracker
    referrals: ReferralStats

    # Social proof
    leaderboard_rank_overall: Optional[int] = None
    leaderboard_rank_category: Optional[int] = None
    leaderboard_rank_zip: Optional[int] = None

    # Market intelligence
    market_insights: JobMarketInsights

    # Progress to next level
    jobs_to_next_level: int = 0
    points_to_next_level: int = 0

    # Notifications (FOMO drivers)
    unread_job_matches: int = 0
    pending_invitations: int = 0
    messages_unread: int = 0

    # VIP status
    is_vip: bool = False
    vip_since: Optional[datetime] = None


class OnboardingIncentives(BaseModel):
    """
    Time-limited incentives shown during onboarding
    Creates urgency and commitment
    """

    # Bonuses
    first_job_bonus: float = 50.0
    signup_bonus: float = 25.0
    speed_bonus_eligible: bool = True  # Complete in <5 min
    speed_bonus_amount: float = 15.0

    # Guarantees
    first_job_guarantee_hours: int = 48
    guarantee_payout: float = 25.0

    # Premium perks
    free_premium_listing_days: int = 30
    premium_value: float = 29.0

    # Referral rewards
    referral_bonus_per_active: float = 50.0
    referral_milestone_bonus: Dict[int, float] = {
        3: 150.0,
        5: 300.0,
        10: 750.0,
    }

    # Time-limited offers
    offer_expires_at: Optional[datetime] = None
    priority_job_access_days: int = 7


class SuccessStory(BaseModel):
    """
    Social proof testimonials
    Shows what's possible
    """
    contractor_name: str
    contractor_category: str
    location: str  # City or ZIP

    # Metrics
    time_on_platform: str  # "2 months", "1 year"
    earnings: str  # "$18,500", "$4,200/week"
    jobs_completed: int
    rating: float

    # Quote
    testimonial: str

    # Visual
    photo_url: Optional[str] = None
    verified: bool = True


# ============================================================================
# EXAMPLE DATA FOR PSYCHOLOGICAL TRIGGERS
# ============================================================================

EXAMPLE_SUCCESS_STORIES = [
    SuccessStory(
        contractor_name="Mike Rodriguez",
        contractor_category="Plumbing",
        location="San Francisco, CA",
        time_on_platform="3 months",
        earnings="$18,500",
        jobs_completed=47,
        rating=4.9,
        testimonial="I was skeptical at first, but after my first week earning $2,400, I quit my old job. Best decision ever. The platform just keeps sending me work!",
        verified=True
    ),
    SuccessStory(
        contractor_name="Sarah Chen",
        contractor_category="Electrical",
        location="Austin, TX",
        time_on_platform="6 months",
        earnings="$6,800/week",
        jobs_completed=124,
        rating=5.0,
        testimonial="The instant payment feature is a game-changer. I don't chase invoices anymore. I work, I get paid, I move on to the next job. It's that simple.",
        verified=True
    ),
    SuccessStory(
        contractor_name="James Thompson",
        contractor_category="HVAC",
        location="Phoenix, AZ",
        time_on_platform="1 year",
        earnings="$112,000",
        jobs_completed=284,
        rating=4.8,
        testimonial="Started part-time filling gaps in my schedule. Now it's my main income. The quality of clients is unmatched - they're pre-qualified and serious.",
        verified=True
    ),
]

BADGE_DEFINITIONS = {
    BadgeType.VERIFIED_LICENSE: {
        "display_name": "Verified Professional",
        "description": "License verified and active",
        "icon": "🎯",
        "rarity": "common",
        "boost": "40% higher job win rate"
    },
    BadgeType.FAST_RESPONDER: {
        "display_name": "Lightning Fast",
        "description": "Responds to jobs in under 15 minutes",
        "icon": "⚡",
        "rarity": "rare",
        "boost": "2x more job invitations"
    },
    BadgeType.QUALITY_PRO: {
        "display_name": "Quality Pro",
        "description": "4.8+ rating with 20+ reviews",
        "icon": "⭐",
        "rarity": "rare",
        "boost": "Featured in search results"
    },
    BadgeType.VIP_CONTRACTOR: {
        "display_name": "VIP Elite",
        "description": "Top 5% of contractors - invitation only",
        "icon": "👑",
        "rarity": "legendary",
        "boost": "Priority job access + 15% higher rates"
    },
}

DEFAULT_ACHIEVEMENTS = [
    {
        "achievement_id": "first_bid",
        "title": "First Bid",
        "description": "Place your first job bid",
        "target": 1,
        "reward_points": 10,
        "reward_badge": None,
    },
    {
        "achievement_id": "first_job",
        "title": "First Win",
        "description": "Complete your first job",
        "target": 1,
        "reward_points": 50,
        "reward_badge": BadgeType.FIRST_JOB,
    },
    {
        "achievement_id": "ten_jobs",
        "title": "Rising Star",
        "description": "Complete 10 jobs",
        "target": 10,
        "reward_points": 100,
        "reward_badge": BadgeType.TEN_JOBS,
    },
    {
        "achievement_id": "five_star_streak",
        "title": "Perfection Streak",
        "description": "Get five 5-star reviews in a row",
        "target": 5,
        "reward_points": 200,
        "reward_badge": BadgeType.QUALITY_PRO,
    },
    {
        "achievement_id": "fast_response",
        "title": "Speed Demon",
        "description": "Respond to 20 jobs within 15 minutes",
        "target": 20,
        "reward_points": 150,
        "reward_badge": BadgeType.FAST_RESPONDER,
    },
    {
        "achievement_id": "referral_champion",
        "title": "Referral Champion",
        "description": "Refer 5 active contractors",
        "target": 5,
        "reward_points": 500,
        "reward_badge": BadgeType.REFERRAL_CHAMPION,
    },
]
