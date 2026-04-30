"""
Evaluation Layer 3 — métricas longitudinais (precisam SessionResults).

Mede o que efetivamente importa: o programa funciona NA REALIDADE?
Estas são as métricas que separam programmer "bonito no papel" de
programmer "que faz o atleta progredir e ficar saudável".

Métricas:
- Compliance rate (% sessões executadas)
- Modification rate (substitutions/scaling — proxy de fit)
- Skip pattern (consistência: pula sempre o mesmo dia?)
- PR cadence (PRs por mesociclo, phase-aware)
- Benchmark progression slopes
- Overreaching frequency (% semanas com signals)
- RPE-load decoupling (RPE subindo na mesma %1RM = fadiga acumulando)

Referências:
- Compliance: Bouchard et al. — adherence > sofisticação programática
- s-RPE Foster (1996) — internal load
- Kraemer & Ratamess (2004) — progressive overload outcomes

Sprint 1 patches embutidos:
- Patch 5: imports limpos (timedelta no topo, sem __import__ inline,
  sem `from datetime import timedelta` dentro de função, sem dead imports)
- Patch 6: modification_rate denominador exclui SKIPPED — atleta que pula
  50% e modifica 100% do que executa NÃO pode parecer "moderado"
- Patch 7: LongitudinalMetric.n_a flag + value=None quando N/A +
  longitudinal_summary aggregator filtra n_a antes de contar passed/failed
- Patch 8: pr_cadence phase-aware (BASE/BUILD esperam 0 PRs — block-style
  periodization é accumulation, sem teste; PEAK/TEST esperam 1-2)
"""

import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from .athlete import Athlete
from .history import TrainingHistory
from .results import CompletionStatus
from .workout_schema import Phase


# ============================================================
# CONTAINERS
# ============================================================

@dataclass
class LongitudinalMetric:
    name: str
    value: Optional[float]                # None quando n_a=True
    target: str
    interpretation: str
    passed: Optional[bool] = None
    n_a: bool = False                     # "métrica não-aplicável"
    details: Optional[dict] = None


# ============================================================
# COMPLIANCE & MODIFICATION
# ============================================================

def compliance_metric(
    history: TrainingHistory, athlete_id: str, days_back: int = 28,
    ref: Optional[datetime] = None,
) -> LongitudinalMetric:
    """% de sessões executadas (qualquer status != SKIPPED) na janela."""
    rate = history.compliance_rate(athlete_id, days_back, ref)
    if rate is None:
        return LongitudinalMetric(
            name="compliance_rate", value=None, n_a=True,
            target="≥0.85",
            interpretation="Sem sessões agendadas na janela",
        )
    if rate >= 0.85:
        interp = "Excelente — programa está cabendo na rotina"
    elif rate >= 0.70:
        interp = "OK — possíveis ajustes de volume/duração"
    elif rate >= 0.50:
        interp = "Baixa — programa pode estar desalinhado com a vida do atleta"
    else:
        interp = "Crítica — revisar urgentemente"
    return LongitudinalMetric(
        name="compliance_rate",
        value=rate,
        target="≥0.85",
        passed=rate >= 0.85,
        interpretation=interp,
    )


def modification_rate_metric(
    history: TrainingHistory, athlete_id: str, days_back: int = 28,
    ref: Optional[datetime] = None,
) -> LongitudinalMetric:
    """% de sessões TENTADAS que foram modificadas.

    Patch 6: denominador exclui SKIPPED — atleta que pula 50% e modifica 100%
    das que executa não pode mostrar `modification_rate=0.5` (parece "razoável"
    mas é catastrófico).
    """
    results = history.in_window(athlete_id, days_back, ref)
    attempted = [r for r in results if r.status != CompletionStatus.SKIPPED]
    if not attempted:
        return LongitudinalMetric(
            name="modification_rate", value=None, n_a=True,
            target="≤0.20",
            interpretation="Sem sessões executadas na janela",
        )
    modified = sum(1 for r in attempted if r.status == CompletionStatus.MODIFIED)
    rate = modified / len(attempted)
    if rate <= 0.10:
        interp = "Programa cabe bem ao atleta"
    elif rate <= 0.25:
        interp = "Aceitável — algumas adaptações esperadas"
    else:
        interp = "Alta — programmer não está calibrando bem ao atleta"
    return LongitudinalMetric(
        name="modification_rate", value=rate, target="≤0.20",
        passed=rate <= 0.20, interpretation=interp,
        details={"modified": modified, "attempted": len(attempted),
                 "skipped": len(results) - len(attempted)},
    )


