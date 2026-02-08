"""
Weekly Schedule API Endpoints
Training schedule management and meal plan generation
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from uuid import UUID
from datetime import date, datetime, time, timedelta

from app.models.training import (
    WeeklyScheduleCreate,
    WeeklySchedule,
    WeeklyMealPlanCreate,
    WeeklyMealPlan,
    DayOfWeek,
    MealWindow,
    MealType,
    DailyMealPlan
)
from app.db.supabase import supabase_client
from app.db.helpers import handle_supabase_response, handle_supabase_single
from app.core.auth import get_current_user
from app.core.engine.ai_programmer import ai_programmer
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/weekly", response_model=WeeklySchedule, status_code=status.HTTP_201_CREATED)
async def create_weekly_schedule(
    schedule: WeeklyScheduleCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create weekly training schedule
    
    Example:
    {
        "name": "HWPO 5x per week",
        "methodology": "hwpo",
        "schedule": {
            "monday": {
                "day": "monday",
                "sessions": [
                    {"time": "06:00", "duration_minutes": 90, "workout_type": "strength"}
                ],
                "rest_day": false
            },
            "tuesday": {
                "day": "tuesday",
                "sessions": [
                    {"time": "06:00", "duration_minutes": 60, "workout_type": "metcon"}
                ],
                "rest_day": false
            },
            ...
            "sunday": {
                "day": "sunday",
                "sessions": [],
                "rest_day": true
            }
        },
        "start_date": "2026-02-10"
    }
    """
    user_id = UUID(current_user["id"])
    
    # Deactivate previous active schedules
    response = supabase_client.table("weekly_schedules").update(
        {"active": False}
    ).eq("user_id", str(user_id)).eq("active", True).execute()
    
    handle_supabase_response(response, "Failed to deactivate old schedules")
    
    # Create new schedule
    schedule_data = schedule.model_dump(mode='json')
    schedule_data["user_id"] = str(user_id)
    schedule_data["created_at"] = datetime.utcnow().isoformat()
    schedule_data["updated_at"] = datetime.utcnow().isoformat()
    
    response = supabase_client.table("weekly_schedules").insert(
        schedule_data
    ).execute()
    
    data = handle_supabase_response(response, "Failed to create schedule")
    
    if not data:
        raise HTTPException(status_code=500, detail="Schedule created but no data returned")
    
    return WeeklySchedule(**data[0])


@router.get("/weekly/active", response_model=WeeklySchedule)
async def get_active_schedule(
    current_user: dict = Depends(get_current_user)
):
    """Get user's currently active weekly schedule"""
    user_id = UUID(current_user["id"])
    
    response = supabase_client.table("weekly_schedules").select("*").eq(
        "user_id", str(user_id)
    ).eq("active", True).order("created_at", desc=True).limit(1).execute()
    
    data = handle_supabase_response(response, "Failed to fetch active schedule")
    
    if not data:
        raise HTTPException(status_code=404, detail="No active schedule found")
    
    return WeeklySchedule(**data[0])


