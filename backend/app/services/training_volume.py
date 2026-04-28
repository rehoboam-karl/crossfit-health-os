"""
Training-volume classification for a given user/date.

Maps the day's planned sessions into a coarse `low | moderate | high` bucket so
nutrition (and other consumers) can adjust targets per-day instead of treating
every day as equivalent. Drafted standalone — no callers yet.

Bucketing rules (kept deliberately simple — tune later against real data):
  - No planned sessions               -> "low"   (rest day)
  - Total duration >= 90 min          -> "high"  (long chipper / 2-a-day)
  - Any session in HIGH_INTENSITY     -> "high"  (metcon, AMRAP, competition)
  - Total duration >= 45 min, or
    any session in MODERATE_INTENSITY -> "moderate"
  - Otherwise                         -> "low"
"""
from __future__ import annotations

from datetime import date as _Date
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PlannedSession as PlannedSessionDB

TrainingVolume = Literal["low", "moderate", "high"]

HIGH_INTENSITY_TYPES = {"metcon", "amrap", "competition", "conditioning"}
MODERATE_INTENSITY_TYPES = {"strength", "mixed", "skill"}

LONG_SESSION_MIN = 90
MODERATE_SESSION_MIN = 45


def training_volume_for_date(
    db: Session,
    user_id: int,
    target_date: _Date,
) -> TrainingVolume:
    """Return the day's training-volume bucket."""
    rows = db.execute(
        select(PlannedSessionDB).where(
            PlannedSessionDB.user_id == user_id,
            PlannedSessionDB.date == target_date,
        )
    ).scalars().all()

    if not rows:
        return "low"

    total_minutes = sum((r.duration_minutes or 0) for r in rows)
    types = {(r.workout_type or "").lower() for r in rows}

    if total_minutes >= LONG_SESSION_MIN:
        return "high"
    if types & HIGH_INTENSITY_TYPES:
        return "high"
    if total_minutes >= MODERATE_SESSION_MIN or (types & MODERATE_INTENSITY_TYPES):
        return "moderate"
    return "low"
