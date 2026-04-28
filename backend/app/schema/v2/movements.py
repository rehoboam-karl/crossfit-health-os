"""
Movement library — entidade central referenciada por movement_id.

Resolve:
- Validação: movement_id em prescriptions existe no catálogo
- Equipment derivation: union dos equipments dos movimentos da sessão
- Injury restriction: tags do movimento vs affected_patterns da Injury
- Scaling defaults: substituições padrão por tier (overridáveis na prescription)
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field

from workout_schema import ScalingTier


# ============================================================
# VOCABULÁRIO DE TAGS
# ============================================================

TAGS_PATTERNS = {
    "squatting", "hip_hinge", "knee_dominant", "hip_dominant",
    "lunging", "single_leg",
    "pulling_vertical", "pulling_horizontal",
    "pressing_vertical", "pressing_horizontal", "overhead",
    "spinal_flexion", "spinal_extension", "anti_rotation", "midline",
    "ballistic", "olympic", "explosive", "isometric",
    "high_impact", "low_impact",
    "carrying", "bracing",
    "cyclical", "ground_contact",
}


# ============================================================
# MODEL
# ============================================================

class MovementScaling(BaseModel):
    substitute_movement_id: Optional[str] = None
    load_factor: Optional[float] = Field(default=None, gt=0)
    reps_factor: Optional[float] = Field(default=None, gt=0)
    notes: Optional[str] = None


class Movement(BaseModel):
    id: str
    name: str
    name_pt: Optional[str] = None
    category: Literal[
        "barbell", "dumbbell", "kettlebell",
        "gymnastic", "monostructural", "odd_object", "accessory",
    ]
    modalities: list[Literal["M", "G", "W"]]
    skill_level: int = Field(ge=1, le=5)
    equipment: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    bilateral: bool = True
    is_warmup_only: bool = False
    default_scaling: dict[ScalingTier, MovementScaling] = Field(default_factory=dict)
    standards: Optional[str] = None
    common_faults: list[str] = Field(default_factory=list)


# ============================================================
# LIBRARY
# ============================================================

class MovementLibrary:
    def __init__(self, movements: list[Movement]):
        self._movements: dict[str, Movement] = {}
        for m in movements:
            if m.id in self._movements:
                raise ValueError(f"movement_id duplicado: {m.id}")
            self._movements[m.id] = m

    def __contains__(self, movement_id: str) -> bool:
        return movement_id in self._movements

    def __len__(self) -> int:
        return len(self._movements)

    def get(self, movement_id: str) -> Movement:
        if movement_id not in self._movements:
            raise KeyError(f"movement_id '{movement_id}' não está no catálogo")
        return self._movements[movement_id]

    def get_or_none(self, movement_id: str) -> Optional[Movement]:
        return self._movements.get(movement_id)

    def all(self) -> list[Movement]:
        return list(self._movements.values())

    def find_by_tag(self, tag: str) -> list[Movement]:
        return [m for m in self._movements.values() if tag in m.tags]

    def find_by_tags_any(self, tags: list[str]) -> list[Movement]:
        s = set(tags)
        return [m for m in self._movements.values() if s & set(m.tags)]

    def find_by_modality(self, modality: Literal["M", "G", "W"]) -> list[Movement]:
        return [m for m in self._movements.values() if modality in m.modalities]

    def find_by_category(self, category: str) -> list[Movement]:
        return [m for m in self._movements.values() if m.category == category]

    def filter_by_equipment(self, available: list[str]) -> list[Movement]:
        avail = set(available)
        return [
            m for m in self._movements.values()
            if not m.equipment or set(m.equipment).issubset(avail)
        ]

    def derive_equipment(self, movement_ids: list[str]) -> list[str]:
        eq: set[str] = set()
        for mid in movement_ids:
            mov = self.get_or_none(mid)
            if mov:
                eq.update(mov.equipment)
        return sorted(eq)

    def validate_ids(self, movement_ids: list[str]) -> list[str]:
        return [mid for mid in movement_ids if mid not in self._movements]