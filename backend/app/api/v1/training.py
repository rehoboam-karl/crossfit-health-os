"""
Training API Endpoints
Workout generation, session tracking, PRs
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from uuid import UUID
from datetime import date, datetime, timedelta

from app.models.training import (
    WorkoutGenerationRequest,
    AdaptiveWorkoutResponse,
    WorkoutSessionCreate,
    WorkoutSession,
    WorkoutSessionUpdate,
    PersonalRecordCreate,
    PersonalRecord,
    WorkoutTemplate
)
from app.core.engine.adaptive import adaptive_engine
from app.db.supabase import supabase_client
from app.db.helpers import handle_supabase_response, handle_supabase_single
from app.core.auth import get_current_user

router = APIRouter()


@router.post("/generate", response_model=AdaptiveWorkoutResponse)
async def generate_adaptive_workout(
    request: WorkoutGenerationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate adaptive workout based on recovery metrics
    
    The core intelligence of the system:
    1. Analyzes HRV, sleep, stress, soreness
    2. Calculates readiness score (0-100)
    3. Adjusts volume accordingly
    4. Returns customized workout
    """
    try:
        workout = await adaptive_engine.generate_workout(
            user_id=request.user_id,
            target_date=request.date,
            force_rest=request.force_rest
        )
        return workout
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate workout: {str(e)}"
        )


@router.get("/workouts/today", response_model=AdaptiveWorkoutResponse)
async def get_todays_workout(
    current_user: dict = Depends(get_current_user)
):
    """Get today's adaptive workout for current user"""
    user_id = UUID(current_user["id"])
    
    workout = await adaptive_engine.generate_workout(
        user_id=user_id,
        target_date=date.today(),
        force_rest=False
    )
    
    return workout


@router.post("/sessions", response_model=WorkoutSession, status_code=status.HTTP_201_CREATED)
async def create_workout_session(
    session: WorkoutSessionCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Start a new workout session
    Records when user begins a workout
    """
    user_id = UUID(current_user["id"])
    
    session_data = session.model_dump()
    session_data["user_id"] = str(user_id)
    session_data["started_at"] = datetime.utcnow().isoformat()
    
    response = supabase_client.table("workout_sessions").insert(
        session_data
    ).execute()

    data = handle_supabase_response(response, "Failed to create workout session")
    return WorkoutSession(**data[0])


@router.patch("/sessions/{session_id}", response_model=WorkoutSession)
async def complete_workout_session(
    session_id: UUID,
    update: WorkoutSessionUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Complete workout session
    Updates with final performance metrics
    """
    user_id = UUID(current_user["id"])
    
    # Verify session belongs to user
    session_response = supabase_client.table("workout_sessions").select("*").eq(
        "id", str(session_id)
    ).single().execute()

    session_data = handle_supabase_single(session_response, "Session not found")

    if session_data["user_id"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Update session with authorization check
    update_data = update.model_dump(exclude_unset=True)

    response = supabase_client.table("workout_sessions").update(
        update_data
    ).eq("id", str(session_id)).eq("user_id", str(user_id)).execute()

    data = handle_supabase_response(response, "Failed to update workout session")
    return WorkoutSession(**data[0])


@router.get("/sessions", response_model=List[WorkoutSession])
async def list_workout_sessions(
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """List user's workout sessions"""
    user_id = UUID(current_user["id"])
    
    response = supabase_client.table("workout_sessions").select("*").eq(
        "user_id", str(user_id)
    ).order("started_at", desc=True).range(offset, offset + limit - 1).execute()
    
    return [WorkoutSession(**session) for session in response.data]


@router.get("/sessions/{session_id}", response_model=WorkoutSession)
async def get_workout_session(
    session_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Get specific workout session"""
    user_id = UUID(current_user["id"])
    
    response = supabase_client.table("workout_sessions").select("*").eq(
        "id", str(session_id)
    ).single().execute()

    session_data = handle_supabase_single(response, "Session not found")

    if session_data["user_id"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    return WorkoutSession(**session_data)


@router.post("/prs", response_model=PersonalRecord, status_code=status.HTTP_201_CREATED)
async def create_personal_record(
    pr: PersonalRecordCreate,
    current_user: dict = Depends(get_current_user)
):
    """Record a new personal record"""
    user_id = UUID(current_user["id"])
    
    pr_data = pr.model_dump()
    pr_data["user_id"] = str(user_id)
    pr_data["achieved_at"] = datetime.utcnow().isoformat()
    
    response = supabase_client.table("personal_records").upsert(
        pr_data,
        on_conflict="user_id,movement_name,record_type"
    ).execute()

    data = handle_supabase_response(response, "Failed to record personal record")
    return PersonalRecord(**data[0])


@router.get("/prs", response_model=List[PersonalRecord])
async def list_personal_records(
    current_user: dict = Depends(get_current_user)
):
    """List user's personal records"""
    user_id = UUID(current_user["id"])
    
    response = supabase_client.table("personal_records").select("*").eq(
        "user_id", str(user_id)
    ).order("achieved_at", desc=True).execute()
    
    return [PersonalRecord(**pr) for pr in response.data]


@router.get("/templates", response_model=List[WorkoutTemplate])
async def list_workout_templates(
    methodology: str = None,
    workout_type: str = None,
    limit: int = 50
):
    """List public workout templates"""
    query = supabase_client.table("workout_templates").select("*").eq("is_public", True)
    
    if methodology:
        query = query.eq("methodology", methodology)
    if workout_type:
        query = query.eq("workout_type", workout_type)
    
    response = query.limit(limit).execute()
    
    return [WorkoutTemplate(**template) for template in response.data]


@router.get("/stats/summary")
async def get_training_summary(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """
    Get training summary statistics
    - Total workouts
    - Average duration
    - Average RPE
    - Workout type distribution
    """
    user_id = UUID(current_user["id"])
    
    from_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    response = supabase_client.table("workout_sessions").select("*").eq(
        "user_id", str(user_id)
    ).gte("started_at", from_date).execute()
    
    sessions = response.data
    
    if not sessions:
        return {
            "total_workouts": 0,
            "avg_duration_minutes": 0,
            "avg_rpe": 0,
            "workout_types": {}
        }
    
    # Calculate stats
    total = len(sessions)
    avg_duration = sum(s.get("duration_minutes", 0) or 0 for s in sessions) / total
    
    rpe_scores = [s.get("rpe_score") for s in sessions if s.get("rpe_score")]
    avg_rpe = sum(rpe_scores) / len(rpe_scores) if rpe_scores else 0
    
    # Workout type distribution
    workout_types = {}
    for session in sessions:
        wtype = session.get("workout_type")
        workout_types[wtype] = workout_types.get(wtype, 0) + 1
    
    return {
        "total_workouts": total,
        "avg_duration_minutes": round(avg_duration, 1),
        "avg_rpe": round(avg_rpe, 1),
        "workout_types": workout_types,
        "period_days": days
    }
