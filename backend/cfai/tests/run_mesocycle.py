"""
Mesocycle harness — Sprint 5e.

Para cada composer disponível, gera 1 mesociclo (4 semanas: 3 BUILD + 1 DELOAD,
5 sessions/semana = 20 sessions). Avalia:

L1 (deterministic, multi-week):
- progressive_overload (slope %1RM W1→W3)
- deload_presence (W4 marcado deload?)
- movement_variety (entropy de movement_id distribution)
- acwr (Acute:Chronic Workload Ratio)

L2 (LLM-as-Judge, multi-week):
- score_mesocycle_progression (judge vê sumário compacto, score 1-5)

Pergunta-chave: progression_logic L2 sobe quando judge vê multi-week
(vs Sprint 5c rerun em que avaliação per-session deu 1.9-3.0)?

Cost estimate: 1 mesocycle × N composers × ~60 LLM composer calls + 5 judge
calls. Com gpt-5-mini default, ~$1-2 total.

Uso:
    cd backend/cfai
    ../venv/bin/python tests/run_mesocycle.py
    JUDGE_PROVIDER=groq ../venv/bin/python tests/run_mesocycle.py
"""
from __future__ import annotations

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
from cfai.evaluation import (
    evaluate_mesocycle, evaluate_session, summary_score,
)
from cfai.evaluation_judge import LLMProviderJudge
from cfai.examples import karl
from cfai.llm_providers import PROVIDER_CLASSES
from cfai.mesocycle_planner import (
    DEFAULT_4WEEK_BUILD, MesocyclePlanner,
)
from cfai.movements_seed import load_default_library
from cfai.programmer import HeuristicComposer

JUDGE_PROVIDER_NAME = os.getenv("JUDGE_PROVIDER", "openai")
START_DATE = date(2026, 5, 4)


# ============================================================
# 1. Setup
# ============================================================

print("=" * 80)
print("MESOCYCLE EVALUATION HARNESS (Sprint 5e)")
print("=" * 80)

library = load_default_library()
print(f"\n📋 Spec: {len(DEFAULT_4WEEK_BUILD.weeks)} weeks "
      f"(deloads: {sorted(DEFAULT_4WEEK_BUILD.deload_weeks)}), "
      f"5 sessions/week = 20 sessions/mesocycle")


# ============================================================
# 2. Init providers
# ============================================================

print("\n🔌 Inicializando providers...")
providers = {}
for name, cls in PROVIDER_CLASSES.items():
    try:
        providers[name] = cls()
        print(f"   ✅ {name:10s} → {providers[name].name}")
    except (ValueError, ImportError) as e:
        print(f"   ⚪ {name:10s} skipped — {e}")

if JUDGE_PROVIDER_NAME not in providers:
    print(f"\n❌ JUDGE_PROVIDER={JUDGE_PROVIDER_NAME!r} indisponível.")
    raise SystemExit(1)
judge_provider = providers[JUDGE_PROVIDER_NAME]
judge = LLMProviderJudge(judge_provider, max_retries=2)
print(f"\n⚖️  Judge: {judge_provider.name}")


# ============================================================
# 3. Composers
# ============================================================

composers: dict[str, object] = {"heuristic": HeuristicComposer(library)}
for name, provider in providers.items():
    composers[f"llm_{name}"] = LLMComposer(
        provider=provider, library=library, max_retries=2,
    )
print(f"\n🎼 Composers: {list(composers)}")


# ============================================================
# 4. Generate mesocycles
# ============================================================

print(f"\n📐 Gerando mesociclos (4 weeks × 5 sessions = 20 sessions cada)...")
meso_context = {
    "athlete_id": karl.id,
    "phase": "build",
    "primary_focus": ["squat_volume", "pulling_capacity"],
    "duration_weeks": 4,
    "training_age_years": karl.training_age_years,
}

mesocycles: dict[str, object] = {}
for cname, composer in composers.items():
    print(f"\n   {cname}...", end=" ", flush=True)
    cost_before = sum(r.cost_usd for r in cost_tracker.records)
    planner = MesocyclePlanner(library, composer, sessions_per_week=5)
    try:
        meso = planner.plan_mesocycle(
            athlete=karl, spec=DEFAULT_4WEEK_BUILD,
            start_date=START_DATE,
            primary_focus=["squat_volume", "pulling_capacity"],
            weekly_focus=["squat_volume"],
            meso_id=f"meso_{cname}",
            meso_name=f"{cname} 4-week BUILD",
        )
        mesocycles[cname] = meso
        cost_delta = sum(r.cost_usd for r in cost_tracker.records) - cost_before
        n_sess = sum(len(w.sessions) for w in meso.weeks)
        n_blocks = sum(len(s.blocks) for w in meso.weeks for s in w.sessions)
        print(f"✅ sessions={n_sess} blocks={n_blocks} cost=${cost_delta:.4f}")
    except Exception as e:
        print(f"❌ {type(e).__name__}: {e}")


# ============================================================
# 5. L1 mesocycle metrics
# ============================================================

