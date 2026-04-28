"""
CrossFit Health OS — Schema v2
Hierarquia: Mesocycle → Week → Session → Block → MovementPrescription
"""

from workout_schema import (
    Phase, SessionTemplate, BlockType, BlockFormat, Stimulus, ScalingTier,
    LoadSpec, MovementPrescription, WorkoutBlock, Session, Week, Mesocycle,
)
from athlete import Athlete, OneRepMax, BenchmarkResult, Injury, InjurySeverity
from percent_table import PercentTable, WeekScheme, SetPrescription
from movements import Movement, MovementLibrary, MovementScaling, TAGS_PATTERNS
from movements_seed import load_default_library
from session_builder import build_session
from programmer import SessionPlanner, HeuristicComposer, ClaudeComposer, ProgrammingContext, BlockHints
from results import CompletionStatus, MovementResult, BlockResult, SessionResult, build_session_result
from history import TrainingHistory, PR, apply_prs_to_athlete
from examples import karl
from macrocycle_adapter import MacrocycleAdapter

__all__ = [
    # Schema
    "Phase", "SessionTemplate", "BlockType", "BlockFormat", "Stimulus", "ScalingTier",
    "LoadSpec", "MovementPrescription", "WorkoutBlock", "Session", "Week", "Mesocycle",
    # Athlete
    "Athlete", "OneRepMax", "BenchmarkResult", "Injury", "InjurySeverity",
    # PercentTable
    "PercentTable", "WeekScheme", "SetPrescription",
    # Movements
    "Movement", "MovementLibrary", "MovementScaling", "TAGS_PATTERNS",
    "load_default_library",
    # Session builder
    "build_session",
    # Programmer
    "SessionPlanner", "HeuristicComposer", "ClaudeComposer", "ProgrammingContext", "BlockHints",
    # Results
    "CompletionStatus", "MovementResult", "BlockResult", "SessionResult", "build_session_result",
    # History
    "TrainingHistory", "PR", "apply_prs_to_athlete",
    # Examples
    "karl",
]