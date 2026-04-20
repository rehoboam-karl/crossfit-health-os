"""
Nutrition API — meal logging and macro tracking (SQLAlchemy).
"""
from datetime import datetime as _Datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.models import MealLog as MealLogDB
from app.db.session import get_session

router = APIRouter()


def _meal_to_dict(row: MealLogDB) -> dict:
    return {
        "id": str(row.id),
        "user_id": row.user_id,
        "logged_at": row.logged_at.isoformat() if row.logged_at else None,
        "meal_type": row.meal_type,
        "description": row.description,
        "calories": row.calories,
        "protein_g": row.protein_g,
        "carbs_g": row.carbs_g,
        "fat_g": row.fat_g,
        "fiber_g": row.fiber_g,
        "foods": row.foods or [],
        "photo_url": row.photo_url,
        "ai_estimation": row.ai_estimation,
        "notes": row.notes,
    }


@router.post("/meals")
async def log_meal(
    meal_data: dict,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Log a meal with macros."""
    user_id = int(current_user["id"])

    logged_at = meal_data.get("logged_at")
    if isinstance(logged_at, str):
        try:
            logged_at = _Datetime.fromisoformat(logged_at.replace("Z", "+00:00"))
        except ValueError:
            logged_at = _Datetime.utcnow()
    if logged_at is None:
        logged_at = _Datetime.utcnow()
    # SQLite doesn't store tz-awareness well; drop tz for consistency
    if logged_at.tzinfo is not None:
        logged_at = logged_at.replace(tzinfo=None)

    row = MealLogDB(
        user_id=user_id,
        logged_at=logged_at,
        meal_type=meal_data.get("meal_type"),
        description=meal_data.get("description"),
        calories=meal_data.get("calories"),
        protein_g=meal_data.get("protein_g"),
        carbs_g=meal_data.get("carbs_g"),
        fat_g=meal_data.get("fat_g"),
        fiber_g=meal_data.get("fiber_g"),
        foods=meal_data.get("foods") or [],
        photo_url=meal_data.get("photo_url"),
        ai_estimation=bool(meal_data.get("ai_estimation", False)),
        notes=meal_data.get("notes"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _meal_to_dict(row)


def _fetch_todays_meals(db: Session, user_id: int) -> list[MealLogDB]:
    today_start = _Datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return db.execute(
        select(MealLogDB).where(
            MealLogDB.user_id == user_id,
            MealLogDB.logged_at >= today_start,
        )
    ).scalars().all()


@router.get("/meals/today")
async def get_todays_meals(
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    rows = _fetch_todays_meals(db, user_id)
    return [_meal_to_dict(r) for r in rows]


@router.get("/macros/summary")
async def get_macro_summary(
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    rows = _fetch_todays_meals(db, user_id)
    total_calories = sum((r.calories or 0) for r in rows)
    total_protein = sum((r.protein_g or 0) for r in rows)
    total_carbs = sum((r.carbs_g or 0) for r in rows)
    total_fat = sum((r.fat_g or 0) for r in rows)
    return {
        "calories": total_calories,
        "protein_g": total_protein,
        "carbs_g": total_carbs,
        "fat_g": total_fat,
        "meals_logged": len(rows),
    }
