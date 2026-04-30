"""
Smoke test multi-provider — Sprint 3.

Gera 1 STRENGTH_DAY via HeuristicComposer (baseline) + 1 sessão por
LLM provider disponível (anthropic/openai/deepseek/groq/minimax).
Compara: blocks_count, movements_count, equipment_required, primary_stimulus,
schema_failure rate (via cost_tracker).

Skipa providers sem API key — não falha o teste.

Uso:
    cd backend/cfai
    ../venv/bin/python tests/smoke_composers.py
"""
import json
from datetime import date

try:
    from dotenv import load_dotenv
    load_dotenv("../.env")
except ImportError:
    pass

from cfai.composer_llm import LLMComposer
from cfai.cost_tracker import cost_tracker
from cfai.examples import karl
from cfai.llm_providers import PROVIDER_CLASSES
from cfai.movements_seed import load_default_library
from cfai.programmer import HeuristicComposer, ProgrammingContext, SessionPlanner
from cfai.workout_schema import Phase


# ============================================================
# 1. Setup
# ============================================================

print("=" * 72)
print("SMOKE TEST — multi-provider LLM composers (Sprint 3)")
print("=" * 72)

library = load_default_library()
ctx = ProgrammingContext(
    athlete=karl, library=library, phase=Phase.BUILD,
    week_number=2, day_number=1,
    target_date=date(2026, 4, 27),
    weekly_focus=["squat_volume"],
)


# ============================================================
# 2. Baseline heurístico
# ============================================================

print("\n📐 BASELINE (HeuristicComposer)")
heuristic_planner = SessionPlanner(library, HeuristicComposer(library))
baseline = heuristic_planner.plan_session(ctx)
print(f"   Session: {baseline.id}")
print(f"   Template: {baseline.template.value}")
print(f"   Blocks: {len(baseline.blocks)}  ({[b.type.value for b in baseline.blocks]})")
print(f"   Movements total: {sum(len(b.movements) for b in baseline.blocks)}")
print(f"   Equipment: {sorted(baseline.equipment_required)}")
print(f"   Primary stimulus: {baseline.primary_stimulus.value}")


# ============================================================
# 3. LLM composers (skipa sem key)
# ============================================================

print("\n🔌 Inicializando providers...")
providers = {}
for name, cls in PROVIDER_CLASSES.items():
    try:
        providers[name] = cls()
        print(f"   ✅ {name:10s} → {providers[name].name}")
    except (ValueError, ImportError) as e:
        print(f"   ⚪ {name:10s} skipped — {e}")

if not providers:
    print("\n❌ Nenhum provider disponível. Configure as API keys no .env.")
    raise SystemExit(1)


# ============================================================
# 4. Roda cada provider como composer
# ============================================================

results = {}
print(f"\n🎯 Gerando STRENGTH_DAY via cada provider:")
print(f"   {'Provider':<12s} {'Blocks':>7s}  {'Movs':>5s}  "
      f"{'Equipment':<24s} {'Stimulus':<22s} {'Status':<8s}")
print(f"   {'-'*12} {'-'*7}  {'-'*5}  {'-'*24} {'-'*22} {'-'*8}")

