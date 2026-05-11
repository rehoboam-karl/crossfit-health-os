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
    LLM para metcon/skill/engine/gym/midline. Implementa MovementComposer.

    Estado per-session: rastreia movement_ids prescritos com percent_1rm pelos
    blocos anteriores da sessão e injeta exclusão em `self.llm` antes de cada
    bloco LLM. Reset acontece em `order == 1` (primeiro bloco da próxima
    sessão). Evita o stacking de INOL >1.0 quando o LLM repete o movimento
    primário (típico em semanas com weekly_focus=squat_volume).
    """

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
        self._session_claimed: set[str] = set()

    @property
    def name(self) -> str:
        return f"hybrid_{self.provider.family}"

    def compose_block(
        self, *, order: int, block_type: BlockType,
        hints: BlockHints, ctx: ProgrammingContext,
    ) -> WorkoutBlock:
        # SessionPlanner sempre começa um session em order=1. Reset aqui.
        if order == 1:
            self._session_claimed = set()

        if block_type in _HEURISTIC_BLOCKS:
            block = self.heuristic.compose_block(
                order=order, block_type=block_type,
                hints=hints, ctx=ctx,
            )
        else:
            self.llm._excluded_movement_ids = frozenset(self._session_claimed)
            try:
                block = self.llm.compose_block(
                    order=order, block_type=block_type,
                    hints=hints, ctx=ctx,
                )
            finally:
                self.llm._excluded_movement_ids = frozenset()

        # Marca movimentos com percent_1rm — são os que contribuem para INOL
        # e estavam causando o stacking. Movements sem %1RM passam livres.
        for mp in block.movements:
            if mp.load and mp.load.type == "percent_1rm":
                self._session_claimed.add(mp.movement_id)
        return block
