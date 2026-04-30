"""
Validação end-to-end do schema.

Cria:
1. Atleta com 1RMs e benchmarks
2. PercentTable de Back Squat (4 semanas, wave loading)
3. Sessão HWPO-style: Strength Day completo
4. Sessão Mayhem-style: Engine Day
5. Mesocycle de 4 semanas
6. Demonstra resolução de cargas (% → kg absoluto)
"""

from datetime import date

from .workout_schema import (
    BlockFormat, BlockType, LoadSpec, Mesocycle, MovementPrescription,
    Phase, ScalingTier, Session, SessionTemplate, Stimulus, Week, WorkoutBlock,
)
from .athlete import Athlete, BenchmarkResult, Injury, InjurySeverity, OneRepMax
from .percent_table import PercentTable, SetPrescription, WeekScheme


# ============================================================
# 1. ATLETA
# ============================================================

karl = Athlete(
    id="ath_001",
    name="Karl",
    birthdate=date(1978, 6, 15),
    body_weight_kg=85.0,
    height_cm=178.0,
    training_age_years=8.0,
    one_rep_maxes={
        "back_squat": OneRepMax(
            movement_id="back_squat", value_kg=160.0, tested_date=date(2026, 3, 1)
        ),
        "deadlift": OneRepMax(
            movement_id="deadlift", value_kg=190.0, tested_date=date(2026, 3, 1)
        ),
        "snatch": OneRepMax(
            movement_id="snatch", value_kg=85.0, tested_date=date(2026, 2, 15)
        ),
        "clean_jerk": OneRepMax(
            movement_id="clean_jerk", value_kg=110.0, tested_date=date(2026, 2, 15)
        ),
        "strict_press": OneRepMax(
            movement_id="strict_press", value_kg=65.0, tested_date=date(2026, 1, 20),
            confidence="stale",
        ),
    },
    benchmarks={
        "fran": BenchmarkResult(
            benchmark_id="fran", value=240.0, unit="seconds",
            tested_date=date(2026, 2, 10),
        ),
        "5k_row": BenchmarkResult(
            benchmark_id="5k_row", value=1185.0, unit="seconds",
            tested_date=date(2026, 3, 10),
        ),
    },
    equipment_available=[
        "barbell", "plates", "rack", "rower", "assault_bike",
        "dumbbells", "kettlebells", "rings", "pull_up_bar",
    ],
    active_injuries=[
        Injury(
            description="Tendinite leve no ombro direito",
            severity=InjurySeverity.MINOR,
            affected_patterns=["overhead_high_volume"],
            start_date=date(2026, 4, 10),
        ),
    ],
    default_scaling=ScalingTier.RX,
    primary_goals=["aerobic_capacity", "snatch_technique"],
    target_benchmarks=["fran", "5k_row", "helen"],
    sessions_per_week=5,
)


# ============================================================
# 2. PERCENT TABLE — Back Squat 4-week wave
# ============================================================

bs_wave = PercentTable(
    id="pt_bs_wave_4w",
    name="Back Squat Wave — 4 weeks",
    description="Wave loading 5/3/1+, deload na semana 4",
    pattern="wave",
    duration_weeks=4,
    target_movement_id="back_squat",
    weeks=[
        WeekScheme(
            week_number=1,
            sets=[
                SetPrescription(set_number=1, reps=5, intensity=LoadSpec(
                    type="percent_1rm", value=70, reference_lift="back_squat"
                ), rest_seconds=180),
                SetPrescription(set_number=2, reps=5, intensity=LoadSpec(
                    type="percent_1rm", value=75, reference_lift="back_squat"
                ), rest_seconds=180),
                SetPrescription(set_number=3, reps=5, intensity=LoadSpec(
                    type="percent_1rm", value=80, reference_lift="back_squat"
                ), rest_seconds=180, notes="AMRAP no último set"),
            ],
        ),
        WeekScheme(
            week_number=2,
            sets=[
                SetPrescription(set_number=1, reps=3, intensity=LoadSpec(
                    type="percent_1rm", value=75, reference_lift="back_squat"
                ), rest_seconds=180),
                SetPrescription(set_number=2, reps=3, intensity=LoadSpec(
                    type="percent_1rm", value=82.5, reference_lift="back_squat"
                ), rest_seconds=180),
                SetPrescription(set_number=3, reps=3, intensity=LoadSpec(
                    type="percent_1rm", value=87.5, reference_lift="back_squat"
                ), rest_seconds=180, notes="AMRAP no último set"),
            ],
        ),
        WeekScheme(
            week_number=3,
            sets=[
                SetPrescription(set_number=1, reps=5, intensity=LoadSpec(
                    type="percent_1rm", value=80, reference_lift="back_squat"
                ), rest_seconds=180),
                SetPrescription(set_number=2, reps=3, intensity=LoadSpec(
                    type="percent_1rm", value=87.5, reference_lift="back_squat"
                ), rest_seconds=180),
                SetPrescription(set_number=3, reps=1, intensity=LoadSpec(
                    type="percent_1rm", value=92.5, reference_lift="back_squat"
                ), rest_seconds=180, notes="AMRAP no último set"),
            ],
        ),
        WeekScheme(
            week_number=4,
            is_deload=True,
            sets=[
                SetPrescription(set_number=1, reps=5, intensity=LoadSpec(
                    type="percent_1rm", value=50, reference_lift="back_squat"
                ), rest_seconds=120),
                SetPrescription(set_number=2, reps=5, intensity=LoadSpec(
                    type="percent_1rm", value=60, reference_lift="back_squat"
                ), rest_seconds=120),
                SetPrescription(set_number=3, reps=5, intensity=LoadSpec(
                    type="percent_1rm", value=65, reference_lift="back_squat"
                ), rest_seconds=120),
            ],
            notes="Deload — recuperação ativa, foco em técnica",
        ),
    ],
)


