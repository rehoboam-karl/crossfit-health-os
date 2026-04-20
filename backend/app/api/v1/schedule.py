"""
Scheduling API — macrocycles, microcycles, and planned sessions (SQLAlchemy).
"""
from __future__ import annotations

from datetime import date as _Date, datetime as _Datetime, time as _Time, timedelta
from typing import List, Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.datetime_utils import snap_to_monday, user_today
from app.core.engine.periodization import (
    default_block_plan_for,
    resolve_block_and_week_in_block,
    total_weeks,
)
from app.db.models import (
    Macrocycle as MacrocycleDB,
    Microcycle as MicrocycleDB,
    PlannedSession as PlannedSessionDB,
)
from app.db.session import get_session
from app.models.training import (
    BlockPlanItem,
    Macrocycle,
    MacrocycleCreate,
    MacrocycleUpdate,
    MacrocycleWithMicrocycles,
    Methodology,
    Microcycle,
    MicrocycleUpdate,
    PlannedSession,
    PlannedSessionCreate,
    PlannedSessionUpdate,
    PlannedSessionStatus,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ==========================================================
# Helpers
# ==========================================================

def _serialize_block_plan(plan: List[BlockPlanItem]) -> list[dict]:
    return [{"type": b.type.value, "weeks": b.weeks} for b in plan]


def _parse_block_plan(raw: list[dict] | None) -> list[BlockPlanItem]:
    if not raw:
        return []
    return [BlockPlanItem(type=item["type"], weeks=item["weeks"]) for item in raw]


def _to_macro_schema(macro: MacrocycleDB, block_plan: List[BlockPlanItem]) -> Macrocycle:
    return Macrocycle(
        id=macro.id,
        user_id=macro.user_id,
        name=macro.name,
        methodology=Methodology(macro.methodology),
        start_date=macro.start_date,
        end_date=macro.end_date,
        block_plan=block_plan,
        goal=macro.goal,
        active=macro.active,
        created_at=macro.created_at,
        updated_at=macro.updated_at,
    )


def _to_micro_schema(
    micro: MicrocycleDB,
    block_plan: List[BlockPlanItem],
    sessions: Optional[list[PlannedSessionDB]] = None,
) -> Microcycle:
    block_type, week_in_block, _ = resolve_block_and_week_in_block(
        block_plan, micro.week_index_in_macro
    )
    session_schemas = [_to_session_schema(s) for s in (sessions or [])]
    return Microcycle(
        id=micro.id,
        macrocycle_id=micro.macrocycle_id,
        user_id=micro.user_id,
        start_date=micro.start_date,
        end_date=micro.end_date,
        week_index_in_macro=micro.week_index_in_macro,
        intensity_target=micro.intensity_target,
        volume_target=micro.volume_target,
        notes=micro.notes,
        created_at=micro.created_at,
        block_type=block_type,
        week_index_in_block=week_in_block,
        sessions=session_schemas,
    )


def _load_micro_sessions(db: Session, micro_id: UUID) -> list[PlannedSessionDB]:
    return db.execute(
        select(PlannedSessionDB)
        .where(PlannedSessionDB.microcycle_id == micro_id)
        .order_by(PlannedSessionDB.date, PlannedSessionDB.order_in_day)
    ).scalars().all()


def _to_session_schema(session: PlannedSessionDB) -> PlannedSession:
    return PlannedSession(
        id=session.id,
        microcycle_id=session.microcycle_id,
        user_id=session.user_id,
        date=session.date,
        order_in_day=session.order_in_day,
        shift=session.shift,
        start_time=session.start_time,
        duration_minutes=session.duration_minutes,
        workout_type=session.workout_type,
        focus=session.focus,
        notes=session.notes,
        status=session.status,
        generated_template_id=session.generated_template_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _get_owned_macro(session: Session, macro_id: UUID, user_id: int) -> MacrocycleDB:
    macro = session.get(MacrocycleDB, macro_id)
    if not macro:
        raise HTTPException(status_code=404, detail="Macrocycle not found")
    if macro.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return macro


def _get_owned_micro(session: Session, micro_id: UUID, user_id: int) -> MicrocycleDB:
    micro = session.get(MicrocycleDB, micro_id)
    if not micro:
        raise HTTPException(status_code=404, detail="Microcycle not found")
    if micro.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return micro


# ==========================================================
# Macrocycles
# ==========================================================

@router.post("/macrocycles", response_model=MacrocycleWithMicrocycles, status_code=status.HTTP_201_CREATED)
async def create_macrocycle(
    payload: MacrocycleCreate,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Create a macrocycle and eagerly materialize its microcycles."""
    user_id = int(current_user["id"])

    block_plan: List[BlockPlanItem] = payload.block_plan or default_block_plan_for(payload.methodology)
    if not block_plan:
        raise HTTPException(
            status_code=400,
            detail="Custom methodology requires a non-empty block_plan",
        )

    weeks_total = total_weeks(block_plan)
    if weeks_total <= 0:
        raise HTTPException(status_code=400, detail="block_plan must sum to at least 1 week")

    start_monday = snap_to_monday(payload.start_date)
    end_date = start_monday + timedelta(days=weeks_total * 7 - 1)

    # Deactivate any existing active macrocycle.
    for existing in session.execute(
        select(MacrocycleDB).where(MacrocycleDB.user_id == user_id, MacrocycleDB.active.is_(True))
    ).scalars().all():
        existing.active = False

    macro = MacrocycleDB(
        user_id=user_id,
        name=payload.name,
        methodology=payload.methodology.value,
        start_date=start_monday,
        end_date=end_date,
        block_plan=_serialize_block_plan(block_plan),
        goal=payload.goal,
        active=True,
    )
    session.add(macro)
    session.flush()  # get macro.id

    for i in range(weeks_total):
        wk_start = start_monday + timedelta(days=i * 7)
        session.add(MicrocycleDB(
            macrocycle_id=macro.id,
            user_id=user_id,
            start_date=wk_start,
            end_date=wk_start + timedelta(days=6),
            week_index_in_macro=i + 1,
        ))

    session.commit()
    session.refresh(macro)

    micros = session.execute(
        select(MicrocycleDB).where(MicrocycleDB.macrocycle_id == macro.id).order_by(MicrocycleDB.week_index_in_macro)
    ).scalars().all()

    macro_schema = _to_macro_schema(macro, block_plan)
    return MacrocycleWithMicrocycles(
        **macro_schema.model_dump(),
        microcycles=[_to_micro_schema(m, block_plan) for m in micros],
    )


@router.get("/macrocycles/active", response_model=MacrocycleWithMicrocycles)
async def get_active_macrocycle(
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    macro = session.execute(
        select(MacrocycleDB)
        .where(MacrocycleDB.user_id == user_id, MacrocycleDB.active.is_(True))
        .order_by(MacrocycleDB.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if not macro:
        raise HTTPException(status_code=404, detail="No active macrocycle")

    block_plan = _parse_block_plan(macro.block_plan)
    micros = session.execute(
        select(MicrocycleDB).where(MicrocycleDB.macrocycle_id == macro.id).order_by(MicrocycleDB.week_index_in_macro)
    ).scalars().all()

    macro_schema = _to_macro_schema(macro, block_plan)
    return MacrocycleWithMicrocycles(
        **macro_schema.model_dump(),
        microcycles=[_to_micro_schema(m, block_plan) for m in micros],
    )


@router.get("/macrocycles/{macro_id}", response_model=MacrocycleWithMicrocycles)
async def get_macrocycle(
    macro_id: UUID,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    macro = _get_owned_macro(session, macro_id, user_id)
    block_plan = _parse_block_plan(macro.block_plan)
    micros = session.execute(
        select(MicrocycleDB).where(MicrocycleDB.macrocycle_id == macro.id).order_by(MicrocycleDB.week_index_in_macro)
    ).scalars().all()
    macro_schema = _to_macro_schema(macro, block_plan)
    return MacrocycleWithMicrocycles(
        **macro_schema.model_dump(),
        microcycles=[_to_micro_schema(m, block_plan) for m in micros],
    )


@router.patch("/macrocycles/{macro_id}", response_model=Macrocycle)
async def update_macrocycle(
    macro_id: UUID,
    payload: MacrocycleUpdate,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    macro = _get_owned_macro(session, macro_id, user_id)

    if payload.name is not None:
        macro.name = payload.name
    if payload.goal is not None:
        macro.goal = payload.goal
    if payload.active is not None:
        macro.active = payload.active

    existing_plan = _parse_block_plan(macro.block_plan)
    new_plan = payload.block_plan or existing_plan

    if payload.block_plan is not None:
        macro.block_plan = _serialize_block_plan(new_plan)
        new_weeks = total_weeks(new_plan)
        macro.end_date = macro.start_date + timedelta(days=new_weeks * 7 - 1)

        # Extend microcycles if plan grew.
        existing_total = total_weeks(existing_plan)
        if new_weeks > existing_total:
            for i in range(existing_total, new_weeks):
                wk = macro.start_date + timedelta(days=i * 7)
                session.add(MicrocycleDB(
                    macrocycle_id=macro.id,
                    user_id=user_id,
                    start_date=wk,
                    end_date=wk + timedelta(days=6),
                    week_index_in_macro=i + 1,
                ))

    session.commit()
    session.refresh(macro)
    return _to_macro_schema(macro, new_plan)


@router.delete("/macrocycles/{macro_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_macrocycle(
    macro_id: UUID,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    macro = _get_owned_macro(session, macro_id, user_id)
    session.delete(macro)
    session.commit()
    return None


# ==========================================================
# Microcycles
# ==========================================================

@router.get("/microcycles/by-date", response_model=Microcycle)
async def get_microcycle_by_date(
    date: Optional[_Date] = Query(None),
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    target = date or user_today(current_user)

    micro = session.execute(
        select(MicrocycleDB)
        .where(
            MicrocycleDB.user_id == user_id,
            MicrocycleDB.start_date <= target,
            MicrocycleDB.end_date >= target,
        )
        .limit(1)
    ).scalar_one_or_none()
    if not micro:
        raise HTTPException(status_code=404, detail="No microcycle covers that date")

    macro = session.get(MacrocycleDB, micro.macrocycle_id)
    block_plan = _parse_block_plan(macro.block_plan if macro else [])
    sessions = _load_micro_sessions(session, micro.id)
    return _to_micro_schema(micro, block_plan, sessions)


@router.get("/microcycles/{micro_id}", response_model=Microcycle)
async def get_microcycle(
    micro_id: UUID,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    micro = _get_owned_micro(session, micro_id, user_id)

    macro = session.get(MacrocycleDB, micro.macrocycle_id)
    block_plan = _parse_block_plan(macro.block_plan if macro else [])
    sessions = _load_micro_sessions(session, micro.id)
    return _to_micro_schema(micro, block_plan, sessions)


@router.patch("/microcycles/{micro_id}", response_model=Microcycle)
async def update_microcycle(
    micro_id: UUID,
    payload: MicrocycleUpdate,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    micro = _get_owned_micro(session, micro_id, user_id)

    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(micro, k, v)
    session.commit()
    session.refresh(micro)

    macro = session.get(MacrocycleDB, micro.macrocycle_id)
    block_plan = _parse_block_plan(macro.block_plan if macro else [])
    sessions = _load_micro_sessions(session, micro.id)
    return _to_micro_schema(micro, block_plan, sessions)


@router.post("/microcycles/{micro_id}/copy-from/{source_id}", response_model=Microcycle)
async def copy_microcycle(
    micro_id: UUID,
    source_id: UUID,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    target = _get_owned_micro(session, micro_id, user_id)
    source = _get_owned_micro(session, source_id, user_id)

    # Wipe target sessions
    for s in session.execute(
        select(PlannedSessionDB).where(PlannedSessionDB.microcycle_id == target.id)
    ).scalars().all():
        session.delete(s)
    session.flush()

    delta_days = (target.start_date - source.start_date).days
    src_sessions = session.execute(
        select(PlannedSessionDB).where(PlannedSessionDB.microcycle_id == source.id)
    ).scalars().all()

    for s in src_sessions:
        session.add(PlannedSessionDB(
            microcycle_id=target.id,
            user_id=user_id,
            date=s.date + timedelta(days=delta_days),
            order_in_day=s.order_in_day,
            shift=s.shift,
            start_time=s.start_time,
            duration_minutes=s.duration_minutes,
            workout_type=s.workout_type,
            focus=s.focus,
            notes=s.notes,
            status=PlannedSessionStatus.PLANNED.value,
        ))

    session.commit()

    macro = session.get(MacrocycleDB, target.macrocycle_id)
    block_plan = _parse_block_plan(macro.block_plan if macro else [])
    sessions = _load_micro_sessions(session, target.id)
    return _to_micro_schema(target, block_plan, sessions)


# ==========================================================
# Planned sessions
# ==========================================================

@router.post(
    "/microcycles/{micro_id}/sessions",
    response_model=PlannedSession,
    status_code=status.HTTP_201_CREATED,
)
async def create_planned_session(
    micro_id: UUID,
    payload: PlannedSessionCreate,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    micro = _get_owned_micro(session, micro_id, user_id)

    if not (micro.start_date <= payload.date <= micro.end_date):
        raise HTTPException(
            status_code=400,
            detail=f"date {payload.date} is outside microcycle {micro.start_date}..{micro.end_date}",
        )

    row = PlannedSessionDB(
        microcycle_id=micro.id,
        user_id=user_id,
        date=payload.date,
        order_in_day=payload.order_in_day,
        shift=payload.shift.value if payload.shift else None,
        start_time=payload.start_time,
        duration_minutes=payload.duration_minutes,
        workout_type=payload.workout_type.value if payload.workout_type else None,
        focus=payload.focus,
        notes=payload.notes,
        status=PlannedSessionStatus.PLANNED.value,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_session_schema(row)


@router.patch("/planned-sessions/{session_id}", response_model=PlannedSession)
async def update_planned_session(
    session_id: UUID,
    payload: PlannedSessionUpdate,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    row = session.get(PlannedSessionDB, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Planned session not found")
    if row.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    data = payload.model_dump(exclude_none=True, mode="python")
    for k, v in data.items():
        # Unwrap enums → string
        if hasattr(v, "value"):
            v = v.value
        setattr(row, k, v)
    session.commit()
    session.refresh(row)
    return _to_session_schema(row)


@router.delete("/planned-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_planned_session(
    session_id: UUID,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["id"])
    row = session.get(PlannedSessionDB, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Planned session not found")
    if row.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    session.delete(row)
    session.commit()
    return None


# ==========================================================
# AI generation
# ==========================================================

class GenerateMicrocycleResponse(BaseModel):
    microcycle_id: UUID
    generated_sessions: int
    message: str


@router.post("/microcycles/{micro_id}/generate", response_model=GenerateMicrocycleResponse)
async def generate_microcycle_workouts(
    micro_id: UUID,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    from app.core.engine.ai_programmer import ai_programmer

    user_id = int(current_user["id"])
    micro = _get_owned_micro(session, micro_id, user_id)
    generated = await ai_programmer.generate_microcycle_program(
        db=session,
        microcycle=micro,
        user_id=user_id,
    )
    return GenerateMicrocycleResponse(
        microcycle_id=micro.id,
        generated_sessions=generated,
        message=f"Generated {generated} workout(s) for this microcycle",
    )


@router.post("/planned-sessions/{session_id}/regenerate", response_model=PlannedSession)
async def regenerate_planned_session(
    session_id: UUID,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    from app.core.engine.ai_programmer import ai_programmer

    user_id = int(current_user["id"])
    row = session.get(PlannedSessionDB, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Planned session not found")
    if row.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await ai_programmer.regenerate_single_session(
        db=session,
        planned=row,
        user_id=user_id,
    )
    session.commit()
    session.refresh(row)
    return _to_session_schema(row)
