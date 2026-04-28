"""
Today's Window — cross-pillar daily card (stub).

Composes data from Training, Health, Nutrition, and Injuries into a single
response shape designers can iterate against. Real data is pulled where it's
already reachable; sections that depend on unimplemented work are returned as
explicit `mock: true` blocks so the UI knows what's placeholder.

Sections:
  - planned        (real: PlannedSession for today)
  - readiness      (real: latest RecoveryMetric + readiness formula)
  - fueling        (real: active UserDietPlan + today's MealLog totals;
                    `impact_prediction` is mocked — needs movement-level
                     history wired into the model first)
  - restrictions   (real: active Injury rows for the user; empty until UI exists)
  - post_workout   (mocked windows; needs session start_time + nutrition rules)
  - forecast       (mocked; needs HRV trend + load model)
"""
from __future__ import annotations

from datetime import date as _Date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.models import (
    Injury as InjuryDB,
    MealLog as MealLogDB,
    PlannedSession as PlannedSessionDB,
    RecoveryMetric as RecoveryMetricDB,
    UserDietPlan as UserDietPlanDB,
)
from app.db.session import get_session
from app.services.training_volume import training_volume_for_date

router = APIRouter(prefix="/api/v1/today", tags=["today"])


def _readiness(recovery: Optional[RecoveryMetricDB]) -> Dict[str, Any]:
    """Mirror of AdaptiveTrainingEngine._calculate_readiness_score, kept inline
    to avoid pulling the full engine for a read-only composition."""
    if recovery is None:
        return {
            "score": None,
            "status": "no_data",
            "banner": "No recovery data logged for today — score will be inferred from defaults.",
            "inputs": None,
        }

    hrv = recovery.hrv_ms or 50
    sleep_q = recovery.sleep_quality or 7
    stress = recovery.stress_level or 5
    soreness = recovery.muscle_soreness or 5

    hrv_norm = max(0.0, min(1.0, (hrv / 50.0 - 0.5) / 1.0))
    sleep_norm = (sleep_q - 1) / 9
    stress_norm = 1 - ((stress - 1) / 9)
    soreness_norm = 1 - ((soreness - 1) / 9)

    score = int(round(
        (hrv_norm * 0.4 + sleep_norm * 0.3 + stress_norm * 0.2 + soreness_norm * 0.1) * 100
    ))

    if score >= 80:
        status = "optimal"
    elif score >= 60:
        status = "adequate"
    elif score >= 40:
        status = "compromised"
    else:
        status = "critical"

    return {
        "score": score,
        "status": status,
        "banner": None,
        "inputs": {
            "hrv_ms": recovery.hrv_ms,
            "sleep_duration_hours": recovery.sleep_duration_hours,
            "sleep_quality": recovery.sleep_quality,
            "stress_level": recovery.stress_level,
            "muscle_soreness": recovery.muscle_soreness,
        },
    }


def _planned_sessions(db: Session, user_id: int, target_date: _Date) -> List[Dict[str, Any]]:
    rows = db.execute(
        select(PlannedSessionDB)
        .where(PlannedSessionDB.user_id == user_id, PlannedSessionDB.date == target_date)
        .order_by(PlannedSessionDB.order_in_day.asc())
    ).scalars().all()
    return [
        {
            "id": str(r.id),
            "order_in_day": r.order_in_day,
            "start_time": r.start_time.isoformat() if r.start_time else None,
            "duration_minutes": r.duration_minutes,
            "workout_type": r.workout_type,
            "focus": r.focus,
            "status": r.status,
        }
        for r in rows
    ]


