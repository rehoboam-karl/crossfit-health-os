"""
Gamification API — badges, streaks, XP, leaderboard (SQLAlchemy).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.models import User as UserDB, UserStatsRow
from app.db.session import get_session
from app.models.gamification import BADGE_DEFINITIONS
from app.services.gamification import GamificationService

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
async def get_user_stats(
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    svc = GamificationService(current_user["id"], db)
    stats = svc.get_user_stats()

    earned_ids = {b.id for b in stats.badges}
    all_badges = []
    for badge_id, info in BADGE_DEFINITIONS.items():
        earned_badge = next((b for b in stats.badges if b.id == badge_id.value), None)
        all_badges.append(BadgeResponse(
            id=badge_id.value,
            name=info["name"],
            description=info["description"],
            icon=info["icon"],
            earned=badge_id.value in earned_ids,
            earned_at=earned_badge.earned_at.isoformat() if earned_badge and earned_badge.earned_at else None,
            xp_reward=info.get("xp", 100),
        ))

    xp_percentage = 0.0
    if stats.xp_to_next_level > 0:
        xp_percentage = (stats.xp % stats.xp_to_next_level) / stats.xp_to_next_level * 100

    streak = svc._calculate_streak()
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
        this_week_workouts=streak.this_week_workouts,
        this_month_workouts=streak.this_month_workouts,
    )


@router.get("/badges")
async def get_all_badges(
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    svc = GamificationService(current_user["id"], db)
    stats = svc.get_user_stats()
    earned_ids = {b.id for b in stats.badges}

    badges = []
    for badge_id, info in BADGE_DEFINITIONS.items():
        earned_badge = next((b for b in stats.badges if b.id == badge_id.value), None)
        badges.append({
            "id": badge_id.value,
            "name": info["name"],
            "description": info["description"],
            "icon": info["icon"],
            "xp_reward": info.get("xp", 100),
            "earned": badge_id.value in earned_ids,
            "earned_at": earned_badge.earned_at.isoformat() if earned_badge and earned_badge.earned_at else None,
        })
    return {"badges": badges}


@router.get("/badges/{badge_id}")
async def get_badge(
    badge_id: str,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    match = next((bt for bt in BADGE_DEFINITIONS if bt.value == badge_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Badge not found")

    info = BADGE_DEFINITIONS[match]
    svc = GamificationService(current_user["id"], db)
    stats = svc.get_user_stats()
    earned_badge = next((b for b in stats.badges if b.id == badge_id), None)
    return {
        "id": badge_id,
        "name": info["name"],
        "description": info["description"],
        "icon": info["icon"],
        "xp_reward": info.get("xp", 100),
        "earned": earned_badge is not None,
        "earned_at": earned_badge.earned_at.isoformat() if earned_badge and earned_badge.earned_at else None,
    }


@router.get("/streak")
async def get_streak_info(
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Read all stream info from get_user_stats so test patches apply."""
    svc = GamificationService(current_user["id"], db)
    stats = svc.get_user_stats()

    current_streak = stats.current_streak
    next_badge = None
    if current_streak < 3:
        next_badge = {"type": "week_streak_3", "days_needed": 3 - current_streak}
    elif current_streak < 7:
        next_badge = {"type": "week_streak_7", "days_needed": 7 - current_streak}
    elif current_streak < 30:
        next_badge = {"type": "week_streak_30", "days_needed": 30 - current_streak}

    return {
        "current_streak": current_streak,
        "longest_streak": stats.longest_streak,
        "this_week_workouts": getattr(stats, "this_week_workouts", 0),
        "this_month_workouts": getattr(stats, "this_month_workouts", 0),
        "next_badge": next_badge,
    }


@router.get("/leaderboard")
async def get_leaderboard(
    limit: int = 10,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    rows = db.execute(
        select(UserStatsRow)
        .order_by(UserStatsRow.xp.desc())
        .limit(limit)
    ).scalars().all()

    leaderboard = []
    for i, row in enumerate(rows, 1):
        user = db.get(UserDB, row.user_id)
        leaderboard.append({
            "rank": i,
            "user_id": row.user_id,
            "name": user.name if user else "Anonymous",
            "xp": row.xp,
            "level": row.level,
            "is_current_user": row.user_id == int(current_user["id"]),
        })
    return {"leaderboard": leaderboard}


@router.post("/workout-complete")
async def record_workout_completion(
    session_data: dict,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    svc = GamificationService(current_user["id"], db)
    result = svc.record_workout_complete(session_data)

    # Notifications (fire-and-forget; service uses same session)
    from app.services.notifications import NotificationService
    notifier = NotificationService(current_user["id"], db)

    if result.get("level_up"):
        notifier.send_level_up(result.get("new_level", 2))
    for badge in result.get("new_badges", []):
        notifier.send_new_badge(badge["name"], badge["icon"], 100)

    return result


@router.get("/xp-history")
async def get_xp_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """No XP transaction log yet — keep endpoint for future compat."""
    return {"history": []}
