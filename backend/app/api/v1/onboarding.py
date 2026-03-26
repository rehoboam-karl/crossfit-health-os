"""
Onboarding API - Guide new users through initial setup
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

from app.core.auth import get_current_user
from app.db.supabase import supabase_client
from app.services.gamification import GamificationService

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


class OnboardingData(BaseModel):
    """Data collected during onboarding."""
    name: str = Field(..., min_length=2, max_length=100)
    birth_date: Optional[str] = None
    weight_kg: Optional[float] = Field(None, ge=30, le=300)
    height_cm: Optional[float] = Field(None, ge=100, le=250)
    fitness_level: str = Field("intermediate", description="beginner|intermediate|advanced|athlete")
    primary_goal: str = Field(..., description="strength|conditioning|both|health")
    available_days: List[str] = Field(
        default=["monday", "wednesday", "friday"],
        description="Days available for training"
    )
    preferred_time: str = Field("morning", description="morning|afternoon|evening")
    training_duration: int = Field(60, ge=30, le=180, description="Minutes per session")
    methodologies: List[str] = Field(
        default=["hwpo"],
        description="Preferred training methodology"
    )
    focus_weaknesses: List[str] = Field(
        default=[],
        description="Movement weaknesses to address"
    )
    has_gym_access: bool = True
    has_barbell: bool = False
    has_rings: bool = False
    has_pullup_bar: bool = False
    # NEW: App focus - determines if nutrition features are enabled
    app_focus: str = Field("full", description="training|full|custom")
    nutrition_enabled: bool = Field(True, description="Whether to enable nutrition features")


class OnboardingProgress(BaseModel):
    step: int
    total_steps: int = 5
    completed: bool = False
    profile_complete: bool = False
    schedule_created: bool = False
    first_workout_done: bool = False


def calculate_readiness_from_age(birth_date: Optional[str]) -> int:
    """Calculate baseline readiness based on age."""
    if not birth_date:
        return 70  # Default
    
    try:
        birth = date.fromisoformat(birth_date)
        today = date.today()
        age = (today - birth).days // 365
        
        # Younger = higher baseline
        if age < 25:
            return 85
        elif age < 35:
            return 75
        elif age < 45:
            return 65
        else:
            return 55
    except:
        return 70


@router.post("/complete")
async def complete_onboarding(
    data: OnboardingData,
    current_user: dict = Depends(get_current_user)
):
    """
    Complete onboarding - saves profile, creates schedule, awards XP.
    """
    user_id = current_user["id"]
    
    try:
        # 1. Update user profile
        profile_data = {
            "name": data.name,
            "birth_date": data.birth_date,
            "weight_kg": data.weight_kg,
            "height_cm": data.height_cm,
            "fitness_level": data.fitness_level,
            "onboarding_completed": True,
            "primary_goal": data.primary_goal,
            "preferred_time": data.preferred_time,
            "training_duration": data.training_duration,
            "methodologies": data.methodologies,
            "focus_weaknesses": data.focus_weaknesses,
            "has_gym_access": data.has_gym_access,
            "has_barbell": data.has_barbell,
            "has_rings": data.has_rings,
            "has_pullup_bar": data.has_pullup_bar,
            "baseline_readiness": calculate_readiness_from_age(data.birth_date),
            # App focus settings
            "app_focus": data.app_focus,
            "nutrition_enabled": data.nutrition_enabled
        }
        
        supabase_client.table("users").update(profile_data).eq(
            "id", user_id
        ).execute()
        
        # 2. Create initial weekly schedule
        days_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        
        # Time preference to hour
        time_map = {
            "morning": "07:00",
            "afternoon": "17:00",
            "evening": "19:00"
        }
        
        schedule = {}
        all_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for day in all_days:
            is_training_day = day in data.available_days
            schedule[day] = {
                "rest_day": not is_training_day,
                "sessions": [] if not is_training_day else [{
                    "time": time_map.get(data.preferred_time, "07:00"),
                    "duration_minutes": data.training_duration,
                    "workout_type": "mixed"
                }]
            }
        
        # Calculate next Monday as start
        from datetime import date, timedelta
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)
        
        schedule_data = {
            "user_id": user_id,
            "name": f"My {data.methodologies[0].upper() if data.methodologies else 'Custom'} Program",
            "methodology": data.methodologies[0] if data.methodologies else "custom",
            "schedule": schedule,
            "start_date": next_monday.isoformat(),
            "active": True
        }
        
        supabase_client.table("weekly_schedules").insert(schedule_data).execute()
        
        # 3. Award XP for completing onboarding
        gamification = GamificationService(user_id)
        new_level, _ = gamification.add_xp(300)  # Onboarding XP
        
        # 4. Record onboarding completion
        try:
            supabase_client.table("user_stats").insert({
                "user_id": user_id,
                "xp": 300,
                "level": 1,
                "current_streak": 0,
                "longest_streak": 0
            }).execute()
        except:
            pass  # May already exist
        
        return {
            "success": True,
            "profile": profile_data,
            "schedule_created": True,
            "xp_earned": 300,
            "message": "Onboarding complete! You're ready to start training."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Onboarding failed: {str(e)}")


@router.get("/progress")
async def get_onboarding_progress(current_user: dict = Depends(get_current_user)):
    """Get current onboarding progress."""
    user_id = current_user["id"]
    
    try:
        # Check user profile
        user_resp = supabase_client.table("users").select("onboarding_completed, name").eq(
            "id", user_id
        ).single().execute()
        
        profile_complete = bool(user_resp.data and user_resp.data.get("onboarding_completed"))
        
        # Check if schedule exists
        schedule_resp = supabase_client.table("weekly_schedules").select("id").eq(
            "user_id", user_id
        ).eq("active", True).execute()
        
        schedule_created = len(schedule_resp.data or []) > 0
        
        # Check first workout
        workout_resp = supabase_client.table("workout_sessions").select("id").eq(
            "user_id", user_id
        ).eq("completed", True).limit(1).execute()
        
        first_workout_done = len(workout_resp.data or []) > 0
        
        step = 1
        if profile_complete:
            step = 2
        if schedule_created:
            step = 3
        if first_workout_done:
            step = 5
        
        return {
            "step": step,
            "total_steps": 5,
            "completed": step >= 5,
            "profile_complete": profile_complete,
            "schedule_created": schedule_created,
            "first_workout_done": first_workout_done
        }
        
    except Exception as e:
        return {
            "step": 1,
            "total_steps": 5,
            "completed": False,
            "profile_complete": False,
            "schedule_created": False,
            "first_workout_done": False
        }


@router.get("/suggestions")
async def get_onboarding_suggestions(current_user: dict = Depends(get_current_user)):
    """Get personalized suggestions for new users."""
    user_id = current_user["id"]
    
    try:
        user_resp = supabase_client.table("users").select("*").eq(
            "id", user_id
        ).single().execute()
        
        if not user_resp.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user_resp.data
        suggestions = []
        
        # Based on fitness level
        if user.get("fitness_level") == "beginner":
            suggestions.append({
                "type": "tip",
                "title": "Start Light",
                "description": "Focus on form over weight. A proper movement pattern is worth more than heavy lifts with bad technique."
            })
            suggestions.append({
                "type": "tip",
                "title": "Recovery Matters",
                "description": "As a beginner, your body needs more rest. Don't train the same muscle group two days in a row."
            })
        
        # Based on goal
        goal = user.get("primary_goal", "")
        if goal == "strength":
            suggestions.append({
                "type": "tip",
                "title": "Compound Movements",
                "description": "Prioritize squats, deadlifts, presses, and pulls. These give you the most strength bang for your buck."
            })
        elif goal == "conditioning":
            suggestions.append({
                "type": "tip",
                "title": "Build Your Engine",
                "description": "Include both high-intensity intervals AND low-intensity steady state. Both are important for conditioning."
            })
        
        # Always include
        suggestions.append({
            "type": "tip",
            "title": "Track Everything",
            "description": "Log your workouts consistently. You can't improve what you don't measure."
        })
        
        return {"suggestions": suggestions}
        
    except HTTPException:
        raise
    except Exception as e:
        return {"suggestions": []}
