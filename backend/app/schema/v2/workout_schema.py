"""
Workout schema — HWPO/Mayhem-style periodization
Hierarquia: Mesocycle → Week → Session → Block → MovementPrescription

Decisões-chave:
- format e stimulus são ortogonais ao type (um metcon pode ser AMRAP/EMOM/ForTime)
- LoadSpec discrimina absolute_kg / percent_1rm / RPE / AHAP / bodyweight
- Scaling é por movimento (não por bloco) — permite RX/Scaled mesclados
- Validação estrutural impede sessões inválidas (2 strength_primary, etc.)
- Mesocycle carrega phase (base/build/peak/deload) para periodização
"""

from datetime import date
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


# ============================================================
# ENUMS
# ============================================================

class Phase(str, Enum):
    BASE = "base"
    BUILD = "build"
    PEAK = "peak"
    DELOAD = "deload"
    TEST = "test"


class SessionTemplate(str, Enum):
    """Constraint estrutural — limita combinações válidas de blocos."""
    STRENGTH_DAY = "strength_day"
    METCON_ONLY = "metcon_only"
    SKILL_DAY = "skill_day"
    ENGINE_DAY = "engine_day"
    GYMNASTIC_DAY = "gymnastic_day"
    RECOVERY = "recovery"
    OPEN_GYM = "open_gym"
    TEST_DAY = "test_day"
    COMP_SIM = "comp_sim"


class BlockType(str, Enum):
    """Papel estrutural do bloco na sessão."""
    WARM_UP = "warm_up"
    ACTIVATION = "activation"
    SKILL = "skill"
    STRENGTH_PRIMARY = "strength_primary"
    STRENGTH_SECONDARY = "strength_secondary"
    OLY_COMPLEX = "oly_complex"
    GYMNASTICS = "gymnastics"
    METCON = "metcon"
    ENGINE = "engine"
    AEROBIC_Z2 = "aerobic_z2"
    MIDLINE = "midline"
    ACCESSORY = "accessory"
    MOBILITY = "mobility"
    COOLDOWN = "cooldown"


class BlockFormat(str, Enum):
    """Estrutura temporal do bloco — ortogonal ao type."""
    SETS_REPS = "sets_reps"
    AMRAP = "amrap"
    EMOM = "emom"
    E2MOM = "e2mom"
    E3MOM = "e3mom"
    FOR_TIME = "for_time"
    FOR_TIME_CAPPED = "for_time_capped"
    INTERVALS = "intervals"
    TABATA = "tabata"
    CHIPPER = "chipper"
    LADDER = "ladder"
    DEATH_BY = "death_by"
    STEADY = "steady"
    REPEATS = "repeats"
    NOT_FOR_TIME = "not_for_time"
    QUALITY = "quality"


class Stimulus(str, Enum):
    """O 'porquê' do bloco — coração da metodologia HWPO/Mayhem."""
    AEROBIC_Z2 = "aerobic_z2"
    AEROBIC_THRESHOLD = "aerobic_threshold"
    VO2_MAX = "vo2_max"
    LACTIC_TOLERANCE = "lactic_tolerance"
    ALACTIC_POWER = "alactic_power"
    MIXED_MODAL = "mixed_modal"
    STRENGTH_MAX = "strength_max"
    STRENGTH_VOLUME = "strength_volume"
    HYPERTROPHY = "hypertrophy"
    POWER = "power"
    GYMNASTIC_CAPACITY = "gymnastic_capacity"
    SKILL_ACQUISITION = "skill_acquisition"
    MIDLINE_ENDURANCE = "midline_endurance"
    RECOVERY = "recovery"


class ScalingTier(str, Enum):
    RX_PLUS = "rx_plus"
    RX = "rx"
    SCALED = "scaled"
    FOUNDATION = "foundation"


# ============================================================
# LOAD & MOVEMENT
# ============================================================

class LoadSpec(BaseModel):
    """Como a carga é prescrita."""
    type: Literal[
        "absolute_kg", "percent_1rm", "percent_bw",
        "rpe", "ahap", "bodyweight",
    ]
    value: Optional[float] = None
    reference_lift: Optional[str] = None

    @model_validator(mode="after")
    def validate_value(self):
        if self.type in ("absolute_kg", "percent_1rm", "percent_bw", "rpe"):
            if self.value is None:
                raise ValueError(f"value obrigatório para type={self.type}")
        if self.type == "percent_1rm" and not self.reference_lift:
            raise ValueError("percent_1rm exige reference_lift")
        return self


