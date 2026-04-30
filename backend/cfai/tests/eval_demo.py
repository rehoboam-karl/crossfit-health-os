"""
Demo do framework de avaliação completo (3 layers).

Aplica métricas em mesociclos gerados — simula comparação entre dois
"modelos" (na prática: HeuristicComposer com hints distintos para emular
qualidade de programmers diferentes).

Output:
1. Layer 1 (deterministic) — todas as métricas com scores 0-1
2. Layer 2 (LLM judge) — stub com rubrica
3. Layer 3 (longitudinal) — sobre execução simulada
4. Comparação agregada entre "modelos"
"""

import json
from datetime import date, datetime, timedelta

from cfai.athlete import Injury, InjurySeverity
from cfai.evaluation import evaluate_mesocycle, summary_score
from cfai.evaluation_judge import (
    JudgeDimension, RUBRIC, StubJudge, compare_models_pointwise,
)
from cfai.evaluation_longitudinal import (
    evaluate_longitudinal, longitudinal_summary,
)
from cfai.examples import karl
from cfai.history import TrainingHistory
from cfai.movements_seed import load_default_library
from cfai.programmer import HeuristicComposer, ProgrammingContext, SessionPlanner
from cfai.results import (
    BlockResult, CompletionStatus, MovementResult, build_session_result,
)
from cfai.workout_schema import Mesocycle, Phase


# ============================================================
# Setup — gerar 2 mesociclos completos
# ============================================================

library = load_default_library()
planner = SessionPlanner(library, HeuristicComposer(library))


def make_mesocycle(
    *, meso_id: str, phase: Phase, start: date,
    weekly_focus: list[str], duration_weeks: int = 4,
) -> Mesocycle:
    weeks = []
    for week_num in range(1, duration_weeks + 1):
        is_deload = (week_num == duration_weeks)
        sessions = []
        for day in range(1, 6):  # 5 sessões/semana
            ctx = ProgrammingContext(
                athlete=karl, library=library, phase=phase,
                week_number=week_num, day_number=day,
                target_date=start + timedelta(days=(week_num-1)*7 + day - 1),
                weekly_focus=weekly_focus,
            )
            sessions.append(planner.plan_session(ctx))
        from cfai.workout_schema import Week
        weeks.append(Week(
            week_number=week_num,
            sessions=sessions,
            deload=is_deload,
            theme=f"W{week_num}",
        ))

    return Mesocycle(
        id=meso_id,
        name=f"Demo {meso_id}",
        phase=phase,
        start_date=start,
        duration_weeks=duration_weeks,
        weeks=weeks,
        primary_focus=weekly_focus,
    )


meso_a = make_mesocycle(
    meso_id="meso_A_squat",
    phase=Phase.BUILD,
    start=date(2026, 4, 27),
    weekly_focus=["squat_volume"],
)
meso_b = make_mesocycle(
    meso_id="meso_B_pull",
    phase=Phase.BUILD,
    start=date(2026, 4, 27),
    weekly_focus=["pulling", "deadlift"],
)


# ============================================================
# LAYER 1 — Determinística
# ============================================================

print("=" * 70)
print("LAYER 1 — Deterministic Metrics (Pydantic + Prilepin + Foster + ACWR)")
print("=" * 70)

results_a = evaluate_mesocycle(meso_a, karl, library)
results_b = evaluate_mesocycle(meso_b, karl, library)

print(f"\n📋 Mesociclo A (focus=squat):")
print(f"   Mesocycle-level metrics:")
for m in results_a["mesocycle_metrics"]:
    marker = "✅" if m.get("passed") else ("❌" if m.get("passed") is False else "📊")
    raw = f"{m['raw_value']:.2f}" if m.get("raw_value") is not None else "—"
    print(f"     {marker} {m['name']:30s} score={m['score']:.2f} raw={raw}")

print(f"\n   Sample week (W2) metrics:")
w2 = results_a["week_metrics"][1]
for m in w2["metrics"]:
    marker = "✅" if m.get("passed") else ("❌" if m.get("passed") is False else "📊")
    raw = f"{m['raw_value']:.2f}" if m.get("raw_value") is not None else "—"
    print(f"     {marker} {m['name']:30s} score={m['score']:.2f} raw={raw}")

print(f"\n   Sample session (W2D1) metrics:")
sm = results_a["session_metrics"][5]  # W2D1
for m in sm["metrics"]:
    marker = "✅" if m.get("passed") else ("❌" if m.get("passed") is False else "📊")
    raw = f"{m['raw_value']:.2f}" if m.get("raw_value") is not None else "—"
    print(f"     {marker} {m['name']:30s} score={m['score']:.2f} raw={raw}")


# ============================================================
# COMPARAÇÃO AGREGADA — Layer 1
# ============================================================

print("\n" + "=" * 70)
print("📊 Comparação agregada Layer 1 (média por categoria)")
print("=" * 70)

sum_a = summary_score(results_a)
sum_b = summary_score(results_b)

categories = sorted(set(sum_a) | set(sum_b))
print(f"\n  {'Category':25s} {'Meso A (squat)':>15s} {'Meso B (pull)':>15s}  Δ")
print(f"  {'-'*25} {'-'*15} {'-'*15}  {'-'*5}")
for cat in categories:
    a, b = sum_a.get(cat, 0), sum_b.get(cat, 0)
    delta = a - b
    arrow = "↑" if delta > 0.05 else ("↓" if delta < -0.05 else "≈")
    print(f"  {cat:25s} {a:>15.3f} {b:>15.3f}   {arrow} {delta:+.3f}")


