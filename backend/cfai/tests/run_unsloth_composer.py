"""
Local composer harness (Ollama) — captura para análise offline.

Roda LLMComposer parametrizado por OllamaProvider sobre N contextos do
fixture tests/fixtures/test_contexts.json. Para cada (context):
  - Gera sessão com Ollama + (opcional) heuristic baseline
  - Avalia L1 (Prilepin, INOL, equipment, injury, library coverage etc.)
  - Captura latency, schema_failures, raw session dict
  - Salva tudo em JSON pra análise posterior

Sem custo monetário (modelo local). Latência domina — qwen3.6:35b-a3b-MoE
em GPU consumer ~3-15s por bloco; sessão completa = 30-120s.

Pré-requisitos:
  - Ollama rodando: `ollama serve`
  - Modelo puxado:  `ollama pull qwen3.6:35b-a3b-coding-mxfp8`

Uso:
    cd backend/cfai
    ../venv/bin/python tests/run_unsloth_composer.py                  # 5 contexts smoke
    ../venv/bin/python tests/run_unsloth_composer.py --max 20         # full
    ../venv/bin/python tests/run_unsloth_composer.py --no-baseline    # só ollama
    OLLAMA_MODEL=llama3.1:8b ../venv/bin/python tests/run_unsloth_composer.py
    OLLAMA_BASE_URL=http://gpu-box:11434/v1 ../venv/bin/python tests/run_unsloth_composer.py
"""
from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict
from datetime import date, datetime, timedelta
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
from cfai.examples import karl
from cfai.llm_providers import OllamaProvider
from cfai.movements_seed import load_default_library
from cfai.programmer import HeuristicComposer, ProgrammingContext, SessionPlanner
from cfai.workout_schema import Phase


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "test_contexts.json"


# ============================================================
# CLI
# ============================================================

parser = argparse.ArgumentParser()
parser.add_argument("--max-contexts", "--max", type=int, default=5,
                    help="contexts a rodar (default 5)")
parser.add_argument("--no-baseline", action="store_true",
                    help="pula HeuristicComposer (default: incluído)")
parser.add_argument("--out", default="run_unsloth_results.json",
                    help="output JSON path")
parser.add_argument("--include-raw-sessions", action="store_true", default=True,
                    help="inclui sessions full no JSON (default: True)")
parser.add_argument("--max-retries", type=int, default=3,
                    help="retries por bloco se schema_failure (default 3)")
args = parser.parse_args()


# ============================================================
# 1. Init
# ============================================================

print("=" * 80)
print("LOCAL COMPOSER HARNESS (Ollama)")
print("=" * 80)
print(f"started: {datetime.now().isoformat(timespec='seconds')}")
print(f"base_url: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434/v1')}")
print(f"model:    {os.getenv('OLLAMA_MODEL', 'qwen3.6:35b-a3b-coding-mxfp8')}")
print()

try:
    provider = OllamaProvider()
except ValueError as e:
    print(f"❌ Ollama indisponível: {e}")
    print("   → rode `ollama serve` e tente novamente.")
    raise SystemExit(1)
print(f"✅ Provider: {provider.name}")

# Smoke probe: 1 call pra verificar endpoint + path (chat/completions)
print(f"\n🔬 Smoke probe (1 call)...")
try:
    probe = provider.complete(
        system="You output JSON only.",
        user='Say {"ok": true}.',
        json_mode=True, temperature=0.0, max_tokens=64,
        label="smoke_probe",
    )
    if probe["schema_failure"]:
        print(f"   ⚠️  endpoint OK mas json_mode falhou — content: {probe['content'][:120]!r}")
    else:
        print(f"   ✅ {probe['latency_ms']}ms | parsed={probe['parsed']} "
              f"| in/out tokens={probe['input_tokens']}/{probe['output_tokens']}")
except Exception as e:
    print(f"   ❌ smoke probe FAIL: {type(e).__name__}: {e}")
    print(f"   → endpoint atingível mas /chat/completions não responde.")
    print(f"     Verifica path no Unsloth Studio (talvez seja /v1/ ou outro).")
    raise SystemExit(1)


# ============================================================
# 2. Load fixture
# ============================================================

with open(FIXTURE_PATH) as f:
    fixture = json.load(f)
contexts_raw = fixture["contexts"][: args.max_contexts]
print(f"\n📋 Contexts: {len(contexts_raw)} de {len(fixture['contexts'])}")