class MovementPrescription(BaseModel):
    """Prescrição contextual ao bloco. Volume = UM de reps/time/dist/cal."""
    movement_id: str
    reps: Optional[int] = None
    time_seconds: Optional[int] = None
    distance_meters: Optional[int] = None
    calories: Optional[int] = None
    load: Optional[LoadSpec] = None
    tempo: Optional[str] = None
    pacing: Optional[str] = None
    notes: Optional[str] = None
    scaling: dict[ScalingTier, "MovementPrescription"] = Field(default_factory=dict)

    @model_validator(mode="after")
    def exactly_one_volume(self):
        volumes = [self.reps, self.time_seconds, self.distance_meters, self.calories]
        if sum(v is not None for v in volumes) != 1:
            raise ValueError(
                "Exatamente um de reps/time_seconds/distance_meters/calories"
            )
        return self


# ============================================================
# BLOCK
# ============================================================

class WorkoutBlock(BaseModel):
    order: int
    type: BlockType
    format: Optional[BlockFormat] = None
    stimulus: Optional[Stimulus] = None
    duration_minutes: Optional[int] = None
    time_cap_minutes: Optional[int] = None
    work_seconds: Optional[int] = None
    rest_seconds: Optional[int] = None
    rounds: Optional[int] = None
    movements: list[MovementPrescription] = Field(default_factory=list)
    target_score: Optional[str] = None
    target_pace: Optional[str] = None
    intensity_rpe: Optional[float] = Field(default=None, ge=1, le=10)
    intent: Optional[str] = None
    coaching_notes: Optional[str] = None
    derived_from_table_id: Optional[str] = None


# ============================================================
# SESSION
# ============================================================

class Session(BaseModel):
    id: str
    date: date
    template: SessionTemplate
    title: Optional[str] = None
    blocks: list[WorkoutBlock]
    estimated_duration_minutes: int
    equipment_required: list[str] = Field(default_factory=list)
    primary_stimulus: Stimulus

    @model_validator(mode="after")
    def validate_structure(self):
        if not self.blocks:
            if self.template != SessionTemplate.OPEN_GYM:
                raise ValueError("Apenas OPEN_GYM permite sessão sem blocos")
            return self

        orders = [b.order for b in self.blocks]
        if len(orders) != len(set(orders)):
            raise ValueError("Order de blocos deve ser único")

        sorted_blocks = sorted(self.blocks, key=lambda b: b.order)

        opener_types = {BlockType.WARM_UP, BlockType.MOBILITY, BlockType.ACTIVATION}
        if (
            self.template not in (SessionTemplate.OPEN_GYM, SessionTemplate.RECOVERY)
            and sorted_blocks[0].type not in opener_types
        ):
            raise ValueError("Primeira peça deve ser warm_up/mobility/activation")

        cooldowns = [b for b in sorted_blocks if b.type == BlockType.COOLDOWN]
        if cooldowns and cooldowns[0] is not sorted_blocks[-1]:
            raise ValueError("Cooldown deve ser o último bloco")

        primaries = [b for b in self.blocks if b.type == BlockType.STRENGTH_PRIMARY]
        if len(primaries) > 1:
            raise ValueError("Máximo 1 strength_primary por sessão")

        if self.template == SessionTemplate.RECOVERY:
            forbidden = {
                BlockType.METCON, BlockType.STRENGTH_PRIMARY,
                BlockType.STRENGTH_SECONDARY, BlockType.ENGINE,
                BlockType.OLY_COMPLEX,
            }
            if any(b.type in forbidden for b in self.blocks):
                raise ValueError("Recovery não permite metcon/strength/engine")

        return self


# ============================================================
# WEEK
# ============================================================

class Week(BaseModel):
    week_number: int
    theme: Optional[str] = None
    sessions: list[Session]
    deload: bool = False

    @model_validator(mode="after")
    def validate_session_count(self):
        if not 3 <= len(self.sessions) <= 7:
            raise ValueError("Semana deve ter 3-7 sessões")
        return self


# ============================================================
# MESOCYCLE
# ============================================================

class Mesocycle(BaseModel):
    id: str
    name: str
    phase: Phase
    start_date: date
    duration_weeks: int = Field(ge=1, le=16)
    weeks: list[Week]
    primary_focus: list[str]
    target_benchmarks: list[str] = Field(default_factory=list)
    parent_macrocycle_id: Optional[str] = None
    next_mesocycle_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_weeks(self):
        if len(self.weeks) != self.duration_weeks:
            raise ValueError(
                f"weeks={len(self.weeks)} mas duration_weeks={self.duration_weeks}"
            )
        nums = [w.week_number for w in self.weeks]
        if sorted(nums) != list(range(1, self.duration_weeks + 1)):
            raise ValueError("week_number deve ser 1..N contíguo")
        return self