# ============================================================
# LAYER 2 — LLM-as-Judge (STUB)
# ============================================================

print("\n" + "=" * 70)
print("LAYER 2 — LLM-as-Judge (stub demonstrativo)")
print("=" * 70)
print("""
Em produção: substituir StubJudge por ClaudeJudge / GPTJudge / GeminiJudge.
Necessário ANTES de uso real:
  1. Calibrar contra ≥30 sessões avaliadas por coach Level 2+
  2. Reportar Cohen κ ou Spearman ρ ≥0.7
  3. Documentar position-bias, verbosity-bias mitigations

Rubrica disponível para 6 dimensões:
""")
for dim in JudgeDimension:
    print(f"  • {dim.value}")
    for score, desc in RUBRIC[dim].items():
        print(f"      {score}: {desc[:70]}{'...' if len(desc) > 70 else ''}")
    print()

# Demo da chamada (resultado é stub)
judge = StubJudge()
sample_session = meso_a.weeks[1].sessions[0]
demo_score = judge.score_pointwise(
    sample_session,
    JudgeDimension.STIMULUS_COHERENCE,
    context={"athlete_id": karl.id, "phase": "build"},
)
print(f"  Demo call: dimension={demo_score.dimension.value} "
      f"score={demo_score.score} (stub)")


# ============================================================
# LAYER 3 — Longitudinal (precisa execução simulada)
# ============================================================

print("\n" + "=" * 70)
print("LAYER 3 — Longitudinal Metrics (simulando execução de Meso A)")
print("=" * 70)

# Simulação rápida: 75% compliance, 1 PR, sem overreaching
sim_results = []
import random
random.seed(42)
sessions_index = {s.id: s for w in meso_a.weeks for s in w.sessions}

for w in meso_a.weeks:
    for s in w.sessions:
        roll = random.random()
        if roll < 0.20:
            # SKIPPED
            sim_results.append(build_session_result(
                session_id=s.id, athlete_id=karl.id,
                executed_at=datetime.combine(s.date, datetime.min.time().replace(hour=18)),
                block_results=[],
            ))
        else:
            # COMPLETED
            block_results = []
            for b in s.blocks:
                block_results.append(BlockResult(
                    block_order=b.order,
                    status=CompletionStatus.COMPLETED,
                    actual_duration_minutes=b.duration_minutes,
                    perceived_rpe=random.uniform(6, 8.5),
                ))
            sim_results.append(build_session_result(
                session_id=s.id, athlete_id=karl.id,
                executed_at=datetime.combine(s.date, datetime.min.time().replace(hour=18)),
                overall_rpe=random.uniform(6.5, 8),
                sleep_quality_prev_night=random.randint(5, 9),
                soreness=random.randint(2, 6),
                block_results=block_results,
            ))

ref_dt = datetime.combine(meso_a.start_date + timedelta(days=28),
                           datetime.min.time())
history = TrainingHistory(sim_results, sessions_index=sessions_index)

print()
long_metrics = evaluate_longitudinal(
    history, karl, current_phase=meso_a.phase, ref=ref_dt,
)
for m in long_metrics:
    if m.n_a:
        print(f"  ⚪ {m.name:30s} N/A — {m.interpretation}")
        continue
    marker = "✅" if m.passed else ("❌" if m.passed is False else "📊")
    val = f"{m.value:.3f}" if m.value is not None else "—"
    print(f"  {marker} {m.name:30s} value={val} target={m.target}")
    print(f"     → {m.interpretation}")

print(f"\n  Aggregator: {longitudinal_summary(long_metrics)}")


# ============================================================
# JSON EXPORT — para tracking longitudinal
# ============================================================

print("\n" + "=" * 70)
print("💾 Export JSON (para tracking ao longo do tempo)")
print("=" * 70)

export = {
    "evaluation_date": datetime.now().isoformat(),
    "model_under_test": "HeuristicComposer-v1",
    "athlete_id": karl.id,
    "mesocycle_id": meso_a.id,
    "layer_1_summary": sum_a,
    "layer_3_summary": {
        m.name: m.value for m in long_metrics if not m.n_a
    },
    "layer_3_aggregator": longitudinal_summary(long_metrics),
}
print(json.dumps(export, indent=2, default=str))


# ============================================================
# COMO USAR PARA TRACKING LONGITUDINAL
# ============================================================

print("\n" + "=" * 70)
print("📈 Como rastrear modelos ao longo do tempo")
print("=" * 70)
print("""
1. Cada vez que rodar um modelo (Claude vN, GPT vN, ...), gerar mesociclo
   com mesmo Athlete/contexto controlado (test set fixo de 50 contextos).

2. Rodar evaluate_mesocycle() + evaluate_longitudinal() (após simular
   execução com mesmo seed para reprodutibilidade).

3. Salvar dict export em JSON com timestamp + model_name + version.

4. Construir time-series por (model, metric):
   - score_evolution.json contendo lista de evaluations
   - Plot scores ao longo do tempo / versões

5. Decision rules para promover modelo:
   - validity (Layer 1) DEVE manter 1.0 em todas — hard constraint
   - volume_intensity ≥0.8 média
   - distribution ≥0.7 média
   - judge dimensions ≥4.0/5.0 média (após calibração)
   - longitudinal: compliance ≥0.85, modification ≤0.20, overreaching ≤0.15

6. Comparação entre modelos (mesmo test set, mesmo athlete pool):
   - Pairwise tournament em Layer 2 (win-rate por dimensão)
   - ANOVA / Wilcoxon em scores Layer 1
   - Comparação de outcomes Layer 3 (PR cadence, benchmark progression)
""")