def skip_pattern_metric(
    history: TrainingHistory, athlete_id: str, days_back: int = 56,
    ref: Optional[datetime] = None,
) -> LongitudinalMetric:
    """Detecta se atleta pula consistentemente o mesmo dia da semana.
    Indica que programmer deveria ajustar split.
    """
    results = history.in_window(athlete_id, days_back, ref)
    skipped = [r for r in results if r.status == CompletionStatus.SKIPPED]
    if not results:
        return LongitudinalMetric(
            name="skip_pattern", value=None, n_a=True,
            target="distribuição uniforme entre dias",
            interpretation="Sem sessões na janela",
        )
    if not skipped:
        return LongitudinalMetric(
            name="skip_pattern", value=0.0,
            target="distribuição uniforme entre dias",
            interpretation="Sem skips",
            passed=True,
        )

    by_dow: dict[int, int] = {}
    for r in skipped:
        dow = r.executed_at.isoweekday()
        by_dow[dow] = by_dow.get(dow, 0) + 1

    max_skips = max(by_dow.values())
    total = sum(by_dow.values())
    concentration = max_skips / total

    if concentration <= 0.4:
        interp = "Skips distribuídos — sem padrão a corrigir"
    elif concentration <= 0.6:
        interp = f"Concentração moderada (dia {max(by_dow, key=by_dow.get)})"
    else:
        worst = max(by_dow, key=by_dow.get)
        interp = (f"Atleta pula consistentemente dia {worst} "
                  f"({concentration:.0%}) — reprogramar split")

    return LongitudinalMetric(
        name="skip_pattern",
        value=concentration,
        target="≤0.40",
        passed=concentration <= 0.40,
        interpretation=interp,
        details={"by_day_of_week": by_dow},
    )


# ============================================================
# PROGRESSION
# ============================================================

# Patch 8: PR expectations por phase. Programmer correto seguindo periodização
# block-style NÃO produz PRs em BASE/BUILD (volume accumulation). Penalizar
# 0 PRs nessas fases é punir boa periodização.
PR_EXPECTATIONS_BY_PHASE = {
    Phase.BASE:   0,   # accumulation, sem teste
    Phase.BUILD:  0,   # ainda accumulation
    Phase.PEAK:   1,   # afiação, esperado começar a ver PRs
    Phase.TEST:   2,   # bloco de teste explícito
    Phase.DELOAD: 0,   # recuperação
}


def pr_cadence_metric(
    history: TrainingHistory, athlete: Athlete,
    phase: Phase,
    mesocycle_weeks: int = 4,
    ref: Optional[datetime] = None,
) -> LongitudinalMetric:
    """PRs detectados na janela do mesociclo, com expectativa por fase.

    Patch 8: phase-aware. BASE/BUILD esperam 0 PRs (accumulation); PEAK/TEST
    esperam 1-2.
    """
    days = mesocycle_weeks * 7
    cutoff = (ref or datetime.now()) - timedelta(days=days)
    prs = [pr for pr in history.detect_prs(athlete, ref)
           if pr.achieved_at >= cutoff]
    n = len(prs)
    expected = PR_EXPECTATIONS_BY_PHASE.get(phase, 0)
    passed = n >= expected

    if expected == 0 and n == 0:
        interp = f"Esperado em {phase.value}: foco em volume, não testes"
    elif n >= expected + 2:
        interp = f"Excelente — {n} PRs (esperado ≥{expected})"
    elif n >= expected:
        interp = f"OK — {n} PR(s), esperado ≥{expected}"
    else:
        interp = (f"Apenas {n} PR(s), esperado ≥{expected} em {phase.value}. "
                  f"Investigar progressão ou retest schedule.")

    return LongitudinalMetric(
        name="pr_cadence",
        value=float(n),
        target=f"≥{expected} em {phase.value}",
        passed=passed,
        interpretation=interp,
        details={"phase": phase.value, "expected": expected,
                 "achieved": [pr.movement_id for pr in prs]},
    )


def benchmark_progression_metric(
    athlete: Athlete, benchmark_id: str, history_results_dates: list,
) -> LongitudinalMetric:
    """Slope de progressão num benchmark repetido.
    Requer ≥2 resultados do mesmo benchmark.

    Para "lower-is-better" (Fran, 5K row em segundos): slope NEGATIVO bom.
    Para "higher-is-better" (rounds em AMRAP): slope POSITIVO bom.

    STUB: precisa lógica de leitura histórica de benchmarks.
    """
    bench = athlete.benchmarks.get(benchmark_id)
    if not bench:
        return LongitudinalMetric(
            name=f"benchmark_progression_{benchmark_id}",
            value=None, n_a=True,
            target="slope significativo",
            interpretation="Sem baseline",
        )

    return LongitudinalMetric(
        name=f"benchmark_progression_{benchmark_id}",
        value=None, n_a=True,
        target="depende do benchmark (lower vs higher is better)",
        interpretation=(
            "STUB: implementar lendo todos resultados do benchmark "
            "ao longo do tempo, calcular regressão linear."
        ),
        details={"is_stub": True},
    )


# ============================================================
# OVERREACHING
# ============================================================

