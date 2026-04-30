"""Regressão: cobertura dos casos-limite que motivaram os 8 patches do Sprint 1.

Roda com:  pytest tests/test_evaluation.py -v
(de dentro de backend/cfai/, com o pacote instalado via `pip install -e .`)

Cada teste cobre um patch específico:
- TestPrilepinZone        → Patch 1 (PRILEPIN_TABLE 100% edge)
- TestFosterMonotonyRestDays → Patch 2 (Foster padding com rest days)
- TestPrilepinReps        → Patch 4 (mp.reps não-int não crasha)
- TestSummaryScoreGating  → Patch 3 (validity hard gate)
"""
from types import SimpleNamespace

from cfai.evaluation import (
    PRILEPIN_TABLE, _prilepin_zone,
    metric_foster_monotony, metric_prilepin_compliance,
    summary_score, MetricCategory,
)
from cfai.workout_schema import BlockType


# ============================================================
# Helpers
# ============================================================

def _session(duration=60, blocks=None):
    return SimpleNamespace(
        id="test", estimated_duration_minutes=duration,
        blocks=blocks or [], equipment_required=set(),
    )


def _week(sessions, week_number=1, deload=False):
    return SimpleNamespace(
        sessions=sessions, week_number=week_number, deload=deload,
    )


def _strength_block(movement_id, load_pct, reps,
                    block_type=BlockType.STRENGTH_PRIMARY):
    return SimpleNamespace(
        order=1,
        type=block_type,
        duration_minutes=20,
        movements=[SimpleNamespace(
            movement_id=movement_id,
            load=SimpleNamespace(type="percent_1rm", value=load_pct),
            reps=reps,
        )],
    )


# ============================================================
# Patch 1 — Prilepin 100% edge
# ============================================================

class TestPrilepinZone:
    def test_100_pct_maps_to_top_zone(self):
        """Pré-patch: 100% caía em None (range era [90, 100))."""
        zone = _prilepin_zone(100.0)
        assert zone is not None, "100% deve mapear pra zona 90+"
        assert zone == (2, 7, 4, 10)

    def test_zone_boundaries(self):
        assert _prilepin_zone(70.0)[0] == 6   # 70-80 zone
        assert _prilepin_zone(79.99)[0] == 6
        assert _prilepin_zone(80.0)[0] == 4   # 80-90 zone
        assert _prilepin_zone(90.0)[0] == 2   # 90+ zone


# ============================================================
# Patch 2 — Foster monotony com rest days
# ============================================================

class TestFosterMonotonyRestDays:
    def test_5_session_week_with_rest_days(self):
        """Pré-patch: 5 sessões iguais → SD=0 → monotony=inf → score=0.
        Pós-patch: rest days padded como 0 → variabilidade real captura."""
        sessions = [_session(duration=60) for _ in range(5)]
        week = _week(sessions)

        result = metric_foster_monotony(week)
        # daily_loads = [60,60,60,60,60,0,0]
        # mean = 300/7 ≈ 42.86; sd ≈ 29.79; monotony ≈ 1.44
        assert result.raw_value is not None
        assert 1.3 < result.raw_value < 1.6
        assert result.passed is True

    def test_perfect_monotony_7_identical_sessions(self):
        """7 sessões diárias iguais é monotony catastrófica (sem rest)."""
        sessions = [_session(duration=60) for _ in range(7)]
        week = _week(sessions)
        result = metric_foster_monotony(week)
        # Todos dias = 60min → SD=0 → monotony inf
        assert result.passed is False
        assert result.score == 0.0


# ============================================================
# Patch 4 — Prilepin/INOL não-int safety
# ============================================================

class TestPrilepinReps:
    def test_amrap_doesnt_crash(self):
        """Pré-patch: mp.reps='AMRAP' causava TypeError em zones[zone]+=str."""
        block = _strength_block(
            movement_id="thruster", load_pct=80, reps="AMRAP",
        )
        session = _session(blocks=[block])
        result = metric_prilepin_compliance(session)
        assert result.score == 1.0  # skip silencioso, bloco "no_pct_load"


# ============================================================
# Patch 3 — summary_score validity hard gate
# ============================================================

class TestSummaryScoreGating:
    def test_validity_failure_zeros_category(self):
        """Validity é hard gate — uma falha → 0.0 (não média)."""
        results = {
            "session_metrics": [{
                "metrics": [
                    {"category": "validity", "score": 1.0},
                    {"category": "validity", "score": 0.0},  # ← injury
                    {"category": "validity", "score": 1.0},
                ],
            }],
            "week_metrics": [],
            "mesocycle_metrics": [],
        }
        s = summary_score(results)
        assert s["validity"] == 0.0   # NÃO 0.667

    def test_non_gate_categories_use_mean(self):
        results = {
            "session_metrics": [{
                "metrics": [
                    {"category": "volume_intensity", "score": 0.8},
                    {"category": "volume_intensity", "score": 0.6},
                ],
            }],
            "week_metrics": [],
            "mesocycle_metrics": [],
        }
        s = summary_score(results)
        assert s["volume_intensity"] == 0.7

    def test_validity_all_pass_returns_1(self):
        results = {
            "session_metrics": [{
                "metrics": [
                    {"category": "validity", "score": 1.0},
                    {"category": "validity", "score": 1.0},
                ],
            }],
            "week_metrics": [],
            "mesocycle_metrics": [],
        }
        s = summary_score(results)
        assert s["validity"] == 1.0
