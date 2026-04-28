"""
Athlete profile — perfil do atleta para resolver prescrições.
Resolve LoadSpec.percent_1rm em kg absoluto via 1RM lookup.
Carrega benchmarks, equipamento disponível, lesões ativas.
"""

from datetime import date
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator

from workout_schema import LoadSpec, ScalingTier


class OneRepMax(BaseModel):
    movement_id: str
    value_kg: float = Field(gt=0)
    tested_date: date
    confidence: Literal["tested", "estimated", "stale"] = "tested"


class BenchmarkResult(BaseModel):
    benchmark_id: str
    value: float
    unit: Literal["seconds", "reps", "rounds_reps", "kg", "watts"]
    tested_date: date
    notes: Optional[str] = None


class InjurySeverity(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"


class Injury(BaseModel):
    description: str
    severity: InjurySeverity
    affected_movements: list[str] = Field(default_factory=list)
    affected_patterns: list[str] = Field(default_factory=list)
    start_date: date
    resolved_date: Optional[date] = None
    notes: Optional[str] = None


class Athlete(BaseModel):
    id: str
    name: str
    birthdate: date
    body_weight_kg: float = Field(gt=0)
    height_cm: Optional[float] = Field(default=None, gt=0)
    training_age_years: float = Field(ge=0)
    one_rep_maxes: dict[str, OneRepMax] = Field(default_factory=dict)
    benchmarks: dict[str, BenchmarkResult] = Field(default_factory=dict)
    equipment_available: list[str] = Field(default_factory=list)
    active_injuries: list[Injury] = Field(default_factory=list)
    default_scaling: ScalingTier = ScalingTier.RX
    primary_goals: list[str] = Field(default_factory=list)
    target_benchmarks: list[str] = Field(default_factory=list)
    sessions_per_week: int = Field(default=5, ge=1, le=14)

    # ---------- Resolvers ----------

    def get_1rm(self, movement_id: str) -> Optional[float]:
        orm = self.one_rep_maxes.get(movement_id)
        return orm.value_kg if orm else None

    def resolve_load(self, load: LoadSpec) -> Optional[float]:
        """Retorna carga absoluta em kg para um LoadSpec."""
        if load.type == "absolute_kg":
            return load.value
        if load.type == "percent_bw":
            return self.body_weight_kg * (load.value / 100)
        if load.type == "percent_1rm":
            base = self.get_1rm(load.reference_lift)
            return base * (load.value / 100) if base else None
        if load.type == "bodyweight":
            return 0.0
        return None

    def has_equipment(self, required: list[str]) -> bool:
        return all(eq in self.equipment_available for eq in required)

    def is_movement_restricted(self, movement_id: str) -> Optional[Injury]:
        for inj in self.active_injuries:
            if inj.resolved_date is not None:
                continue
            if movement_id in inj.affected_movements:
                return inj
        return None

    @model_validator(mode="after")
    def validate_orm_keys(self):
        for key, orm in self.one_rep_maxes.items():
            if key != orm.movement_id:
                raise ValueError(f"Chave '{key}' difere de movement_id '{orm.movement_id}'")
        for key, bench in self.benchmarks.items():
            if key != bench.benchmark_id:
                raise ValueError(f"Chave '{key}' difere de benchmark_id '{bench.benchmark_id}'")
        return self