# ============================================================
# 3. SESSÃO HWPO STRENGTH DAY (semana 1 do bs_wave aplicada)
# ============================================================

strength_day = Session(
    id="sess_001",
    date=date(2026, 4, 27),
    template=SessionTemplate.STRENGTH_DAY,
    title="Squat Wave W1 + EMOM Conditioning",
    primary_stimulus=Stimulus.STRENGTH_VOLUME,
    estimated_duration_minutes=75,
    equipment_required=["barbell", "rack", "rower", "dumbbells"],
    blocks=[
        WorkoutBlock(
            order=1,
            type=BlockType.WARM_UP,
            duration_minutes=10,
            intent="Elevar temperatura, ROM de quadril e tornozelo",
            movements=[
                MovementPrescription(movement_id="row", calories=15, pacing="easy"),
                MovementPrescription(movement_id="world_greatest_stretch", reps=10),
                MovementPrescription(movement_id="cossack_squat", reps=10),
            ],
        ),
        WorkoutBlock(
            order=2,
            type=BlockType.ACTIVATION,
            duration_minutes=5,
            intent="Ativação glúteos + core para padrão de squat",
            format=BlockFormat.NOT_FOR_TIME,
            movements=[
                MovementPrescription(
                    movement_id="banded_glute_bridge", reps=15,
                    load=LoadSpec(type="bodyweight"),
                ),
                MovementPrescription(
                    movement_id="dead_bug", reps=10,
                    load=LoadSpec(type="bodyweight"),
                ),
            ],
        ),
        # Strength primary aplicado da PercentTable
        WorkoutBlock(
            order=3,
            type=BlockType.STRENGTH_PRIMARY,
            format=BlockFormat.SETS_REPS,
            stimulus=Stimulus.STRENGTH_VOLUME,
            duration_minutes=20,
            intent="Construir volume sub-máximo, qualidade de bar path",
            target_score="último set 5+ reps @ 80%",
            movements=bs_wave.apply_to_movement("back_squat", week_number=1),
        ),
        WorkoutBlock(
            order=4,
            type=BlockType.STRENGTH_SECONDARY,
            format=BlockFormat.SETS_REPS,
            stimulus=Stimulus.HYPERTROPHY,
            duration_minutes=12,
            intent="Hipertrofia posterior, complemento ao squat",
            movements=[
                MovementPrescription(
                    movement_id="romanian_deadlift", reps=8,
                    load=LoadSpec(type="rpe", value=7),
                    tempo="31X1",
                    notes="4 sets, 90s rest entre",
                ),
            ],
            rounds=4,
            rest_seconds=90,
        ),
        WorkoutBlock(
            order=5,
            type=BlockType.METCON,
            format=BlockFormat.AMRAP,
            stimulus=Stimulus.MIXED_MODAL,
            duration_minutes=10,
            intent="Conditioning leve pós-strength, manter mecânica sob fadiga",
            target_score="5+ rounds",
            intensity_rpe=7.5,
            movements=[
                MovementPrescription(
                    movement_id="db_snatch_alt", reps=10,
                    load=LoadSpec(type="absolute_kg", value=22.5),
                ),
                MovementPrescription(movement_id="run", distance_meters=200),
                MovementPrescription(
                    movement_id="wall_ball", reps=15,
                    load=LoadSpec(type="absolute_kg", value=9.0),
                ),
            ],
        ),
        WorkoutBlock(
            order=6,
            type=BlockType.COOLDOWN,
            duration_minutes=5,
            intent="Down-regulation, mobilidade quadril",
            movements=[
                MovementPrescription(
                    movement_id="couch_stretch", time_seconds=120,
                    notes="60s cada perna",
                ),
                MovementPrescription(
                    movement_id="box_breathing", time_seconds=180,
                    notes="4-4-4-4",
                ),
            ],
        ),
    ],
)


