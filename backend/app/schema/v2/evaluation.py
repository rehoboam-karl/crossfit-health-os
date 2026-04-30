"""
Evaluation framework — Layer 1 (deterministic).

Métricas computáveis sobre output do programmer (Session, Week, Mesocycle)
SEM precisar de LLM judge nem execução real. São checks objetivos com
referências científicas explícitas.

Dimensões cobertas:
A. Validity        — schema, library coverage, equipment, injury safety
B. Volume/Intensity — Prilepin compliance, INOL, ACWR, Foster monotony/strain
C. Distribution    — stimulus, MGW modal balance, movement variety
D. Periodization   — progressive overload, deload, phase consistency

Referências:
- Prilepin's Chart (1970s) — Olympic weightlifting volume/intensity standards
- Hristov, H. (2005) — INOL formula
- Foster, C. (1996) — Training monotony/strain
- Gabbett, T. (2016) — ACWR sweet spot 0.8-1.3
- JMIR Scoping Review 2025 (e79217) — Evaluation Rigor Score
- Glassman, G. — CrossFit Theoretical Template (3-on-1-off, MGW)

Sprint 1 patches embutidos desde a primeira escrita:
- Patch 1: PRILEPIN_TABLE 90+% range agora inclui 100% (lo=90, hi=101)
- Patch 2: metric_foster_monotony e metric_foster_strain padding com rest days
- Patch 3: summary_score com hard gating de validity
- Patch 4: metric_prilepin_compliance e metric_inol defendem mp.reps não-int
"""

import math
import statistics
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from athlete import Athlete
from movements import MovementLibrary
from workout_schema import (
    BlockType, LoadSpec, Mesocycle, Phase, Session, Stimulus, Week,
)


# ============================================================
# RESULT CONTAINER
# ============================================================

class MetricCategory(str, Enum):
    VALIDITY = "validity"             # binárias, hard constraints
    VOLUME_INTENSITY = "volume_intensity"
    DISTRIBUTION = "distribution"
    PERIODIZATION = "periodization"


@dataclass
class MetricResult:
    name: str
    category: MetricCategory
    score: float                       # 0-1 normalizado (1 = perfeito)
    raw_value: Optional[float] = None  # valor bruto (kg, %, ratio, etc)
    target: Optional[str] = None       # descrição do alvo ("0.8-1.3")
    passed: Optional[bool] = None      # binárias: True/False
    details: Optional[dict] = None
    reference: Optional[str] = None    # citação

    def __repr__(self) -> str:
        marker = "✅" if self.passed else ("❌" if self.passed is False else "📊")
        v = f"{self.raw_value:.2f}" if self.raw_value is not None else "—"
        return f"{marker} {self.name:35s} score={self.score:.2f} raw={v} target={self.target}"


# ============================================================
# A. VALIDITY (BINÁRIAS)
# ============================================================

def metric_movement_library_coverage(
    session: Session, library: MovementLibrary,
) -> MetricResult:
    """100% dos movement_ids da sessão existem no catálogo."""
    ids = [mp.movement_id for b in session.blocks for mp in b.movements]
    missing = library.validate_ids(ids)
    return MetricResult(
        name="movement_library_coverage",
        category=MetricCategory.VALIDITY,
        score=1.0 if not missing else 0.0,
        passed=not missing,
        target="0 movement_ids ausentes",
        details={"missing_ids": sorted(set(missing))} if missing else None,
        reference="JMIR ERS 2025 — instrument validity",
    )


def metric_equipment_feasibility(
    session: Session, athlete: Athlete,
) -> MetricResult:
    """Equipment requerido pela sessão está disponível ao atleta."""
    available = set(athlete.equipment_available)
    required = set(session.equipment_required)
    missing = required - available
    return MetricResult(
        name="equipment_feasibility",
        category=MetricCategory.VALIDITY,
        score=1.0 if not missing else 0.0,
        passed=not missing,
        target="todos equipments disponíveis",
        details={"missing_equipment": sorted(missing)} if missing else None,
    )


