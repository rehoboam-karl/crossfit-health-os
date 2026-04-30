"""
Compatibility shim — schema v2 agora vive em `cfai` (instalado via
`backend/cfai/`). Este `__init__.py` re-exporta o vocabulário que código
existente possa estar importando como `app.schema.v2.X`.

Para código novo: importe direto de `cfai`:

    from cfai.programmer import HeuristicComposer
    from cfai.workout_schema import Phase, BlockType
    from cfai.evaluation import evaluate_mesocycle, summary_score

`MacrocycleAdapter` continua aqui porque depende de `app.db.models` (bridge
entre o schema cfai e os modelos SQLAlchemy do FastAPI).
"""
from cfai.workout_schema import (
    Phase, SessionTemplate, BlockType, BlockFormat, Stimulus, ScalingTier,
    LoadSpec, MovementPrescription, WorkoutBlock, Session, Week, Mesocycle,
)
from cfai.athlete import Athlete, OneRepMax, BenchmarkResult, Injury, InjurySeverity
from cfai.percent_table import PercentTable, WeekScheme, SetPrescription
from cfai.movements import Movement, MovementLibrary, MovementScaling, TAGS_PATTERNS
from cfai.movements_seed import load_default_library
from cfai.session_builder import build_session
from cfai.programmer import (
    SessionPlanner, HeuristicComposer, ClaudeComposer,
    ProgrammingContext, BlockHints,
)
from cfai.results import (
    CompletionStatus, MovementResult, BlockResult, SessionResult,
    build_session_result,
)
from cfai.history import TrainingHistory, PR, apply_prs_to_athlete
from cfai.examples import karl

from .macrocycle_adapter import MacrocycleAdapter

__all__ = [
    "Phase", "SessionTemplate", "BlockType", "BlockFormat", "Stimulus", "ScalingTier",
    "LoadSpec", "MovementPrescription", "WorkoutBlock", "Session", "Week", "Mesocycle",
    "Athlete", "OneRepMax", "BenchmarkResult", "Injury", "InjurySeverity",
    "PercentTable", "WeekScheme", "SetPrescription",
    "Movement", "MovementLibrary", "MovementScaling", "TAGS_PATTERNS",
    "load_default_library",
    "build_session",
    "SessionPlanner", "HeuristicComposer", "ClaudeComposer", "ProgrammingContext", "BlockHints",
    "CompletionStatus", "MovementResult", "BlockResult", "SessionResult", "build_session_result",
    "TrainingHistory", "PR", "apply_prs_to_athlete",
    "karl",
    "MacrocycleAdapter",
]
