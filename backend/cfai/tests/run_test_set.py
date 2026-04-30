"""
Frozen test set runner — Sprint 5c.

Roda cada composer disponível (heuristic + LLMs) sobre N contextos do
fixture tests/fixtures/test_contexts.json, agrega:
  - L1 mean por composer × métrica
  - L2 mean por composer × dimension
  - Ranking final por composer (L2 mean across all contexts/dims)
  - Win-rate matrix (composer A > B em quantos % dos contextos)

Runs determinísticos? Não — LLMs com temperature>0 variam. Mas N≥10 estabiliza
o ranking dentro do erro do judge.

Custo escala linear em N: ~\$0.30 por context com judge=openai (5 composers
× 6 dims × 1 context). Para os 20 contexts default → ~\$6.

Uso:
    cd backend/cfai
    ../venv/bin/python tests/run_test_set.py                    # todos 20
    ../venv/bin/python tests/run_test_set.py --max-contexts 5   # smoke
    JUDGE_PROVIDER=groq ../venv/bin/python tests/run_test_set.py --max 10
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

from cfai.composer_llm import LLMComposer
from cfai.cost_tracker import cost_tracker
from cfai.evaluation import evaluate_session
from cfai.evaluation_judge import JudgeDimension, LLMProviderJudge
from cfai.examples import karl
from cfai.llm_providers import PROVIDER_CLASSES
from cfai.movements_seed import load_default_library
from cfai.programmer import HeuristicComposer, ProgrammingContext, SessionPlanner
from cfai.workout_schema import Phase


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "test_contexts.json"
JUDGE_PROVIDER_NAME = os.getenv("JUDGE_PROVIDER", "openai")
EST_USD_PER_CONTEXT = 0.32  # baseado em compare_composers (Sprint 4)


# ============================================================
# CLI
# ============================================================

parser = argparse.ArgumentParser()
parser.add_argument("--max-contexts", "--max", type=int, default=5,
                    help="máximo de contexts a rodar (default 5 — smoke; "
                         "use 20 para corrida completa)")
parser.add_argument("--out", default="run_test_set_results.json")
parser.add_argument("--no-confirm", action="store_true",
                    help="pula confirmação de custo")
args = parser.parse_args()


# ============================================================
# 1. Load fixture
# ============================================================

print("=" * 80)
print("FROZEN TEST SET RUNNER (Sprint 5c)")
print("=" * 80)

with open(FIXTURE_PATH) as f:
    fixture = json.load(f)

contexts_raw = fixture["contexts"][: args.max_contexts]
print(f"\n📋 Contexts loaded: {len(contexts_raw)} de {len(fixture['contexts'])}")
print(f"   Fixture: {FIXTURE_PATH}")
print(f"   Athlete: {fixture['athlete_id']}, version={fixture['version']}")


# ============================================================
# 2. Init providers + judge
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
    print(f"\n❌ JUDGE_PROVIDER={JUDGE_PROVIDER_NAME!r} não disponível.")
    raise SystemExit(1)

judge_provider = providers[JUDGE_PROVIDER_NAME]
judge = LLMProviderJudge(judge_provider, max_retries=2)
print(f"\n⚖️  Judge: {judge_provider.name}")


# ============================================================
# 3. Composers
# ============================================================

library = load_default_library()
composers: dict[str, object] = {"heuristic": HeuristicComposer(library)}
for name, provider in providers.items():
    composers[f"llm_{name}"] = LLMComposer(
        provider=provider, library=library, max_retries=2,
    )

print(f"\n🎼 Composers: {list(composers)}")


# ============================================================
# 4. Cost estimate + confirm
# ============================================================

n_cells = len(contexts_raw) * len(composers)
est_cost = len(contexts_raw) * EST_USD_PER_CONTEXT
print(f"\n💵 Estimated cost: ~${est_cost:.2f} "
      f"({n_cells} sessions × ~6 judge calls each)")

if not args.no_confirm and est_cost > 1.0:
    resp = input(f"   Continuar? [y/N] ").strip().lower()
    if resp != "y":
        print("   Abortado.")
        raise SystemExit(0)


# ============================================================
# 5. Build ProgrammingContext objects
# ============================================================

def build_ctx(raw: dict) -> ProgrammingContext:
    return ProgrammingContext(
        athlete=karl,
        library=library,
        phase=Phase(raw["phase"]),
        week_number=raw["week_number"],
        day_number=raw["day_number"],
        target_date=date(2026, 4, 27) + timedelta(days=raw["day_number"]),
        weekly_focus=raw["weekly_focus"],
    )


contexts = [(c["id"], build_ctx(c), c) for c in contexts_raw]


# ============================================================
# 6. Main loop — generate + evaluate
# ============================================================

# results[composer][context_id] = {l1: {...}, l2: {...}}
results: dict[str, dict[str, dict]] = {c: {} for c in composers}
session_failures: list[tuple[str, str, str]] = []  # (composer, ctx_id, error)

dims = list(JudgeDimension)
total_contexts = len(contexts)

for i, (cid, ctx, raw) in enumerate(contexts, 1):
    print(f"\n[{i}/{total_contexts}] {cid}: {raw['phase']}/W{raw['week_number']}/D{raw['day_number']} "
          f"focus={raw['weekly_focus']}")
    judge_context = {
        "athlete_id": karl.id, "phase": ctx.phase.value,
        "week": ctx.week_number, "day": ctx.day_number,
        "weekly_focus": ctx.weekly_focus,
    }

    for cname, composer in composers.items():
        planner = SessionPlanner(library, composer)
        try:
            sess = planner.plan_session(ctx)
        except Exception as e:
            print(f"   ❌ {cname:18s} session failed: {type(e).__name__}: {e}")
            session_failures.append((cname, cid, f"{type(e).__name__}: {e}"))
            results[cname][cid] = {"error": str(e)}
            continue

        # L1
        l1_metrics = evaluate_session(sess, karl, library)
        l1 = {m.name: {"score": m.score, "passed": m.passed,
                       "raw_value": m.raw_value} for m in l1_metrics}

        # L2
        l2 = {}
        for dim in dims:
            try:
                score = judge.score_pointwise(sess, dim, judge_context)
                l2[dim.value] = {"score": score.score, "reasoning": score.reasoning[:200]}
            except Exception as e:
                l2[dim.value] = {"score": 0, "reasoning": f"ERR: {type(e).__name__}: {e}"}

        l2_mean = mean(l2[d.value]["score"] for d in dims)
        results[cname][cid] = {
            "l1": l1, "l2": l2, "l2_mean": round(l2_mean, 2),
            "n_blocks": len(sess.blocks),
            "n_movements": sum(len(b.movements) for b in sess.blocks),
            "primary_stimulus": sess.primary_stimulus.value,
        }
        print(f"   ✅ {cname:18s} L2_mean={l2_mean:.2f} "
              f"blocks={len(sess.blocks)} movs={sum(len(b.movements) for b in sess.blocks)}")


# ============================================================
# 7. Aggregations
# ============================================================

print(f"\n{'='*80}\nAGGREGATIONS\n{'='*80}")

# 7a. Per-composer L2 stats
print(f"\n📊 Per-composer L2 mean (across {len(contexts)} contexts):")
print(f"   {'composer':<18s} {'n':>3s}  {'mean':>5s}  {'std':>5s}  {'min':>4s}  {'max':>4s}")
print(f"   {'-'*18} {'-'*3}  {'-'*5}  {'-'*5}  {'-'*4}  {'-'*4}")
composer_stats: dict[str, dict] = {}
for cname in composers:
    means = [r["l2_mean"] for r in results[cname].values() if "l2_mean" in r]
    if not means:
        print(f"   {cname:<18s}  no successful runs")
        continue
    s = round(stdev(means), 2) if len(means) > 1 else 0.0
    composer_stats[cname] = {
        "n": len(means), "mean": round(mean(means), 2), "std": s,
        "min": min(means), "max": max(means),
    }
    print(f"   {cname:<18s} {len(means):>3d}  "
          f"{composer_stats[cname]['mean']:>5.2f}  "
          f"{s:>5.2f}  {min(means):>4.2f}  {max(means):>4.2f}")


# 7b. Per-dimension breakdown
print(f"\n📐 Per-dimension mean per composer:")
hdr = f"   {'composer':<18s} " + " ".join(f"{d.value[:10]:<11s}" for d in dims)
print(hdr)
print(f"   {'-'*18} " + " ".join("-"*11 for _ in dims))
dim_stats: dict[str, dict[str, float]] = {}
for cname in composers:
    dim_stats[cname] = {}
    cells = []
    for d in dims:
        scores = [r["l2"][d.value]["score"] for r in results[cname].values()
                  if "l2" in r and r["l2"].get(d.value, {}).get("score", 0) > 0]
        m = round(mean(scores), 2) if scores else 0.0
        dim_stats[cname][d.value] = m
        cells.append(f"{m:<11.2f}")
    print(f"   {cname:<18s} {' '.join(cells)}")


# 7c. Win-rate matrix (head-to-head per context)
print(f"\n🥊 Win-rate (row beats column, % of contexts where row L2_mean > col):")
hdr = f"   {'vs':<18s} " + " ".join(f"{c[:10]:<11s}" for c in composers)
print(hdr)
print(f"   {'-'*18} " + " ".join("-"*11 for _ in composers))
win_matrix: dict[str, dict[str, float]] = {}
for ca in composers:
    win_matrix[ca] = {}
    cells = []
    for cb in composers:
        if ca == cb:
            cells.append(f"{'-':<11s}")
            win_matrix[ca][cb] = None
            continue
        wins, ties, losses = 0, 0, 0
        for cid in [c[0] for c in contexts]:
            ra = results[ca].get(cid, {}).get("l2_mean")
            rb = results[cb].get(cid, {}).get("l2_mean")
            if ra is None or rb is None:
                continue
            if ra > rb:
                wins += 1
            elif ra < rb:
                losses += 1
            else:
                ties += 1
        total = wins + ties + losses
        rate = round(100 * wins / total, 0) if total else 0.0
        win_matrix[ca][cb] = rate
        cells.append(f"{rate:>3.0f}% ({wins}-{ties}-{losses})  ")
    print(f"   {ca:<18s} {''.join(cells)}")


# 7d. L1 summary
print(f"\n📏 L1 means (validity gates + volume metrics):")
l1_metric_names = ["movement_library_coverage", "equipment_feasibility",
                   "injury_safety", "prilepin_compliance", "inol_per_session"]
short = ["lib", "equip", "injury", "prilepin", "inol"]
print(f"   {'composer':<18s} " + " ".join(f"{s:<10s}" for s in short))
print(f"   {'-'*18} " + " ".join("-"*10 for _ in short))
l1_stats: dict[str, dict[str, float]] = {}
for cname in composers:
    l1_stats[cname] = {}
    cells = []
    for n in l1_metric_names:
        scores = [r["l1"][n]["score"] for r in results[cname].values()
                  if "l1" in r and n in r.get("l1", {})]
        m = round(mean(scores), 2) if scores else 0.0
        l1_stats[cname][n] = m
        cells.append(f"{m:<10.2f}")
    print(f"   {cname:<18s} {' '.join(cells)}")


# ============================================================
# 8. Cost summary
# ============================================================

print(f"\n💰 Cost summary:")
report = cost_tracker.report()
print(f"   Total calls: {report['n_calls']}")
print(f"   Total cost:  ${report['total_cost_usd']:.4f}")
for prov, b in report["by_provider"].items():
    print(f"     {prov:12s} calls={b['n_calls']:<3d} cost=${b['cost_usd']:.4f} "
          f"avg_lat={b['latency_ms_avg']}ms schema_fail={b['schema_failure_rate']*100:.0f}%")

if session_failures:
    print(f"\n⚠️  Session generation failures: {len(session_failures)}")
    for cname, cid, err in session_failures[:10]:
        print(f"     {cname:18s} {cid}: {err[:80]}")


# ============================================================
# 9. Export
# ============================================================

export = {
    "fixture_version": fixture["version"],
    "n_contexts": len(contexts),
    "judge_provider": JUDGE_PROVIDER_NAME,
    "judge_model": judge_provider.model,
    "composers": list(composers),
    "results": results,
    "aggregations": {
        "composer_stats": composer_stats,
        "dim_stats": dim_stats,
        "win_matrix": win_matrix,
        "l1_stats": l1_stats,
    },
    "cost_report": report,
    "session_failures": session_failures,
}
with open(args.out, "w") as f:
    json.dump(export, f, indent=2, default=str)
print(f"\n💾 JSON saved → {args.out}")

print(f"\n{'='*80}\nDONE\n{'='*80}")
