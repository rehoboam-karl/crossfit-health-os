"""
Users API Endpoints
User profile management
"""
from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID

from app.db.supabase import supabase_client
from app.db.helpers import handle_supabase_response
from app.core.auth import get_current_user

router = APIRouter()


@router.get("/me")
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user)
):
    """Get current user profile"""
    return current_user


@router.patch("/me")
async def update_user_profile(
    updates: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update user profile"""
    user_id = UUID(current_user["id"])
    
    response = supabase_client.table("users").update(updates).eq(
        "id", str(user_id)
    ).execute()

    data = handle_supabase_response(response, "Failed to update user profile")
    return data[0]


@router.get("/stats")
async def get_user_stats(
    current_user: dict = Depends(get_current_user)
):
    """Get user statistics overview"""
    user_id = UUID(current_user["id"])
    
    # Get total workouts
    workouts = supabase_client.table("workout_sessions").select("id").eq(
        "user_id", str(user_id)
    ).execute()
    
    # Get PRs
    prs = supabase_client.table("personal_records").select("id").eq(
        "user_id", str(user_id)
    ).execute()
    
    return {
        "total_workouts": len(workouts.data) if workouts.data else 0,
        "personal_records": len(prs.data) if prs.data else 0,
        "member_since": current_user.get("created_at")
    }