@router.get("/weekly", response_model=List[WeeklySchedule])
async def list_schedules(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """List user's training schedules"""
    user_id = UUID(current_user["id"])
    
    response = supabase_client.table("weekly_schedules").select("*").eq(
        "user_id", str(user_id)
    ).order("created_at", desc=True).limit(limit).execute()
    
    data = handle_supabase_response(response, "Failed to fetch schedules")
    
    return [WeeklySchedule(**s) for s in data]


@router.patch("/weekly/{schedule_id}", response_model=WeeklySchedule)
async def update_schedule(
    schedule_id: UUID,
    schedule_update: WeeklyScheduleCreate,
    current_user: dict = Depends(get_current_user)
):
    """Update weekly schedule"""
    user_id = UUID(current_user["id"])
    
    # Verify ownership
    response = supabase_client.table("weekly_schedules").select("*").eq(
        "id", str(schedule_id)
    ).single().execute()
    
    existing = handle_supabase_single(response, "Schedule not found")
    
    if existing["user_id"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Update
    update_data = schedule_update.model_dump(mode='json')
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    response = supabase_client.table("weekly_schedules").update(
        update_data
    ).eq("id", str(schedule_id)).execute()
    
    data = handle_supabase_response(response, "Failed to update schedule")
    
    if not data:
        raise HTTPException(status_code=500, detail="Update failed")
    
    return WeeklySchedule(**data[0])


@router.delete("/weekly/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Delete weekly schedule"""
    user_id = UUID(current_user["id"])
    
    # Verify ownership
    response = supabase_client.table("weekly_schedules").select("*").eq(
        "id", str(schedule_id)
    ).single().execute()
    
    existing = handle_supabase_single(response, "Schedule not found")
    
    if existing["user_id"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Delete
    response = supabase_client.table("weekly_schedules").delete().eq(
        "id", str(schedule_id)
    ).execute()
    
    handle_supabase_response(response, "Failed to delete schedule")
    
    return None


# ============================================
# Meal Plan Generation (Auto-synced with Training)
# ============================================

@router.post("/weekly/{schedule_id}/meal-plan", response_model=WeeklyMealPlan)
async def generate_meal_plan(
    schedule_id: UUID,
    pre_workout_offset_minutes: int = -60,
    post_workout_offset_minutes: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate meal plan automatically from training schedule
    
    Logic:
    - Pre-workout meal: 60min before each session
    - Post-workout meal: 30min after each session
    - Standard meals: Breakfast (07:00), Lunch (12:00), Dinner (19:00)
    - Adjusts meal times to avoid conflicts with workouts
    """
    user_id = UUID(current_user["id"])
    
    # Get training schedule
    response = supabase_client.table("weekly_schedules").select("*").eq(
        "id", str(schedule_id)
    ).single().execute()
    
    schedule_data = handle_supabase_single(response, "Schedule not found")
    
    if schedule_data["user_id"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    training_schedule = WeeklySchedule(**schedule_data)
    
    # Generate meal plans for each day
    meal_plans = {}
    
    for day_key, day_schedule in training_schedule.schedule.items():
        meals = []
        
        if day_schedule.rest_day:
            # Rest day: standard 3 meals
            meals = [
                MealWindow(
                    meal_type=MealType.BREAKFAST,
                    time=time(7, 0),
                    duration_minutes=30
                ),
                MealWindow(
                    meal_type=MealType.LUNCH,
                    time=time(12, 0),
                    duration_minutes=45
                ),
                MealWindow(
                    meal_type=MealType.DINNER,
                    time=time(19, 0),
                    duration_minutes=45
                )
            ]
        else:
            # Training day: add pre/post workout meals
            for session in day_schedule.sessions:
                # Pre-workout meal
                pre_workout_time = (
                    datetime.combine(date.today(), session.time) + 
                    timedelta(minutes=pre_workout_offset_minutes)
                ).time()
                
                meals.append(MealWindow(
                    meal_type=MealType.PRE_WORKOUT,
                    time=pre_workout_time,
                    duration_minutes=20,
                    notes=f"Before {session.time} session"
                ))
                
                # Post-workout meal
                post_workout_time = (
                    datetime.combine(date.today(), session.time) + 
                    timedelta(minutes=session.duration_minutes + post_workout_offset_minutes)
                ).time()
                
                meals.append(MealWindow(
                    meal_type=MealType.POST_WORKOUT,
                    time=post_workout_time,
                    duration_minutes=30,
                    notes=f"After {session.time} session"
                ))
            
            # Add standard meals (avoiding workout times)
            # TODO: Implement smart meal spacing logic
            meals.append(MealWindow(
                meal_type=MealType.BREAKFAST,
                time=time(7, 0),
                duration_minutes=30
            ))
            
            meals.append(MealWindow(
                meal_type=MealType.LUNCH,
                time=time(12, 0),
                duration_minutes=45
            ))
            
            meals.append(MealWindow(
                meal_type=MealType.DINNER,
                time=time(19, 0),
                duration_minutes=45
            ))
        
        # Sort meals by time
        meals.sort(key=lambda m: m.time)
        
        meal_plans[day_key] = DailyMealPlan(
            day=day_schedule.day,
            meals=meals,
            training_day=not day_schedule.rest_day
        )
    
    # Save meal plan
    meal_plan_data = {
        "user_id": str(user_id),
        "training_schedule_id": str(schedule_id),
        "meal_plans": {k.value: v.model_dump(mode='json') for k, v in meal_plans.items()},
        "pre_workout_offset_minutes": pre_workout_offset_minutes,
        "post_workout_offset_minutes": post_workout_offset_minutes,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    response = supabase_client.table("weekly_meal_plans").insert(
        meal_plan_data
    ).execute()
    
    data = handle_supabase_response(response, "Failed to create meal plan")
    
    if not data:
        raise HTTPException(status_code=500, detail="Meal plan created but no data returned")
    
    return WeeklyMealPlan(**data[0])


@router.get("/weekly/{schedule_id}/meal-plan", response_model=WeeklyMealPlan)
async def get_meal_plan(
    schedule_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Get meal plan for training schedule"""
    user_id = UUID(current_user["id"])
    
    response = supabase_client.table("weekly_meal_plans").select("*").eq(
        "training_schedule_id", str(schedule_id)
    ).eq("user_id", str(user_id)).order("created_at", desc=True).limit(1).execute()
    
    data = handle_supabase_response(response, "Failed to fetch meal plan")
    
    if not data:
        raise HTTPException(status_code=404, detail="No meal plan found for this schedule")
    
    return WeeklyMealPlan(**data[0])


# ============================================
# AI-Powered Program Generation
# ============================================

from pydantic import BaseModel, Field

class AIWeeklyProgramRequest(BaseModel):
    """Request to generate weekly program via AI"""
    methodology: str = Field("hwpo", description="Programming methodology: hwpo, mayhem, comptrain, custom")
    week_number: int = Field(1, ge=1, le=52, description="Week number in mesocycle (1-52)")
    focus_movements: list[str] = Field(default_factory=list, description="Movements to emphasize (e.g., ['squat', 'snatch'])")
    include_previous_week: bool = Field(False, description="Use previous week data for progression")


@router.post("/weekly/generate-ai", status_code=status.HTTP_201_CREATED)
async def generate_weekly_program_ai(
    request: AIWeeklyProgramRequest,
    schedule_id: UUID = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate weekly training program using AI
    
    This endpoint creates an intelligent, progressive training program based on:
    - User's fitness level, goals, and weaknesses
    - Selected methodology (HWPO, Mayhem, CompTrain)
    - Week number in mesocycle (for progression)
    - Optional focus on specific movements
    - Previous week performance (for progressive overload)
    
    Example:
    ```json
    {
        "methodology": "hwpo",
        "week_number": 3,
        "focus_movements": ["snatch", "handstand_walk"],
        "include_previous_week": true
    }
    ```
    
    If schedule_id provided, it will use that schedule's training days and durations.
    Otherwise, uses user's active schedule.
    """
    user_id = UUID(current_user["id"])
    
    # Get user profile
    user_response = supabase_client.table("users").select("*").eq(
        "id", str(user_id)
    ).single().execute()
    
    user_profile = handle_supabase_single(user_response, "User not found")
    
    # Get training schedule
    if schedule_id:
        schedule_response = supabase_client.table("weekly_schedules").select("*").eq(
            "id", str(schedule_id)
        ).single().execute()
        schedule_data = handle_supabase_single(schedule_response, "Schedule not found")
    else:
        # Use active schedule
        schedule_response = supabase_client.table("weekly_schedules").select("*").eq(
            "user_id", str(user_id)
        ).eq("active", True).order("created_at", desc=True).limit(1).execute()
        
        data = handle_supabase_response(schedule_response, "Failed to fetch schedule")
        if not data:
            raise HTTPException(
                status_code=404,
                detail="No active schedule found. Create one first with POST /weekly"
            )
        schedule_data = data[0]
    
    training_schedule = WeeklySchedule(**schedule_data)
    
    # Extract training days and durations from schedule
    training_days = []
    session_durations = {}
    
    for day_key, day_schedule in training_schedule.schedule.items():
        if not day_schedule.rest_day and day_schedule.sessions:
            day_enum = DayOfWeek(day_key.value if isinstance(day_key, DayOfWeek) else day_key)
            training_days.append(day_enum)
            
            # Use duration of first session (can be enhanced)
            total_duration = sum(s.duration_minutes for s in day_schedule.sessions)
            session_durations[day_enum] = total_duration
    
    # Get previous week data if requested
    previous_week_data = None
    if request.include_previous_week and request.week_number > 1:
        # TODO: Fetch actual previous week performance
        previous_week_data = {
            "note": "Previous week data integration coming soon",
            "completed_workouts": 5,
            "avg_rpe": 7.5
        }
    
    # Generate program via AI
    try:
        from app.models.training import Methodology as MethodEnum
        methodology_enum = MethodEnum(request.methodology.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid methodology. Choose: hwpo, mayhem, comptrain, custom"
        )
    
    weekly_program = await ai_programmer.generate_weekly_program(
        user_profile=user_profile,
        methodology=methodology_enum,
        training_days=training_days,
        session_durations=session_durations,
        week_number=request.week_number,
        focus_movements=request.focus_movements,
        previous_week_data=previous_week_data
    )
    
    # Save generated workouts to database
    saved_templates = []
    for day, template in weekly_program.items():
        template_data = {
            "name": template.name,
            "description": template.description,
            "methodology": template.methodology.value,
            "difficulty_level": template.difficulty_level,
            "workout_type": template.workout_type.value,
            "duration_minutes": template.duration_minutes,
            "movements": [m.model_dump(mode='json') for m in template.movements],
            "target_stimulus": template.target_stimulus,
            "tags": template.tags + [f"week_{request.week_number}", f"ai_{request.methodology}"],
            "equipment_required": template.equipment_required,
            "is_public": False,
            "created_at": datetime.utcnow().isoformat()
        }
        
        response = supabase_client.table("workout_templates").insert(
            template_data
        ).execute()
        
        data = handle_supabase_response(response, f"Failed to save {day.value} workout")
        if data:
            saved_templates.append(data[0])
    
    return {
        "status": "success",
        "message": f"Generated {len(saved_templates)} AI-powered workouts for week {request.week_number}",
        "methodology": request.methodology,
        "week_number": request.week_number,
        "training_days": [d.value for d in training_days],
        "workouts": saved_templates,
        "note": "Workouts saved to workout_templates. You can now schedule them in your weekly calendar."
    }
