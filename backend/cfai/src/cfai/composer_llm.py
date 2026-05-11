"""
LLM-based composer — Sprint 3.

Plug qualquer LLMProvider (Anthropic, OpenAI, DeepSeek, Groq, Minimax) como
MovementComposer. Substitui o `HeuristicComposer` em blocos onde criatividade
adiciona valor (escolha de movimentos, intent narrativo, scaling contextual).

Arquitetura:
- Implementa `MovementComposer` Protocol (ver programmer.py).
- Para blocos não-criativos (warm_up/cooldown/mobility/activation) delega ao
  HeuristicComposer — LLM não agrega valor e tende a inventar movement_ids.
- Para blocos criativos (strength/metcon/engine/skill/gym/midline) monta prompt
  estruturado contendo: papel do bloco, hints, perfil do atleta, catálogo
  filtrado de movimentos disponíveis, schema de output.
- Output é JSON parseado e validado contra Pydantic. movement_id é checado
  contra o catálogo (evita LLM inventar).
- Retry até `max_retries` em schema_failure ou movement_id inválido. Fallback
  final para HeuristicComposer (graceful degradation).
- Telemetria via cost_tracker do provider (latency, tokens, cost, schema_fail).

Status default: `composer_status="uncalibrated"` — não usar em produção sem
test set congelado + comparação L1 contra HeuristicComposer.

Uso:
    from cfai.llm_providers import GroqProvider
    from cfai.composer_llm import LLMComposer

    provider = GroqProvider()
    composer = LLMComposer(provider=provider, library=lib)
    planner = SessionPlanner(library=lib, composer=composer)
    session = planner.plan_session(ctx)
"""
from __future__ import annotations

from typing import Optional, Protocol

from .athlete import Athlete
from .movements import Movement, MovementLibrary
from .programmer import (
    BlockHints, HeuristicComposer, MovementComposer, ProgrammingContext,
    expand_scaling,
)
from .workout_schema import (
    BlockFormat, BlockType, LoadSpec, MovementPrescription, Stimulus,
    WorkoutBlock,
)


# ============================================================
# PROVIDER INTERFACE (subset of llm_providers.LLMProvider)
# ============================================================

class LLMProviderLike(Protocol):
    """Subset do contrato de LLMProvider que o composer precisa."""
    family: str
    model: str
    name: str

    def complete(
        self, system: str, user: str,
        json_mode: bool = True, temperature: float = 0.0,
        max_tokens: int = 1024, label: Optional[str] = None,
    ) -> dict: ...


# Blocos que delegamos pro heurístico (sem valor LLM, schema rígido)
_DELEGATE_TO_HEURISTIC = {
    BlockType.WARM_UP, BlockType.ACTIVATION,
    BlockType.COOLDOWN, BlockType.MOBILITY,
}


# ============================================================
# COMPOSER
# ============================================================