# ============================================================
# 3. Composers
# ============================================================

library = load_default_library()
composers: dict[str, object] = {}
if not args.no_baseline:
    composers["heuristic"] = HeuristicComposer(library)
composers["ollama"] = LLMComposer(
    provider=provider, library=library, max_retries=args.max_retries,
)
print(f"🎼 Composers: {list(composers)}")


# ============================================================
# 4. Build planner per composer + run
# ============================================================

START_DATE = date(2026, 5, 4)
results: dict[str, dict] = {c: {} for c in composers}

print(f"\n📐 Gerando sessions ({len(contexts_raw)} contexts × {len(composers)} composers)...")

for c_idx, ctx_raw in enumerate(contexts_raw, 1):
    cid = ctx_raw["id"]
    print(f"\n[{c_idx}/{len(contexts_raw)}] {cid} | "
          f"phase={ctx_raw['phase']} W{ctx_raw['week_number']}D{ctx_raw['day_number']} "
          f"focus={ctx_raw['weekly_focus']}")

    pctx = ProgrammingContext(
        athlete=karl, library=library,
        phase=Phase(ctx_raw["phase"]),
        week_number=ctx_raw["week_number"],
        day_number=ctx_raw["day_number"],
        target_date=START_DATE + timedelta(days=c_idx),
        weekly_focus=ctx_raw["weekly_focus"],
    )

    for cname, composer in composers.items():
        # Track LLM call deltas via cost_tracker
        n_calls_before = len(cost_tracker.records)
        latency_ms_before = sum(r.latency_ms for r in cost_tracker.records)
        schema_fails_before = sum(
            1 for r in cost_tracker.records if r.schema_failure
        )
        t_wall = time.monotonic()

        planner = SessionPlanner(library=library, composer=composer)
        try:
            session = planner.plan_session(pctx)
            wall_ms = int((time.monotonic() - t_wall) * 1000)
            err = None
        except Exception as e:
            wall_ms = int((time.monotonic() - t_wall) * 1000)
            session = None
            err = f"{type(e).__name__}: {e}"
            print(f"   ❌ {cname:10s} GEN FAIL ({wall_ms}ms) — {err}")
            results[cname][cid] = {
                "context": ctx_raw, "error": err, "wall_ms": wall_ms,
            }
            continue

        # Per-call deltas
        new_records = cost_tracker.records[n_calls_before:]
        n_calls = len(new_records)
        llm_latency = sum(r.latency_ms for r in new_records)
        schema_fails = sum(1 for r in new_records if r.schema_failure)

        # L1 evaluate — evaluate_session retorna list[MetricResult]
        try:
            metric_results = evaluate_session(session, karl, library)
            metrics_by_name = {m.name: m.__dict__ for m in metric_results}
            # Category summary local (summary_score só funciona para mesocycle dict)
            by_cat: dict[str, list[float]] = {}
            for m in metric_results:
                cat_key = str(m.category).split(".")[-1].lower()
                by_cat.setdefault(cat_key, []).append(m.score)
            cat_summary = {
                cat: round(sum(scores) / len(scores), 3)
                for cat, scores in by_cat.items()
            }
        except Exception as e:
            cat_summary = {}
            metrics_by_name = {}
            print(f"   ⚠️  {cname:10s} L1 FAIL — {type(e).__name__}: {e}")

        results[cname][cid] = {
            "context": ctx_raw,
            "wall_ms": wall_ms,
            "llm": {
                "n_calls": n_calls,
                "latency_ms_total": llm_latency,
                "schema_failures": schema_fails,
                "calls": [
                    {
                        "label": r.label,
                        "in_tokens": r.in_tokens, "out_tokens": r.out_tokens,
                        "latency_ms": r.latency_ms,
                        "schema_failure": r.schema_failure,
                    }
                    for r in new_records
                ],
            },
            "l1": {
                "category_summary": cat_summary,
                "metrics": {
                    n: {
                        "score": m["score"],
                        "raw_value": m.get("raw_value"),
                        "passed": m.get("passed"),
                    }
                    for n, m in metrics_by_name.items()
                },
            },
            "session": (
                json.loads(session.model_dump_json())
                if args.include_raw_sessions and session
                else None
            ),
        }
        # Detecta fallback silencioso: composer LLM mas n_calls=0 = todas
        # tentativas raised antes de cost_tracker.record (endpoint quebrado).
        is_llm = cname != "heuristic"
        fallback_warn = ""
        if is_llm and n_calls == 0:
            fallback_warn = " ⚠️ FALLBACK (0 LLM calls — provider raising silently)"

        marker = "✅" if metrics_by_name else "⚠️"
        print(f"   {marker} {cname:10s} wall={wall_ms/1000:.1f}s "
              f"llm_calls={n_calls} llm_lat={llm_latency/1000:.1f}s "
              f"schema_fails={schema_fails} "
              f"prilepin={metrics_by_name.get('prilepin_compliance', {}).get('score', 0):.2f} "
              f"inol={metrics_by_name.get('inol_per_session', {}).get('score', 0):.2f} "
              f"equip={metrics_by_name.get('equipment_feasibility', {}).get('score', 0):.2f}"
              f"{fallback_warn}")


