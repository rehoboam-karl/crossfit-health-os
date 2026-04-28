"""
Programmer skeleton — gera Session a partir de Athlete + Phase + contexto.

Arquitetura:
ProgrammingContext (input)
  → SessionPlanner.plan_session()
    → _select_template() : determina SessionTemplate
    → _scaffold_blocks() : lista ordenada de (BlockType, BlockHints)
    → composer.compose_block() : preenche cada bloco com movimentos/cargas
  → Session (output, validada)

Composer é um Protocol — HeuristicComposer (rule-based) incluso.
ClaudeComposer (Anthropic API) é stub documentado para Karl plugar.

Princípio: skeleton determinístico, IA só entra no composer.
"""

from dataclasses import dataclass, field
from datetime import date as Date
from typing import Optional, Protocol

from athlete import Athlete
from movements import Movement, MovementLibrary
from session_builder import build_session
from workout_schema import (
    BlockFormat, BlockType, LoadSpec, MovementPrescription,
    Phase, ScalingTier, Session, SessionTemplate, Stimulus, WorkoutBlock,
)


# ============================================================
# CONTEXTO E HINTS
# ============================================================

@dataclass
class ProgrammingContext:
    """Tudo que o programmer precisa para decidir."""
    athlete: Athlete
    library: MovementLibrary
    phase: Phase
    week_number: int
    day_number: int
    target_date: Date
    weekly_focus: list[str] = field(default_factory=list)
    recent_sessions: list[Session] = field(default_factory=list)
    available_minutes: int = 60


@dataclass
class BlockHints:
    """Pistas para o composer preencher um bloco."""
    target_stimulus: Optional[Stimulus] = None
    target_tags: list[str] = field(default_factory=list)
    target_modalities: list[str] = field(default_factory=list)
    target_format: Optional[BlockFormat] = None
    duration_minutes: Optional[int] = None
    intent: Optional[str] = None
    rounds: Optional[int] = None
    rpe: Optional[float] = None


# ============================================================
# COMPOSER INTERFACE
# ============================================================

class MovementComposer(Protocol):
    """Interface para preencher um bloco. Plug Claude API aqui."""
    def compose_block(
        self, *, order: int, block_type: BlockType,
        hints: BlockHints, ctx: ProgrammingContext,
    ) -> WorkoutBlock: ...


# ============================================================
# PLANNER
# ============================================================

