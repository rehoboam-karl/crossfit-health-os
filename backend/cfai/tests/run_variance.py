"""
Sprint 5k — variance intra-scenario harness.

Roda o mesmo scenario N vezes pra separar:
  - phase signal (variação ENTRE scenarios)
  - LLM stochastic noise (variação DENTRO do mesmo scenario)
  - judge stochastic noise (variação ENTRE chamadas do mesmo judge)

Pra cada scenario × repetition: gera mesocycle por composer, avalia L1+L2
e armazena por (scenario, rep, composer). No fim:
  - within_std = std das N reps DENTRO de cada (scenario, composer)
  - between_std = std ENTRE scenarios da MEAN de cada composer
  - signal/noise = between/within. Se >2, diferença entre phases é real.

Cost-cuidadoso: por default 2 scenarios × 3 reps × len(composers) mesocycles.
Com 6 composers (heuristic + 5 LLM) = 36 mesocycles ≈ $2.50.

Uso:
    cd backend/cfai
    ../venv/bin/python tests/run_variance.py                       # 2 scen × 3 reps
    ../venv/bin/python tests/run_variance.py --reps 5 --scenarios 3
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, stdev

try:
    from dotenv import load_dotenv
    load_dotenv("../.env")
except ImportError:
    pass

from cfai.composer_hybrid import HybridComposer
from cfai.composer_llm import LLMComposer
from cfai.cost_tracker import cost_tracker
from cfai.evaluation import evaluate_mesocycle
from cfai.evaluation_judge import LLMProviderJudge
from cfai.examples import karl
from cfai.llm_providers import PROVIDER_CLASSES
from cfai.mesocycle_planner import MesocyclePlanner, MesocycleSpec
from cfai.movements_seed import load_default_library
from cfai.programmer import HeuristicComposer
from cfai.workout_schema import Phase

FIXTURE = Path(__file__).parent / "fixtures" / "mesocycle_scenarios.json"
JUDGE_PROVIDER_NAME = os.getenv("JUDGE_PROVIDER", "openai")
EXCLUDED_JUDGES = frozenset({"groq"})  # consistente com Sprint 5d/multi_judge


# ============================================================
# CLI
# ============================================================

parser = argparse.ArgumentParser()
parser.add_argument("--scenarios", "--max-scenarios", type=int, default=2,
                    help="quantos scenarios do fixture (default 2)")
parser.add_argument("--reps", type=int, default=3,
                    help="repetições por scenario (default 3)")
parser.add_argument("--out", default="run_variance_results.json")
parser.add_argument("--no-confirm", action="store_true")
parser.add_argument("--exclude-providers", default="",
                    help="lista CSV pra excluir do pool, ex: 'minimax,groq'")
args = parser.parse_args()
EXCLUDED_PROVIDERS = frozenset(
    p.strip() for p in args.exclude_providers.split(",") if p.strip()
)


# ============================================================
# 1. Setup
# ============================================================

print("=" * 80)
print("VARIANCE INTRA-SCENARIO HARNESS (Sprint 5k)")
print("=" * 80)

with open(FIXTURE) as f:
    fixture = json.load(f)
scenarios_raw = fixture["scenarios"][: args.scenarios]
print(f"\n📋 Scenarios × reps: {len(scenarios_raw)} × {args.reps} = "
      f"{len(scenarios_raw) * args.reps} runs por composer")
for s in scenarios_raw:
    print(f"   - {s['id']}: {s['name']}")


# ============================================================
# 2. Providers + judge
# ============================================================

print("\n🔌 Providers...")
providers = {}
for name, cls in PROVIDER_CLASSES.items():
    if name in ("ollama", "unsloth"):
        continue  # local providers — escopo separado
    if name in EXCLUDED_PROVIDERS:
        print(f"   ⛔ {name} excluído via --exclude-providers")
        continue
    try:
        providers[name] = cls()
        print(f"   ✅ {name}")
    except (ValueError, ImportError) as e:
        print(f"   ⚪ {name} skip — {e}")

if JUDGE_PROVIDER_NAME not in providers:
    raise SystemExit(f"❌ JUDGE_PROVIDER={JUDGE_PROVIDER_NAME} indisponível")
judge = LLMProviderJudge(providers[JUDGE_PROVIDER_NAME], max_retries=2)
print(f"\n⚖️  Judge: {providers[JUDGE_PROVIDER_NAME].name}")


# ============================================================
# 3. Composers
# ============================================================

library = load_default_library()
composers: dict[str, object] = {"heuristic": HeuristicComposer(library)}
for name, prov in providers.items():
    composers[f"hybrid_{name}"] = HybridComposer(prov, library, max_retries=2)
print(f"\n🎼 Composers: {len(composers)} → {list(composers)}")


# ============================================================
# 4. Cost prelude
# ============================================================

n_meso = len(scenarios_raw) * args.reps * len(composers)
est_cost = n_meso * 0.07
print(f"\n💵 ~{n_meso} mesocycles × $0.07 ≈ ${est_cost:.2f}")
if not args.no_confirm and est_cost > 1.0:
    if input("   Continuar? [y/N] ").strip().lower() != "y":
        raise SystemExit(0)


# ============================================================
# 5. Loop
# ============================================================

# results[composer][scenario_id][rep_idx] = {l1_*, l2_*}
results: dict[str, dict[str, list[dict]]] = {
    c: {s["id"]: [] for s in scenarios_raw} for c in composers
}
start_date = date(2026, 5, 4)

for s_idx, scen in enumerate(scenarios_raw, 1):
    print(f"\n{'='*80}")
    print(f"[SCENARIO {s_idx}/{len(scenarios_raw)}] {scen['id']}")
    print(f"{'='*80}")
    spec = MesocycleSpec(
        weeks=[Phase(p) for p in scen["weeks"]],
        deload_weeks=set(scen.get("deload_weeks", [])),
    )
    judge_context = {
        "athlete_id": karl.id, "scenario": scen["id"],
        "phases": scen["weeks"], "primary_focus": scen["primary_focus"],
    }

    for rep in range(args.reps):
        print(f"\n  ── rep {rep+1}/{args.reps}")
        for cname, composer in composers.items():
            cost_before = sum(r.cost_usd for r in cost_tracker.records)
            planner = MesocyclePlanner(library, composer, sessions_per_week=5)
            try:
                meso = planner.plan_mesocycle(
                    athlete=karl, spec=spec,
                    start_date=start_date + timedelta(
                        days=(s_idx * 100 + rep) * 7
                    ),
                    primary_focus=scen["primary_focus"],
                    weekly_focus=scen["weekly_focus"],
                    meso_id=f"{scen['id']}__{cname}__rep{rep}",
                    meso_name=f"{cname} {scen['name']} rep{rep}",
                )
            except Exception as e:
                print(f"     ❌ {cname:18s} GEN FAIL — {type(e).__name__}: {e}")
                results[cname][scen["id"]].append({"error": str(e)})
                continue

            eval_res = evaluate_mesocycle(meso, karl, library)
            by_meso = {m["name"]: m for m in eval_res["mesocycle_metrics"]}
            sess_avg: dict[str, float] = {}
            for sm in eval_res["session_metrics"]:
                for m in sm["metrics"]:
                    sess_avg.setdefault(m["name"], []).append(m["score"])
            sess_avg = {k: mean(v) for k, v in sess_avg.items()}

            try:
                l2 = judge.score_mesocycle_progression(meso, judge_context)
                l2_score = l2.score
            except Exception as e:
                l2_score = 0
            cost_delta = sum(r.cost_usd for r in cost_tracker.records) - cost_before

            results[cname][scen["id"]].append({
                "rep": rep,
                "l1_overload": by_meso["progressive_overload"]["score"],
                "l1_prilepin": sess_avg.get("prilepin_compliance", 0),
                "l1_inol": sess_avg.get("inol_per_session", 0),
                "l2_progression": l2_score,
                "cost_usd": cost_delta,
            })
            print(f"     ✅ {cname:18s} prilepin={sess_avg.get('prilepin_compliance', 0):.2f} "
                  f"inol={sess_avg.get('inol_per_session', 0):.2f} "
                  f"L2={l2_score} cost=${cost_delta:.4f}")


# ============================================================
# 6. Variance analysis
# ============================================================

print(f"\n{'='*80}\nVARIANCE ANALYSIS\n{'='*80}")

metrics = ["l1_overload", "l1_prilepin", "l1_inol", "l2_progression"]
short = ["overload", "prilepin", "inol", "L2_prog"]

# within_std: std das reps DENTRO de cada (scenario, composer)
# between_std: std DAS MEDIAS por scenario, agregado
agg: dict[str, dict] = {}
for cname in composers:
    agg[cname] = {}
    for m, lbl in zip(metrics, short):
        within_stds = []
        scen_means = []
        for sid, runs in results[cname].items():
            valid = [r[m] for r in runs if isinstance(r, dict) and m in r]
            if len(valid) >= 2:
                within_stds.append(stdev(valid))
            if valid:
                scen_means.append(mean(valid))
        if not scen_means:
            agg[cname][m] = None
            continue
        within = mean(within_stds) if within_stds else 0.0
        between = stdev(scen_means) if len(scen_means) > 1 else 0.0
        snr = (between / within) if within > 0 else float("inf")
        agg[cname][m] = {
            "within_std": round(within, 3),
            "between_std": round(between, 3),
            "snr": round(snr, 2) if snr != float("inf") else "inf",
            "scenario_means": [round(s, 2) for s in scen_means],
        }

# Tabela
print(f"\n📊 Within-rep STD (LLM/judge stochastic noise):")
print(f"   {'composer':<18s} " + " ".join(f"{n:<10s}" for n in short))
print(f"   {'-'*18} " + " ".join("-"*10 for _ in short))
for cname in composers:
    cells = []
    for m in metrics:
        d = agg[cname][m]
        cells.append(f"{d['within_std']:<10.3f}" if d else f"{'N/A':<10s}")
    print(f"   {cname:<18s} {' '.join(cells)}")

print(f"\n📊 Between-scenario STD (phase signal):")
print(f"   {'composer':<18s} " + " ".join(f"{n:<10s}" for n in short))
print(f"   {'-'*18} " + " ".join("-"*10 for _ in short))
for cname in composers:
    cells = []
    for m in metrics:
        d = agg[cname][m]
        cells.append(f"{d['between_std']:<10.3f}" if d else f"{'N/A':<10s}")
    print(f"   {cname:<18s} {' '.join(cells)}")

print(f"\n📊 SNR = between_std / within_std (>2 = phase signal real, <1 = noise dominates):")
print(f"   {'composer':<18s} " + " ".join(f"{n:<10s}" for n in short))
print(f"   {'-'*18} " + " ".join("-"*10 for _ in short))
for cname in composers:
    cells = []
    for m in metrics:
        d = agg[cname][m]
        cells.append(f"{d['snr']!s:<10s}" if d else f"{'N/A':<10s}")
    print(f"   {cname:<18s} {' '.join(cells)}")


# ============================================================
# 7. Export
# ============================================================

print(f"\n💰 Cost: ${sum(r.cost_usd for r in cost_tracker.records):.4f}")

export = {
    "scenarios": [s["id"] for s in scenarios_raw],
    "reps": args.reps,
    "judge": JUDGE_PROVIDER_NAME,
    "composers": list(composers),
    "results": results,
    "variance_agg": agg,
    "cost_report": cost_tracker.report(),
}
with open(args.out, "w") as f:
    json.dump(export, f, indent=2, default=str)
print(f"💾 → {args.out}")
print(f"\n{'='*80}\nDONE\n{'='*80}")
