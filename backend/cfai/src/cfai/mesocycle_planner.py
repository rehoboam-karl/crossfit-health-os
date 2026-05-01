"""
Mesocycle planner — Sprint 5e.

Orquestra SessionPlanner ao longo de N semanas, gerando uma estrutura
Mesocycle completa (Week × sessions). Necessário pra avaliar dimensões
multi-semana: progressive_overload, deload_presence, ACWR, movement_variety.

Decisão arquitetural: mantém SessionPlanner intocado. Mesocycle planner
é um wrapper que itera (week, day) chamando o planner por sessão e
populando ProgrammingContext.recent_sessions com sessões anteriores —
permite que composers (especialmente LLMComposer) considerem progressão.

Não é Pydantic — é orquestrador. A saída sim (Mesocycle) é validada Pydantic.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date, timedelta
from typing import Optional

from .athlete import Athlete
from .movements import MovementLibrary
from .programmer import (
    MovementComposer, ProgrammingContext, SessionPlanner,
)
from .workout_schema import (
    Mesocycle, Phase, Session, SessionTemplate, Week,
)


# Default split semanal — 5 dias on (D1-D5), D6 recovery, D7 open_gym.
# Sessões geradas: D1-D5 (5 por semana). D6/D7 ficam fora do plan_session loop
# pra economizar custo (D6 recovery + D7 open_gym têm pouco conteúdo a evaluar).
DEFAULT_SESSIONS_PER_WEEK = 5


@dataclass
class MesocycleSpec:
    """Plano do mesociclo: phases por semana + flags de deload."""
    weeks: list[Phase]               # phase efetiva de CADA semana
    deload_weeks: set[int] = None    # week_numbers (1-indexed) marcados deload

    def __post_init__(self):
        if self.deload_weeks is None:
            self.deload_weeks = set()


# Spec default: 4 semanas — 3 BUILD + 1 DELOAD na semana 4
DEFAULT_4WEEK_BUILD = MesocycleSpec(
    weeks=[Phase.BUILD, Phase.BUILD, Phase.BUILD, Phase.DELOAD],
    deload_weeks={4},
)


class MesocyclePlanner:
    """Constrói Mesocycle completo iterando SessionPlanner por (week, day)."""

    def __init__(
        self,
        library: MovementLibrary,
        composer: MovementComposer,
        sessions_per_week: int = DEFAULT_SESSIONS_PER_WEEK,
    ):
        self.library = library
        self.composer = composer
        self.sessions_per_week = sessions_per_week
        self.session_planner = SessionPlanner(library, composer)

    def plan_mesocycle(
        self,
        *,
        athlete: Athlete,
        spec: MesocycleSpec,
        start_date: Date,
        primary_focus: list[str],
        target_benchmarks: Optional[list[str]] = None,
        weekly_focus: Optional[list[str]] = None,
        meso_id: str = "meso_001",
        meso_name: str = "Generated Mesocycle",
    ) -> Mesocycle:
        """Gera mesociclo completo. recent_sessions é populado entre semanas
        para que composers vejam histórico — necessário pra progression_logic."""
        weeks: list[Week] = []
        history: list[Session] = []  # sessões geradas até agora

        for week_idx, phase in enumerate(spec.weeks, start=1):
            week_sessions: list[Session] = []
            for day in range(1, self.sessions_per_week + 1):
                target_date = start_date + timedelta(
                    days=(week_idx - 1) * 7 + (day - 1)
                )
                ctx = ProgrammingContext(
                    athlete=athlete,
                    library=self.library,
                    phase=phase,
                    week_number=week_idx,
                    day_number=day,
                    target_date=target_date,
                    weekly_focus=weekly_focus or [],
                    recent_sessions=history[-7:],  # últimos 7 dias = ~1 semana
                )
                sess = self.session_planner.plan_session(ctx)
                week_sessions.append(sess)
                history.append(sess)

            week = Week(
                week_number=week_idx,
                theme=f"{phase.value} W{week_idx}",
                sessions=week_sessions,
                deload=(week_idx in spec.deload_weeks),
            )
            weeks.append(week)

        # phase do mesociclo: BUILD se há build, senão a primeira phase
        meso_phase = (
            Phase.BUILD if Phase.BUILD in spec.weeks
            else spec.weeks[0]
        )

        return Mesocycle(
            id=meso_id,
            name=meso_name,
            phase=meso_phase,
            start_date=start_date,
            duration_weeks=len(spec.weeks),
            weeks=weeks,
            primary_focus=primary_focus,
            target_benchmarks=target_benchmarks or [],
        )