# ============================================================
# 4. SESSÃO MAYHEM ENGINE DAY
# ============================================================

engine_day = Session(
    id="sess_002",
    date=date(2026, 4, 28),
    template=SessionTemplate.ENGINE_DAY,
    title="Threshold Intervals + Z2 Bike",
    primary_stimulus=Stimulus.AEROBIC_THRESHOLD,
    estimated_duration_minutes=70,
    equipment_required=["rower", "assault_bike"],
    blocks=[
        WorkoutBlock(
            order=1,
            type=BlockType.WARM_UP,
            duration_minutes=12,
            intent="Progressivo até zona de trabalho",
            movements=[
                MovementPrescription(
                    movement_id="bike", time_seconds=480, pacing="conversacional",
                    notes="2min easy → 2min mod → 2min easy → 2min @ pace alvo",
                ),
            ],
        ),
        WorkoutBlock(
            order=2,
            type=BlockType.ENGINE,
            format=BlockFormat.INTERVALS,
            stimulus=Stimulus.AEROBIC_THRESHOLD,
            duration_minutes=30,
            rounds=5,
            work_seconds=240,
            rest_seconds=120,
            target_pace="2:00/500m",
            intent="Threshold sustentável, respiração nasal sempre que possível",
            intensity_rpe=8.0,
            movements=[
                MovementPrescription(
                    movement_id="row", distance_meters=1000,
                    pacing="2:00/500m split",
                ),
            ],
        ),
        WorkoutBlock(
            order=3,
            type=BlockType.AEROBIC_Z2,
            format=BlockFormat.STEADY,
            stimulus=Stimulus.AEROBIC_Z2,
            duration_minutes=20,
            intent="Recuperação ativa em Z2, base aeróbica",
            target_pace="HR 130-145bpm, nasal breathing",
            movements=[
                MovementPrescription(
                    movement_id="bike", time_seconds=1200, pacing="zone 2",
                ),
            ],
        ),
        WorkoutBlock(
            order=4,
            type=BlockType.COOLDOWN,
            duration_minutes=5,
            movements=[
                MovementPrescription(
                    movement_id="box_breathing", time_seconds=300,
                ),
            ],
        ),
    ],
)


# ============================================================
# 5. RESOLUÇÃO DE CARGAS (% → kg)
# ============================================================

def demo_resolution():
    print("=" * 60)
    print(f"Atleta: {karl.name} | BS 1RM: {karl.get_1rm('back_squat')}kg")
    print("=" * 60)
    print(f"\n📋 Strength Day — Squat Wave W1:")
    strength_block = strength_day.blocks[2]
    for i, mov in enumerate(strength_block.movements, 1):
        kg = karl.resolve_load(mov.load) if mov.load else None
        pct = mov.load.value if mov.load else "?"
        print(f"  Set {i}: {mov.reps} reps @ {pct}% = {kg:.1f}kg")

    print(f"\n📋 Engine Day — Row Intervals:")
    engine_block = engine_day.blocks[1]
    print(f"  {engine_block.rounds}x{engine_block.work_seconds}s "
          f"work / {engine_block.rest_seconds}s rest")
    print(f"  Target: {engine_block.target_pace}")

    print(f"\n✅ Sessões validadas:")
    print(f"  - {strength_day.title} ({len(strength_day.blocks)} blocos)")
    print(f"  - {engine_day.title} ({len(engine_day.blocks)} blocos)")


# ============================================================
# 6. MESOCYCLE 4 SEMANAS (estrutural — sessões reais omitidas)
# ============================================================

# Stub: copia strength_day e engine_day variando datas para preencher
def make_week(week_num: int, start: date) -> Week:
    from copy import deepcopy
    sessions = []
    for i in range(5):  # 5 sessões/semana
        s = deepcopy(strength_day if i % 2 == 0 else engine_day)
        s.id = f"sess_w{week_num}_d{i+1}"
        s.date = date.fromordinal(start.toordinal() + (week_num - 1) * 7 + i)
        sessions.append(s)
    return Week(week_number=week_num, theme=f"Week {week_num}", sessions=sessions,
                deload=(week_num == 4))


meso_q2_base = Mesocycle(
    id="meso_q2_base_2026",
    name="Q2 Base — Strength Volume + Aerobic",
    phase=Phase.BASE,
    start_date=date(2026, 4, 27),
    duration_weeks=4,
    primary_focus=["squat_volume", "aerobic_threshold"],
    target_benchmarks=["5k_row", "fran"],
    weeks=[make_week(i, date(2026, 4, 27)) for i in range(1, 5)],
)


if __name__ == "__main__":
    demo_resolution()
    print(f"\n🗓  Mesocycle: {meso_q2_base.name}")
    print(f"   Phase: {meso_q2_base.phase} | "
          f"{meso_q2_base.duration_weeks} semanas | "
          f"{sum(len(w.sessions) for w in meso_q2_base.weeks)} sessões total")