for name, provider in providers.items():
    cost_tracker_calls_before = len(cost_tracker.records)
    composer = LLMComposer(provider=provider, library=library, max_retries=2)
    planner = SessionPlanner(library, composer)
    try:
        session = planner.plan_session(ctx)
        n_blocks = len(session.blocks)
        n_movs = sum(len(b.movements) for b in session.blocks)
        eq = sorted(session.equipment_required)
        stim = session.primary_stimulus.value
        # Cost tracking só dessas chamadas
        new_calls = cost_tracker.records[cost_tracker_calls_before:]
        n_schema_fail = sum(1 for r in new_calls if r.schema_failure)
        total_cost = sum(r.cost_usd for r in new_calls)
        avg_lat = (
            sum(r.latency_ms for r in new_calls) // max(1, len(new_calls))
        )
        status = "ok"
        print(f"   {name:<12s} {n_blocks:>7d}  {n_movs:>5d}  "
              f"{str(eq)[:23]:<24s} {stim[:21]:<22s} {status:<8s}")
        results[name] = {
            "model": provider.model,
            "session_id": session.id,
            "n_blocks": n_blocks,
            "n_movements": n_movs,
            "block_types": [b.type.value for b in session.blocks],
            "equipment": eq,
            "primary_stimulus": stim,
            "n_calls": len(new_calls),
            "schema_failures": n_schema_fail,
            "total_cost_usd": round(total_cost, 5),
            "avg_latency_ms": avg_lat,
            "blocks_detail": [
                {
                    "type": b.type.value,
                    "format": b.format.value if b.format else None,
                    "stimulus": b.stimulus.value if b.stimulus else None,
                    "intent": b.intent,
                    "movements": [
                        {
                            "id": mp.movement_id,
                            "reps": mp.reps, "time_s": mp.time_seconds,
                            "dist_m": mp.distance_meters, "cal": mp.calories,
                            "load": (
                                {
                                    "type": mp.load.type, "value": mp.load.value,
                                    "ref": mp.load.reference_lift,
                                } if mp.load else None
                            ),
                        }
                        for mp in b.movements
                    ],
                }
                for b in session.blocks
            ],
        }
    except Exception as e:
        print(f"   {name:<12s}   ERR    {type(e).__name__}: {str(e)[:60]}")
        results[name] = {"error": f"{type(e).__name__}: {e}"}


# ============================================================
# 5. Detalhamento per-provider (resumo de movements escolhidos nos
#    blocos criativos: STRENGTH_PRIMARY/SECONDARY/METCON)
# ============================================================

print("\n💬 Movement choices nos blocos criativos:")
for name, r in results.items():
    if "error" in r:
        print(f"\n   ❌ {name}: {r['error']}")
        continue
    print(f"\n   • {name} ({r['model']})  n_calls={r['n_calls']} "
          f"schema_fail={r['schema_failures']} cost=${r['total_cost_usd']:.5f}:")
    for b in r["blocks_detail"]:
        if b["type"] in ("strength_primary", "strength_secondary", "metcon"):
            mids = [m["id"] for m in b["movements"]]
            print(f"     {b['type']:<22s} fmt={b['format']:<20s} → {mids}")


# ============================================================
# 6. Cost summary
# ============================================================

print(f"\n💰 Cost summary (TODAS as chamadas, inclui retries):")
report = cost_tracker.report()
print(f"   Total calls: {report['n_calls']}")
print(f"   Total cost:  ${report['total_cost_usd']:.5f}")
print(f"\n   Per provider:")
for prov, b in report["by_provider"].items():
    print(f"     {prov:12s} calls={b['n_calls']:<3d} cost=${b['cost_usd']:.5f} "
          f"avg_latency={b['latency_ms_avg']}ms "
          f"schema_fail={b['schema_failure_rate']*100:.0f}%")


# ============================================================
# 7. JSON export
# ============================================================

export = {
    "context": {
        "athlete": karl.id,
        "phase": ctx.phase.value,
        "week": ctx.week_number,
        "day": ctx.day_number,
        "weekly_focus": ctx.weekly_focus,
    },
    "baseline_heuristic": {
        "n_blocks": len(baseline.blocks),
        "n_movements": sum(len(b.movements) for b in baseline.blocks),
        "equipment": sorted(baseline.equipment_required),
        "primary_stimulus": baseline.primary_stimulus.value,
        "block_types": [b.type.value for b in baseline.blocks],
    },
    "llm_results": results,
    "cost_report": report,
}
out_path = "smoke_composers_results.json"
with open(out_path, "w") as f:
    json.dump(export, f, indent=2, default=str)
print(f"\n💾 JSON saved → {out_path}")

print(f"\n{'='*72}\nDONE\n{'='*72}")
