"""
Weekly Review & Session Feedback API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from uuid import UUID
from datetime import date, timedelta

from app.models.review import (
    SessionFeedbackCreate,
    SessionFeedbackResponse,
    WeeklyReviewCreate,
    WeeklyReview
)
from app.db.supabase import supabase_client
from app.db.helpers import handle_supabase_response, handle_supabase_single
from app.core.auth import get_current_user
from app.core.engine.weekly_reviewer import weekly_reviewer
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================
# Session Feedback
# ============================================

@router.post("/feedback", response_model=SessionFeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_session_feedback(
    feedback: SessionFeedbackCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit post-workout feedback
    
    Critical data for weekly review:
    - RPE (Rate of Perceived Exertion) 1-10
    - Difficulty assessment
    - Technique quality
    - Movement-specific notes
    
    Example:
    ```json
    {
      "session_id": "uuid",
      "date": "2026-02-08",
      "rpe_score": 8,
      "difficulty": "hard_but_manageable",
      "technique_quality": 7,
      "pacing": "good",
      "energy_level_pre": 8,
      "energy_level_post": 4,
      "would_repeat": true,
      "notes": "Squats felt strong, MetCon was spicy",
      "movements_feedback": [
        {
          "movement": "back_squat",
          "prescribed_sets": 5,
          "prescribed_reps": 5,
          "prescribed_weight_kg": 112,
          "actual_sets": 5,
          "actual_reps": [5, 5, 5, 5, 4],
          "actual_weight_kg": [112, 112, 112, 112, 110],
          "technique_quality": 8,
          "notes": "Last set too heavy, dropped weight"
        }
      ]
    }
    ```
    """
    user_id = UUID(current_user["id"])
    
    # Verify session belongs to user
    session_response = supabase_client.table("workout_sessions").select("*").eq(
        "id", str(feedback.session_id)
    ).single().execute()
    
    session = handle_supabase_single(session_response, "Session not found")
    
    if session["user_id"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Save feedback
    feedback_data = feedback.model_dump(mode='json')
    feedback_data["user_id"] = str(user_id)
    feedback_data["session_id"] = str(feedback.session_id)
    
    response = supabase_client.table("session_feedback").insert(
        feedback_data
    ).execute()
    
    data = handle_supabase_response(response, "Failed to save feedback")
    
    if not data:
        raise HTTPException(status_code=500, detail="Feedback saved but no data returned")
    
    return SessionFeedbackResponse(**data[0])


@router.get("/feedback/{session_id}", response_model=SessionFeedbackResponse)
async def get_session_feedback(
    session_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Get feedback for a specific session"""
    user_id = UUID(current_user["id"])
    
    response = supabase_client.table("session_feedback").select("*").eq(
        "session_id", str(session_id)
    ).eq("user_id", str(user_id)).single().execute()
    
    data = handle_supabase_single(response, "Feedback not found")
    
    return SessionFeedbackResponse(**data)


@router.get("/feedback", response_model=List[SessionFeedbackResponse])
async def list_feedback(
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """List user's session feedback"""
    user_id = UUID(current_user["id"])
    
    response = supabase_client.table("session_feedback").select("*").eq(
        "user_id", str(user_id)
    ).order("date", desc=True).range(offset, offset + limit - 1).execute()
    
    data = handle_supabase_response(response, "Failed to fetch feedback")
    
    return [SessionFeedbackResponse(**f) for f in data]


# ============================================
# Weekly Review
# ============================================

@router.post("/weekly", response_model=WeeklyReview)
async def generate_weekly_review(
    request: WeeklyReviewCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate AI-powered weekly review
    
    Analyzes:
    - Session completion & adherence
    - RPE trends
    - Recovery metrics (HRV, sleep, readiness)
    - Movement-specific performance
    - Volume & intensity appropriateness
    
    Returns:
    - Strengths & weaknesses identified
    - Recovery status assessment
    - Specific recommendations for next week
    - Motivational coaching message
    
    Example:
    ```json
    {
      "week_number": 3,
      "week_start_date": "2026-02-03",
      "week_end_date": "2026-02-09",
      "athlete_notes": "Felt great this week. Ready to push harder."
    }
    ```
    
    Triggers automatic adjustments:
    - If recovery compromised → reduce volume next week
    - If performance plateauing → adjust focus movements
    - If technique issues → add skill work
    """
    user_id = UUID(current_user["id"])
    
    # Generate review using AI
    try:
        review = await weekly_reviewer.generate_weekly_review(
            user_id=user_id,
            week_number=request.week_number,
            week_start=request.week_start_date,
            week_end=request.week_end_date,
            athlete_notes=request.athlete_notes
        )
        
        logger.info(f"Generated weekly review for user {user_id}, week {request.week_number}")
        
        return review
        
    except Exception as e:
        logger.error(f"Failed to generate weekly review: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate review: {str(e)}"
        )


@router.get("/weekly/latest", response_model=WeeklyReview)
async def get_latest_review(
    current_user: dict = Depends(get_current_user)
):
    """Get most recent weekly review"""
    user_id = UUID(current_user["id"])
    
    response = supabase_client.table("weekly_reviews").select("*").eq(
        "user_id", str(user_id)
    ).order("created_at", desc=True).limit(1).execute()
    
    data = handle_supabase_response(response, "Failed to fetch reviews")
    
    if not data:
        raise HTTPException(status_code=404, detail="No reviews found")
    
    return WeeklyReview(**data[0])


@router.get("/weekly", response_model=List[WeeklyReview])
async def list_weekly_reviews(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """List user's weekly reviews"""
    user_id = UUID(current_user["id"])
    
    response = supabase_client.table("weekly_reviews").select("*").eq(
        "user_id", str(user_id)
    ).order("created_at", desc=True).limit(limit).execute()
    
    data = handle_supabase_response(response, "Failed to fetch reviews")
    
    return [WeeklyReview(**r) for r in data]


@router.get("/weekly/{week_number}", response_model=WeeklyReview)
async def get_review_by_week(
    week_number: int,
    current_user: dict = Depends(get_current_user)
):
    """Get review for specific week number"""
    user_id = UUID(current_user["id"])
    
    response = supabase_client.table("weekly_reviews").select("*").eq(
        "user_id", str(user_id)
    ).eq("week_number", week_number).order("created_at", desc=True).limit(1).execute()
    
    data = handle_supabase_response(response, "Failed to fetch review")
    
    if not data:
        raise HTTPException(status_code=404, detail=f"No review found for week {week_number}")
    
    return WeeklyReview(**data[0])


# ============================================
# Auto-Apply Review Adjustments
# ============================================

@router.post("/weekly/{review_id}/apply")
async def apply_review_adjustments(
    review_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Apply review recommendations to next week's program
    
    Automatically:
    1. Adjusts volume based on recovery
    2. Updates focus movements
    3. Adds skill work if recommended
    4. Modifies intensity if needed
    5. Generates next week's program with adjustments
    
    Returns the generated program for next week
    """
    user_id = UUID(current_user["id"])
    
    # Get review
    review_response = supabase_client.table("weekly_reviews").select("*").eq(
        "id", str(review_id)
    ).single().execute()
    
    review_data = handle_supabase_single(review_response, "Review not found")
    
    if review_data["user_id"] != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    review = WeeklyReview(**review_data)
    
    # Generate next week's program with adjustments
    from app.core.engine.ai_programmer import ai_programmer
    from app.models.training import Methodology, DayOfWeek
    
    # Get active schedule
    schedule_response = supabase_client.table("weekly_schedules").select("*").eq(
        "user_id", str(user_id)
    ).eq("active", True).order("created_at", desc=True).limit(1).execute()
    
    schedule_data = handle_supabase_response(schedule_response, "Failed to fetch schedule")
    
    if not schedule_data:
        raise HTTPException(status_code=404, detail="No active schedule found")
    
    # Extract training days and durations
    schedule = schedule_data[0]
    training_days = []
    session_durations = {}
    
    for day_key, day_schedule in schedule["schedule"].items():
        if not day_schedule.get("rest_day") and day_schedule.get("sessions"):
            day_enum = DayOfWeek(day_key)
            training_days.append(day_enum)
            total_duration = sum(s["duration_minutes"] for s in day_schedule["sessions"])
            session_durations[day_enum] = total_duration
    
    # Get user profile
    user_response = supabase_client.table("users").select("*").eq(
        "id", str(user_id)
    ).single().execute()
    
    user_profile = handle_supabase_response(user_response, "Failed to fetch user")
    
    # Apply adjustments
    next_week_number = review.week_number + 1
    adjustments = review.next_week_adjustments
    
    # Calculate volume modifier
    volume_modifier = 1 + (adjustments.volume_change_pct / 100)
    
    # Generate program
    try:
        next_week_program = await ai_programmer.generate_weekly_program(
            user_profile=user_profile,
            methodology=Methodology.HWPO,  # TODO: Get from schedule
            training_days=training_days,
            session_durations=session_durations,
            week_number=next_week_number,
            focus_movements=adjustments.focus_movements,
            previous_week_data={
                "review": review_data,
                "volume_modifier": volume_modifier
            }
        )
        
        # Save templates
        saved_templates = []
        for day, template in next_week_program.items():
            template_data = template.model_dump(mode='json', exclude={'id'})
            template_data["tags"] = template.tags + [f"week_{next_week_number}", "review_adjusted"]
            
            save_response = supabase_client.table("workout_templates").insert(
                template_data
            ).execute()
            
            data = handle_supabase_response(save_response, "Failed to save template")
            if data:
                saved_templates.append(data[0])
        
        return {
            "status": "success",
            "message": f"Applied week {review.week_number} review adjustments to week {next_week_number}",
            "adjustments_applied": {
                "volume_change_pct": adjustments.volume_change_pct,
                "intensity_change": adjustments.intensity_change,
                "focus_movements": adjustments.focus_movements
            },
            "workouts_generated": len(saved_templates),
            "templates": saved_templates
        }
        
    except Exception as e:
        logger.error(f"Failed to apply adjustments: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply adjustments: {str(e)}"
        )
