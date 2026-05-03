"""
Análise offline dos resultados de run_unsloth_composer.py.

Carrega run_unsloth_results.json (ou outro path via --in) e mostra:
  - L1 metric distributions (mean, std, p50, p95)
  - Latency stats per composer (mean, p50, p95, max)
  - Schema failure rate by block label
  - Per-context drill-down (one line each)
  - Worst sessions por métrica (pra debug visual)

Uso:
    cd backend/cfai
    ../venv/bin/python tests/analyze_unsloth_results.py
    ../venv/bin/python tests/analyze_unsloth_results.py --in run_unsloth_results.json
    ../venv/bin/python tests/analyze_unsloth_results.py --metric prilepin_compliance --worst 3
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


parser = argparse.ArgumentParser()
parser.add_argument("--in", dest="inp", default="run_unsloth_results.json")
parser.add_argument("--metric", default="prilepin_compliance",
                    help="L1 metric pra worst-sessions report")
parser.add_argument("--worst", type=int, default=3,
                    help="quantas worst sessions mostrar")
args = parser.parse_args()

path = Path(args.inp)
if not path.exists():
    raise SystemExit(f"❌ {path} não existe. Rode run_unsloth_composer.py primeiro.")

with open(path) as f:
    data = json.load(f)

print(f"=== {path.name} ===")
print(f"started:  {data.get('started_at', 'unknown')}")
print(f"provider: {data['provider']['name']}")
print(f"contexts: {len(data['contexts'])}  composers: {data['composers']}")
print()


# ============================================================
# 1. L1 distributions
# ============================================================

print("=" * 80)
print("L1 METRIC DISTRIBUTIONS (mean | std | p50 | p95 | min)")
print("=" * 80)

key_metrics = ["prilepin_compliance", "inol_per_session",
               "equipment_feasibility", "injury_safety",
               "movement_library_coverage"]

for cname in data["composers"]:
    rows = [r for r in data["results"][cname].values() if "l1" in r]
    if not rows:
        print(f"\n{cname}: no data")
        continue
    print(f"\n📊 {cname} (n={len(rows)})")
    print(f"   {'metric':<28s} {'mean':>6s} {'std':>6s} {'p50':>6s} {'p95':>6s} {'min':>6s}")
    print(f"   {'-'*28} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6}")
    for m in key_metrics:
        vals = [
            r["l1"]["metrics"].get(m, {}).get("score", 0)
            for r in rows if m in r["l1"]["metrics"]
        ]
        if not vals:
            print(f"   {m:<28s} {'N/A'}")
            continue
        mu = mean(vals)
        sd = stdev(vals) if len(vals) > 1 else 0.0
        p50 = percentile(vals, 0.5)
        p95 = percentile(vals, 0.95)
        mn = min(vals)
        print(f"   {m:<28s} {mu:>6.2f} {sd:>6.2f} {p50:>6.2f} {p95:>6.2f} {mn:>6.2f}")


# ============================================================
# 2. Latency stats
# ============================================================

print(f"\n{'='*80}")
print("LATENCY STATS (wall clock, seconds)")
print("=" * 80)

for cname in data["composers"]:
    rows = [r for r in data["results"][cname].values() if "wall_ms" in r]
    walls_s = [r["wall_ms"] / 1000 for r in rows]
    if not walls_s:
        continue
    print(f"\n⏱️  {cname}")
    print(f"   wall_total: {sum(walls_s):.1f}s")
    print(f"   per session: mean={mean(walls_s):.1f}s "
          f"p50={percentile(walls_s, 0.5):.1f}s "
          f"p95={percentile(walls_s, 0.95):.1f}s "
          f"max={max(walls_s):.1f}s")


# ============================================================
# 3. Schema failure breakdown by block label
# ============================================================

print(f"\n{'='*80}")
print("SCHEMA FAILURES BY BLOCK LABEL")
print("=" * 80)

for cname in data["composers"]:
    rows = [r for r in data["results"][cname].values() if "llm" in r]
    if not rows:
        continue
    by_label: dict[str, dict] = defaultdict(lambda: {"calls": 0, "fails": 0})
    for r in rows:
        for c in r["llm"].get("calls", []):
            label = c.get("label") or "unknown"
            by_label[label]["calls"] += 1
            if c.get("schema_failure"):
                by_label[label]["fails"] += 1
    if not by_label:
        continue
    print(f"\n🔧 {cname}")
    print(f"   {'label':<32s} {'calls':>6s} {'fails':>6s} {'rate':>6s}")
    print(f"   {'-'*32} {'-'*6} {'-'*6} {'-'*6}")
    for label, b in sorted(by_label.items(), key=lambda x: -x[1]["fails"]):
        rate = b["fails"] / b["calls"] if b["calls"] else 0
        if b["fails"] == 0 and rate == 0:
            continue
        print(f"   {label:<32s} {b['calls']:>6d} {b['fails']:>6d} {rate*100:>5.0f}%")


# ============================================================
# 4. Per-context drill-down
# ============================================================

print(f"\n{'='*80}")
print("PER-CONTEXT DRILL-DOWN")
print("=" * 80)

for cname in data["composers"]:
    print(f"\n🎯 {cname}")
    print(f"   {'cid':<8s} {'phase':<8s} {'wall_s':>7s} "
          f"{'prilepin':>8s} {'inol':>5s} {'equip':>6s} {'fails':>6s}")
    print(f"   {'-'*8} {'-'*8} {'-'*7} {'-'*8} {'-'*5} {'-'*6} {'-'*6}")
    for cid, r in data["results"][cname].items():
        if "l1" not in r:
            print(f"   {cid:<8s} {'?':<8s} {'-':>7s} ERROR: {r.get('error', '?')[:60]}")
            continue
        m = r["l1"]["metrics"]
        ctx = r.get("context", {})
        print(f"   {cid:<8s} {ctx.get('phase', '?'):<8s} "
              f"{r['wall_ms']/1000:>7.1f} "
              f"{m.get('prilepin_compliance', {}).get('score', 0):>8.2f} "
              f"{m.get('inol_per_session', {}).get('score', 0):>5.2f} "
              f"{m.get('equipment_feasibility', {}).get('score', 0):>6.2f} "
              f"{r['llm'].get('schema_failures', 0):>6d}")


# ============================================================
# 5. Worst sessions on chosen metric (debug aid)
# ============================================================

print(f"\n{'='*80}")
print(f"WORST {args.worst} SESSIONS ON `{args.metric}` (debug aid)")
print("=" * 80)

for cname in data["composers"]:
    rows = [
        (cid, r["l1"]["metrics"].get(args.metric, {}).get("score", 0), r)
        for cid, r in data["results"][cname].items()
        if "l1" in r
    ]
    rows.sort(key=lambda x: x[1])
    print(f"\n🔍 {cname}")
    for cid, score, r in rows[: args.worst]:
        ctx = r.get("context", {})
        m_detail = r["l1"]["metrics"].get(args.metric, {})
        print(f"   {cid} ({ctx.get('phase')}) score={score:.2f} "
              f"raw={m_detail.get('raw_value')} passed={m_detail.get('passed')}")
        if r.get("session"):
            blocks = r["session"].get("blocks", [])
            for b in blocks:
                if b.get("type") in ("strength_primary", "strength_secondary",
                                     "metcon", "skill", "gymnastics"):
                    movs = ", ".join(
                        mp.get("movement_id", "?")
                        + (f"@{mp['load']['value']:.0f}{mp['load'].get('type','')[:1]}"
                           if mp.get("load", {}).get("value") else "")
                        for mp in b.get("movements", [])[:4]
                    )
                    print(f"     [{b['order']}] {b['type']}/{b.get('format', '-')}: {movs}")

print(f"\n{'='*80}\nDONE\n{'='*80}")
