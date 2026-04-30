"""
Smoke test multi-provider — Sprint 2.

Gera 1 session com HeuristicComposer e roda 5 LLM providers como judges
sobre a dimensão STIMULUS_COHERENCE. Reporta scores, reasoning, custos.

Skipa providers sem API key — não falha o teste, só registra "skipped".

Uso:
    cd backend/cfai
    ../venv/bin/python tests/smoke_judges.py
"""
import json
import os
from datetime import date

# Carrega .env se existir (pra pegar as keys sem precisar export)
try:
    from dotenv import load_dotenv
    load_dotenv("../.env")
except ImportError:
    pass  # python-dotenv não é obrigatório

from cfai.examples import karl
from cfai.movements_seed import load_default_library
from cfai.programmer import HeuristicComposer, ProgrammingContext, SessionPlanner
from cfai.workout_schema import Phase

from cfai.cost_tracker import cost_tracker
from cfai.evaluation_judge import (
    JudgeDimension, LLMProviderJudge, RUBRIC,
)
from cfai.llm_providers import (
    AnthropicProvider, OpenAIProvider, DeepSeekProvider,
    GroqProvider, MinimaxProvider, PROVIDER_CLASSES,
)


# ============================================================
# 1. Gera 1 session de exemplo
# ============================================================

print("=" * 70)
print("SMOKE TEST — multi-provider LLM judges")
print("=" * 70)

library = load_default_library()
planner = SessionPlanner(library, HeuristicComposer(library))
ctx = ProgrammingContext(
    athlete=karl, library=library, phase=Phase.BUILD,
    week_number=2, day_number=1,
    target_date=date(2026, 4, 27),
    weekly_focus=["squat_volume"],
)
session = planner.plan_session(ctx)
print(f"\n📋 Session gerada: {session.id}")
print(f"   Template: {session.template.value}, blocos: {len(session.blocks)}")
print(f"   Equipment: {sorted(session.equipment_required)}")


# ============================================================
# 2. Inicializa providers (skipa os sem key)
# ============================================================

print(f"\n🔌 Inicializando providers...")
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
# 3. Roda STIMULUS_COHERENCE em todos
# ============================================================

dimension = JudgeDimension.STIMULUS_COHERENCE
context = {
    "athlete_id": karl.id, "phase": ctx.phase.value,
    "week": ctx.week_number, "day": ctx.day_number,
    "weekly_focus": ctx.weekly_focus,
}

print(f"\n🎯 Avaliando dimensão: {dimension.value}")
print(f"   Rubrica:")
for s, desc in RUBRIC[dimension].items():
    print(f"     {s}: {desc[:80]}{'...' if len(desc) > 80 else ''}")

print(f"\n📊 Scores por provider:")
print(f"   {'Provider':<12s} {'Model':<28s} {'Score':>5s}  {'Latency':>9s}  {'Cost':>9s}")
print(f"   {'-'*12} {'-'*28} {'-'*5}  {'-'*9}  {'-'*9}")

results = {}
for name, provider in providers.items():
    judge = LLMProviderJudge(provider)
    try:
        score = judge.score_pointwise(session, dimension, context)
        # pega o último record do cost_tracker pra esse provider
        last_call = next(
            (r for r in reversed(cost_tracker.records) if r.provider == provider.family),
            None,
        )
        lat = f"{last_call.latency_ms}ms" if last_call else "—"
        cost = f"${last_call.cost_usd:.5f}" if last_call else "—"
        print(f"   {name:<12s} {provider.model[:28]:<28s} {score.score:>5d}  {lat:>9s}  {cost:>9s}")
        results[name] = {
            "model": provider.model,
            "score": score.score,
            "reasoning": score.reasoning,
            "judge_model": score.judge_model,
            "latency_ms": last_call.latency_ms if last_call else None,
            "cost_usd": last_call.cost_usd if last_call else None,
            "schema_failure": last_call.schema_failure if last_call else None,
        }
    except Exception as e:
        print(f"   {name:<12s} {provider.model[:28]:<28s}  ERR  — {type(e).__name__}: {str(e)[:60]}")
        results[name] = {"error": f"{type(e).__name__}: {e}"}


# ============================================================
# 4. Reasoning side-by-side
# ============================================================

print(f"\n💬 Reasoning por provider (truncado a 220 chars):")
for name, r in results.items():
    if "error" in r:
        print(f"\n   ❌ {name}: {r['error']}")
        continue
    print(f"\n   • {name} (score={r['score']}/5):")
    print(f"     {r['reasoning'][:220]}{'...' if len(r['reasoning']) > 220 else ''}")


# ============================================================
# 5. Cost tracker report
# ============================================================

print(f"\n💰 Cost summary:")
report = cost_tracker.report()
print(f"   Total calls: {report['n_calls']}")
print(f"   Total cost:  ${report['total_cost_usd']:.5f}")
print(f"   Total in/out tokens: {report['total_in_tokens']} / {report['total_out_tokens']}")
print(f"\n   Per provider:")
for prov, b in report["by_provider"].items():
    print(f"     {prov:12s} calls={b['n_calls']} cost=${b['cost_usd']:.5f} "
          f"avg_latency={b['latency_ms_avg']}ms "
          f"schema_fail={b['schema_failure_rate']*100:.0f}%")


# ============================================================
# 6. JSON export
# ============================================================

export = {
    "session_id": session.id,
    "athlete": karl.id,
    "phase": ctx.phase.value,
    "dimension": dimension.value,
    "results": results,
    "cost_report": report,
}
out_path = "smoke_judges_results.json"
with open(out_path, "w") as f:
    json.dump(export, f, indent=2, default=str)
print(f"\n💾 JSON saved → {out_path}")

print(f"\n{'='*70}\nDONE\n{'='*70}")