class SessionPlanner:
    """Skeleton de programmer — determinístico no esqueleto, IA no composer."""
    DEFAULT_WEEKLY_PATTERN: dict[int, SessionTemplate] = {
        1: SessionTemplate.STRENGTH_DAY,
        2: SessionTemplate.METCON_ONLY,
        3: SessionTemplate.ENGINE_DAY,
        4: SessionTemplate.STRENGTH_DAY,
        5: SessionTemplate.GYMNASTIC_DAY,
        6: SessionTemplate.RECOVERY,
        7: SessionTemplate.OPEN_GYM,
    }

    def __init__(self, library: MovementLibrary, composer: MovementComposer):
        self.library = library
        self.composer = composer

    def plan_session(self, ctx: ProgrammingContext) -> Session:
        template = self._select_template(ctx)
        scaffold = self._scaffold_blocks(template, ctx)

        blocks = []
        for order, (block_type, hints) in enumerate(scaffold, start=1):
            block = self.composer.compose_block(
                order=order, block_type=block_type, hints=hints, ctx=ctx,
            )
            blocks.append(block)

        return build_session(
            id=f"sess_w{ctx.week_number}_d{ctx.day_number}",
            date=ctx.target_date,
            template=template,
            title=self._title_for(template, ctx),
            blocks=blocks,
            primary_stimulus=self._primary_stimulus(template, ctx),
            library=self.library,
        )

    def _select_template(self, ctx: ProgrammingContext) -> SessionTemplate:
        if ctx.phase == Phase.DELOAD:
            if ctx.day_number in (1, 4):
                return SessionTemplate.STRENGTH_DAY
            if ctx.day_number == 3:
                return SessionTemplate.SKILL_DAY
            if ctx.day_number in (6, 7):
                return SessionTemplate.OPEN_GYM
            return SessionTemplate.RECOVERY

        if ctx.phase == Phase.TEST:
            return SessionTemplate.TEST_DAY if ctx.day_number <= 5 else SessionTemplate.RECOVERY

        if ctx.phase == Phase.PEAK and ctx.day_number == 5:
            return SessionTemplate.COMP_SIM

        return self.DEFAULT_WEEKLY_PATTERN.get(ctx.day_number, SessionTemplate.OPEN_GYM)

    def _scaffold_blocks(self, template: SessionTemplate, ctx: ProgrammingContext) -> list[tuple[BlockType, BlockHints]]:
        if template == SessionTemplate.STRENGTH_DAY:
            return [
                (BlockType.WARM_UP, BlockHints(duration_minutes=10)),
                (BlockType.ACTIVATION, BlockHints(duration_minutes=5)),
                (BlockType.STRENGTH_PRIMARY, BlockHints(
                    duration_minutes=20, target_stimulus=Stimulus.STRENGTH_VOLUME,
                    target_tags=self._strength_focus_tags(ctx), target_format=BlockFormat.SETS_REPS)),
                (BlockType.STRENGTH_SECONDARY, BlockHints(
                    duration_minutes=12, target_stimulus=Stimulus.HYPERTROPHY, rpe=7.0)),
                (BlockType.METCON, BlockHints(
                    duration_minutes=10, target_stimulus=Stimulus.MIXED_MODAL,
                    target_format=BlockFormat.AMRAP, rpe=7.5)),
                (BlockType.COOLDOWN, BlockHints(duration_minutes=5)),
            ]

        if template == SessionTemplate.METCON_ONLY:
            return [
                (BlockType.WARM_UP, BlockHints(duration_minutes=12)),
                (BlockType.METCON, BlockHints(
                    duration_minutes=20, target_stimulus=Stimulus.MIXED_MODAL,
                    target_format=BlockFormat.FOR_TIME_CAPPED, rpe=8.5)),
                (BlockType.MIDLINE, BlockHints(
                    duration_minutes=8, target_stimulus=Stimulus.MIDLINE_ENDURANCE, rounds=3)),
                (BlockType.COOLDOWN, BlockHints(duration_minutes=5)),
            ]

        if template == SessionTemplate.ENGINE_DAY:
            return [
                (BlockType.WARM_UP, BlockHints(duration_minutes=12)),
                (BlockType.ENGINE, BlockHints(
                    duration_minutes=30, target_stimulus=Stimulus.AEROBIC_THRESHOLD,
                    target_format=BlockFormat.INTERVALS, rounds=5, rpe=8.0)),
                (BlockType.AEROBIC_Z2, BlockHints(
                    duration_minutes=20, target_stimulus=Stimulus.AEROBIC_Z2,
                    target_format=BlockFormat.STEADY)),
                (BlockType.COOLDOWN, BlockHints(duration_minutes=5)),
            ]

        if template == SessionTemplate.GYMNASTIC_DAY:
            return [
                (BlockType.WARM_UP, BlockHints(duration_minutes=10)),
                (BlockType.SKILL, BlockHints(
                    duration_minutes=12, target_stimulus=Stimulus.SKILL_ACQUISITION,
                    target_modalities=["G"])),
                (BlockType.GYMNASTICS, BlockHints(
                    duration_minutes=15, target_stimulus=Stimulus.GYMNASTIC_CAPACITY,
                    target_modalities=["G"], target_format=BlockFormat.EMOM)),
                (BlockType.METCON, BlockHints(
                    duration_minutes=10, target_stimulus=Stimulus.MIXED_MODAL,
                    target_format=BlockFormat.AMRAP)),
                (BlockType.COOLDOWN, BlockHints(duration_minutes=5)),
            ]

        if template == SessionTemplate.RECOVERY:
            return [
                (BlockType.MOBILITY, BlockHints(duration_minutes=20)),
                (BlockType.COOLDOWN, BlockHints(duration_minutes=10)),
            ]

        if template == SessionTemplate.OPEN_GYM:
            return []

        return [
            (BlockType.WARM_UP, BlockHints(duration_minutes=10)),
            (BlockType.METCON, BlockHints(duration_minutes=20)),
            (BlockType.COOLDOWN, BlockHints(duration_minutes=5)),
        ]

    def _strength_focus_tags(self, ctx: ProgrammingContext) -> list[str]:
        focus = " ".join(ctx.weekly_focus).lower()
        if "squat" in focus:
            return ["squatting", "knee_dominant"]
        if "pull" in focus or "deadlift" in focus:
            return ["hip_hinge", "pulling_vertical"]
        if "press" in focus or "overhead" in focus:
            return ["pressing_vertical", "overhead"]
        return ["squatting"] if ctx.day_number % 2 == 1 else ["hip_hinge"]

    def _primary_stimulus(self, template: SessionTemplate, ctx: ProgrammingContext) -> Stimulus:
        mapping = {
            SessionTemplate.STRENGTH_DAY: Stimulus.STRENGTH_VOLUME,
            SessionTemplate.METCON_ONLY: Stimulus.MIXED_MODAL,
            SessionTemplate.ENGINE_DAY: Stimulus.AEROBIC_THRESHOLD,
            SessionTemplate.GYMNASTIC_DAY: Stimulus.GYMNASTIC_CAPACITY,
            SessionTemplate.RECOVERY: Stimulus.RECOVERY,
            SessionTemplate.OPEN_GYM: Stimulus.RECOVERY,
            SessionTemplate.SKILL_DAY: Stimulus.SKILL_ACQUISITION,
            SessionTemplate.TEST_DAY: Stimulus.STRENGTH_MAX,
            SessionTemplate.COMP_SIM: Stimulus.MIXED_MODAL,
        }
        return mapping.get(template, Stimulus.MIXED_MODAL)

    def _title_for(self, template: SessionTemplate, ctx: ProgrammingContext) -> str:
        return f"W{ctx.week_number}D{ctx.day_number} — {template.value}"