print(f"\n📏 L1 (multi-week deterministic) — evaluate_mesocycle:")
print(f"   {'composer':<18s} {'overload':>9s}  {'deload':>7s}  {'variety':>8s}  {'acwr':>5s}  {'period':>7s}  {'valid':>6s}")
print(f"   {'-'*18} {'-'*9}  {'-'*7}  {'-'*8}  {'-'*5}  {'-'*7}  {'-'*6}")

l1_results: dict[str, dict] = {}
for cname, meso in mesocycles.items():
    res = evaluate_mesocycle(meso, karl, library)
    by_name = {m["name"]: m for m in res["mesocycle_metrics"]}
    cat_summary = summary_score(res)
    # Cat keys são MetricCategory enum — convert para str
    cat = {str(k).split(".")[-1].lower(): v for k, v in cat_summary.items()}
    l1_results[cname] = {
        "mesocycle_metrics": {n: m for n, m in by_name.items()},
        "category_summary": cat,
    }
    print(f"   {cname:<18s} "
          f"{by_name['progressive_overload']['score']:>9.2f}  "
          f"{by_name['deload_presence']['score']:>7.2f}  "
          f"{by_name['movement_variety']['score']:>8.2f}  "
          f"{by_name['acwr']['score']:>5.2f}  "
          f"{cat.get('periodization', 0):>7.2f}  "
          f"{cat.get('validity', 0):>6.2f}")


# ============================================================
# 6. L2 — multi-week progression_logic
# ============================================================

print(f"\n⚖️  L2 progression_logic (judge vê SUMÁRIO multi-week):")
print(f"   {'composer':<18s} {'score':>5s}  reasoning (truncado)")
print(f"   {'-'*18} {'-'*5}  {'-'*60}")

l2_results: dict[str, dict] = {}
for cname, meso in mesocycles.items():
    try:
        score = judge.score_mesocycle_progression(meso, meso_context)
        l2_results[cname] = {
            "score": score.score,
            "reasoning": score.reasoning,
            "judge_model": score.judge_model,
        }
        print(f"   {cname:<18s} {score.score:>5d}  {score.reasoning[:140]}")
    except Exception as e:
        l2_results[cname] = {"score": 0, "reasoning": f"ERR: {type(e).__name__}: {e}"}
        print(f"   {cname:<18s}   ERR  {type(e).__name__}: {str(e)[:60]}")


# ============================================================
# 7. Comparison vs session-isolated baseline (Sprint 5c rerun)
# ============================================================

# Valores de referência do Sprint 5c rerun (session-isolated, 10 contexts):
sprint5c_progression = {
    "heuristic": 1.90,
    "llm_openai": 3.00,
    "llm_deepseek": 2.80,
    "llm_groq": 2.50,
    "llm_minimax": 3.00,
}

print(f"\n📊 Progression_logic — session-isolated vs mesocycle-aware:")
print(f"   {'composer':<18s} {'5c rerun':>8s}  {'5e meso':>8s}  {'Δ':>5s}")
print(f"   {'-'*18} {'-'*8}  {'-'*8}  {'-'*5}")
for cname in composers:
    old = sprint5c_progression.get(cname, 0.0)
    new = l2_results.get(cname, {}).get("score", 0)
    delta = round(new - old, 1)
    sign = "+" if delta > 0 else ""
    print(f"   {cname:<18s} {old:>8.2f}  {new:>8d}  {sign}{delta:>4}")


# ============================================================
# 8. Cost
# ============================================================

print(f"\n💰 Cost summary:")
report = cost_tracker.report()
print(f"   Total calls: {report['n_calls']}")
print(f"   Total cost:  ${report['total_cost_usd']:.4f}")
for prov, b in report["by_provider"].items():
    print(f"     {prov:12s} calls={b['n_calls']:<3d} cost=${b['cost_usd']:.4f} "
          f"avg_lat={b['latency_ms_avg']}ms schema_fail={b['schema_failure_rate']*100:.0f}%")


# ============================================================
# 9. Export
# ============================================================

# Mesocycles são objetos pesados — só exporta IDs + metrics
export = {
    "spec": {
        "weeks": [p.value for p in DEFAULT_4WEEK_BUILD.weeks],
        "deload_weeks": sorted(DEFAULT_4WEEK_BUILD.deload_weeks),
        "sessions_per_week": 5,
    },
    "judge_provider": JUDGE_PROVIDER_NAME,
    "judge_model": judge_provider.model,
    "composers": list(composers),
    "l1_results": {
        c: {
            "category_summary": l1_results[c]["category_summary"],
            "mesocycle_metrics": {
                n: {"score": m["score"], "raw_value": m.get("raw_value"),
                    "passed": m.get("passed"), "details": m.get("details")}
                for n, m in l1_results[c]["mesocycle_metrics"].items()
            },
        }
        for c in mesocycles
    },
    "l2_progression": l2_results,
    "comparison": {
        cname: {
            "session_isolated_baseline": sprint5c_progression.get(cname),
            "mesocycle_aware": l2_results.get(cname, {}).get("score"),
        }
        for cname in composers
    },
    "cost_report": report,
}
out_path = "run_mesocycle_results.json"
with open(out_path, "w") as f:
    json.dump(export, f, indent=2, default=str)
print(f"\n💾 JSON saved → {out_path}")

print(f"\n{'='*80}\nDONE\n{'='*80}")
