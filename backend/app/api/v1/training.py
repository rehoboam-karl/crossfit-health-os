"""
Training API — workout generation, session tracking, personal records (SQLAlchemy).
"""
from datetime import date as _Date, datetime as _Datetime, timedelta
from typing import List, Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.engine.adaptive import adaptive_engine
from app.db.models import (
    PersonalRecord as PersonalRecordDB,
    WorkoutSession as WorkoutSessionDB,
    WorkoutTemplate as WorkoutTemplateDB,
)
from app.db.session import get_session
from app.models.training import (
    AdaptiveWorkoutResponse,
    PersonalRecord,
    PersonalRecordCreate,
    Movement,
    Methodology,
    WorkoutGenerationRequest,
    WorkoutSession,
    WorkoutSessionCreate,
    WorkoutSessionUpdate,
    WorkoutTemplate,
    WorkoutType,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _ws_to_schema(row: WorkoutSessionDB) -> WorkoutSession:
    return WorkoutSession(
        id=row.id,
        user_id=row.user_id,
        template_id=row.template_id,
        scheduled_at=row.scheduled_at,
        started_at=row.started_at,
        completed_at=row.completed_at,
        duration_minutes=row.duration_minutes,
        workout_type=WorkoutType(row.workout_type),
        movements=[],  # shell entity keeps movements elsewhere for now
        score=row.score,
        rpe_score=row.rpe_score,
        notes=row.notes,
    )


def _pr_to_schema(row: PersonalRecordDB) -> PersonalRecord:
    return PersonalRecord(
        id=row.id,
        user_id=row.user_id,
        movement_name=row.movement_name,
        record_type=row.record_type,
        value=row.value,
        unit=row.unit,
        notes=row.notes,
        video_url=row.video_url,
        achieved_at=row.achieved_at,
        session_id=row.session_id,
    )


def _template_to_schema(row: WorkoutTemplateDB) -> WorkoutTemplate:
    return WorkoutTemplate(
        id=row.id,
        name=row.name,
        description=row.description,
        methodology=Methodology(row.methodology),
        difficulty_level=row.difficulty_level,
        workout_type=WorkoutType(row.workout_type),
        duration_minutes=row.duration_minutes,
        movements=[Movement(**m) for m in (row.movements or [])],
        target_stimulus=row.target_stimulus,
        rep_scheme=row.rep_scheme,
        tags=row.tags or [],
        equipment_required=row.equipment_required or [],
        video_url=None,
        created_at=row.created_at,
        is_public=row.is_public,
    )


# ==========================================================
# Adaptive workout generation
# ==========================================================

@router.post("/generate", response_model=AdaptiveWorkoutResponse)
async def generate_adaptive_workout(
    request: WorkoutGenerationRequest,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Generate an adaptive workout adjusted for today's readiness."""
    user_id = request.user_id if request.user_id is not None else int(current_user["id"])
    target_date = request.date or _Date.today()
    try:
        return await adaptive_engine.generate_workout(
            db=db, user_id=user_id, target_date=target_date, force_rest=request.force_rest
        )
    except Exception as e:
        logger.error(f"generate_adaptive_workout failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate workout: {e}")


@router.get("/workouts/today", response_model=AdaptiveWorkoutResponse)
async def get_todays_workout(
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    return await adaptive_engine.generate_workout(
        db=db, user_id=user_id, target_date=_Date.today(), force_rest=False
    )


# ==========================================================
# Workout sessions
# ==========================================================

@router.post("/sessions", response_model=WorkoutSession, status_code=status.HTTP_201_CREATED)
async def create_workout_session(
    payload: WorkoutSessionCreate,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    row = WorkoutSessionDB(
        user_id=user_id,
        template_id=payload.template_id,
        scheduled_at=payload.scheduled_at,
        started_at=_Datetime.utcnow(),
        workout_type=payload.workout_type.value,
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _ws_to_schema(row)


@router.patch("/sessions/{session_id}", response_model=WorkoutSession)
async def complete_workout_session(
    session_id: UUID,
    update: WorkoutSessionUpdate,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    row = db.get(WorkoutSessionDB, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    if row.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    data = update.model_dump(exclude_unset=True, mode="python")
    # Scalar fields only — drop legacy dict-shaped fields.
    for skip in ("actual_weight_kg", "actual_reps", "muscle_groups_worked", "video_url"):
        data.pop(skip, None)
    if "score_type" in data and hasattr(data["score_type"], "value"):
        data["score_type"] = data["score_type"].value
    for k, v in data.items():
        if hasattr(row, k):
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _ws_to_schema(row)


@router.get("/sessions", response_model=List[WorkoutSession])
async def list_workout_sessions(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    rows = db.execute(
        select(WorkoutSessionDB)
        .where(WorkoutSessionDB.user_id == user_id)
        .order_by(WorkoutSessionDB.started_at.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()
    return [_ws_to_schema(r) for r in rows]


@router.get("/sessions/{session_id}", response_model=WorkoutSession)
async def get_workout_session(
    session_id: UUID,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    row = db.get(WorkoutSessionDB, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    if row.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return _ws_to_schema(row)


# ==========================================================
# Personal records
# ==========================================================

@router.post("/prs", response_model=PersonalRecord, status_code=status.HTTP_201_CREATED)
async def create_personal_record(
    pr: PersonalRecordCreate,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    # Upsert on (user_id, movement_name, record_type)
    existing = db.execute(
        select(PersonalRecordDB).where(
            PersonalRecordDB.user_id == user_id,
            PersonalRecordDB.movement_name == pr.movement_name,
            PersonalRecordDB.record_type == pr.record_type.value,
        )
    ).scalar_one_or_none()
    if existing:
        existing.value = pr.value
        existing.unit = pr.unit
        existing.notes = pr.notes
        existing.video_url = pr.video_url
        existing.achieved_at = _Datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return _pr_to_schema(existing)

    row = PersonalRecordDB(
        user_id=user_id,
        movement_name=pr.movement_name,
        record_type=pr.record_type.value,
        value=pr.value,
        unit=pr.unit,
        notes=pr.notes,
        video_url=pr.video_url,
        achieved_at=_Datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _pr_to_schema(row)


@router.get("/prs", response_model=List[PersonalRecord])
async def list_personal_records(
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    rows = db.execute(
        select(PersonalRecordDB)
        .where(PersonalRecordDB.user_id == user_id)
        .order_by(PersonalRecordDB.achieved_at.desc())
    ).scalars().all()
    return [_pr_to_schema(r) for r in rows]


# ==========================================================
# Templates (public)
# ==========================================================

@router.get("/templates", response_model=List[WorkoutTemplate])
async def list_workout_templates(
    methodology: Optional[str] = None,
    workout_type: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_session),
):
    stmt = select(WorkoutTemplateDB).where(WorkoutTemplateDB.is_public.is_(True))
    if methodology:
        stmt = stmt.where(WorkoutTemplateDB.methodology == methodology)
    if workout_type:
        stmt = stmt.where(WorkoutTemplateDB.workout_type == workout_type)
    stmt = stmt.limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [_template_to_schema(r) for r in rows]


# ==========================================================
# Training stats summary
# ==========================================================

@router.get("/stats/summary")
async def get_training_summary(
    days: int = 30,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    from_date = _Datetime.utcnow() - timedelta(days=days)
    rows = db.execute(
        select(WorkoutSessionDB).where(
            and_(
                WorkoutSessionDB.user_id == user_id,
                WorkoutSessionDB.started_at >= from_date,
            )
        )
    ).scalars().all()

    if not rows:
        return {
            "total_workouts": 0,
            "avg_duration_minutes": 0,
            "avg_rpe": 0,
            "workout_types": {},
            "period_days": days,
        }

    total = len(rows)
    avg_duration = sum((r.duration_minutes or 0) for r in rows) / total
    rpes = [r.rpe_score for r in rows if r.rpe_score is not None]
    avg_rpe = sum(rpes) / len(rpes) if rpes else 0

    types: dict[str, int] = {}
    for r in rows:
        types[r.workout_type] = types.get(r.workout_type, 0) + 1

    return {
        "total_workouts": total,
        "avg_duration_minutes": round(avg_duration, 1),
        "avg_rpe": round(avg_rpe, 1),
        "workout_types": types,
        "period_days": days,
    }