# ============================================================
# HEURISTIC COMPOSER (MVP rule-based)
# ============================================================

class HeuristicComposer:
    """Rule-based composer. Pega primeiro match para reprodutibilidade."""

    def __init__(self, library: MovementLibrary):
        self.library = library

    def compose_block(self, *, order: int, block_type: BlockType,
                      hints: BlockHints, ctx: ProgrammingContext) -> WorkoutBlock:
        candidates = self._candidate_movements(hints, ctx)

        if block_type == BlockType.WARM_UP:
            return self._warm_up_block(order, hints, ctx)
        if block_type == BlockType.ACTIVATION:
            return self._activation_block(order, hints)
        if block_type == BlockType.COOLDOWN:
            return self._cooldown_block(order, hints)
        if block_type == BlockType.MOBILITY:
            return self._mobility_block(order, hints)
        if block_type == BlockType.STRENGTH_PRIMARY:
            return self._strength_primary_block(order, hints, ctx, candidates)
        if block_type == BlockType.STRENGTH_SECONDARY:
            return self._strength_secondary_block(order, hints, candidates)
        if block_type == BlockType.METCON:
            return self._metcon_block(order, hints, ctx, candidates)
        if block_type == BlockType.ENGINE:
            return self._engine_block(order, hints)
        if block_type == BlockType.AEROBIC_Z2:
            return self._z2_block(order, hints)
        if block_type == BlockType.SKILL:
            return self._skill_block(order, hints, ctx)
        if block_type == BlockType.GYMNASTICS:
            return self._gym_capacity_block(order, hints, candidates)
        if block_type == BlockType.MIDLINE:
            return self._midline_block(order, hints)

        return WorkoutBlock(order=order, type=block_type, duration_minutes=hints.duration_minutes or 5)

    def _candidate_movements(self, hints: BlockHints, ctx: ProgrammingContext) -> list[Movement]:
        movs = self.library.filter_by_equipment(ctx.athlete.equipment_available)
        if hints.target_modalities:
            movs = [m for m in movs if any(mod in hints.target_modalities for mod in m.modalities)]
        if hints.target_tags:
            movs = [m for m in movs if any(t in m.tags for t in hints.target_tags)]
        movs = [m for m in movs if not self._is_restricted(m, ctx.athlete)]
        movs = [m for m in movs if not m.is_warmup_only]
        return movs

    def _is_restricted(self, movement: Movement, athlete: Athlete) -> bool:
        for inj in athlete.active_injuries:
            if inj.resolved_date:
                continue
            if movement.id in inj.affected_movements:
                return True
            if any(p in movement.tags for p in inj.affected_patterns):
                return True
        return False

    def _warm_up_block(self, order: int, hints: BlockHints, ctx: ProgrammingContext) -> WorkoutBlock:
        cardio = "row" if "rower" in ctx.athlete.equipment_available else "run"
        return WorkoutBlock(
            order=order, type=BlockType.WARM_UP,
            duration_minutes=hints.duration_minutes or 10,
            intent="Elevar temperatura, ROM completo",
            movements=[
                MovementPrescription(movement_id=cardio, time_seconds=240, pacing="easy"),
                MovementPrescription(movement_id="world_greatest_stretch", reps=10),
                MovementPrescription(movement_id="cossack_squat", reps=10),
            ],
        )

    def _activation_block(self, order: int, hints: BlockHints) -> WorkoutBlock:
        return WorkoutBlock(
            order=order, type=BlockType.ACTIVATION,
            format=BlockFormat.NOT_FOR_TIME,
            duration_minutes=hints.duration_minutes or 5,
            intent="Ativação posterior + core",
            movements=[
                MovementPrescription(movement_id="banded_glute_bridge", reps=15,
                                      load=LoadSpec(type="bodyweight")),
                MovementPrescription(movement_id="dead_bug", reps=10,
                                      load=LoadSpec(type="bodyweight")),
            ],
        )

    def _cooldown_block(self, order: int, hints: BlockHints) -> WorkoutBlock:
        return WorkoutBlock(
            order=order, type=BlockType.COOLDOWN,
            duration_minutes=hints.duration_minutes or 5,
            intent="Down-regulation",
            movements=[
                MovementPrescription(movement_id="couch_stretch", time_seconds=120),
                MovementPrescription(movement_id="box_breathing", time_seconds=180),
            ],
        )

    def _mobility_block(self, order: int, hints: BlockHints) -> WorkoutBlock:
        return WorkoutBlock(
            order=order, type=BlockType.MOBILITY,
            duration_minutes=hints.duration_minutes or 20,
            intent="Mobilidade de quadril, tornozelo, ombro",
            movements=[
                MovementPrescription(movement_id="couch_stretch", time_seconds=180),
                MovementPrescription(movement_id="cossack_squat", reps=10),
                MovementPrescription(movement_id="world_greatest_stretch", reps=10),
            ],
        )

    def _strength_primary_block(self, order: int, hints: BlockHints,
                                ctx: ProgrammingContext, candidates: list[Movement]) -> WorkoutBlock:
        barbell = [m for m in candidates if m.category == "barbell"]
        chosen = barbell[0] if barbell else candidates[0]
        pct = 70 + (ctx.week_number * 2.5) if ctx.phase == Phase.BUILD else 75
        sets = [
            MovementPrescription(movement_id=chosen.id, reps=5,
                                  load=LoadSpec(type="percent_1rm", value=pct, reference_lift=chosen.id))
            for _ in range(5)
        ]
        return WorkoutBlock(
            order=order, type=BlockType.STRENGTH_PRIMARY,
            format=BlockFormat.SETS_REPS, stimulus=hints.target_stimulus,
            duration_minutes=hints.duration_minutes,
            intent=hints.intent or f"Strength volume — {chosen.name}",
            movements=sets, rest_seconds=180,
        )

    def _strength_secondary_block(self, order: int, hints: BlockHints,
                                  candidates: list[Movement]) -> WorkoutBlock:
        accessories = [m for m in candidates if m.category in ("dumbbell", "kettlebell", "accessory")]
        chosen = accessories[0] if accessories else candidates[-1]
        return WorkoutBlock(
            order=order, type=BlockType.STRENGTH_SECONDARY,
            format=BlockFormat.SETS_REPS, stimulus=Stimulus.HYPERTROPHY,
            duration_minutes=hints.duration_minutes,
            intent="Volume complementar", rounds=4, rest_seconds=90,
            movements=[MovementPrescription(movement_id=chosen.id, reps=8,
                                             load=LoadSpec(type="rpe", value=hints.rpe or 7.0))],
        )

    def _metcon_block(self, order: int, hints: BlockHints,
                      ctx: ProgrammingContext, candidates: list[Movement]) -> WorkoutBlock:
        wl = next((m for m in candidates if "W" in m.modalities and m.category != "barbell"), None)
        gym = next((m for m in candidates if "G" in m.modalities and not m.equipment), None)
        mono = next((m for m in self.library.find_by_modality("M")
                     if set(m.equipment).issubset(ctx.athlete.equipment_available)), None)
        movements = []
        if wl:
            movements.append(MovementPrescription(movement_id=wl.id, reps=10,
                                                  load=LoadSpec(type="absolute_kg", value=22.5)))
        if gym:
            movements.append(MovementPrescription(movement_id=gym.id, reps=15))
        if mono:
            if mono.id == "run":
                movements.append(MovementPrescription(movement_id=mono.id, distance_meters=200))
            else:
                movements.append(MovementPrescription(movement_id=mono.id, calories=15))
        return WorkoutBlock(
            order=order, type=BlockType.METCON,
            format=hints.target_format or BlockFormat.AMRAP,
            stimulus=hints.target_stimulus or Stimulus.MIXED_MODAL,
            duration_minutes=hints.duration_minutes,
            intent=hints.intent or "Mixed modal triplet",
            intensity_rpe=hints.rpe, movements=movements,
        )

    def _engine_block(self, order: int, hints: BlockHints) -> WorkoutBlock:
        return WorkoutBlock(
            order=order, type=BlockType.ENGINE,
            format=BlockFormat.INTERVALS, stimulus=Stimulus.AEROBIC_THRESHOLD,
            duration_minutes=hints.duration_minutes or 30,
            rounds=hints.rounds or 5, work_seconds=240, rest_seconds=120,
            target_pace="2:00/500m", intensity_rpe=hints.rpe or 8.0,
            intent="Threshold sustentável",
            movements=[MovementPrescription(movement_id="row", distance_meters=1000,
                                             pacing="2:00/500m split")],
        )

    def _z2_block(self, order: int, hints: BlockHints) -> WorkoutBlock:
        return WorkoutBlock(
            order=order, type=BlockType.AEROBIC_Z2,
            format=BlockFormat.STEADY, stimulus=Stimulus.AEROBIC_Z2,
            duration_minutes=hints.duration_minutes or 20,
            target_pace="HR 130-145, nasal breathing", intent="Base aeróbica Z2",
            movements=[MovementPrescription(movement_id="bike",
                                             time_seconds=(hints.duration_minutes or 20) * 60,
                                             pacing="zone 2")],
        )

    def _skill_block(self, order: int, hints: BlockHints, ctx: ProgrammingContext) -> WorkoutBlock:
        skills = [m for m in self.library.find_by_modality("G")
                  if m.skill_level >= 3
                  and not self._is_restricted(m, ctx.athlete)
                  and set(m.equipment).issubset(ctx.athlete.equipment_available)]
        chosen = skills[0] if skills else self.library.get("pull_up")
        return WorkoutBlock(
            order=order, type=BlockType.SKILL,
            format=BlockFormat.QUALITY, stimulus=Stimulus.SKILL_ACQUISITION,
            duration_minutes=hints.duration_minutes or 12,
            intent=f"Skill — {chosen.name}, foco em técnica",
            movements=[MovementPrescription(movement_id=chosen.id, reps=3,
                                             notes="EMOM 8min, foco em qualidade")],
        )

    def _gym_capacity_block(self, order: int, hints: BlockHints,
                            candidates: list[Movement]) -> WorkoutBlock:
        gym_movs = [m for m in candidates if "G" in m.modalities]
        chosen = gym_movs[0] if gym_movs else self.library.get("pull_up")
        return WorkoutBlock(
            order=order, type=BlockType.GYMNASTICS,
            format=hints.target_format or BlockFormat.EMOM,
            stimulus=Stimulus.GYMNASTIC_CAPACITY,
            duration_minutes=hints.duration_minutes or 15,
            intent="Capacidade gímnica",
            movements=[MovementPrescription(movement_id=chosen.id, reps=8)],
        )

    def _midline_block(self, order: int, hints: BlockHints) -> WorkoutBlock:
        return WorkoutBlock(
            order=order, type=BlockType.MIDLINE,
            format=BlockFormat.NOT_FOR_TIME, stimulus=Stimulus.MIDLINE_ENDURANCE,
            duration_minutes=hints.duration_minutes or 8,
            rounds=hints.rounds or 3, intent="Midline endurance",
            movements=[
                MovementPrescription(movement_id="hollow_hold", time_seconds=30),
                MovementPrescription(movement_id="plank", time_seconds=45),
                MovementPrescription(movement_id="dead_bug", reps=10),
            ],
        )


# ============================================================
# CLAUDE COMPOSER — STUB
# ============================================================

class ClaudeComposer:
    """STUB — Implementar com Anthropic API.

    Estrutura esperada:
      1. Monta prompt estruturado com (block_type, hints, ctx, library_subset)
      2. Chama Anthropic API com response_format=JSON
      3. Valida resposta contra schema (Pydantic)
      4. Constrói WorkoutBlock validado

    Vantagens: variedade, intent rico, adaptação contextual, scaling per-tier.
    """
    def __init__(self, library: MovementLibrary, api_key: str):
        self.library = library
        raise NotImplementedError("Implementar em sprint dedicada — ver docstring")

    def compose_block(self, *, order, block_type, hints, ctx) -> WorkoutBlock:
        raise NotImplementedError