def _diet_plan(db: Session, user_id: int) -> Optional[UserDietPlanDB]:
    return db.execute(
        select(UserDietPlanDB)
        .where(UserDietPlanDB.user_id == user_id, UserDietPlanDB.active.is_(True))
        .order_by(UserDietPlanDB.uploaded_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _meal_totals(db: Session, user_id: int, target_date: _Date) -> Dict[str, float]:
    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())
    rows = db.execute(
        select(MealLogDB).where(
            MealLogDB.user_id == user_id,
            MealLogDB.logged_at >= start,
            MealLogDB.logged_at <= end,
        )
    ).scalars().all()
    return {
        "calories": float(sum((m.calories or 0) for m in rows)),
        "protein_g": float(sum((m.protein_g or 0) for m in rows)),
        "carbs_g": float(sum((m.carbs_g or 0) for m in rows)),
        "fat_g": float(sum((m.fat_g or 0) for m in rows)),
        "meals_logged": len(rows),
    }


def _active_injuries(db: Session, user_id: int, target_date: _Date) -> List[Dict[str, Any]]:
    rows = db.execute(
        select(InjuryDB).where(
            InjuryDB.user_id == user_id,
            InjuryDB.started_at <= target_date,
        )
    ).scalars().all()
    active = [
        i for i in rows
        if i.resolved_at is None or i.resolved_at >= target_date
    ]
    return [
        {
            "body_part": i.body_part,
            "description": i.description,
            "restriction_tags": i.restriction_tags or [],
            "severity": i.severity,
            "started_at": i.started_at.isoformat(),
        }
        for i in active
    ]


@router.get("/window")
async def get_today_window(
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Cross-pillar composition for today's dashboard card."""
    user_id = int(current_user["id"])
    today = _Date.today()

    planned = _planned_sessions(db, user_id, today)
    recovery_row = db.execute(
        select(RecoveryMetricDB).where(
            RecoveryMetricDB.user_id == user_id,
            RecoveryMetricDB.date == today,
        )
    ).scalar_one_or_none()

    diet_plan = _diet_plan(db, user_id)
    consumed = _meal_totals(db, user_id, today)
    volume = training_volume_for_date(db, user_id, today)
    injuries = _active_injuries(db, user_id, today)

    target_carbs = diet_plan.carbs_g if diet_plan else None
    target_protein = diet_plan.protein_g if diet_plan else None
    target_calories = diet_plan.daily_calories if diet_plan else None

    return {
        "date": today.isoformat(),
        "user_id": user_id,
        "training_volume_today": volume,

        "planned": {
            "sessions": planned,
            "session_count": len(planned),
        },

        "readiness": _readiness(recovery_row),

        "fueling": {
            "targets": {
                "calories": target_calories,
                "protein_g": target_protein,
                "carbs_g": target_carbs,
                "training_aware": False,
                "note": (
                    "Targets are static from the uploaded diet plan. "
                    "Training-aware adjustment (P0 #3) not wired yet."
                ),
            },
            "consumed": consumed,
            "remaining": {
                "calories": (target_calories - consumed["calories"]) if target_calories else None,
                "protein_g": (target_protein - consumed["protein_g"]) if target_protein else None,
                "carbs_g": (target_carbs - consumed["carbs_g"]) if target_carbs else None,
            },
            "impact_prediction": {
                "mock": True,
                "message": (
                    "Predicted RPE drift from under-fueling will appear here once "
                    "movement-level history is wired into the model."
                ),
            },
        },

        "restrictions": {
            "active_injuries": injuries,
            "exclusion_tags": sorted({tag for inj in injuries for tag in (inj.get("restriction_tags") or [])}),
        },

        "post_workout": {
            "mock": True,
            "window_minutes_after_session": 60,
            "recommendation": "30g protein + 50g carbs within 60 min post-session.",
        },

        "forecast": {
            "mock": True,
            "hours_to_baseline_hrv": None,
            "next_session_outlook": "neutral",
            "message": (
                "HRV-rebound forecast requires 14d trend + load model — "
                "not implemented yet."
            ),
        },

        "_meta": {
            "stub_version": "0.1",
            "real_sections": ["planned", "readiness", "fueling.targets",
                              "fueling.consumed", "fueling.remaining",
                              "restrictions", "training_volume_today"],
            "mocked_sections": ["fueling.impact_prediction", "post_workout", "forecast"],
        },
    }