def metric_injury_safety(
    session: Session, athlete: Athlete, library: MovementLibrary,
) -> MetricResult:
    """Zero movimentos prescritos que violem injury restrictions
    (por id direto ou padrão biomecânico via tags)."""
    violations = []
    for inj in athlete.active_injuries:
        if inj.resolved_date is not None:
            continue
        for block in session.blocks:
            for mp in block.movements:
                mov = library.get_or_none(mp.movement_id)
                if mp.movement_id in inj.affected_movements:
                    violations.append((mp.movement_id, "direct"))
                elif mov and any(p in mov.tags for p in inj.affected_patterns):
                    violations.append((mp.movement_id, "pattern"))
    return MetricResult(
        name="injury_safety",
        category=MetricCategory.VALIDITY,
        score=1.0 if not violations else 0.0,
        passed=not violations,
        target="0 movimentos restritos",
        details={"violations": violations} if violations else None,
        reference="Hard safety constraint — escala não-negociável",
    )


# ============================================================
# B. VOLUME / INTENSITY
# ============================================================

# Prilepin's Chart — referência clássica.
# (%1RM_min, %1RM_max) → (reps_per_set_max, optimal_total, range_min, range_max)
# Patch 1: range superior inclui 100% (hi=101) — antes 100% caía em None.
PRILEPIN_TABLE = [
    (0,   70,  6, 24, 18, 30),     # <70%
    (70,  80,  6, 18, 12, 24),     # 70-79%
    (80,  90,  4, 15, 10, 20),     # 80-89%
    (90,  101, 2, 7,  4,  10),     # 90%+ (inclusive 100%)
]


def _prilepin_zone(pct: float) -> Optional[tuple]:
    for lo, hi, max_per_set, optimal, rng_min, rng_max in PRILEPIN_TABLE:
        if lo <= pct < hi:
            return (max_per_set, optimal, rng_min, rng_max)
    return None


def metric_prilepin_compliance(session: Session) -> MetricResult:
    """% de blocos strength_primary cuja prescrição cai dentro do range
    de Prilepin para a zona de %1RM dominante.

    Score = (compliant_blocks / strength_blocks) — 1.0 se todos OK.

    Patch 4: mp.reps não-int (AMRAP, "12-15", "max") é skip silencioso —
    Prilepin não faz sentido para volume aberto.
    """
    strength_blocks = [b for b in session.blocks
                       if b.type in (BlockType.STRENGTH_PRIMARY,
                                     BlockType.STRENGTH_SECONDARY,
                                     BlockType.OLY_COMPLEX)]
    if not strength_blocks:
        return MetricResult(
            name="prilepin_compliance",
            category=MetricCategory.VOLUME_INTENSITY,
            score=1.0,  # N/A — não penaliza
            passed=True,
            target="strength block reps em range Prilepin",
            details={"note": "sessão sem strength blocks"},
            reference="Prilepin (1970s)",
        )

    compliant = 0
    block_details = []
    for block in strength_blocks:
        # Agrupa reps por zona de %1RM
        zones: dict[tuple, int] = {}
        for mp in block.movements:
            if (mp.load and mp.load.type == "percent_1rm"
                    and isinstance(mp.reps, int) and mp.reps > 0):
                zone = _prilepin_zone(mp.load.value)
                if zone:
                    zones[zone] = zones.get(zone, 0) + mp.reps

        if not zones:
            block_details.append({"block_order": block.order, "status": "no_pct_load"})
            compliant += 1  # não dá pra avaliar; não penaliza
            continue

        # Cada zona: total reps deve ficar no range
        ok = all(rng_min <= total <= rng_max
                 for (_, _, rng_min, rng_max), total in zones.items())
        compliant += 1 if ok else 0
        block_details.append({
            "block_order": block.order,
            "zones": [
                {"reps_total": tot, "range": (rng_min, rng_max),
                 "in_range": rng_min <= tot <= rng_max}
                for (_, _, rng_min, rng_max), tot in zones.items()
            ],
        })

    score = compliant / len(strength_blocks)
    return MetricResult(
        name="prilepin_compliance",
        category=MetricCategory.VOLUME_INTENSITY,
        score=score,
        raw_value=score,
        passed=score >= 0.8,
        target="≥80% blocos em range",
        details={"blocks": block_details},
        reference="Prilepin (1970s)",
    )


