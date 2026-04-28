"""
PercentTable — progressões multi-semana para strength.
Modela patterns clássicos: linear, wave, block, conjugate.
"""

from typing import Optional
from pydantic import BaseModel, Field, model_validator

from workout_schema import LoadSpec, MovementPrescription


class SetPrescription(BaseModel):
    set_number: int = Field(ge=1)
    reps: int = Field(ge=1)
    intensity: LoadSpec
    rest_seconds: Optional[int] = Field(default=None, ge=0)
    tempo: Optional[str] = None
    notes: Optional[str] = None


class WeekScheme(BaseModel):
    week_number: int = Field(ge=1)
    sets: list[SetPrescription]
    is_deload: bool = False
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_set_numbers(self):
        nums = [s.set_number for s in self.sets]
        if sorted(nums) != list(range(1, len(nums) + 1)):
            raise ValueError("set_number deve ser 1..N contíguo")
        return self


class PercentTable(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    pattern: str
    duration_weeks: int = Field(ge=1, le=16)
    weeks: list[WeekScheme]
    target_movement_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_weeks(self):
        if len(self.weeks) != self.duration_weeks:
            raise ValueError(f"weeks={len(self.weeks)} != duration_weeks={self.duration_weeks}")
        nums = [w.week_number for w in self.weeks]
        if sorted(nums) != list(range(1, self.duration_weeks + 1)):
            raise ValueError("week_number deve ser 1..N contíguo")
        return self

    def get_week(self, week_number: int) -> WeekScheme:
        for w in self.weeks:
            if w.week_number == week_number:
                return w
        raise ValueError(f"week_number {week_number} não encontrada")

    def apply_to_movement(self, movement_id: str, week_number: int) -> list[MovementPrescription]:
        scheme = self.get_week(week_number)
        return [
            MovementPrescription(
                movement_id=movement_id,
                reps=s.reps,
                load=s.intensity,
                tempo=s.tempo,
                notes=s.notes,
            )
            for s in scheme.sets
        ]