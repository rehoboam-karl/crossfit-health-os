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
    BASE = "base"           # acumulação, volume, técnica
    BUILD = "build"         # intensificação
    PEAK = "peak"           # alta intensidade, baixo volume
    DELOAD = "deload"       # recuperação ativa
    TEST = "test"           # benchmarks / 1RM


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
    COMP_SIM = "comp_sim"   # simulação de competição (múltiplas peças)


class BlockType(str, Enum):
    """Papel estrutural do bloco na sessão."""
    WARM_UP = "warm_up"
    ACTIVATION = "activation"
    SKILL = "skill"                    # prática técnica, baixa intensidade
    STRENGTH_PRIMARY = "strength_primary"
    STRENGTH_SECONDARY = "strength_secondary"
    OLY_COMPLEX = "oly_complex"        # complexos olímpicos (sn+ohs+sn balance)
    GYMNASTICS = "gymnastics"          # volume/capacidade gímnica
    METCON = "metcon"
    ENGINE = "engine"                  # metcon focado em aeróbico/intervalado
    AEROBIC_Z2 = "aerobic_z2"          # zona 2 prolongada, monostructural
    MIDLINE = "midline"                # core/trunk standalone
    ACCESSORY = "accessory"            # bodybuilding, unilateral, prehab
    MOBILITY = "mobility"
    COOLDOWN = "cooldown"


class BlockFormat(str, Enum):
    """Estrutura temporal do bloco — ortogonal ao type."""
    SETS_REPS = "sets_reps"            # 5x3, 4x8 — strength
    AMRAP = "amrap"
    EMOM = "emom"
    E2MOM = "e2mom"
    E3MOM = "e3mom"
    FOR_TIME = "for_time"
    FOR_TIME_CAPPED = "for_time_capped"
    INTERVALS = "intervals"            # 5x3min @ pace
    TABATA = "tabata"
    CHIPPER = "chipper"
    LADDER = "ladder"                  # ascending/descending
    DEATH_BY = "death_by"
    STEADY = "steady"                  # zona 2, ritmo contínuo
    REPEATS = "repeats"                # rodadas com descanso fixo
    NOT_FOR_TIME = "not_for_time"
    QUALITY = "quality"                # execução, sem timer


class Stimulus(str, Enum):
    """O 'porquê' do bloco — coração da metodologia HWPO/Mayhem."""
    AEROBIC_Z2 = "aerobic_z2"
    AEROBIC_THRESHOLD = "aerobic_threshold"
    VO2_MAX = "vo2_max"
    LACTIC_TOLERANCE = "lactic_tolerance"
    ALACTIC_POWER = "alactic_power"
    MIXED_MODAL = "mixed_modal"        # CrossFit clássico
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
        "absolute_kg",      # peso fixo: 60kg
        "percent_1rm",      # 75% de back_squat 1RM
        "percent_bw",       # 50% bodyweight
        "rpe",              # RPE 8
        "ahap",             # As Heavy As Possible
        "bodyweight",       # apenas BW, sem load externa
    ]
    value: Optional[float] = None
    reference_lift: Optional[str] = None  # para percent_1rm: "back_squat"

    @model_validator(mode="after")
    def validate_value(self):
        if self.type in ("absolute_kg", "percent_1rm", "percent_bw", "rpe"):
            if self.value is None:
                raise ValueError(f"value obrigatório para type={self.type}")
        if self.type == "percent_1rm" and not self.reference_lift:
            raise ValueError("percent_1rm exige reference_lift")
        return self


class Movement(BaseModel):
    """Entidade no catálogo de movimentos (referência por id)."""
    id: str
    name: str
    category: Literal[
        "barbell", "dumbbell", "kettlebell",
        "gymnastic", "monostructural", "odd_object", "accessory"
    ]
    skill_level: int = Field(ge=1, le=5)   # 1=básico, 5=elite
    equipment: list[str]


class MovementPrescription(BaseModel):
    """Prescrição contextual ao bloco. Volume = UM de reps/time/dist/cal."""
    movement_id: str

    # Volume — exatamente UM
    reps: Optional[int] = None
    time_seconds: Optional[int] = None
    distance_meters: Optional[int] = None
    calories: Optional[int] = None

    # Carga
    load: Optional[LoadSpec] = None

    # Execução
    tempo: Optional[str] = None           # "31X1"
    pacing: Optional[str] = None          # "unbroken", "smooth", "all-out"
    notes: Optional[str] = None

    # Scaling — substituições por tier (mesmo movimento ajustado OU outro)
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
    stimulus: Optional[Stimulus] = None    # opcional para warm/cool/mobility

    # Tempo
    duration_minutes: Optional[int] = None  # planejado/estimado
    time_cap_minutes: Optional[int] = None  # limite duro (For Time Capped)
    work_seconds: Optional[int] = None      # intervals/tabata
    rest_seconds: Optional[int] = None
    rounds: Optional[int] = None            # AMRAP rounds-target, intervals

    # Conteúdo
    movements: list[MovementPrescription] = Field(default_factory=list)

    # Targets de performance
    target_score: Optional[str] = None      # "sub-12min", "5+ rounds", "BW snatch"
    target_pace: Optional[str] = None       # "2:00/500m row"
    intensity_rpe: Optional[float] = Field(default=None, ge=1, le=10)

    # Coaching
    intent: Optional[str] = None            # "sustained breathing zone, no redline"
    coaching_notes: Optional[str] = None


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

        # Order único e contíguo
        orders = [b.order for b in self.blocks]
        if len(orders) != len(set(orders)):
            raise ValueError("Order de blocos deve ser único")

        sorted_blocks = sorted(self.blocks, key=lambda b: b.order)

        # Primeira peça: warm_up / mobility / activation (exceto recovery/open_gym)
        opener_types = {BlockType.WARM_UP, BlockType.MOBILITY, BlockType.ACTIVATION}
        if (
            self.template not in (SessionTemplate.OPEN_GYM, SessionTemplate.RECOVERY)
            and sorted_blocks[0].type not in opener_types
        ):
            raise ValueError("Primeira peça deve ser warm_up/mobility/activation")

        # Cooldown, se presente, é última
        cooldowns = [b for b in sorted_blocks if b.type == BlockType.COOLDOWN]
        if cooldowns and cooldowns[0] is not sorted_blocks[-1]:
            raise ValueError("Cooldown deve ser o último bloco")

        # Máximo 1 strength_primary
        primaries = [b for b in self.blocks if b.type == BlockType.STRENGTH_PRIMARY]
        if len(primaries) > 1:
            raise ValueError("Máximo 1 strength_primary por sessão")

        # Recovery: sem metcon/strength/engine
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
    week_number: int                       # 1..N dentro do mesociclo
    theme: Optional[str] = None            # "high-pulling volume", "midline emphasis"
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
    name: str                              # "Q2 Base — Engine + Pulling"
    phase: Phase
    start_date: date
    duration_weeks: int = Field(ge=1, le=16)
    weeks: list[Week]

    # Foco programático
    primary_focus: list[str]               # ["overhead_capacity", "engine_z2"]
    target_benchmarks: list[str] = Field(default_factory=list)  # ["Fran", "5K row"]

    # Encadeamento (macrocycle implícito)
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