def metric_inol(session: Session) -> MetricResult:
    """INOL = reps / (100 - %1RM) por exercício na sessão.
    Ideal 0.4-1.0 por exercício; >2.0 é overload por sessão.

    Patch 4: mp.reps não-int é skip silencioso (mesma justificativa do Prilepin).
    """
    inol_per_movement: dict[str, float] = {}
    for block in session.blocks:
        for mp in block.movements:
            if (mp.load and mp.load.type == "percent_1rm"
                    and isinstance(mp.reps, int) and mp.reps > 0):
                pct = mp.load.value
                if pct >= 100:
                    continue
                inol = mp.reps / (100 - pct)
                inol_per_movement[mp.movement_id] = (
                    inol_per_movement.get(mp.movement_id, 0) + inol
                )

    if not inol_per_movement:
        return MetricResult(
            name="inol_per_session",
            category=MetricCategory.VOLUME_INTENSITY,
            score=1.0, passed=True,
            target="0.4-1.0 por exercício",
            details={"note": "sem prescrições percent_1rm"},
            reference="Hristov (2005)",
        )

    in_range = sum(1 for v in inol_per_movement.values() if 0.4 <= v <= 1.0)
    score = in_range / len(inol_per_movement)
    avg_inol = statistics.mean(inol_per_movement.values())

    return MetricResult(
        name="inol_per_session",
        category=MetricCategory.VOLUME_INTENSITY,
        score=score,
        raw_value=avg_inol,
        passed=score >= 0.6,
        target="0.4-1.0 por exercício, média ≤1.5",
        details={"per_movement": inol_per_movement},
        reference="Hristov (2005)",
    )


def metric_acwr(weeks: list[Week], chronic_window_weeks: int = 4) -> MetricResult:
    """Acute:Chronic Workload Ratio (Gabbett 2016).
    Acute = última semana, Chronic = média 4 semanas anteriores.
    Sweet spot 0.8-1.3.

    Carga = soma de duration_minutes por sessão (proxy simples).
    Para usar s-RPE real, alimentar com SessionResults.
    """
    if len(weeks) < chronic_window_weeks + 1:
        return MetricResult(
            name="acwr",
            category=MetricCategory.VOLUME_INTENSITY,
            score=1.0,
            details={"note": f"menos de {chronic_window_weeks+1} semanas, N/A"},
            reference="Gabbett (2016)",
        )

    def week_load(w: Week) -> float:
        return sum(s.estimated_duration_minutes for s in w.sessions)

    sorted_weeks = sorted(weeks, key=lambda w: w.week_number)
    acute = week_load(sorted_weeks[-1])
    chronic_window = sorted_weeks[-(chronic_window_weeks+1):-1]
    chronic = statistics.mean(week_load(w) for w in chronic_window)

    if chronic == 0:
        ratio = 1.0
    else:
        ratio = acute / chronic

    if 0.8 <= ratio <= 1.3:
        score = 1.0
    elif 0.5 <= ratio < 0.8 or 1.3 < ratio <= 1.5:
        score = 0.5
    else:
        score = 0.0

    return MetricResult(
        name="acwr",
        category=MetricCategory.VOLUME_INTENSITY,
        score=score,
        raw_value=ratio,
        passed=score >= 1.0,
        target="0.8-1.3 (sweet spot)",
        details={"acute_load": acute, "chronic_load": chronic},
        reference="Gabbett (2016) Br J Sports Med",
    )


def metric_foster_monotony(week: Week) -> MetricResult:
    """Foster's Training Monotony (1996).
    Monotony = média_diária / desvio_padrão_diário sobre 7 dias.
    Rest days entram como 0 — sem isso, a SD fica artificialmente baixa
    e atletas treinando 5x/sem mostram monotony "perfeita" enganosamente.

    Patch 2: padding com rest days (assume 1 sessão/dia; se schema permitir
    two-a-day no futuro, agregar por Session.date antes).
    """
    sessions_load = [s.estimated_duration_minutes for s in week.sessions]
    daily_loads = sessions_load + [0.0] * max(0, 7 - len(sessions_load))

    if len(daily_loads) < 2:
        return MetricResult(
            name="foster_monotony",
            category=MetricCategory.VOLUME_INTENSITY,
            score=1.0, target="<2.0",
            details={"note": "<2 dias de dados"},
            reference="Foster (1996)",
        )

    mean = statistics.mean(daily_loads)
    sd = statistics.stdev(daily_loads)
    if sd == 0 or mean == 0:
        # mean=0 → semana sem treino; sd=0 → todos dias iguais (incl. 0s)
        monotony = float("inf") if mean > 0 else 0.0
        score = 0.0 if monotony == float("inf") else 1.0
    else:
        monotony = mean / sd
        if   monotony < 1.5: score = 1.0
        elif monotony < 2.0: score = 0.7
        elif monotony < 2.5: score = 0.3
        else:                score = 0.0

    return MetricResult(
        name="foster_monotony",
        category=MetricCategory.VOLUME_INTENSITY,
        score=score,
        raw_value=monotony if monotony not in (float("inf"), 0.0) else None,
        passed=(monotony != float("inf") and monotony < 2.0),
        target="<2.0 (Foster 1996)",
        details={"daily_loads": daily_loads, "training_days": len(sessions_load)},
        reference="Foster (1996) Med Sci Sports Exerc",
    )


