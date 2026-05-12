"""Re-gen hybrid_grok mesocycle and dump per-session INOL detail to find drop cause."""
import json
import os
from datetime import date

try:
    from dotenv import load_dotenv
    load_dotenv("../.env")
except ImportError:
    pass

from cfai.composer_hybrid import HybridComposer
from cfai.evaluation import metric_inol
from cfai.examples import karl
from cfai.llm_providers import GrokProvider
from cfai.mesocycle_planner import DEFAULT_4WEEK_BUILD, MesocyclePlanner
from cfai.movements_seed import load_default_library

library = load_default_library()
provider = GrokProvider()
composer = HybridComposer(provider=provider, library=library, max_retries=2)
planner = MesocyclePlanner(library, composer, sessions_per_week=5)

print(f"Generating hybrid_grok mesocycle (judge/composer={provider.name})...")
meso = planner.plan_mesocycle(
    athlete=karl, spec=DEFAULT_4WEEK_BUILD,
    start_date=date(2026, 5, 4),
    primary_focus=["squat_volume", "pulling_capacity"],
    weekly_focus=["squat_volume"],
    meso_id="meso_hybrid_inspect",
    meso_name="hybrid INOL inspection",
)

# Per-session INOL with per-movement breakdown
failures = []  # sessions with INOL < 0.6 (passed=False threshold)
all_results = []
for w_idx, week in enumerate(meso.weeks, 1):
    for s_idx, sess in enumerate(week.sessions, 1):
        r = metric_inol(sess)
        per_mov = r.details.get("per_movement", {})
        out_of_range = {
            mid: round(v, 3) for mid, v in per_mov.items()
            if not (0.4 <= v <= 1.0)
        }
        all_results.append({
            "week": w_idx, "session": s_idx,
            "template": sess.template.value,
            "score": r.score, "avg_inol": r.raw_value,
            "n_movements": len(per_mov),
            "per_movement": {k: round(v, 3) for k, v in per_mov.items()},
            "out_of_range": out_of_range,
        })
        if r.score < 0.6:
            failures.append(all_results[-1])

print(f"\n📊 INOL summary across {len(all_results)} sessions:")
scores = [r["score"] for r in all_results]
print(f"   mean score: {sum(scores)/len(scores):.3f}")
print(f"   sessions with score < 0.6 (fail): {len(failures)}/{len(all_results)}")

print(f"\n❌ Failing sessions (score < 0.6):")
for r in failures:
    print(f"\n   W{r['week']} S{r['session']} — {r['template']} — score={r['score']:.2f}")
    print(f"     all movements with %1RM: {r['per_movement']}")
    print(f"     OUT OF RANGE [0.4, 1.0]: {r['out_of_range']}")

# Aggregate: which movements are most often out of range?
out_count: dict[str, int] = {}
out_vals: dict[str, list[float]] = {}
for r in all_results:
    for mid, v in r["out_of_range"].items():
        out_count[mid] = out_count.get(mid, 0) + 1
        out_vals.setdefault(mid, []).append(v)

print(f"\n🔍 Movements most often out of range:")
for mid, n in sorted(out_count.items(), key=lambda kv: -kv[1]):
    vals = out_vals[mid]
    low = sum(1 for v in vals if v < 0.4)
    high = sum(1 for v in vals if v > 1.0)
    print(f"   {mid:<28s} n={n:<3d}  too_low={low}  too_high={high}  "
          f"min={min(vals):.2f} max={max(vals):.2f}")

with open("hybrid_inol_inspect.json", "w") as f:
    json.dump({"sessions": all_results, "out_of_range_counts": out_count}, f, indent=2)
print(f"\n💾 Dump → hybrid_inol_inspect.json")
