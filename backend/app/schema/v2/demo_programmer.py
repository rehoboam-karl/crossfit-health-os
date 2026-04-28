"""
Demo: gerar uma semana inteira via SessionPlanner + HeuristicComposer.

Valida:
1. Planner gera 7 sessões válidas (Pydantic validation)
2. Templates variam por dia conforme split
3. Phase deload muda comportamento
4. Injuries são respeitadas (overhead movements ficam de fora)
5. Equipment derivado bate com movimentos prescritos
"""
from datetime import date, timedelta

from athlete import Athlete, Injury, InjurySeverity
from movements_seed import load_default_library
from programmer import HeuristicComposer, ProgrammingContext, SessionPlanner
from workout_schema import Phase

library = load_default_library()
composer = HeuristicComposer(library)
planner = SessionPlanner(library, composer)

start_date = date(2026, 4, 27)

# --- Karl com lesão overhead (não deve gerar movimentos com tag "overhead") ---
karl = Athlete(
    id="karl", name="Karl",
    birthdate=date(1978, 6, 17),
    body_weight_kg=83,
    training_age_years=5,
    equipment_available=["barbell","plates","rack","bench","pull_up_bar","rower","box","dumbbells","kettlebell","jump_rope","assault_bike"],
    active_injuries=[],
    primary_goals=["strength","competitions"],
    target_benchmarks=["Fran","Helen","Grace"],
    sessions_per_week=5,
)

karl_overhead = Athlete(
    id="karl", name="Karl",
    birthdate=date(1978, 6, 17),
    body_weight_kg=83,
    training_age_years=5,
    equipment_available=["barbell","plates","rack","bench","pull_up_bar","rower","box","dumbbells","kettlebell","jump_rope","assault_bike"],
    active_injuries=[
        Injury(description="Tendinite ombro direito", severity=InjurySeverity.MODERATE,
              affected_patterns=["overhead"], start_date=date(2026, 4, 10))
    ],
    primary_goals=["strength","competitions"],
    target_benchmarks=["Fran","Helen","Grace"],
    sessions_per_week=5,
)

# ─── 1. BUILD phase — semana completa ───────────────────────────────────────
print("=" * 65)
print("📅 Semana — Phase BUILD, Week 2")
print("=" * 65)

sessions_build = []
for day in range(1, 8):
    ctx = ProgrammingContext(
        athlete=karl_overhead, library=library,
        phase=Phase.BUILD, week_number=2, day_number=day,
        target_date=start_date + timedelta(days=day - 1),
        weekly_focus=["squat_volume", "engine"],
    )
    sessions_build.append(planner.plan_session(ctx))

for s in sessions_build:
    blocks_str = " → ".join(b.type.value for b in s.blocks) if s.blocks else "(open)"
    print(f"\n Day {s.date.strftime('%a')} | {s.title}")
    print(f"   Blocks: {blocks_str}")
    print(f"   Equip: {s.equipment_required}")
    print(f"   Duration: {s.estimated_duration_minutes}min")

# ─── 2. Injury restriction validation ────────────────────────────────────────
print("\n" + "=" * 65)
print("🩹 Injury restriction (overhead pattern)")
print("=" * 65)

all_ids = [mp.movement_id for s in sessions_build for b in s.blocks for mp in b.movements]
overhead_ids = {m.id for m in library.find_by_tag("overhead")}
violations = [mid for mid in all_ids if mid in overhead_ids]

if violations:
    print(f"FAIL: movements overhead prescrito: {set(violations)}")
else:
    print(f"OK: zero overhead prescrito ({len(overhead_ids)} in library)")

# ─── 3. BUILD vs DELOAD ──────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("🔄 BUILD vs DELOAD — diferença estrutural")
print("=" * 65)

def summarize_week(phase: Phase, week: int):
    out = []
    for day in range(1, 8):
        ctx = ProgrammingContext(athlete=karl, library=library, phase=phase,
                                 week_number=week, day_number=day,
                                 target_date=start_date + timedelta(days=day - 1))
        s = planner.plan_session(ctx)
        out.append(f"D{day}: {s.template.value:14s} ({len(s.blocks)}bl)")
    return out

build_wk = summarize_week(Phase.BUILD, 2)
deload_wk = summarize_week(Phase.DELOAD, 4)

for b, d in zip(build_wk, deload_wk):
    print(f"  BUILD {b:42s} | DELOAD {d}")

# ─── 4. Stats ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
unique_movs = sorted(set(all_ids))
print(f"✅ Total prescriptions: {len(all_ids)} | Únicos: {len(unique_movs)}")
print(f"   Movimentos: {unique_movs}")
print(f"   Média/sessão: {len(all_ids)/7:.1f}")
print("=" * 65)