def metric_foster_strain(week: Week) -> MetricResult:
    """Training Strain = total weekly load × monotony.
    Sem cutoff universal — útil pra trend longitudinal.

    Patch 2: padding com rest days (mesma justificativa do monotony).
    """
    sessions_load = [s.estimated_duration_minutes for s in week.sessions]
    daily = sessions_load + [0.0] * max(0, 7 - len(sessions_load))

    if len(daily) < 2:
        return MetricResult(
            name="foster_strain",
            category=MetricCategory.VOLUME_INTENSITY,
            score=1.0, target="trend longitudinal",
            details={"note": "<2 dias de dados"},
            reference="Foster (1996)",
        )
    total = sum(daily)
    mean = statistics.mean(daily)
    sd = statistics.stdev(daily)
    if sd == 0 or mean == 0:
        return MetricResult(
            name="foster_strain", category=MetricCategory.VOLUME_INTENSITY,
            score=0.0 if mean > 0 else 1.0, raw_value=None,
            target="trend longitudinal",
            details={"note": "monotony degenerada (mean=0 ou sd=0)",
                     "training_days": len(sessions_load)},
            reference="Foster (1996)",
        )
    monotony = mean / sd
    strain = total * monotony
    return MetricResult(
        name="foster_strain",
        category=MetricCategory.VOLUME_INTENSITY,
        score=1.0,  # informativa, sem score
        raw_value=strain,
        target="trend (não-absoluto)",
        details={"total_load": total, "monotony": monotony,
                 "training_days": len(sessions_load)},
        reference="Foster (1996)",
    )


# ============================================================
# C. DISTRIBUTION & BALANCE
# ============================================================

# Targets de distribuição modal por phase (CrossFit Theoretical Template)
# Glassman propõe ~3-on-1-off com alternância M/G/W; refletido como faixas
MODAL_TARGETS_BY_PHASE: dict[Phase, dict[str, tuple[float, float]]] = {
    Phase.BASE:  {"M": (0.25, 0.45), "G": (0.20, 0.40), "W": (0.25, 0.45)},
    Phase.BUILD: {"M": (0.20, 0.35), "G": (0.20, 0.35), "W": (0.30, 0.50)},
    Phase.PEAK:  {"M": (0.15, 0.30), "G": (0.20, 0.35), "W": (0.35, 0.55)},
    Phase.DELOAD:{"M": (0.30, 0.60), "G": (0.10, 0.30), "W": (0.10, 0.30)},
    Phase.TEST:  {"M": (0.15, 0.40), "G": (0.15, 0.40), "W": (0.30, 0.60)},
}


def metric_modal_balance(
    week: Week, phase: Phase, library: MovementLibrary,
) -> MetricResult:
    """Distribuição M/G/W de minutos vs. targets da phase.
    Cada movimento contribui com (duration/n_movements) × {1 por modality}.
    """
    counts = {"M": 0.0, "G": 0.0, "W": 0.0}
    for sess in week.sessions:
        for block in sess.blocks:
            n = len(block.movements) or 1
            dur = block.duration_minutes or 0
            per_mp = dur / n
            for mp in block.movements:
                mov = library.get_or_none(mp.movement_id)
                if not mov:
                    continue
                for m in mov.modalities:
                    if m in counts:
                        counts[m] += per_mp

    total = sum(counts.values()) or 1
    pcts = {k: v / total for k, v in counts.items()}
    targets = MODAL_TARGETS_BY_PHASE[phase]

    in_range = sum(
        1 for k, (lo, hi) in targets.items()
        if lo <= pcts[k] <= hi
    )
    score = in_range / 3

    return MetricResult(
        name="modal_balance",
        category=MetricCategory.DISTRIBUTION,
        score=score,
        raw_value=score,
        passed=score >= 0.66,
        target=str(targets),
        details={"distribution": pcts},
        reference="Glassman — CrossFit Theoretical Template",
    )


