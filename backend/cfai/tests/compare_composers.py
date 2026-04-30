"""
Comparison harness multi-composer — Sprint 4.

Para 1 ProgrammingContext (BUILD/W2/D1, weekly_focus=squat_volume):
  1. Gera 1 Session via HeuristicComposer (baseline)
  2. Gera 1 Session via cada LLMComposer disponível
  3. Roda L1 (deterministic) — evaluate_session: 5 métricas
  4. Roda L2 (LLM-as-judge) — LLMProviderJudge pointwise nas 6 dimensões da
     RUBRIC, usando UM judge fixo (default: openai gpt-4o — rápido, baixo
     schema_failure).
  5. Imprime matriz composer × dimension + custo total.

Padrão escolhido pra L2: single-judge fixo. Multi-judge reduziria viés mas
multiplicaria custo (5 composers × 6 dims × N judges → cara). Para Sprint 4
um judge basta para gerar comparativo; multi-judge fica pra calibração.

Não há "right answer" — o objetivo é gerar matriz interpretável que aponte
onde HeuristicComposer perde/ganha contra LLMs e onde LLMs divergem entre si.

Uso:
    cd backend/cfai
    ../venv/bin/python tests/compare_composers.py
    # ou com judge específico:
    JUDGE_PROVIDER=groq ../venv/bin/python tests/compare_composers.py
"""
import json
import os
from datetime import date
from statistics import mean

try:
    from dotenv import load_dotenv
    load_dotenv("../.env")
except ImportError:
    pass

from cfai.composer_llm import LLMComposer
from cfai.cost_tracker import cost_tracker
from cfai.evaluation import evaluate_session, MetricCategory
from cfai.evaluation_judge import JudgeDimension, LLMProviderJudge, RUBRIC
from cfai.examples import karl
from cfai.llm_providers import PROVIDER_CLASSES
from cfai.movements_seed import load_default_library
from cfai.programmer import HeuristicComposer, ProgrammingContext, SessionPlanner
from cfai.workout_schema import Phase


JUDGE_PROVIDER_NAME = os.getenv("JUDGE_PROVIDER", "openai")


# ============================================================
# 1. Setup
# ============================================================

print("=" * 78)
print("COMPARISON HARNESS — composers × evaluation (Sprint 4)")
print("=" * 78)

library = load_default_library()
ctx = ProgrammingContext(
    athlete=karl, library=library, phase=Phase.BUILD,
    week_number=2, day_number=1,
    target_date=date(2026, 4, 27),
    weekly_focus=["squat_volume"],
)
judge_context = {
    "athlete_id": karl.id, "phase": ctx.phase.value,
    "week": ctx.week_number, "day": ctx.day_number,
    "weekly_focus": ctx.weekly_focus,
}


# ============================================================
# 2. Inicializa providers
# ============================================================

print("\n🔌 Inicializando providers...")
providers = {}
for name, cls in PROVIDER_CLASSES.items():
    try:
        providers[name] = cls()
        print(f"   ✅ {name:10s} → {providers[name].name}")
    except (ValueError, ImportError) as e:
        print(f"   ⚪ {name:10s} skipped — {e}")


# ============================================================
# 3. Seleciona judge
# ============================================================

if JUDGE_PROVIDER_NAME not in providers:
    print(f"\n❌ JUDGE_PROVIDER={JUDGE_PROVIDER_NAME!r} não está disponível.")
    print(f"   Disponíveis: {list(providers)}")
    raise SystemExit(1)

judge_provider = providers[JUDGE_PROVIDER_NAME]
judge = LLMProviderJudge(judge_provider, max_retries=2)
print(f"\n⚖️  Judge fixado: {judge_provider.name}")


# ============================================================
# 4. Gera sessões — heurístico + cada LLM
# ============================================================

print("\n📐 Gerando sessões...")
composers: dict[str, object] = {
    "heuristic": HeuristicComposer(library),
}
for name, provider in providers.items():
    composers[f"llm_{name}"] = LLMComposer(
        provider=provider, library=library, max_retries=2,
    )

sessions: dict[str, object] = {}
session_costs_before: dict[str, int] = {}
for cname, composer in composers.items():
    session_costs_before[cname] = len(cost_tracker.records)
    planner = SessionPlanner(library, composer)
    try:
        sess = planner.plan_session(ctx)
        sessions[cname] = sess
        print(f"   ✅ {cname:18s} blocks={len(sess.blocks)} "
              f"movs={sum(len(b.movements) for b in sess.blocks)}")
    except Exception as e:
        print(f"   ❌ {cname:18s} ERR — {type(e).__name__}: {e}")


# ============================================================
# 5. L1 — evaluate_session
# ============================================================

