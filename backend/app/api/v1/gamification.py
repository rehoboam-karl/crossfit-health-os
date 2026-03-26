"""
Gamification API - badges, streaks, XP, achievements
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.auth import get_current_user
from app.db.supabase import supabase_client
from app.services.gamification import GamificationService, BADGE_DEFINITIONS

router = APIRouter(prefix="/api/v1/gamification", tags=["gamification"])


class BadgeResponse(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    earned: bool
    earned_at: Optional[str] = None
    xp_reward: int = 0


class StatsResponse(BaseModel):
    total_workouts: int
    current_streak: int
    longest_streak: int
    level: int
    xp: int
    xp_to_next_level: int
    xp_percentage: float
    average_rpe: float
    badges: List[BadgeResponse]
    this_week_workouts: int
    this_month_workouts: int


@router.get("/stats", response_model=StatsResponse)
async def get_user_stats(current_user: dict = Depends(get_current_user)):
    """Get comprehensive user stats including streaks, badges, and XP."""
    user_id = current_user["id"]
    gamification = GamificationService(user_id)
    stats = gamification.get_user_stats()
    
    # Build badge list with all available badges
    all_badges = []
    earned_ids = {b.id for b in stats.badges}
    
    for badge_id, badge_info in BADGE_DEFINITIONS.items():
        earned_badge = next((b for b in stats.badges if b.id == badge_id.value), None)
        all_badges.append(BadgeResponse(
            id=badge_id.value,
            name=badge_info["name"],
            description=badge_info["description"],
            icon=badge_info["icon"],
            earned=badge_id.value in earned_ids,
            earned_at=earned_badge.earned_at.isoformat() if earned_badge and earned_badge.earned_at else None,
            xp_reward=badge_info.get("xp", 100)
        ))
    
    # Calculate XP percentage to next level
    xp_percentage = 0
    if stats.xp_to_next_level > 0:
        xp_percentage = (stats.xp % stats.xp_to_next_level) / stats.xp_to_next_level * 100
    
    return StatsResponse(
        total_workouts=stats.total_workouts,
        current_streak=stats.current_streak,
        longest_streak=stats.longest_streak,
        level=stats.level,
        xp=stats.xp,
        xp_to_next_level=stats.xp_to_next_level,
        xp_percentage=xp_percentage,
        average_rpe=round(stats.average_rpe, 1),
        badges=all_badges,
        this_week_workouts=stats.this_week_workouts,
        this_month_workouts=stats.this_month_workouts
    )


@router.get("/badges")
async def get_all_badges(current_user: dict = Depends(get_current_user)):
    """Get all available badges and user's earned badges."""
    gamification = GamificationService(current_user["id"])
    stats = gamification.get_user_stats()
    earned_ids = {b.id for b in stats.badges}
    
    badges = []
    for badge_id, badge_info in BADGE_DEFINITIONS.items():
        earned_badge = next((b for b in stats.badges if b.id == badge_id.value), None)
        badges.append({
            "id": badge_id.value,
            "name": badge_info["name"],
            "description": badge_info["description"],
            "icon": badge_info["icon"],
            "xp_reward": badge_info.get("xp", 100),
            "earned": badge_id.value in earned_ids,
            "earned_at": earned_badge.earned_at.isoformat() if earned_badge and earned_badge.earned_at else None
        })
    
    return {"badges": badges}


@router.get("/badges/{badge_id}")
async def get_badge(badge_id: str, current_user: dict = Depends(get_current_user)):
    """Get details about a specific badge."""
    if badge_id not in BADGE_DEFINITIONS:
        raise HTTPException(status_code=404, detail="Badge not found")
    
    badge_info = BADGE_DEFINITIONS[badge_id]
    gamification = GamificationService(current_user["id"])
    stats = gamification.get_user_stats()
    
    earned_badge = next((b for b in stats.badges if b.id == badge_id), None)
    
    return {
        "id": badge_id,
        "name": badge_info["name"],
        "description": badge_info["description"],
        "icon": badge_info["icon"],
        "xp_reward": badge_info.get("xp", 100),
        "earned": earned_badge is not None,
        "earned_at": earned_badge.earned_at.isoformat() if earned_badge and earned_badge.earned_at else None
    }


@router.get("/streak")
async def get_streak_info(current_user: dict = Depends(get_current_user)):
    """Get detailed streak information."""
    gamification = GamificationService(current_user["id"])
    stats = gamification.get_user_stats()
    
    # Calculate next badge
    next_badge = None
    if stats.current_streak < 3:
        next_badge = {"type": "week_streak_3", "days_needed": 3 - stats.current_streak}
    elif stats.current_streak < 7:
        next_badge = {"type": "week_streak_7", "days_needed": 7 - stats.current_streak}
    elif stats.current_streak < 30:
        next_badge = {"type": "week_streak_30", "days_needed": 30 - stats.current_streak}
    
    return {
        "current_streak": stats.current_streak,
        "longest_streak": stats.longest_streak,
        "this_week_workouts": stats.this_week_workouts,
        "this_month_workouts": stats.this_month_workouts,
        "next_badge": next_badge
    }


@router.get("/leaderboard")
async def get_leaderboard(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get XP leaderboard for competitive element."""
    try:
        # Get top users by XP
        response = supabase_client.table("user_stats").select(
            "user_id, xp, level"
        ).order("xp", desc=True).limit(limit).execute()
        
        leaderboard = []
        for i, row in enumerate(response.data or [], 1):
            # Get user name
            try:
                user_resp = supabase_client.table("users").select("name").eq(
                    "id", row["user_id"]
                ).single().execute()
                name = user_resp.data.get("name", "Anonymous") if user_resp.data else "Anonymous"
            except:
                name = "Anonymous"
            
            leaderboard.append({
                "rank": i,
                "user_id": row["user_id"],
                "name": name,
                "xp": row.get("xp", 0),
                "level": row.get("level", 1),
                "is_current_user": row["user_id"] == current_user["id"]
            })
        
        return {"leaderboard": leaderboard}
        
    except Exception as e:
        return {"leaderboard": [], "error": str(e)}


@router.post("/workout-complete")
async def record_workout_completion(
    session_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Record workout completion and award XP/badges."""
    gamification = GamificationService(current_user["id"])
    result = gamification.record_workout_complete(session_data)
    
    # Create notifications for achievements
    from app.services.notifications import NotificationService
    notifier = NotificationService(current_user["id"])
    
    # Level up notification
    if result.get("level_up"):
        notifier.send_level_up(result.get("new_level", 2))
    
    # Badge notifications
    for badge in result.get("new_badges", []):
        notifier.send_new_badge(
            badge["name"],
            badge["icon"],
            100  # Badge XP
        )
    
    return result


@router.get("/xp-history")
async def get_xp_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get recent XP gain history."""
    # This would query an xp_transactions table if we have one
    # For now, return empty
    return {"history": []}