def overreaching_frequency_metric(
    history: TrainingHistory, athlete_id: str, days_back: int = 56,
    ref: Optional[datetime] = None,
) -> LongitudinalMetric:
    """% de semanas (em janelas de 7d) com overreaching signals."""
    results = history.in_window(athlete_id, days_back, ref)
    if not results:
        return LongitudinalMetric(
            name="overreaching_frequency", value=None, n_a=True,
            target="≤0.15", interpretation="Sem dados",
        )

    n_weeks = days_back // 7
    weeks_with_signals = 0
    for w in range(n_weeks):
        end = (ref or datetime.now()) - timedelta(days=w * 7)
        signals = history.overreaching_signals(athlete_id, ref=end)
        if signals:
            weeks_with_signals += 1
    rate = weeks_with_signals / n_weeks if n_weeks else 0

    if rate <= 0.15:
        interp = "Carga bem-calibrada"
    elif rate <= 0.30:
        interp = "Atenção — mais semanas com signals que ideal"
    else:
        interp = "Overreaching crônico — programmer está prescrevendo demais"

    return LongitudinalMetric(
        name="overreaching_frequency",
        value=rate,
        target="≤0.15",
        passed=rate <= 0.15,
        interpretation=interp,
    )


def rpe_load_decoupling_metric(
    history: TrainingHistory, athlete: Athlete, movement_id: str,
    days_back: int = 28, ref: Optional[datetime] = None,
) -> LongitudinalMetric:
    """RPE-Load decoupling: para um movimento específico, RPE médio sobe
    enquanto carga relativa fica igual ou cai = sinal de fadiga acumulando.

    Score: correlação entre %1RM (constante ou caindo) e RPE (subindo).
    """
    results = history.in_window(athlete.id, days_back, ref)

    points = []
    one_rm = athlete.get_1rm(movement_id)
    if not one_rm:
        return LongitudinalMetric(
            name="rpe_load_decoupling", value=None, n_a=True,
            target="RPE estável em mesma %1RM",
            interpretation=f"Sem 1RM registrado para {movement_id}",
        )

    for r in results:
        for b in r.block_results:
            for mr in b.movement_results:
                if mr.movement_id != movement_id:
                    continue
                if mr.actual_load_kg and mr.perceived_rpe and mr.actual_reps:
                    pct = (mr.actual_load_kg / one_rm) * 100
                    points.append((r.executed_at, pct, mr.perceived_rpe))

    if len(points) < 4:
        return LongitudinalMetric(
            name="rpe_load_decoupling", value=None, n_a=True,
            target="≥4 pontos para análise",
            interpretation="Dados insuficientes",
        )

    points.sort(key=lambda p: p[0])
    xs = [(p[0] - points[0][0]).total_seconds() / 86400 for p in points]
    rpes = [p[2] for p in points]
    pcts = [p[1] for p in points]

    n = len(xs)
    mean_x, mean_rpe = statistics.mean(xs), statistics.mean(rpes)
    num = sum((x - mean_x) * (r - mean_rpe) for x, r in zip(xs, rpes))
    den = sum((x - mean_x) ** 2 for x in xs) or 1
    rpe_slope = num / den

    pct_trend = statistics.mean(pcts[len(pcts)//2:]) - statistics.mean(pcts[:len(pcts)//2])

    decoupling = rpe_slope > 0.05 and pct_trend <= 0
    if decoupling:
        interp = ("Decoupling detectado: RPE subindo na mesma %1RM. "
                  "Programa provavelmente excessivo — considerar deload.")
        passed = False
    else:
        interp = "Acoplamento normal RPE-carga"
        passed = True

    return LongitudinalMetric(
        name=f"rpe_load_decoupling_{movement_id}",
        value=rpe_slope,
        target="slope RPE ≤0.05/dia em mesma %1RM",
        passed=passed,
        interpretation=interp,
        details={"n_points": n, "rpe_slope_per_day": rpe_slope,
                 "pct_trend": pct_trend},
    )


# ============================================================
# AGREGADOR
# ============================================================

def evaluate_longitudinal(
    history: TrainingHistory, athlete: Athlete,
    current_phase: Phase,
    ref: Optional[datetime] = None,
) -> list[LongitudinalMetric]:
    return [
        compliance_metric(history, athlete.id, ref=ref),
        modification_rate_metric(history, athlete.id, ref=ref),
        skip_pattern_metric(history, athlete.id, ref=ref),
        pr_cadence_metric(history, athlete, phase=current_phase, ref=ref),
        overreaching_frequency_metric(history, athlete.id, ref=ref),
    ]


def longitudinal_summary(metrics: list[LongitudinalMetric]) -> dict:
    """Patch 7: aggregator filtra n_a antes de contar passed/failed."""
    measurable = [m for m in metrics if not m.n_a]
    return {
        "n_metrics": len(metrics),
        "n_measurable": len(measurable),
        "n_passed": sum(1 for m in measurable if m.passed is True),
        "n_failed": sum(1 for m in measurable if m.passed is False),
        "critical_failures": [m.name for m in measurable
                              if m.passed is False and m.name in
                              {"compliance_rate", "overreaching_frequency"}],
    }
