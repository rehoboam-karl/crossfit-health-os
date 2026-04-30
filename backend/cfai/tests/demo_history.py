"""
Demo do feedback loop:
1. Planejamento → 7 sessões (programmer)
2. Simulação de execução → SessionResults realistas (compliance imperfeita)
3. Analytics → PRs, compliance, RPE, volume, stimulus, overreaching
4. Atualização de 1RMs no Athlete a partir dos PRs detectados
"""

from datetime import date, datetime, timedelta

from cfai.athlete import Injury, InjurySeverity
from cfai.examples import karl
from cfai.history import TrainingHistory, apply_prs_to_athlete
from cfai.movements_seed import load_default_library
from cfai.programmer import HeuristicComposer, ProgrammingContext, SessionPlanner
from cfai.results import (
    BlockResult, CompletionStatus, MovementResult, build_session_result,
)
from cfai.workout_schema import Phase


# ============================================================
# 1. PLANEJAMENTO — semana de BUILD
# ============================================================

library = load_default_library()
planner = SessionPlanner(library, HeuristicComposer(library))

start = date(2026, 4, 27)
sessions = []
for day in range(1, 8):
    ctx = ProgrammingContext(
        athlete=karl, library=library, phase=Phase.BUILD,
        week_number=2, day_number=day,
        target_date=start + timedelta(days=day - 1),
        weekly_focus=["squat_volume"],
    )
    sessions.append(planner.plan_session(ctx))

sessions_index = {s.id: s for s in sessions}
print(f"📅 Semana planejada: {len(sessions)} sessões")


# ============================================================
# 2. SIMULAÇÃO DE EXECUÇÃO — semana realista
# ============================================================

# Cenário: Karl manda bem nos strength days, falha um Z2, pula um dia
results = []

# D1 Strength Day — completou tudo, hit prescribed loads
sess1 = sessions[0]
strength_block_d1 = next(b for b in sess1.blocks if b.type.value == "strength_primary")
results.append(build_session_result(
    session_id=sess1.id, athlete_id=karl.id,
    executed_at=datetime.combine(sess1.date, datetime.min.time().replace(hour=18)),
    overall_rpe=7.5, sleep_quality_prev_night=7, soreness=3,
    block_results=[
        BlockResult(block_order=1, status=CompletionStatus.COMPLETED, actual_duration_minutes=10),
        BlockResult(block_order=2, status=CompletionStatus.COMPLETED, actual_duration_minutes=5),
        BlockResult(
            block_order=3, status=CompletionStatus.COMPLETED,
            actual_duration_minutes=22, perceived_rpe=7.5,
            actual_score="5x5 @ 75%",
            movement_results=[
                MovementResult(
                    prescribed_movement_id="back_squat", movement_id="back_squat",
                    set_number=i+1, actual_reps=5, actual_load_kg=120.0,
                ) for i in range(5)
            ],
        ),
        BlockResult(block_order=4, status=CompletionStatus.COMPLETED, actual_duration_minutes=12, perceived_rpe=7),
        BlockResult(block_order=5, status=CompletionStatus.COMPLETED, actual_duration_minutes=10,
                    actual_score="6+8 rounds", actual_rounds=6, actual_reps_total=8, perceived_rpe=8),
        BlockResult(block_order=6, status=CompletionStatus.COMPLETED, actual_duration_minutes=5),
    ],
))

# D2 Metcon Only — completou mas RPE alto
sess2 = sessions[1]
results.append(build_session_result(
    session_id=sess2.id, athlete_id=karl.id,
    executed_at=datetime.combine(sess2.date, datetime.min.time().replace(hour=18)),
    overall_rpe=9.0, sleep_quality_prev_night=6, soreness=5,
    block_results=[
        BlockResult(block_order=1, status=CompletionStatus.COMPLETED, actual_duration_minutes=12),
        BlockResult(
            block_order=2, status=CompletionStatus.COMPLETED,
            actual_score="14:32", actual_score_seconds=872,
            perceived_rpe=9.0, actual_duration_minutes=15,
            notes="redlined cedo, last round arrastou",
        ),
        BlockResult(block_order=3, status=CompletionStatus.COMPLETED, actual_duration_minutes=8),
        BlockResult(block_order=4, status=CompletionStatus.COMPLETED, actual_duration_minutes=5),
    ],
))

