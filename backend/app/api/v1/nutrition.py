"""
Nutrition API Endpoints
Meal logging, macro tracking
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from uuid import UUID

from app.db.supabase import supabase_client
from app.core.auth import get_current_user

router = APIRouter()


@router.post("/meals")
async def log_meal(
    meal_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Log a meal with macros"""
    user_id = UUID(current_user["id"])
    
    meal_data["user_id"] = str(user_id)
    
    response = supabase_client.table("meal_logs").insert(meal_data).execute()
    
    return response.data[0] if response.data else {}


@router.get("/meals/today")
async def get_todays_meals(
    current_user: dict = Depends(get_current_user)
):
    """Get today's meals"""
    user_id = UUID(current_user["id"])
    
    from datetime import datetime, timedelta
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
    
    response = supabase_client.table("meal_logs").select("*").eq(
        "user_id", str(user_id)
    ).gte("logged_at", today_start.isoformat()).execute()
    
    return response.data


@router.get("/macros/summary")
async def get_macro_summary(
    current_user: dict = Depends(get_current_user)
):
    """Get today's macro summary"""
    meals = await get_todays_meals(current_user)
    
    total_calories = sum(m.get("calories", 0) or 0 for m in meals)
    total_protein = sum(m.get("protein_g", 0) or 0 for m in meals)
    total_carbs = sum(m.get("carbs_g", 0) or 0 for m in meals)
    total_fat = sum(m.get("fat_g", 0) or 0 for m in meals)
    
    return {
        "calories": total_calories,
        "protein_g": total_protein,
        "carbs_g": total_carbs,
        "fat_g": total_fat,
        "meals_logged": len(meals)
    }
