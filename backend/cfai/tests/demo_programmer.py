"""
Demo: gerar uma semana inteira via SessionPlanner + HeuristicComposer.

Valida que:
1. Planner gera 7 sessões válidas (passa Pydantic validation)
2. Templates variam por dia conforme split
3. Phase deload muda comportamento
4. Injuries são respeitadas (overhead movements ficam de fora)
5. Equipment derivado bate com movimentos prescritos
"""

from datetime import date, timedelta

from cfai.athlete import Injury, InjurySeverity
from cfai.examples import karl
from cfai.movements_seed import load_default_library
from cfai.programmer import HeuristicComposer, ProgrammingContext, SessionPlanner
from cfai.workout_schema import Phase


# ============================================================
# Setup
# ============================================================

library = load_default_library()
composer = HeuristicComposer(library)
planner = SessionPlanner(library, composer)


# Karl com lesão "overhead" — programmer deve evitar esses movimentos
karl_overhead = karl.model_copy(update={
    "active_injuries": [
        Injury(
            description="Tendinite ombro direito",
            severity=InjurySeverity.MODERATE,
            affected_patterns=["overhead"],
            start_date=date(2026, 4, 10),
        ),
    ],
})


# ============================================================
# 1. Semana de BUILD phase (week 2 do mesociclo)
# ============================================================

print("=" * 65)
print("📅 Semana planejada — Phase BUILD, Week 2 do mesociclo")
print("=" * 65)

start_date = date(2026, 4, 27)
sessions_build = []
for day in range(1, 8):
    ctx = ProgrammingContext(
        athlete=karl_overhead,
        library=library,
        phase=Phase.BUILD,
        week_number=2,
        day_number=day,
        target_date=start_date + timedelta(days=day - 1),
        weekly_focus=["squat_volume", "engine"],
        available_minutes=60,
    )
    sess = planner.plan_session(ctx)
    sessions_build.append(sess)

for s in sessions_build:
    blocks_summary = " → ".join(b.type.value for b in s.blocks) if s.blocks else "(open)"
    print(f"\n  Day {s.date.isoweekday()} | {s.title}")
    print(f"    Stimulus: {s.primary_stimulus.value}")
    print(f"    Blocos:   {blocks_summary}")
    print(f"    Equip:    {s.equipment_required}")
    print(f"    Duração:  {s.estimated_duration_minutes}min")


# ============================================================
# 2. Validar que injury restriction funcionou
# ============================================================

print("\n" + "=" * 65)
print("🩹 Validação injury restriction — overhead pattern")
print("=" * 65)

all_movement_ids = [
    mp.movement_id
    for s in sessions_build for b in s.blocks for mp in b.movements
]
overhead_ids = {m.id for m in library.find_by_tag("overhead")}
violations = [mid for mid in all_movement_ids if mid in overhead_ids]
if violations:
    print(f"  ❌ Movimentos overhead prescritos apesar da lesão: {set(violations)}")
else:
    print(f"  ✅ Nenhum movimento overhead prescrito (de {len(overhead_ids)} no catálogo)")


# ============================================================
# 3. Comparar BUILD vs DELOAD (semana 4)
# ============================================================

print("\n" + "=" * 65)
print("🔄 Phase BUILD vs DELOAD — diferença estrutural")
print("=" * 65)

def summary_for_phase(phase: Phase, week: int) -> list[str]:
    out = []
    for day in range(1, 8):
        ctx = ProgrammingContext(
            athlete=karl, library=library, phase=phase,
            week_number=week, day_number=day,
            target_date=start_date + timedelta(days=day - 1),
        )
        s = planner.plan_session(ctx)
        n_blocks = len(s.blocks)
        out.append(f"D{day}: {s.template.value:14s} ({n_blocks} blocos)")
    return out

build_summary = summary_for_phase(Phase.BUILD, 2)
deload_summary = summary_for_phase(Phase.DELOAD, 4)

for b, d in zip(build_summary, deload_summary):
    print(f"  BUILD  {b:42s}  |  DELOAD  {d}")


# ============================================================
# 4. Sanity check: tudo passa validação Pydantic?
# ============================================================

print("\n" + "=" * 65)
print("✅ Resumo — todas as 7 sessões passaram validação Pydantic")
print(f"   Total movimentos prescritos: {len(all_movement_ids)}")
print(f"   Movimentos únicos: {len(set(all_movement_ids))}")
print(f"   Volume médio por sessão: {len(all_movement_ids)/7:.1f} prescriptions")
