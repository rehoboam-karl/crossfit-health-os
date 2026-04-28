"""
Workout results — o que efetivamente aconteceu na sessao.

Hierarquia espelha o schema de planejamento:
Session (planejada) ←→ SessionResult (executada)
WorkoutBlock ←→ BlockResult
MovementPrescription ←→ MovementResult

Filosofia:
- Block-level score e OBRIGATORIO se status=COMPLETED
- Movement-level results sao OPCIONAIS (relevante para strength/intervals)
- MODIFIED vs PARTIAL sao fenomenos diferentes - nao mistura
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from workout_schema import ScalingTier


class CompletionStatus(str, Enum):
    COMPLETED = "completed"
    MODIFIED = "modified"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class MovementResult(BaseModel):
    prescribed_movement_id: str
    movement_id: str  # o que foi efetivamente feito
    actual_reps: Optional[int] = None
    actual_time_seconds: Optional[int] = None
    actual_distance_meters: Optional[int] = None
    actual_calories: Optional[int] = None
    actual_load_kg: Optional[float] = None
    failed_reps: int = 0
    perceived_rpe: Optional[float] = Field(default=None, ge=1, le=10)
    set_number: Optional[int] = None
    notes: Optional[str] = None


class BlockResult(BaseModel):
    block_order: int
    status: CompletionStatus
    actual_score: Optional[str] = None  # "12:34", "5+12", "3RM 100kg"
    actual_score_seconds: Optional[int] = None
    actual_rounds: Optional[int] = None
    actual_reps_total: Optional[int] = None
    actual_load_kg: Optional[float] = None
    actual_duration_minutes: Optional[int] = None
    perceived_rpe: Optional[float] = Field(default=None, ge=1, le=10)
    movement_results: list[MovementResult] = Field(default_factory=list)
    scaling_used: Optional[ScalingTier] = None
    substitutions: list[tuple[str, str]] = Field(default_factory=list)
    notes: Optional[str] = None


class SessionResult(BaseModel):
    id: str
    session_id: str
    athlete_id: str
    executed_at: datetime
    duration_actual_minutes: int
    status: CompletionStatus
    block_results: list[BlockResult] = Field(default_factory=list)
    overall_rpe: Optional[float] = Field(default=None, ge=1, le=10)
    energy_pre: Optional[int] = Field(default=None, ge=1, le=10)
    energy_post: Optional[int] = Field(default=None, ge=1, le=10)
    sleep_quality_prev_night: Optional[int] = Field(default=None, ge=1, le=10)
    soreness: Optional[int] = Field(default=None, ge=0, le=10)
    notes: Optional[str] = None


# ============================================================
# HELPERS
# ============================================================

def derive_status(block_results: list[BlockResult]) -> CompletionStatus:
    if not block_results:
        return CompletionStatus.SKIPPED
    statuses = [b.status for b in block_results]
    if all(s == CompletionStatus.SKIPPED for s in statuses):
        return CompletionStatus.SKIPPED
    if all(s == CompletionStatus.COMPLETED for s in statuses):
        return CompletionStatus.COMPLETED
    if any(s == CompletionStatus.MODIFIED for s in statuses):
        return CompletionStatus.MODIFIED
    return CompletionStatus.PARTIAL


def build_session_result(
    *,
    session_id: str,
    athlete_id: str,
    executed_at: datetime,
    block_results: list[BlockResult],
    overall_rpe: Optional[float] = None,
    energy_pre: Optional[int] = None,
    energy_post: Optional[int] = None,
    sleep_quality_prev_night: Optional[int] = None,
    soreness: Optional[int] = None,
    notes: Optional[str] = None,
    duration_actual_minutes: Optional[int] = None,
) -> SessionResult:
    status = derive_status(block_results)
    duration = duration_actual_minutes
    if duration is None:
        duration = sum(b.actual_duration_minutes or 0 for b in block_results)
        if duration == 0:
            duration = 60
    return SessionResult(
        id=f"result_{session_id}_{int(executed_at.timestamp())}",
        session_id=session_id, athlete_id=athlete_id,
        executed_at=executed_at, duration_actual_minutes=duration,
        status=status, block_results=block_results,
        overall_rpe=overall_rpe, energy_pre=energy_pre, energy_post=energy_post,
        sleep_quality_prev_night=sleep_quality_prev_night,
        soreness=soreness, notes=notes,
    )