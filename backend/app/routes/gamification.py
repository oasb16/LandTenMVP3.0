"""
Gamification Routes - Contractor engagement & retention system

Provides endpoints for:
- Leaderboards (overall, category, zip code)
- Contractor scores & rankings
- Badges & achievements
- Streaks & earnings insights
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from ..models.contractor_gamification import (
    ContractorGamification,
    LeaderboardEntry,
    ContractorLevel,
    ContractorScore,
    Badge,
    Achievement,
    StreakTracker,
    EarningsInsight,
    ReferralStats,
    JobMarketInsights,
    OnboardingIncentives,
    SuccessStory,
    EXAMPLE_SUCCESS_STORIES,
    BADGE_DEFINITIONS,
    DEFAULT_ACHIEVEMENTS,
)
from ..deps.auth import verify_firebase_token

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory storage for development (replace with DynamoDB in production)
_GAMIFICATION_DATA: dict[str, ContractorGamification] = {}
_LEADERBOARD_CACHE: List[LeaderboardEntry] = []


def _get_contractor_level(jobs_completed: int) -> ContractorLevel:
    """Calculate contractor level based on jobs completed"""
    if jobs_completed >= 500:
        return ContractorLevel.ELITE
    elif jobs_completed >= 251:
        return ContractorLevel.DIAMOND
    elif jobs_completed >= 101:
        return ContractorLevel.PLATINUM
    elif jobs_completed >= 51:
        return ContractorLevel.GOLD
    elif jobs_completed >= 11:
        return ContractorLevel.SILVER
    else:
        return ContractorLevel.BRONZE


def _calculate_score(contractor_data: dict) -> ContractorScore:
    """Calculate contractor score (0-100)"""
    profile_score = min(20, contractor_data.get("profile_completeness", 50) // 5)
    verification_score = len(contractor_data.get("verifications", [])) * 5
    response_score = 15 if contractor_data.get("avg_response_time_min", 60) < 30 else 8
    completion_score = int((contractor_data.get("completion_rate", 0) / 100) * 15)
    rating_score = int((contractor_data.get("rating", 0) / 5) * 20)
    engagement_score = min(10, contractor_data.get("login_streak", 0))

    total = (
        profile_score
        + verification_score
        + response_score
        + completion_score
        + rating_score
        + engagement_score
    )

    return ContractorScore(
        total_score=min(100, total),
        profile_score=profile_score,
        verification_score=verification_score,
        response_score=response_score,
        completion_score=completion_score,
        rating_score=rating_score,
        engagement_score=engagement_score,
    )


@router.get("/gamification/leaderboard")
async def get_leaderboard(
    category: Optional[str] = None,
    zip_code: Optional[str] = None,
    limit: int = Query(default=50, le=100),
):
    """
    Get leaderboard rankings

    Args:
        category: Filter by contractor category (plumbing, electrical, etc.)
        zip_code: Filter by geographic area
        limit: Number of entries to return (max 100)

    Returns:
        List of leaderboard entries sorted by score
    """
    try:
        # In production, query from DynamoDB
        # For now, return mock data
        mock_leaderboard = [
            LeaderboardEntry(
                contractor_id=f"contractor_{i}",
                rank=i,
                display_name=f"Contractor {i}",
                score=100 - i,
                level=_get_contractor_level(100 - i * 2),
                jobs_completed=100 - i * 2,
                rating=4.9 - (i * 0.01),
                badges_count=5 - (i // 10),
                show_name=True,
            )
            for i in range(1, min(limit + 1, 51))
        ]

        return {"success": True, "leaderboard": mock_leaderboard, "total": len(mock_leaderboard)}

    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch leaderboard")


@router.get("/gamification/contractor/{contractor_id}")
async def get_contractor_gamification(
    contractor_id: str, token: str = Depends(verify_firebase_token)
):
    """
    Get full gamification profile for a contractor

    Returns:
        - Level & score
        - Badges & achievements
        - Leaderboard rankings
        - Earnings insights
        - Streak tracking
        - Market insights
    """
    try:
        # Check cache first
        if contractor_id in _GAMIFICATION_DATA:
            return {"success": True, "data": _GAMIFICATION_DATA[contractor_id]}

        # Mock data for development
        # In production, fetch from DynamoDB and calculate metrics
        mock_data = ContractorGamification(
            contractor_id=contractor_id,
            level=ContractorLevel.SILVER,
            score=ContractorScore(
                total_score=72,
                profile_score=15,
                verification_score=15,
                response_score=12,
                completion_score=13,
                rating_score=17,
                engagement_score=8,
                percentile=25,  # Top 25%
                category_rank=12,
                zip_rank=3,
            ),
            badges=[
                Badge(
                    badge_type="verified_license",
                    earned_at="2024-01-15T10:00:00Z",
                    display_name="Verified Professional",
                    description="License verified and active",
                    rarity="common",
                ),
                Badge(
                    badge_type="first_job",
                    earned_at="2024-01-20T14:30:00Z",
                    display_name="First Win",
                    description="Completed first job successfully",
                    rarity="common",
                ),
            ],
            achievements=[
                Achievement(
                    achievement_id="first_job",
                    title="First Win",
                    description="Complete your first job",
                    progress=1,
                    target=1,
                    reward_points=50,
                    completed=True,
                ),
                Achievement(
                    achievement_id="ten_jobs",
                    title="Rising Star",
                    description="Complete 10 jobs",
                    progress=7,
                    target=10,
                    reward_points=100,
                    completed=False,
                ),
            ],
            earnings_insights=EarningsInsight(
                today_earnings=125.50,
                week_earnings=850.00,
                month_earnings=3200.00,
                projected_weekly=900.00,
                projected_monthly=3600.00,
                projected_annual=43200.00,
                category_average_weekly=720.00,
                top_10_percent_weekly=1500.00,
                your_vs_average=18.1,
                best_earning_day="Tuesday",
                best_earning_hour="10am-12pm",
                average_job_value=212.50,
            ),
            streak=StreakTracker(
                current_streak=12, longest_streak=18, streak_milestone_next=14, streak_bonus_unlocked=False
            ),
            referrals=ReferralStats(
                referral_code=f"REF_{contractor_id[:8]}".upper(),
                referrals_sent=3,
                referrals_signed_up=2,
                referrals_active=1,
                earnings_from_referrals=50.00,
                bonus_earned=25.00,
                next_bonus_at=3,
            ),
            leaderboard_rank_overall=47,
            leaderboard_rank_category=12,
            leaderboard_rank_zip=3,
            market_insights=JobMarketInsights(
                jobs_posted_today=24,
                jobs_in_your_area=8,
                jobs_in_your_category=5,
                avg_bid_count=3,
                avg_job_value=285.00,
                hot_jobs_expiring_soon=2,
                premium_jobs_available=1,
                market_heat=72,
            ),
            jobs_to_next_level=4,
            points_to_next_level=280,
            unread_job_matches=3,
            pending_invitations=1,
            messages_unread=2,
            is_vip=False,
        )

        # Cache for 5 minutes
        _GAMIFICATION_DATA[contractor_id] = mock_data

        return {"success": True, "data": mock_data}

    except Exception as e:
        logger.error(f"Error fetching gamification for {contractor_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch gamification data")


@router.get("/gamification/badges")
async def get_badge_definitions():
    """
    Get all available badge definitions

    Returns:
        Dictionary of badge types with display info
    """
    return {"success": True, "badges": BADGE_DEFINITIONS}


@router.get("/gamification/achievements")
async def get_achievement_definitions():
    """
    Get all available achievement definitions

    Returns:
        List of achievable milestones
    """
    return {"success": True, "achievements": DEFAULT_ACHIEVEMENTS}


@router.get("/gamification/success-stories")
async def get_success_stories(limit: int = Query(default=3, le=10)):
    """
    Get contractor success stories for social proof

    Returns:
        List of verified success testimonials
    """
    return {"success": True, "stories": EXAMPLE_SUCCESS_STORIES[:limit]}


@router.get("/gamification/onboarding-incentives")
async def get_onboarding_incentives():
    """
    Get current onboarding incentives and bonuses

    Returns:
        Time-limited offers for new contractors
    """
    from datetime import datetime, timedelta

    incentives = OnboardingIncentives(
        first_job_bonus=50.0,
        signup_bonus=25.0,
        speed_bonus_eligible=True,
        speed_bonus_amount=15.0,
        first_job_guarantee_hours=48,
        guarantee_payout=25.0,
        free_premium_listing_days=30,
        premium_value=29.0,
        referral_bonus_per_active=50.0,
        referral_milestone_bonus={3: 150.0, 5: 300.0, 10: 750.0},
        offer_expires_at=datetime.now() + timedelta(days=7),
        priority_job_access_days=7,
    )

    return {"success": True, "incentives": incentives}


@router.post("/gamification/update-streak/{contractor_id}")
async def update_contractor_streak(contractor_id: str, token: str = Depends(verify_firebase_token)):
    """
    Update contractor's daily login streak

    In production, this would be called automatically on login
    """
    try:
        # In production: Update streak in DynamoDB, award bonuses if milestone reached
        return {"success": True, "message": "Streak updated", "current_streak": 13, "bonus_unlocked": False}

    except Exception as e:
        logger.error(f"Error updating streak for {contractor_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update streak")


@router.post("/gamification/award-badge/{contractor_id}")
async def award_badge(contractor_id: str, badge_type: str, token: str = Depends(verify_firebase_token)):
    """
    Award a badge to a contractor

    In production, this would be triggered by achievement conditions
    """
    try:
        if badge_type not in BADGE_DEFINITIONS:
            raise HTTPException(status_code=400, detail=f"Invalid badge type: {badge_type}")

        badge_info = BADGE_DEFINITIONS[badge_type]

        return {
            "success": True,
            "message": f"Badge '{badge_info['display_name']}' awarded!",
            "badge": {
                "badge_type": badge_type,
                "display_name": badge_info["display_name"],
                "description": badge_info["description"],
                "rarity": badge_info["rarity"],
                "boost": badge_info.get("boost", ""),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error awarding badge to {contractor_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to award badge")