# D3 Engine Day — pulou Z2, só fez intervals
sess3 = sessions[2]
results.append(build_session_result(
    session_id=sess3.id, athlete_id=karl.id,
    executed_at=datetime.combine(sess3.date, datetime.min.time().replace(hour=6)),
    overall_rpe=7.8, sleep_quality_prev_night=5, soreness=6,
    block_results=[
        BlockResult(block_order=1, status=CompletionStatus.COMPLETED, actual_duration_minutes=12),
        BlockResult(
            block_order=2, status=CompletionStatus.COMPLETED,
            actual_score="5x1000m avg 4:01", actual_duration_minutes=30,
            perceived_rpe=8.0,
        ),
        BlockResult(block_order=3, status=CompletionStatus.SKIPPED,
                    notes="acabou o tempo, pulei o Z2"),
        BlockResult(block_order=4, status=CompletionStatus.COMPLETED, actual_duration_minutes=5),
    ],
    notes="Manhã corrida, cortei Z2",
))

# D4 Strength Day — NEW PR no back squat (162.5kg, anterior 160)
sess4 = sessions[3]
results.append(build_session_result(
    session_id=sess4.id, athlete_id=karl.id,
    executed_at=datetime.combine(sess4.date, datetime.min.time().replace(hour=18)),
    overall_rpe=8.5, sleep_quality_prev_night=8, soreness=4,
    block_results=[
        BlockResult(block_order=1, status=CompletionStatus.COMPLETED, actual_duration_minutes=10),
        BlockResult(block_order=2, status=CompletionStatus.COMPLETED, actual_duration_minutes=5),
        BlockResult(
            block_order=3, status=CompletionStatus.MODIFIED,
            actual_duration_minutes=25, perceived_rpe=9.5,
            actual_score="1RM PR 162.5kg", actual_load_kg=162.5,
            notes="Senti forte, fui no PR — bateu. Antes era 160kg",
            movement_results=[
                MovementResult(
                    prescribed_movement_id="back_squat", movement_id="back_squat",
                    actual_reps=1, actual_load_kg=162.5, perceived_rpe=9.5,
                ),
            ],
        ),
        BlockResult(block_order=4, status=CompletionStatus.COMPLETED, actual_duration_minutes=12, perceived_rpe=7),
        BlockResult(block_order=5, status=CompletionStatus.SKIPPED, notes="cansado pós-PR"),
        BlockResult(block_order=6, status=CompletionStatus.COMPLETED, actual_duration_minutes=5),
    ],
))

# D5 Gymnastic Day — SKIPPED (saiu cedo do trabalho não rolou)
sess5 = sessions[4]
results.append(build_session_result(
    session_id=sess5.id, athlete_id=karl.id,
    executed_at=datetime.combine(sess5.date, datetime.min.time().replace(hour=20)),
    block_results=[],
    notes="Reunião puxou pra noite, não treinei",
))

# D6 Recovery — feito
sess6 = sessions[5]
results.append(build_session_result(
    session_id=sess6.id, athlete_id=karl.id,
    executed_at=datetime.combine(sess6.date, datetime.min.time().replace(hour=10)),
    overall_rpe=3, sleep_quality_prev_night=8, soreness=4,
    block_results=[
        BlockResult(block_order=1, status=CompletionStatus.COMPLETED, actual_duration_minutes=20),
        BlockResult(block_order=2, status=CompletionStatus.COMPLETED, actual_duration_minutes=10),
    ],
))