def metric_movement_variety(
    weeks: list[Week], library: MovementLibrary,
) -> MetricResult:
    """Shannon entropy normalizada da distribuição de movement_ids
    no conjunto de semanas. Próximo de 1 = bem distribuído.
    Penaliza repetição excessiva (programmer monótono).
    """
    counts: Counter = Counter()
    for w in weeks:
        for s in w.sessions:
            for b in s.blocks:
                for mp in b.movements:
                    counts[mp.movement_id] += 1

    if not counts:
        return MetricResult(
            name="movement_variety",
            category=MetricCategory.DISTRIBUTION,
            score=0.0, target="entropy normalizada",
        )

    total = sum(counts.values())
    probs = [c / total for c in counts.values()]
    entropy = -sum(p * math.log2(p) for p in probs if p > 0)
    max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1
    normalized = entropy / max_entropy if max_entropy > 0 else 0.0

    catalog_pct = len(counts) / len(library)

    return MetricResult(
        name="movement_variety",
        category=MetricCategory.DISTRIBUTION,
        score=normalized,
        raw_value=normalized,
        passed=normalized >= 0.7,
        target="entropy ≥0.7, ≥30% catálogo",
        details={
            "unique_movements": len(counts),
            "catalog_coverage_pct": round(catalog_pct, 3),
            "top5": counts.most_common(5),
        },
        reference="Glassman — variance princípio CrossFit",
    )


def metric_stimulus_distribution(
    week: Week, phase: Phase,
) -> MetricResult:
    """Distribuição de minutos por stimulus.
    Score = % de sessions com primary_stimulus declarado.
    Penaliza ausência total de aerobic_z2 em BASE/BUILD.
    """
    stim_minutes: dict[Stimulus, int] = {}
    for sess in week.sessions:
        for b in sess.blocks:
            if b.stimulus and b.duration_minutes:
                stim_minutes[b.stimulus] = (
                    stim_minutes.get(b.stimulus, 0) + b.duration_minutes
                )

    total = sum(stim_minutes.values()) or 1
    pcts = {s.value: round(m / total, 3) for s, m in stim_minutes.items()}

    # Heurística de phase
    issues = []
    if phase in (Phase.BASE, Phase.BUILD):
        if stim_minutes.get(Stimulus.AEROBIC_Z2, 0) == 0:
            issues.append("phase requer aerobic_z2 mas ausente")
    if phase == Phase.DELOAD:
        if stim_minutes.get(Stimulus.STRENGTH_MAX, 0) > 0:
            issues.append("strength_max em deload")

    score = 1.0 if not issues else max(0.0, 1.0 - 0.5 * len(issues))
    return MetricResult(
        name="stimulus_distribution",
        category=MetricCategory.DISTRIBUTION,
        score=score,
        passed=not issues,
        target=f"phase={phase.value} apropriado",
        details={"distribution_pct": pcts, "issues": issues},
        reference="Periodization principles + JMIR ERS 2025",
    )


# ============================================================
# D. PERIODIZATION
# ============================================================

def metric_progressive_overload(mesocycle: Mesocycle) -> MetricResult:
    """Carga média de strength_primary cresce W1→W3 (excluindo deload)?
    Mede slope linear da %1RM média semanal.
    """
    weekly_pcts: list[float] = []
    for week in sorted(mesocycle.weeks, key=lambda w: w.week_number):
        if week.deload:
            continue
        pcts = []
        for sess in week.sessions:
            for block in sess.blocks:
                if block.type != BlockType.STRENGTH_PRIMARY:
                    continue
                for mp in block.movements:
                    if mp.load and mp.load.type == "percent_1rm":
                        pcts.append(mp.load.value)
        if pcts:
            weekly_pcts.append(statistics.mean(pcts))

    if len(weekly_pcts) < 2:
        return MetricResult(
            name="progressive_overload",
            category=MetricCategory.PERIODIZATION,
            score=1.0,
            details={"note": "dados insuficientes"},
            reference="Block periodization principle",
        )

    # Slope simples
    n = len(weekly_pcts)
    xs = list(range(n))
    mean_x, mean_y = statistics.mean(xs), statistics.mean(weekly_pcts)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, weekly_pcts))
    den = sum((x - mean_x) ** 2 for x in xs) or 1
    slope = num / den

    # Slope esperado: ~2-3% por semana em BUILD
    if mesocycle.phase == Phase.BUILD:
        score = 1.0 if 1.5 <= slope <= 5.0 else 0.5 if slope > 0 else 0.0
    elif mesocycle.phase == Phase.PEAK:
        score = 1.0 if 0 <= slope <= 3.0 else 0.5
    else:
        score = 1.0  # BASE/DELOAD não exigem overload linear

    return MetricResult(
        name="progressive_overload",
        category=MetricCategory.PERIODIZATION,
        score=score,
        raw_value=slope,
        passed=score >= 0.5,
        target="slope >0 em BUILD, ~2-3%/semana",
        details={"weekly_avg_pcts": weekly_pcts, "slope_pct_per_week": slope},
        reference="Block periodization (Issurin 2010)",
    )


