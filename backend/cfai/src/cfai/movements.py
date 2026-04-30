"""
Movement library — entidade central referenciada por movement_id.

Resolve:
- Validação: movement_id em prescriptions existe no catálogo
- Equipment derivation: union dos equipments dos movimentos da sessão
- Injury restriction: tags do movimento vs affected_patterns da Injury
- Scaling defaults: substituições padrão por tier (overridáveis na prescription)

Tags são vocabulário controlado (ver TAGS abaixo) — uso consistente é o que
permite injury patterns e queries (ex.: "todos os movimentos overhead").

Modalities: classificação CrossFit clássica
- M (Monostructural): cardio puro (run, row, bike)
- G (Gymnastic): peso corporal contra gravidade
- W (Weightlifting): cargas externas
Um movimento pode ter múltiplas (ex.: thruster = G+W).
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field

from .workout_schema import ScalingTier


# ============================================================
# VOCABULÁRIO DE TAGS (padrões de movimento)
# ============================================================

# Padrões biomecânicos — base para injury restriction matching
TAGS_PATTERNS = {
    # Pernas
    "squatting", "hip_hinge", "knee_dominant", "hip_dominant",
    "lunging", "single_leg",
    # Pulling
    "pulling_vertical", "pulling_horizontal",
    # Pressing
    "pressing_vertical", "pressing_horizontal", "overhead",
    # Tronco
    "spinal_flexion", "spinal_extension", "anti_rotation", "midline",
    # Características
    "ballistic", "olympic", "explosive", "isometric",
    "high_impact", "low_impact",
    "carrying", "bracing",
    # Cardio
    "cyclical", "ground_contact",
}


# ============================================================
# MODEL
# ============================================================

class MovementScaling(BaseModel):
    """Default scaling de um movimento para um tier específico."""
    substitute_movement_id: Optional[str] = None  # None = mesmo movimento ajustado
    # Factors são multiplicadores — <1 reduz, >1 aumenta
    # Ex.: BMU → C2B com reps_factor=2.0 (dobra reps p/ compensar)
    load_factor: Optional[float] = Field(default=None, gt=0)
    reps_factor: Optional[float] = Field(default=None, gt=0)
    notes: Optional[str] = None


class Movement(BaseModel):
    id: str                            # canonical: "back_squat", "db_snatch_alt"
    name: str                          # display: "Back Squat"
    name_pt: Optional[str] = None      # i18n PT-BR

    category: Literal[
        "barbell", "dumbbell", "kettlebell",
        "gymnastic", "monostructural", "odd_object", "accessory",
    ]
    modalities: list[Literal["M", "G", "W"]]  # MGW classification
    skill_level: int = Field(ge=1, le=5)
    equipment: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    bilateral: bool = True
    is_warmup_only: bool = False       # mobility/breathing — não conta como "trabalho"

    # Scaling defaults (overridáveis na MovementPrescription)
    default_scaling: dict[ScalingTier, MovementScaling] = Field(default_factory=dict)

    # Coaching
    standards: Optional[str] = None    # ROM standards, regra de validade
    common_faults: list[str] = Field(default_factory=list)


# ============================================================
# LIBRARY
# ============================================================

class MovementLibrary:
    """Registry de movimentos com lookups e filtros.

    Carregado uma vez na inicialização. Não é Pydantic model (é registry,
    não dados serializáveis).
    """

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

    # ---------- Filtros ----------

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
        """Retorna movimentos cujo equipment é subconjunto do disponível."""
        avail = set(available)
        return [
            m for m in self._movements.values()
            if set(m.equipment).issubset(avail) or not m.equipment
        ]

    # ---------- Derivações ----------

    def derive_equipment(self, movement_ids: list[str]) -> list[str]:
        """Union dos equipments — útil para Session.equipment_required auto."""
        eq: set[str] = set()
        for mid in movement_ids:
            mov = self.get_or_none(mid)
            if mov:
                eq.update(mov.equipment)
        return sorted(eq)

    def validate_ids(self, movement_ids: list[str]) -> list[str]:
        """Retorna a lista de ids que NÃO existem no catálogo."""
        return [mid for mid in movement_ids if mid not in self._movements]
