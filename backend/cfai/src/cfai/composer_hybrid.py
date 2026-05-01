"""
Hybrid composer — Sprint 5h.

Best-of-both: HeuristicComposer + LLMComposer combinados via dispatch
por block_type. Heurístico cuida de load science (Prilepin/INOL ótimos
por construção); LLM cuida de criatividade narrativa em blocos onde
diversidade e intent agregam valor.

Decisão arquitetural:
- HEURISTIC handles: WARM_UP, ACTIVATION, MOBILITY, COOLDOWN
  (rotina determinística, sem ganho LLM)
  + STRENGTH_PRIMARY, STRENGTH_SECONDARY, OLY_COMPLEX
  (load science: 5x5 @ 75% sempre cabe Prilepin/INOL — LLM derrapa
  ao tentar diversificar volume)
- LLM handles: METCON, ENGINE, AEROBIC_Z2, SKILL, GYMNASTICS,
  MIDLINE, ACCESSORY
  (criatividade na escolha de movimentos, intent narrativo,
  variação semana-a-semana)

Esperado em multi-week mesocycle:
- Prilepin/INOL: paridade com HeuristicComposer (load=heurístico)
- progression_logic L2: paridade com LLMComposer (intent=LLM, e
  recent_sessions enrichment ainda flui)
- Schema_failure rate cai (menos blocos vão pro LLM)
- Cost cai ~30-40% (menos LLM calls)

Uso:
    from cfai.llm_providers import OpenAIProvider
    from cfai.composer_hybrid import HybridComposer

    composer = HybridComposer(provider=OpenAIProvider(), library=lib)
    planner = SessionPlanner(library=lib, composer=composer)
    session = planner.plan_session(ctx)
"""
from __future__ import annotations

from .composer_llm import LLMComposer, LLMProviderLike
from .movements import MovementLibrary
from .programmer import (
    BlockHints, HeuristicComposer, MovementComposer, ProgrammingContext,
)
from .workout_schema import BlockType, WorkoutBlock


# Blocos onde heurístico vence ou empata com LLM e tem load science correta
_HEURISTIC_BLOCKS = frozenset({
    BlockType.WARM_UP,
    BlockType.ACTIVATION,
    BlockType.MOBILITY,
    BlockType.COOLDOWN,
    BlockType.STRENGTH_PRIMARY,
    BlockType.STRENGTH_SECONDARY,
    BlockType.OLY_COMPLEX,
})


class HybridComposer:
    """Dispatcher: heurístico para load science + warm/cool;
    LLM para metcon/skill/engine/gym/midline. Implementa MovementComposer."""

    composer_status = "uncalibrated"  # consistente com LLMProviderJudge

    def __init__(
        self,
        provider: LLMProviderLike,
        library: MovementLibrary,
        max_retries: int = 3,
    ):
        self.provider = provider
        self.library = library
        self.heuristic = HeuristicComposer(library)
        self.llm = LLMComposer(
            provider=provider, library=library,
            max_retries=max_retries, fallback=self.heuristic,
        )

    @property
    def name(self) -> str:
        return f"hybrid_{self.provider.family}"

    def compose_block(
        self, *, order: int, block_type: BlockType,
        hints: BlockHints, ctx: ProgrammingContext,
    ) -> WorkoutBlock:
        if block_type in _HEURISTIC_BLOCKS:
            return self.heuristic.compose_block(
                order=order, block_type=block_type,
                hints=hints, ctx=ctx,
            )
        return self.llm.compose_block(
            order=order, block_type=block_type,
            hints=hints, ctx=ctx,
        )