print("\n📏 L1 (deterministic) — evaluate_session:")
l1_results: dict[str, dict] = {}
for cname, sess in sessions.items():
    metrics = evaluate_session(sess, karl, library)
    by_name = {m.name: m for m in metrics}
    by_cat: dict[str, list[float]] = {}
    for m in metrics:
        by_cat.setdefault(m.category.value, []).append(m.score)
    cat_scores = {c: round(mean(s), 2) for c, s in by_cat.items()}
    l1_results[cname] = {
        "metrics": {m.name: {
            "score": m.score, "passed": m.passed,
            "raw_value": m.raw_value, "target": m.target,
            "details": m.details,
        } for m in metrics},
        "by_category": cat_scores,
    }

# Tabela L1 — uma linha por composer, colunas = nomes de métricas
metric_names = [
    "movement_library_coverage", "equipment_feasibility",
    "injury_safety", "prilepin_compliance", "inol_per_session",
]
short_names = ["lib_cov", "equip", "injury", "prilepin", "inol"]
print(f"   {'composer':<18s} " + " ".join(f"{n:<10s}" for n in short_names))
print(f"   {'-'*18} " + " ".join("-"*10 for _ in short_names))
for cname, r in l1_results.items():
    row = " ".join(
        f"{r['metrics'][n]['score']:<10.2f}" for n in metric_names
    )
    print(f"   {cname:<18s} {row}")


# ============================================================
# 6. L2 — LLM judge pointwise (todas dimensões × todos composers)
# ============================================================

print(f"\n⚖️  L2 (LLM-as-Judge via {judge_provider.name}) — pointwise:")
dims = list(JudgeDimension)
l2_results: dict[str, dict] = {}

for cname, sess in sessions.items():
    l2_results[cname] = {}
    for dim in dims:
        try:
            score = judge.score_pointwise(sess, dim, judge_context)
            l2_results[cname][dim.value] = {
                "score": score.score,
                "reasoning": score.reasoning,
                "judge_model": score.judge_model,
            }
        except Exception as e:
            l2_results[cname][dim.value] = {
                "score": 0,
                "reasoning": f"ERROR: {type(e).__name__}: {e}",
                "judge_model": judge_provider.name,
            }

# Tabela L2
print(f"\n   {'composer':<18s} " + " ".join(
    f"{d.value[:14]:<14s}" for d in dims
) + "  mean")
print(f"   {'-'*18} " + " ".join("-"*14 for _ in dims) + "  ----")
for cname, r in l2_results.items():
    scores = [r[d.value]["score"] for d in dims]
    row = " ".join(f"{s:<14d}" for s in scores)
    avg = round(mean(scores), 2)
    print(f"   {cname:<18s} {row}  {avg}")


# ============================================================
# 7. Cost summary
# ============================================================

print(f"\n💰 Cost summary:")
report = cost_tracker.report()
print(f"   Total calls: {report['n_calls']}")
print(f"   Total cost:  ${report['total_cost_usd']:.4f}")
print(f"\n   Per provider (composing + judging):")
for prov, b in report["by_provider"].items():
    print(f"     {prov:12s} calls={b['n_calls']:<3d} cost=${b['cost_usd']:.4f} "
          f"avg_latency={b['latency_ms_avg']}ms "
          f"schema_fail={b['schema_failure_rate']*100:.0f}%")


# ============================================================
# 8. Aggregate matrix (Markdown — fácil colar em PR/relatório)
# ============================================================

print(f"\n📊 Markdown matrix (composer × L2 dimension):")
print()
hdr = "| composer | " + " | ".join(d.value.replace("_", " ") for d in dims) + " | mean |"
sep = "|" + "---|" * (len(dims) + 2)
print(hdr)
print(sep)
for cname, r in l2_results.items():
    scores = [r[d.value]["score"] for d in dims]
    avg = round(mean(scores), 2)
    cells = " | ".join(str(s) for s in scores)
    print(f"| {cname} | {cells} | {avg} |")


# ============================================================
# 9. JSON export
# ============================================================

export = {
    "context": {
        "athlete": karl.id,
        "phase": ctx.phase.value,
        "week": ctx.week_number,
        "day": ctx.day_number,
        "weekly_focus": ctx.weekly_focus,
    },
    "judge_provider": JUDGE_PROVIDER_NAME,
    "judge_model": judge_provider.model,
    "composers_evaluated": list(sessions.keys()),
    "l1": l1_results,
    "l2": l2_results,
    "cost_report": report,
}
out_path = "compare_composers_results.json"
with open(out_path, "w") as f:
    json.dump(export, f, indent=2, default=str)
print(f"\n💾 JSON saved → {out_path}")

print(f"\n{'='*78}\nDONE\n{'='*78}")