class LLMComposer:
    """Composer parametrizado por LLMProvider. Implementa MovementComposer."""

    composer_status = "uncalibrated"  # parallel a LLMProviderJudge

    def __init__(
        self,
        provider: LLMProviderLike,
        library: MovementLibrary,
        max_retries: int = 3,
        max_movements_in_prompt: int = 30,
        fallback: Optional[MovementComposer] = None,
    ):
        self.provider = provider
        self.library = library
        self.max_retries = max_retries
        self.max_movements_in_prompt = max_movements_in_prompt
        # Heurístico é o fallback default (e quem cuida de blocos triviais).
        self.fallback: MovementComposer = fallback or HeuristicComposer(library)
        # Per-session exclusion. HybridComposer sets this between blocks to
        # prevent LLM from re-prescribing movements already claimed at %1RM
        # by the heuristic strength block (caused INOL stacking >1.0 on
        # back_squat during squat-focused weeks — Sprint 5h followup).
        # Reset to empty per `compose_block`; whoever orchestrates is expected
        # to set it before the call.
        self._excluded_movement_ids: frozenset[str] = frozenset()

    # ---------- API pública (Protocol) ----------

    def compose_block(
        self, *, order: int, block_type: BlockType,
        hints: BlockHints, ctx: ProgrammingContext,
    ) -> WorkoutBlock:
        if block_type in _DELEGATE_TO_HEURISTIC:
            return self.fallback.compose_block(
                order=order, block_type=block_type, hints=hints, ctx=ctx,
            )

        candidates = self._candidates(block_type, hints, ctx)
        if not candidates:
            # Sem movimentos viáveis — heurístico tem fallbacks específicos
            return self.fallback.compose_block(
                order=order, block_type=block_type, hints=hints, ctx=ctx,
            )

        last_error: Optional[str] = None
        for attempt in range(self.max_retries):
            system_msg = self._system_prompt()
            user_msg = self._user_prompt(
                block_type=block_type, hints=hints, ctx=ctx,
                candidates=candidates, last_error=last_error,
            )
            label = f"composer_{block_type.value}_attempt{attempt+1}"
            try:
                resp = self.provider.complete(
                    system=system_msg, user=user_msg,
                    json_mode=True, temperature=0.3, max_tokens=4096,
                    label=label,
                )
            except Exception as e:
                last_error = f"provider_error: {type(e).__name__}: {e}"
                continue

            payload = resp.get("parsed")
            if payload is None:
                last_error = "json_parse_failed: response was not valid JSON"
                continue

            try:
                block = self._build_block(
                    payload=payload, order=order, block_type=block_type,
                    hints=hints, candidates=candidates,
                )
                return block
            except (ValueError, KeyError, TypeError) as e:
                last_error = f"schema_validation: {type(e).__name__}: {e}"
                continue

        # Todas tentativas falharam — fallback heurístico (degradação graciosa)
        return self.fallback.compose_block(
            order=order, block_type=block_type, hints=hints, ctx=ctx,
        )

    # ---------- Filtragem de candidatos ----------

    def _candidates(
        self, block_type: BlockType, hints: BlockHints, ctx: ProgrammingContext,
    ) -> list[Movement]:
        movs = self.library.filter_by_equipment(ctx.athlete.equipment_available)
        movs = [m for m in movs if not m.is_warmup_only]
        movs = [m for m in movs if not _is_restricted(m, ctx.athlete)]
        # Per-session exclusion (movements already claimed by prior blocks in
        # this session). Skip if filter would empty the catalog — fallback to
        # unfiltered list is preferable to hard-failing the block.
        if self._excluded_movement_ids:
            filtered = [m for m in movs if m.id not in self._excluded_movement_ids]
            if filtered:
                movs = filtered

        # Filtros suaves por hint — best-effort, não exclui se vazia
        if hints.target_modalities:
            filt = [
                m for m in movs
                if any(mod in hints.target_modalities for mod in m.modalities)
            ]
            movs = filt or movs

        # Tag-based scoping para strength
        if block_type in (BlockType.STRENGTH_PRIMARY, BlockType.STRENGTH_SECONDARY):
            if hints.target_tags:
                tagged = [m for m in movs if any(t in m.tags for t in hints.target_tags)]
                if tagged:
                    movs = tagged
            else:
                movs = [m for m in movs if m.category in (
                    "barbell", "dumbbell", "kettlebell", "accessory"
                )]

        if block_type == BlockType.GYMNASTICS:
            movs = [m for m in movs if "G" in m.modalities]
        if block_type == BlockType.SKILL:
            movs = [m for m in movs if "G" in m.modalities and m.skill_level >= 3]
        if block_type == BlockType.ENGINE or block_type == BlockType.AEROBIC_Z2:
            movs = [m for m in movs if "M" in m.modalities]
        if block_type == BlockType.MIDLINE:
            movs = [m for m in movs if "midline" in m.tags or "anti_rotation" in m.tags
                    or "spinal_flexion" in m.tags]

        # Cap pra prompt não inflar
        return movs[: self.max_movements_in_prompt]

    # ---------- Prompt construction ----------

    def _system_prompt(self) -> str:
        return (
            "You are an elite CrossFit programmer (HWPO/Mayhem methodology). "
            "Given a block role and athlete context, output a single workout "
            "block as JSON. Stimulus drives selection: pick movements whose "
            "biomechanics + modality match the target stimulus. Respect "
            "athlete equipment and injury restrictions strictly. "
            "Use only movement_id values from the provided catalog. "
            "When prior session history is provided, ensure progressive "
            "overload — STRENGTH_PRIMARY %1RM should grow ~2-3% per week in "
            "BUILD phase vs the previous week's load on the same lift. "
            "Avoid stimulus monotony — vary block stimuli across the week. "
            "Output ONLY valid JSON matching the schema — no prose, no "
            "markdown fences."
        )

    def _user_prompt(
        self, *, block_type: BlockType, hints: BlockHints,
        ctx: ProgrammingContext, candidates: list[Movement],
        last_error: Optional[str],
    ) -> str:
        athlete_summary = self._athlete_summary(ctx.athlete)
        catalog = self._catalog_summary(candidates)
        hints_dict = self._hints_payload(hints)
        schema = self._output_schema_doc()
        history = self._recent_sessions_summary(ctx)

        retry_block = ""
        if last_error:
            retry_block = (
                f"\n\nPREVIOUS ATTEMPT FAILED: {last_error}\n"
                f"Fix the issue and try again.\n"
            )

        load_guidance = self._strength_load_guidance(block_type)
        focus_scope = self._weekly_focus_scope_guidance(block_type, ctx.weekly_focus)

        return (
            f"BLOCK_ROLE: {block_type.value}\n"
            f"PHASE: {ctx.phase.value}, week {ctx.week_number}, day {ctx.day_number}\n"
            f"WEEKLY_FOCUS: {ctx.weekly_focus}\n"
            f"{focus_scope}"
            f"HINTS:\n{hints_dict}\n\n"
            f"ATHLETE:\n{athlete_summary}\n"
            f"{history}\n"
            f"{load_guidance}"
            f"MOVEMENT_CATALOG (use ONLY these movement_id values):\n{catalog}\n\n"
            f"OUTPUT_SCHEMA:\n{schema}"
            f"{retry_block}"
        )

    @staticmethod
    def _weekly_focus_scope_guidance(
        block_type: BlockType, weekly_focus: list[str],
    ) -> str:
        """WEEKLY_FOCUS dosa o STRENGTH_PRIMARY do dia, não o resto da sessão.
        Sem essa nota, o LLM defaultava back_squat/front_squat com %1RM em
        metcons, skill_days e gymnastic_days dos squat-focus weeks — INOL
        per_movement caía para 0.25-0.40 e o test set falhava (ver
        hybrid_grok 7/20 sessions failing INOL antes do guard)."""
        if not weekly_focus:
            return ""
        if block_type in (
            BlockType.STRENGTH_PRIMARY,
            BlockType.STRENGTH_SECONDARY,
            BlockType.OLY_COMPLEX,
        ):
            return ""
        return (
            "WEEKLY_FOCUS_SCOPE: weekly_focus dosa apenas STRENGTH_PRIMARY do "
            "dia. Para este bloco, NÃO use percent_1rm em movimentos que "
            "implementem o padrão do focus (ex: focus=squat_volume → não "
            "prescreva back_squat/front_squat/overhead_squat com percent_1rm). "
            "Esses movimentos podem aparecer com bodyweight/absolute_kg leve "
            "ou ser substituídos por padrões complementares.\n"
        )

    @staticmethod
    def _strength_load_guidance(block_type: BlockType) -> str:
        """Sprint 5g: Prilepin chart + INOL target — só para blocos onde
        percent_1rm faz sentido (strength_primary, strength_secondary,
        oly_complex). Faz alinhamento direto com PRILEPIN_TABLE em
        evaluation.py (mesmas zonas e ranges)."""
        if block_type not in (
            BlockType.STRENGTH_PRIMARY,
            BlockType.STRENGTH_SECONDARY,
            BlockType.OLY_COMPLEX,
        ):
            return ""
        return (
            "\nLOAD_SCIENCE (REQUIRED for strength blocks):\n"
            "  Prilepin's table (zone %1RM → reps/set max, optimal_total, valid_range):\n"
            "    <70%   : ≤6 reps/set, optimal 24 total, valid 18-30\n"
            "    70-79% : ≤6 reps/set, optimal 18 total, valid 12-24\n"
            "    80-89% : ≤4 reps/set, optimal 15 total, valid 10-20\n"
            "    90%+   : ≤2 reps/set, optimal  7 total, valid  4-10\n"
            "  INOL = reps / (100 - %1RM) per exercise per session, target 0.4-1.0.\n"
            "  Examples that PASS:\n"
            "    5x5 @ 75% (25 reps, INOL=1.0) — borderline ok\n"
            "    5x3 @ 80% (15 reps, INOL=0.75) — optimal\n"
            "    4x2 @ 88% (8 reps, INOL=0.67) — optimal peaking\n"
            "  Examples that FAIL:\n"
            "    5x5 @ 90% (25 reps in 90+ zone, valid_range was 4-10) — overshoot\n"
            "    8x5 @ 70% (40 reps, valid_range 12-24) — overshoot\n"
            "    3x2 @ 75% (6 reps, valid_range 12-24) — undershoot\n"
            "  Pick reps × sets that land in the optimal_total or close to it.\n\n"
        )

    @staticmethod
    def _recent_sessions_summary(ctx: ProgrammingContext) -> str:
        """Sumário compacto de recent_sessions (Sprint 5f). Vazio se ctx
        não tiver histórico — typical em chamadas standalone do SessionPlanner.
        Para mesocycle planning, MesocyclePlanner popula com últimas sessões."""
        if not ctx.recent_sessions:
            return ""
        # Agrupa loads de strength_primary por (week, movement_id)
        lines = []
        for s in ctx.recent_sessions[-7:]:  # cap 7 sessions
            strength_loads: list[str] = []
            stims: list[str] = []
            for b in s.blocks:
                if b.stimulus:
                    stims.append(b.stimulus.value)
                if b.type.value == "strength_primary":
                    for mp in b.movements:
                        if mp.load and mp.load.type == "percent_1rm":
                            strength_loads.append(
                                f"{mp.movement_id}@{mp.load.value:.0f}%"
                            )
                        elif mp.load and mp.load.type == "absolute_kg":
                            strength_loads.append(
                                f"{mp.movement_id}@{mp.load.value:.0f}kg"
                            )
            stim_summary = ", ".join(sorted(set(stims))[:4]) if stims else "—"
            load_summary = strength_loads[0] if strength_loads else "no_strength"
            lines.append(
                f"  - {s.template.value} | strength_primary={load_summary} | stims=[{stim_summary}]"
            )
        return (
            "\nRECENT_SESSION_HISTORY (use to plan progression — increase "
            "%1RM 2-3% in BUILD vs prior week on same lift):\n"
            + "\n".join(lines)
        )

    @staticmethod
    def _hints_payload(hints: BlockHints) -> str:
        parts = []
        if hints.target_stimulus:
            parts.append(f"  target_stimulus: {hints.target_stimulus.value}")
        if hints.target_format:
            parts.append(f"  target_format: {hints.target_format.value}")
        if hints.target_tags:
            parts.append(f"  target_tags: {hints.target_tags}")
        if hints.target_modalities:
            parts.append(f"  target_modalities: {hints.target_modalities}")
        if hints.duration_minutes is not None:
            parts.append(f"  duration_minutes: {hints.duration_minutes}")
        if hints.rounds is not None:
            parts.append(f"  rounds: {hints.rounds}")
        if hints.rpe is not None:
            parts.append(f"  rpe: {hints.rpe}")
        if hints.intent:
            parts.append(f"  intent: {hints.intent}")
        return "\n".join(parts) if parts else "  (no specific hints)"

    @staticmethod
    def _athlete_summary(athlete: Athlete) -> str:
        prs = ", ".join(
            f"{k}={v.value_kg}kg" for k, v in sorted(athlete.one_rep_maxes.items())
        ) if athlete.one_rep_maxes else "—"
        injuries = [
            f"{i.description} ({i.severity.value})"
            for i in athlete.active_injuries if i.resolved_date is None
        ] or ["none"]
        return (
            f"  body_weight_kg: {athlete.body_weight_kg}\n"
            f"  training_age_years: {athlete.training_age_years}\n"
            f"  equipment: {sorted(athlete.equipment_available)}\n"
            f"  1RMs: {prs}\n"
            f"  active_injuries: {injuries}"
        )

    @staticmethod
    def _catalog_summary(candidates: list[Movement]) -> str:
        lines = []
        for m in candidates:
            mods = "".join(m.modalities)
            lines.append(
                f"  - {m.id} | {m.name} | {mods} | "
                f"cat={m.category} | skill={m.skill_level} | "
                f"tags={m.tags[:5]}"
            )
        return "\n".join(lines)

    @staticmethod
    def _output_schema_doc() -> str:
        return (
            '{\n'
            '  "intent": "<string, narrative purpose>",\n'
            '  "duration_minutes": <int or null>,\n'
            '  "format": "<one of: sets_reps|amrap|emom|e2mom|e3mom|for_time|'
            'for_time_capped|intervals|tabata|chipper|ladder|death_by|steady|'
            'repeats|not_for_time|quality, or null>",\n'
            '  "stimulus": "<one of: aerobic_z2|aerobic_threshold|vo2_max|'
            'lactic_tolerance|alactic_power|mixed_modal|strength_max|'
            'strength_volume|hypertrophy|power|gymnastic_capacity|'
            'skill_acquisition|midline_endurance|recovery, or null>",\n'
            '  "rounds": <int or null>,\n'
            '  "work_seconds": <int or null>,\n'
            '  "rest_seconds": <int or null>,\n'
            '  "intensity_rpe": <float 1-10 or null>,\n'
            '  "target_score": "<string or null>",\n'
            '  "target_pace": "<string or null>",\n'
            '  "coaching_notes": "<string or null>",\n'
            '  "movements": [\n'
            '    {\n'
            '      "movement_id": "<MUST be from catalog>",\n'
            '      "reps": <int or null>,\n'
            '      "time_seconds": <int or null>,\n'
            '      "distance_meters": <int or null>,\n'
            '      "calories": <int or null>,\n'
            '      "load": {\n'
            '        "type": "<absolute_kg|percent_1rm|percent_bw|rpe|ahap|'
            'bodyweight>",\n'
            '        "value": <float or null>,\n'
            '        "reference_lift": "<movement_id or null>"\n'
            '      } or null,\n'
            '      "pacing": "<string or null>",\n'
            '      "notes": "<string or null>"\n'
            '    }\n'
            '  ]\n'
            '}\n'
            'CONSTRAINTS:\n'
            '  - Each movement must have EXACTLY ONE of '
            'reps/time_seconds/distance_meters/calories.\n'
            '  - load.type=percent_1rm REQUIRES reference_lift (a barbell '
            'movement_id).\n'
            '  - load.type=bodyweight or ahap may omit value.\n'
            '  - movement_id MUST exist in the catalog above.\n'
            '  - At least 1 movement.\n'
        )

    # ---------- Build & validate ----------

    def _build_block(
        self, *, payload: dict, order: int, block_type: BlockType,
        hints: BlockHints, candidates: list[Movement],
    ) -> WorkoutBlock:
        catalog_ids = {m.id for m in candidates}
        raw_movs = payload.get("movements") or []
        if not isinstance(raw_movs, list) or not raw_movs:
            raise ValueError("movements must be a non-empty list")

        catalog_by_id = {m.id: m for m in candidates}
        prescriptions: list[MovementPrescription] = []
        for raw in raw_movs:
            if not isinstance(raw, dict):
                raise ValueError("movement entry must be object")
            mid = raw.get("movement_id")
            if not mid or mid not in catalog_ids:
                raise ValueError(f"movement_id {mid!r} not in candidate catalog")
            load_spec = _coerce_load(raw.get("load"))
            base = MovementPrescription(
                movement_id=mid,
                reps=_coerce_int(raw.get("reps")),
                time_seconds=_coerce_int(raw.get("time_seconds")),
                distance_meters=_coerce_int(raw.get("distance_meters")),
                calories=_coerce_int(raw.get("calories")),
                load=load_spec,
                pacing=_coerce_str(raw.get("pacing")),
                notes=_coerce_str(raw.get("notes")),
            )
            # Sprint 5b: post-process scaling tiers via library defaults.
            # LLM gera só a base; tiers RX/Scaled/Foundation vêm do
            # Movement.default_scaling encodado no seed (vocabulário de domínio).
            scaling = expand_scaling(base, catalog_by_id[mid])
            if scaling:
                base = base.model_copy(update={"scaling": scaling})
            prescriptions.append(base)

        fmt = _coerce_enum(payload.get("format"), BlockFormat)
        stim = _coerce_enum(payload.get("stimulus"), Stimulus) or hints.target_stimulus

        return WorkoutBlock(
            order=order,
            type=block_type,
            format=fmt or hints.target_format,
            stimulus=stim,
            duration_minutes=_coerce_int(payload.get("duration_minutes"))
                or hints.duration_minutes,
            rounds=_coerce_int(payload.get("rounds")) or hints.rounds,
            work_seconds=_coerce_int(payload.get("work_seconds")),
            rest_seconds=_coerce_int(payload.get("rest_seconds")),
            intensity_rpe=_coerce_float(payload.get("intensity_rpe")) or hints.rpe,
            target_score=_coerce_str(payload.get("target_score")),
            target_pace=_coerce_str(payload.get("target_pace")),
            intent=_coerce_str(payload.get("intent")) or hints.intent,
            coaching_notes=_coerce_str(payload.get("coaching_notes")),
            movements=prescriptions,
        )


