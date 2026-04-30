"""
PercentTable — progressões multi-semana para strength.

Modela patterns clássicos:
- Linear: mesmo set/rep, % crescente (70 → 75 → 80 → deload)
- Wave: 5/3/1 com % crescente por set dentro da semana
- Block: mesma intensidade 3 semanas + deload na 4ª
- Conjugate: max effort vs dynamic effort alternados

Uso: PercentTable é template/library entity. Helper apply_to_block()
gera MovementPrescriptions concretas para um WorkoutBlock dado:
  - movement_id alvo
  - week_number do mesociclo

A intenção é "bake" no momento de gerar a sessão (não resolução
em runtime), preservando lineage via WorkoutBlock.derived_from_table_id.
"""

from typing import Optional
from pydantic import BaseModel, Field, model_validator

from .workout_schema import LoadSpec, MovementPrescription


class SetPrescription(BaseModel):
    """Uma linha da tabela: 'Set 2: 3 reps @ 80%'."""
    set_number: int = Field(ge=1)
    reps: int = Field(ge=1)
    intensity: LoadSpec
    rest_seconds: Optional[int] = Field(default=None, ge=0)
    tempo: Optional[str] = None
    notes: Optional[str] = None


class WeekScheme(BaseModel):
    """Prescrição de UMA semana — pode ter sets heterogêneos (wave loading)."""
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
    """Template de progressão multi-semana."""
    id: str
    name: str                             # "Back Squat Wave 5/3/1 — 4 weeks"
    description: Optional[str] = None
    pattern: str                          # "linear" | "wave" | "block" | "conjugate"
    duration_weeks: int = Field(ge=1, le=16)
    weeks: list[WeekScheme]

    # Movimento alvo (None = template genérico aplicável a qualquer lift)
    target_movement_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_weeks(self):
        if len(self.weeks) != self.duration_weeks:
            raise ValueError(
                f"weeks={len(self.weeks)} != duration_weeks={self.duration_weeks}"
            )
        nums = [w.week_number for w in self.weeks]
        if sorted(nums) != list(range(1, self.duration_weeks + 1)):
            raise ValueError("week_number deve ser 1..N contíguo")
        return self

    def get_week(self, week_number: int) -> WeekScheme:
        for w in self.weeks:
            if w.week_number == week_number:
                return w
        raise ValueError(f"week_number {week_number} não encontrada")

    def apply_to_movement(
        self, movement_id: str, week_number: int
    ) -> list[MovementPrescription]:
        """Gera MovementPrescriptions para um movimento numa semana específica.

        Cada SetPrescription vira um MovementPrescription (com mesmo movement_id).
        Útil quando o WorkoutBlock tem format=SETS_REPS e cada set é um item.
        """
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