def metric_deload_presence(mesocycle: Mesocycle) -> MetricResult:
    """Mesociclo de 4+ semanas deve ter ≥1 semana deload."""
    if mesocycle.duration_weeks < 4:
        return MetricResult(
            name="deload_presence",
            category=MetricCategory.PERIODIZATION,
            score=1.0,
            details={"note": "mesociclo curto, deload opcional"},
        )
    has_deload = any(w.deload for w in mesocycle.weeks)
    return MetricResult(
        name="deload_presence",
        category=MetricCategory.PERIODIZATION,
        score=1.0 if has_deload else 0.0,
        passed=has_deload,
        target="≥1 deload em mesociclo ≥4 sem",
        reference="Selye GAS + supercompensation",
    )


# ============================================================
# AGREGADOR
# ============================================================

def evaluate_session(
    session: Session, athlete: Athlete, library: MovementLibrary,
) -> list[MetricResult]:
    return [
        metric_movement_library_coverage(session, library),
        metric_equipment_feasibility(session, athlete),
        metric_injury_safety(session, athlete, library),
        metric_prilepin_compliance(session),
        metric_inol(session),
    ]


def evaluate_week(
    week: Week, phase: Phase, library: MovementLibrary,
) -> list[MetricResult]:
    return [
        metric_modal_balance(week, phase, library),
        metric_stimulus_distribution(week, phase),
        metric_foster_monotony(week),
        metric_foster_strain(week),
    ]


def evaluate_mesocycle(
    mesocycle: Mesocycle, athlete: Athlete, library: MovementLibrary,
) -> dict:
    """Roda todas as métricas. Retorna dict aninhado pra export/comparação."""
    results = {
        "mesocycle_id": mesocycle.id,
        "phase": mesocycle.phase.value,
        "duration_weeks": mesocycle.duration_weeks,
        "session_metrics": [],
        "week_metrics": [],
        "mesocycle_metrics": [],
    }

    for week in mesocycle.weeks:
        for session in week.sessions:
            results["session_metrics"].append({
                "session_id": session.id,
                "week_number": week.week_number,
                "metrics": [m.__dict__ for m in evaluate_session(session, athlete, library)],
            })
        results["week_metrics"].append({
            "week_number": week.week_number,
            "metrics": [m.__dict__ for m in evaluate_week(week, mesocycle.phase, library)],
        })

    results["mesocycle_metrics"] = [
        m.__dict__ for m in [
            metric_progressive_overload(mesocycle),
            metric_deload_presence(mesocycle),
            metric_movement_variety(mesocycle.weeks, library),
            metric_acwr(mesocycle.weeks),
        ]
    ]
    return results


def summary_score(
    results: dict,
    *,
    hard_gate_categories: tuple[str, ...] = ("validity",),
) -> dict:
    """Score agregado por categoria.

    Patch 3: hard gating. Categorias listadas em `hard_gate_categories` viram
    0.0 se QUALQUER métrica daquela categoria falhar (não vira média).
    Validity (injury_safety, equipment, library coverage) é não-negociável —
    uma única falha no conjunto reprovaria o programa todo.
    """
    by_cat: dict[str, list[float]] = {}

    def collect(metric_dicts):
        for m in metric_dicts:
            by_cat.setdefault(m["category"], []).append(m["score"])

    for sm in results["session_metrics"]:
        collect(sm["metrics"])
    for wm in results["week_metrics"]:
        collect(wm["metrics"])
    collect(results["mesocycle_metrics"])

    out = {}
    for cat, scores in by_cat.items():
        if cat in hard_gate_categories:
            out[cat] = 1.0 if all(s >= 1.0 for s in scores) else 0.0
        else:
            out[cat] = round(statistics.mean(scores), 3) if scores else 0.0
    return out