# ============================================================
# Helpers (defensive coercion — LLMs return many shapes for null/empty)
# ============================================================

def _is_restricted(movement: Movement, athlete: Athlete) -> bool:
    for inj in athlete.active_injuries:
        if inj.resolved_date is not None:
            continue
        if movement.id in inj.affected_movements:
            return True
        if any(p in movement.tags for p in inj.affected_patterns):
            return True
    return False


def _coerce_int(v) -> Optional[int]:
    if v is None or v == "" or v == "null":
        return None
    if isinstance(v, bool):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _coerce_float(v) -> Optional[float]:
    if v is None or v == "" or v == "null":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _coerce_str(v) -> Optional[str]:
    if v is None or v == "null":
        return None
    s = str(v).strip()
    return s or None


def _coerce_enum(v, enum_cls):
    if v is None or v == "" or v == "null":
        return None
    if isinstance(v, enum_cls):
        return v
    try:
        return enum_cls(v)
    except (ValueError, KeyError):
        return None


def _coerce_load(raw) -> Optional[LoadSpec]:
    if raw is None or not isinstance(raw, dict):
        return None
    ltype = raw.get("type")
    if not ltype:
        return None
    try:
        return LoadSpec(
            type=ltype,
            value=_coerce_float(raw.get("value")),
            reference_lift=_coerce_str(raw.get("reference_lift")),
        )
    except (ValueError, TypeError):
        return None