# ============================================================
# 5. Aggregations
# ============================================================

print(f"\n{'='*80}\nAGGREGATIONS\n{'='*80}")

key_metrics = ["prilepin_compliance", "inol_per_session",
               "equipment_feasibility", "injury_safety",
               "movement_library_coverage"]
short_names = ["prilepin", "inol", "equip", "injury", "lib"]

print(f"\n📊 L1 mean ± std per composer:")
hdr = f"   {'composer':<12s} " + " ".join(f"{n:<14s}" for n in short_names) + " " + f"{'wall_s':<10s} {'fail_rate':<10s}"
print(hdr)
print(f"   {'-'*12} " + " ".join("-"*14 for _ in short_names) + f" {'-'*10} {'-'*10}")

agg = {}
for cname in composers:
    rows = [r for r in results[cname].values() if "l1" in r]
    if not rows:
        continue
    cells = []
    composer_agg = {}
    for m in key_metrics:
        vals = [
            r["l1"]["metrics"].get(m, {}).get("score", 0)
            for r in rows
        ]
        if not vals:
            cells.append(f"{'N/A':<14s}")
            composer_agg[m] = None
            continue
        mu = round(mean(vals), 2)
        sd = round(stdev(vals), 2) if len(vals) > 1 else 0.0
        composer_agg[m] = {"mean": mu, "std": sd, "values": vals}
        cells.append(f"{mu:.2f}±{sd:.2f}    "[:14].ljust(14))
    walls = [r["wall_ms"] for r in rows]
    schema_total = sum(
        r.get("llm", {}).get("schema_failures", 0) for r in rows
    )
    n_calls_total = sum(
        r.get("llm", {}).get("n_calls", 0) for r in rows
    )
    fail_rate = (schema_total / n_calls_total) if n_calls_total else 0.0
    composer_agg["wall_s_mean"] = round(mean(walls) / 1000, 1) if walls else 0
    composer_agg["schema_failure_rate"] = round(fail_rate, 3)
    agg[cname] = composer_agg
    print(f"   {cname:<12s} {' '.join(cells)} "
          f"{composer_agg['wall_s_mean']:<10.1f} "
          f"{fail_rate*100:<9.1f}%")


# ============================================================
# 6. Cost / latency
# ============================================================

print(f"\n💰 Provider report:")
report = cost_tracker.report()
print(f"   Total calls: {report['n_calls']}")
print(f"   Total cost:  ${report['total_cost_usd']:.4f}  (Ollama=local, $0)")
for prov, b in report["by_provider"].items():
    print(f"     {prov:10s} calls={b['n_calls']:<3d} "
          f"avg_lat={b['latency_ms_avg']}ms "
          f"schema_fail={b['schema_failure_rate']*100:.0f}%")


# ============================================================
# 7. Export
# ============================================================

export = {
    "started_at": datetime.now().isoformat(timespec="seconds"),
    "fixture_version": fixture["version"],
    "provider": {
        "family": provider.family,
        "model": provider.model,
        "name": provider.name,
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    },
    "args": {
        "max_contexts": args.max_contexts,
        "no_baseline": args.no_baseline,
        "max_retries": args.max_retries,
    },
    "contexts": [c["id"] for c in contexts_raw],
    "composers": list(composers),
    "results": results,
    "aggregations": agg,
    "cost_report": report,
}
with open(args.out, "w") as f:
    json.dump(export, f, indent=2, default=str)
print(f"\n💾 JSON saved → {args.out}")
print(f"   ({Path(args.out).stat().st_size // 1024} KB)")

print(f"\n{'='*80}\nDONE\n{'='*80}")
