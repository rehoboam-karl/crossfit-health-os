"""Examples — Karl profile for demo/validation"""
from datetime import date
from athlete import Athlete, OneRepMax, Injury, InjurySeverity
from workout_schema import ScalingTier

karl = Athlete(
    id="karl",
    name="Karl",
    birthdate=date(1978, 6, 17),
    body_weight_kg=83,
    height_cm=178,
    training_age_years=5.0,
    one_rep_maxes={
        "back_squat": OneRepMax(movement_id="back_squat", value_kg=160, tested_date=date(2026, 4, 1)),
        "deadlift": OneRepMax(movement_id="deadlift", value_kg=200, tested_date=date(2026, 4, 1)),
        "clean_jerk": OneRepMax(movement_id="clean_jerk", value_kg=120, tested_date=date(2026, 4, 1)),
    },
    benchmarks={},
    equipment_available=[
        "barbell", "plates", "rack", "bench",
        "pull_up_bar", "rower", "box", "dumbbells",
        "kettlebell", "jump_rope", "assault_bike",
    ],
    active_injuries=[],
    default_scaling=ScalingTier.RX,
    primary_goals=["strength", "competitions"],
    target_benchmarks=["Fran", "Helen", "Grace"],
    sessions_per_week=5,
)