"""
Workout results — o que efetivamente aconteceu na sessão.

Hierarquia espelha o schema de planejamento:
  Session (planejada) ←→ SessionResult (executada)
    WorkoutBlock     ←→ BlockResult
      MovementPrescription ←→ MovementResult

Filosofia:
- Block-level score é OBRIGATÓRIO se status=COMPLETED (tempo, rounds, peso)
- Movement-level results são OPCIONAIS (relevante p/ strength e intervals;
  pra metcon For Time geralmente só o tempo total importa)
- Modifications/scaling/substitutions são first-class — atleta raramente
  executa exatamente o prescrito; rastrear isso é o ponto principal
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from .workout_schema import ScalingTier


class CompletionStatus(str, Enum):
    COMPLETED = "completed"        # tudo conforme planejado
    MODIFIED = "modified"          # feito mas com substituições/ajustes
    PARTIAL = "partial"            # alguns blocos pulados
    SKIPPED = "skipped"            # não treinou


class MovementResult(BaseModel):
    """O que aconteceu em uma MovementPrescription específica.

    movement_id pode diferir de prescribed_movement_id (substituição).
    """
    prescribed_movement_id: str
    movement_id: str                            # o que foi efetivamente feito

    # Volume executado (espelha MovementPrescription)
    actual_reps: Optional[int] = None
    actual_time_seconds: Optional[int] = None
    actual_distance_meters: Optional[int] = None
    actual_calories: Optional[int] = None

    # Carga real
    actual_load_kg: Optional[float] = None

    # Qualidade
    failed_reps: int = 0
    perceived_rpe: Optional[float] = Field(default=None, ge=1, le=10)
    set_number: Optional[int] = None            # p/ strength: qual set é

    notes: Optional[str] = None


class BlockResult(BaseModel):
    """Resultado de um WorkoutBlock."""
    block_order: int
    status: CompletionStatus

    # Score do bloco — formato livre + campos parseados p/ analytics
    actual_score: Optional[str] = None          # "12:34", "5+12", "3RM 100kg"
    actual_score_seconds: Optional[int] = None  # For Time → segundos
    actual_rounds: Optional[int] = None         # AMRAP → rounds completos
    actual_reps_total: Optional[int] = None     # AMRAP → +reps no round parcial
    actual_load_kg: Optional[float] = None      # 1RM/3RM → peso da última série

    # Tempo
    actual_duration_minutes: Optional[int] = None

    # Subjetivo do bloco
    perceived_rpe: Optional[float] = Field(default=None, ge=1, le=10)

    # Detalhes opcionais por movimento (uso comum em strength)
    movement_results: list[MovementResult] = Field(default_factory=list)

    # Modificações
    scaling_used: Optional[ScalingTier] = None
    substitutions: list[tuple[str, str]] = Field(default_factory=list)
    # tuple = (prescribed_movement_id, actual_movement_id)

    notes: Optional[str] = None


class SessionResult(BaseModel):
    """Sessão executada, vinculada à Session planejada."""
    id: str
    session_id: str                             # FK p/ Session planejada
    athlete_id: str

    executed_at: datetime
    duration_actual_minutes: int

    status: CompletionStatus
    block_results: list[BlockResult] = Field(default_factory=list)

    # Subjetivo da sessão inteira
    overall_rpe: Optional[float] = Field(default=None, ge=1, le=10)
    energy_pre: Optional[int] = Field(default=None, ge=1, le=10)
    energy_post: Optional[int] = Field(default=None, ge=1, le=10)
    sleep_quality_prev_night: Optional[int] = Field(default=None, ge=1, le=10)
    soreness: Optional[int] = Field(default=None, ge=0, le=10)

    notes: Optional[str] = None


# ============================================================
# BUILDERS / HELPERS
# ============================================================

def derive_status(block_results: list[BlockResult]) -> CompletionStatus:
    """Deriva status da sessão a partir do status dos blocos."""
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
    """Constrói SessionResult derivando status e duração."""
    status = derive_status(block_results)

    duration = duration_actual_minutes
    if duration is None:
        duration = sum(b.actual_duration_minutes or 0 for b in block_results)
        if duration == 0:
            duration = 60

    return SessionResult(
        id=f"result_{session_id}_{int(executed_at.timestamp())}",
        session_id=session_id,
        athlete_id=athlete_id,
        executed_at=executed_at,
        duration_actual_minutes=duration,
        status=status,
        block_results=block_results,
        overall_rpe=overall_rpe,
        energy_pre=energy_pre,
        energy_post=energy_post,
        sleep_quality_prev_night=sleep_quality_prev_night,
        soreness=soreness,
        notes=notes,
    )
