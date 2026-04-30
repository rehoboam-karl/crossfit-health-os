"""
Multi-judge calibration — Sprint 5d.

Pergunta: o ranking de composers de Sprint 5c é consenso ou só opinião do
gpt-4o (judge default)? Para responder:

1. Gera sessões UMA vez por (composer × context). Mesmas sessões pra todos os
   judges → controla variância de session.
2. Para cada session, scoreia com CADA judge disponível em CADA dimension.
3. Calcula:
   - Per-judge composer ranking (mean L2 across contexts)
   - Spearman ρ entre rankings dos judges (par-a-par)
   - Per-dimension agreement: std das scores entre judges (alta std = ponto
     onde judges discordam)

Cost-conservative por design: rebenta sessões 1x (não regen por judge);
cheap providers (groq/deepseek/minimax) judge cost é ~10-100x menor que openai.

Uso:
    cd backend/cfai
    ../venv/bin/python tests/multi_judge.py                      # 3 contexts
    ../venv/bin/python tests/multi_judge.py --max-contexts 5     # mais robusto
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
from cfai.evaluation_judge import JudgeDimension, LLMProviderJudge
from cfai.examples import karl
from cfai.llm_providers import PROVIDER_CLASSES
from cfai.movements_seed import load_default_library
from cfai.programmer import HeuristicComposer, ProgrammingContext, SessionPlanner
from cfai.workout_schema import Phase


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "test_contexts.json"


# ============================================================
# CLI
# ============================================================

parser = argparse.ArgumentParser()
parser.add_argument("--max-contexts", "--max", type=int, default=3,
                    help="contexts a rodar (default 3 — cheap)")
parser.add_argument("--out", default="multi_judge_results.json")
parser.add_argument("--no-confirm", action="store_true")
args = parser.parse_args()


# ============================================================
# 1. Spearman ρ helper (no scipy dep)
# ============================================================

def spearman_rho(x: list[float], y: list[float]) -> float:
    """Spearman rank correlation. Para n pequeno (5 composers) sem ties:
    ρ = 1 - 6·Σd² / (n·(n²-1))
    Para ties, usa fórmula geral via Pearson nos ranks."""
    if len(x) != len(y) or len(x) < 2:
        return 0.0
    n = len(x)

    def ranks(vals: list[float]) -> list[float]:
        # Average rank for ties
        sorted_idx = sorted(range(n), key=lambda i: vals[i])
        rank = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[sorted_idx[j + 1]] == vals[sorted_idx[i]]:
                j += 1
            avg_rank = (i + j) / 2 + 1
            for k in range(i, j + 1):
                rank[sorted_idx[k]] = avg_rank
            i = j + 1
        return rank

    rx, ry = ranks(x), ranks(y)
    mx, my = mean(rx), mean(ry)
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    denom_x = sum((rx[i] - mx) ** 2 for i in range(n)) ** 0.5
    denom_y = sum((ry[i] - my) ** 2 for i in range(n)) ** 0.5
    if denom_x == 0 or denom_y == 0:
        return 0.0
    return num / (denom_x * denom_y)


# ============================================================
# 2. Load fixture
# ============================================================

print("=" * 80)
print("MULTI-JUDGE CALIBRATION (Sprint 5d)")
print("=" * 80)

with open(FIXTURE_PATH) as f:
    fixture = json.load(f)

contexts_raw = fixture["contexts"][: args.max_contexts]
print(f"\n📋 Contexts: {len(contexts_raw)} de {len(fixture['contexts'])}")


# ============================================================
# 3. Init providers (used as both composers + judges)
# ============================================================

print("\n🔌 Inicializando providers...")
providers = {}
for name, cls in PROVIDER_CLASSES.items():
    try:
        providers[name] = cls()
        print(f"   ✅ {name:10s} → {providers[name].name}")
    except (ValueError, ImportError) as e:
        print(f"   ⚪ {name:10s} skipped — {e}")

if len(providers) < 2:
    print(f"\n❌ Multi-judge precisa ≥2 providers. Apenas {list(providers)}.")
    raise SystemExit(1)

judges = {name: LLMProviderJudge(p, max_retries=2) for name, p in providers.items()}


# ============================================================
# 4. Composers
# ============================================================

library = load_default_library()
composers: dict[str, object] = {"heuristic": HeuristicComposer(library)}
for name, provider in providers.items():
    composers[f"llm_{name}"] = LLMComposer(
        provider=provider, library=library, max_retries=2,
    )


# ============================================================
# 5. Cost estimate
# ============================================================

# Cost = compose(N×n_composers) + judge(N×n_composers×n_judges×n_dims)
# Approx: openai dominates judging cost
n_judge_calls = len(contexts_raw) * len(composers) * len(judges) * len(JudgeDimension)
n_compose_calls = len(contexts_raw) * (len(composers) - 1) * 3  # avg blocks/session
est_cost_openai_pct = 0.5  # if openai is among judges
est_cost = (
    n_judge_calls * 0.005  # mixed avg per judge call
    + n_compose_calls * 0.003
)
print(f"\n💵 Estimated cost: ~${est_cost:.2f}")
print(f"   (composes={n_compose_calls}, judge calls={n_judge_calls})")
if not args.no_confirm and est_cost > 1.0:
    if input("   Continuar? [y/N] ").strip().lower() != "y":
        raise SystemExit(0)


# ============================================================
# 6. Generate sessions ONCE (caching)
# ============================================================

def build_ctx(raw):
    return ProgrammingContext(
        athlete=karl, library=library, phase=Phase(raw["phase"]),
        week_number=raw["week_number"], day_number=raw["day_number"],
        target_date=date(2026, 4, 27) + timedelta(days=raw["day_number"]),
        weekly_focus=raw["weekly_focus"],
    )


print("\n🎼 Gerando sessões (1x cada, cacheadas para todos judges)...")
sessions: dict[str, dict[str, object]] = {c: {} for c in composers}
generation_failures: list[tuple[str, str, str]] = []

for raw in contexts_raw:
    cid = raw["id"]
    ctx = build_ctx(raw)
    print(f"\n   {cid}: {raw['phase']}/W{raw['week_number']}/D{raw['day_number']} focus={raw['weekly_focus']}")
    for cname, composer in composers.items():
        planner = SessionPlanner(library, composer)
        try:
            sess = planner.plan_session(ctx)
            sessions[cname][cid] = sess
            print(f"      ✅ {cname:18s} blocks={len(sess.blocks)}")
        except Exception as e:
            generation_failures.append((cname, cid, str(e)))
            print(f"      ❌ {cname:18s} {type(e).__name__}: {e}")


# ============================================================
# 7. Each judge scores ALL sessions
# ============================================================

dims = list(JudgeDimension)

# scores[judge][composer][cid][dim] = int score
scores: dict[str, dict[str, dict[str, dict[str, int]]]] = {
    j: {c: {} for c in composers} for j in judges
}

print(f"\n⚖️  Multi-judge scoring ({len(judges)} judges × {len(composers)} composers × {len(contexts_raw)} contexts × {len(dims)} dims)...")
total_pairs = sum(1 for c in composers for cid in [r["id"] for r in contexts_raw] if cid in sessions[c])

pair_idx = 0
for cname in composers:
    for raw in contexts_raw:
        cid = raw["id"]
        if cid not in sessions[cname]:
            continue
        sess = sessions[cname][cid]
        ctx = build_ctx(raw)
        judge_context = {
            "athlete_id": karl.id, "phase": ctx.phase.value,
            "week": ctx.week_number, "day": ctx.day_number,
            "weekly_focus": ctx.weekly_focus,
        }
        pair_idx += 1
        print(f"\n   [{pair_idx}/{total_pairs}] {cname:18s} {cid}")

        for jname, judge in judges.items():
            scores[jname][cname][cid] = {}
            judge_scores: list[int] = []
            for dim in dims:
                try:
                    score = judge.score_pointwise(sess, dim, judge_context)
                    scores[jname][cname][cid][dim.value] = score.score
                    judge_scores.append(score.score)
                except Exception as e:
                    scores[jname][cname][cid][dim.value] = 0
                    judge_scores.append(0)
            avg = round(mean(judge_scores), 2) if judge_scores else 0.0
            print(f"      judge={jname:10s} L2_mean={avg}")


# ============================================================
# 8. Aggregations
# ============================================================

print(f"\n{'='*80}\nAGGREGATIONS\n{'='*80}")

# 8a. Per-judge composer ranking (mean L2 across all contexts × dimensions)
print(f"\n📊 Composer ranking PER JUDGE (mean L2 across {len(contexts_raw)} contexts × 6 dims):")
hdr = f"   {'composer':<18s} " + " ".join(f"judge={j[:8]:<10s}" for j in judges)
print(hdr)
print(f"   {'-'*18} " + " ".join("-"*16 for _ in judges))

# composer_means[judge][composer] = float
composer_means: dict[str, dict[str, float]] = {j: {} for j in judges}
for cname in composers:
    cells = []
    for jname in judges:
        all_scores = []
        for cid in scores[jname][cname]:
            for d in dims:
                v = scores[jname][cname][cid].get(d.value, 0)
                if v > 0:
                    all_scores.append(v)
        m = round(mean(all_scores), 2) if all_scores else 0.0
        composer_means[jname][cname] = m
        cells.append(f"{m:<16.2f}")
    print(f"   {cname:<18s} {''.join(cells)}")


# 8b. Per-judge ranking order
print(f"\n🏅 Ranking ORDER per judge (best → worst by L2 mean):")
judge_orderings: dict[str, list[str]] = {}
for jname in judges:
    ordered = sorted(composer_means[jname].items(), key=lambda x: -x[1])
    judge_orderings[jname] = [c for c, _ in ordered]
    chain = " > ".join(f"{c.replace('llm_','')}({v})" for c, v in ordered)
    print(f"   {jname:10s} → {chain}")


# 8c. Spearman ρ between judges (composer rankings)
print(f"\n📐 Spearman ρ entre judges (rankings de composer agreement):")
print(f"   ρ ≥ 0.7  → ranking robusto (judges concordam)")
print(f"   ρ < 0.5  → ranking não-confiável (judges discordam)")
print()
judge_list = list(judges)
hdr = f"   {'':<10s} " + " ".join(f"{j:<10s}" for j in judge_list)
print(hdr)
print(f"   {'-'*10} " + " ".join("-"*10 for _ in judge_list))
rho_matrix: dict[str, dict[str, float]] = {}
for ja in judge_list:
    rho_matrix[ja] = {}
    cells = []
    for jb in judge_list:
        if ja == jb:
            cells.append(f"{'1.00':<10s}")
            rho_matrix[ja][jb] = 1.0
            continue
        # Vectors aligned by composer
        x = [composer_means[ja][c] for c in composers]
        y = [composer_means[jb][c] for c in composers]
        rho = round(spearman_rho(x, y), 2)
        rho_matrix[ja][jb] = rho
        cells.append(f"{rho:<10.2f}")
    print(f"   {ja:<10s} {''.join(cells)}")

# 8d. Mean ρ (excluding diagonal) — overall agreement signal
off_diag = []
for ja in judge_list:
    for jb in judge_list:
        if ja != jb:
            off_diag.append(rho_matrix[ja][jb])
mean_rho = round(mean(off_diag), 3) if off_diag else 0.0
print(f"\n   Mean off-diagonal ρ: {mean_rho:.3f}  ", end="")
if mean_rho >= 0.7:
    print("✅ judges concordam — ranking robusto")
elif mean_rho >= 0.5:
    print("⚠️  agreement moderado — ranking sugestivo mas não conclusivo")
else:
    print("❌ judges discordam — ranking não-confiável, calibração necessária")


# 8e. Per-dimension agreement std
print(f"\n📏 Per-dimension judge disagreement (std of scores across judges, mean across composers/contexts):")
print(f"   alta std = judges discordam nessa dimension")
print()
for d in dims:
    stds = []
    for cname in composers:
        for raw in contexts_raw:
            cid = raw["id"]
            if cid not in sessions[cname]:
                continue
            judge_scores = [scores[j][cname][cid].get(d.value, 0) for j in judges]
            judge_scores = [s for s in judge_scores if s > 0]
            if len(judge_scores) >= 2:
                stds.append(stdev(judge_scores))
    avg_std = round(mean(stds), 2) if stds else 0.0
    print(f"   {d.value:<28s} mean_std = {avg_std}")


# ============================================================
# 9. Cost
# ============================================================

print(f"\n💰 Cost summary:")
report = cost_tracker.report()
print(f"   Total calls: {report['n_calls']}")
print(f"   Total cost:  ${report['total_cost_usd']:.4f}")
for prov, b in report["by_provider"].items():
    print(f"     {prov:12s} calls={b['n_calls']:<3d} cost=${b['cost_usd']:.4f} "
          f"avg_lat={b['latency_ms_avg']}ms schema_fail={b['schema_failure_rate']*100:.0f}%")


# ============================================================
# 10. Export
# ============================================================

export = {
    "fixture_version": fixture["version"],
    "n_contexts": len(contexts_raw),
    "judges": list(judges),
    "composers": list(composers),
    "scores": scores,
    "aggregations": {
        "composer_means_per_judge": composer_means,
        "judge_orderings": judge_orderings,
        "spearman_rho_matrix": rho_matrix,
        "mean_off_diagonal_rho": mean_rho,
    },
    "cost_report": report,
    "generation_failures": generation_failures,
}
with open(args.out, "w") as f:
    json.dump(export, f, indent=2, default=str)
print(f"\n💾 JSON saved → {args.out}")

print(f"\n{'='*80}\nDONE\n{'='*80}")