# D7 Open Gym — não foi
sess7 = sessions[6]
results.append(build_session_result(
    session_id=sess7.id, athlete_id=karl.id,
    executed_at=datetime.combine(sess7.date, datetime.min.time().replace(hour=10)),
    block_results=[],
))


# ============================================================
# 3. ANALYTICS
# ============================================================

# Ref temporal artificial (fim da semana simulada)
ref = datetime.combine(start + timedelta(days=7), datetime.min.time())

history = TrainingHistory(results, sessions_index=sessions_index)

print("\n" + "=" * 65)
print("📊 ADHERENCE & ANALYTICS — semana W2 BUILD")
print("=" * 65)

print(f"\n📈 Status por sessão:")
for r in results:
    sess = sessions_index[r.session_id]
    print(f"  {sess.date} D{sess.date.isoweekday()} | "
          f"{sess.template.value:14s} | "
          f"{r.status.value:10s} | "
          f"RPE {r.overall_rpe or '—'}")

print(f"\n📊 Compliance últimos 7d: "
      f"{history.compliance_rate(karl.id, days_back=7, ref=ref):.0%}")

print(f"\n💪 RPE médio últimos 7d:  "
      f"{history.average_rpe(karl.id, days_back=7, ref=ref):.1f}")

print(f"\n🏋️  Volume por movimento (kg × reps):")
volume = history.volume_per_movement(karl.id, days_back=7, ref=ref)
for mid, v in volume.items():
    print(f"  {mid:20s} {v:>8,.0f} kg")

print(f"\n⏱  Minutos por stimulus:")
stim = history.stimulus_minutes(karl.id, days_back=7, ref=ref)
for s, m in stim.items():
    print(f"  {s.value:25s} {m:>4}min")

print(f"\n⚠️  Overreaching signals:")
signals = history.overreaching_signals(karl.id, ref=ref)
if signals:
    for sig in signals:
        print(f"  - {sig}")
else:
    print("  (nenhum)")


# ============================================================
# 4. APLICAR PRs DETECTADOS
# ============================================================

prs = history.detect_prs(karl, ref=ref)

print("\n" + "=" * 65)
print("🏆 PRs DETECTADOS")
print("=" * 65)
if prs:
    for pr in prs:
        prev = f"{pr.previous_value_kg}kg" if pr.previous_value_kg else "—"
        print(f"  {pr.movement_id:20s} {pr.value_kg}kg "
              f"(anterior: {prev}) em {pr.achieved_at.date()}")
else:
    print("  Nenhum PR nesta janela")

karl_updated = apply_prs_to_athlete(karl, prs)

print("\n📝 Atleta atualizado:")
for mid in sorted(karl.one_rep_maxes.keys()):
    old = karl.get_1rm(mid)
    new = karl_updated.get_1rm(mid)
    arrow = " ✨" if new > old else ""
    print(f"  {mid:15s} {old:>6.1f}kg → {new:>6.1f}kg{arrow}")


# ============================================================
# 5. NEXT WEEK COM CONTEXTO HISTÓRICO
# ============================================================

print("\n" + "=" * 65)
print("🔄 Próxima semana — context com recent_results disponível")
print("=" * 65)

next_week_ctx = ProgrammingContext(
    athlete=karl_updated,
    library=library,
    phase=Phase.BUILD,
    week_number=3,
    day_number=1,
    target_date=start + timedelta(days=7),
    weekly_focus=["squat_volume"],
    recent_sessions=sessions,  # passa as planejadas + ClaudeComposer recebe results
)

next_strength = planner.plan_session(next_week_ctx)
print(f"\n  W3D1 planejada: {next_strength.title}")
strength_block = next(b for b in next_strength.blocks if b.type.value == "strength_primary")
first_set = strength_block.movements[0]
new_pct = first_set.load.value
new_kg = karl_updated.resolve_load(first_set.load)
print(f"  Strength primary: {first_set.load.reference_lift} @ {new_pct}% = {new_kg:.1f}kg")
print(f"  (1RM atualizado de 160 → 162.5kg, % aplicado em cima do novo)")
