"""
Tests for app/core/engine/ai_programmer.py and app/core/engine/weekly_reviewer.py
Covers fallback methods and pure logic (no real AI calls needed)
"""
import pytest
from datetime import date, timedelta
from uuid import UUID, uuid4
from unittest.mock import MagicMock, AsyncMock, patch

from app.models.training import DayOfWeek, Methodology, WorkoutType
from app.models.review import (
    RecoveryStatus, VolumeAssessment, IntensityChange, NextWeekAdjustments
)


# ─────────────────────────────────────────────
# AITrainingProgrammer tests
# ─────────────────────────────────────────────

class TestAITrainingProgrammer:
    """Tests for the microcycle-based AI programmer (post-periodization)."""

    @pytest.fixture
    def programmer(self):
        with patch("app.core.engine.ai_programmer.AsyncOpenAI"):
            from app.core.engine.ai_programmer import AITrainingProgrammer
            p = AITrainingProgrammer()
            p.client = None  # Force fallback mode
            return p

    def test_normalize_workout_type_direct_match(self, programmer):
        assert programmer._normalize_workout_type("strength") == WorkoutType.STRENGTH

    def test_normalize_workout_type_metcon_keywords(self, programmer):
        assert programmer._normalize_workout_type("AMRAP 12min") == WorkoutType.METCON

    def test_normalize_workout_type_strength_with_metcon(self, programmer):
        assert programmer._normalize_workout_type("strength + metcon") == WorkoutType.MIXED

    def test_normalize_workout_type_unknown_defaults_mixed(self, programmer):
        assert programmer._normalize_workout_type("totally_unknown") == WorkoutType.MIXED

    def test_normalize_skill(self, programmer):
        assert programmer._normalize_workout_type("gymnastics skill work") == WorkoutType.SKILL

    def test_normalize_conditioning(self, programmer):
        assert programmer._normalize_workout_type("aerobic conditioning") == WorkoutType.CONDITIONING

    def test_system_prompt_contains_methodology_guidance(self, programmer):
        prompt = programmer._get_system_prompt()
        assert "HWPO" in prompt
        assert "Mayhem" in prompt
        assert "CompTrain" in prompt

    def test_system_prompt_contains_block_types(self, programmer):
        """The new system prompt should describe all periodization block types."""
        prompt = programmer._get_system_prompt()
        assert "ACCUMULATION" in prompt
        assert "INTENSIFICATION" in prompt
        assert "REALIZATION" in prompt
        assert "DELOAD" in prompt
        assert "TEST" in prompt

    def test_fallback_template_matches_workout_type(self, programmer):
        from types import SimpleNamespace
        from datetime import date as _date

        strength_ps = SimpleNamespace(workout_type="strength", duration_minutes=60, date=_date(2026, 4, 20))
        tpl_strength = programmer._fallback_template_for_session(strength_ps)
        assert tpl_strength.workout_type == WorkoutType.STRENGTH
        assert tpl_strength.duration_minutes == 60

        metcon_ps = SimpleNamespace(workout_type="metcon", duration_minutes=45, date=_date(2026, 4, 21))
        tpl_metcon = programmer._fallback_template_for_session(metcon_ps)
        assert tpl_metcon.workout_type == WorkoutType.METCON

    def test_parse_single_workout(self, programmer):
        from types import SimpleNamespace
        from datetime import date as _date
        workout_data = {
            "session_id": "abc",
            "name": "Heavy Squat Day",
            "workout_type": "strength",
            "duration_minutes": 90,
            "description": "Heavy squats",
            "target_stimulus": "max strength",
            "movements": [
                {"movement": "back_squat", "sets": 5, "reps": 5, "intensity": "80%", "rest": "3min"}
            ],
        }
        session_row = SimpleNamespace(date=_date(2026, 4, 20), workout_type="strength", duration_minutes=90)
        tpl = programmer._parse_single_workout(workout_data, session_row, Methodology.HWPO)
        assert tpl.name == "Heavy Squat Day"
        assert tpl.workout_type == WorkoutType.STRENGTH
        assert len(tpl.movements) == 1
        assert tpl.methodology == Methodology.HWPO


# ─────────────────────────────────────────────
# WeeklyReviewEngine tests
# ─────────────────────────────────────────────

class TestWeeklyReviewEngineFallback:
    @pytest.fixture
    def reviewer(self):
        # Weekly reviewer no longer holds a Supabase client — it takes a Session per call.
        with patch("app.core.engine.weekly_reviewer.AsyncAnthropic"):
            from app.core.engine.weekly_reviewer import WeeklyReviewEngine
            r = WeeklyReviewEngine()
            r.anthropic_client = None
            r.openai_client = None
            return r

    def _make_weekly_data(
        self,
        planned=5,
        completed=5,
        avg_rpe=7.0,
        avg_readiness=75.0
    ):
        return {
            "sessions": [{"id": str(uuid4())}] * planned,
            "recovery_metrics": [],
            "feedback": [],
            "planned_sessions": planned,
            "completed_sessions": completed,
            "adherence_rate": (completed / planned * 100) if planned else 0,
            "avg_rpe": avg_rpe,
            "avg_readiness": avg_readiness,
        }

    def test_fallback_excellent_adherence(self, reviewer):
        data = self._make_weekly_data(5, 5)  # 100% adherence
        result = reviewer._generate_review_fallback(data, 1)
        assert "excellent" in result["summary"].lower() or "100" in result["summary"]

    def test_fallback_good_adherence(self, reviewer):
        data = self._make_weekly_data(5, 4)  # 80% adherence
        result = reviewer._generate_review_fallback(data, 1)
        assert "good" in result["summary"].lower() or "80" in result["summary"]

    def test_fallback_low_adherence(self, reviewer):
        data = self._make_weekly_data(5, 2)  # 40% adherence
        result = reviewer._generate_review_fallback(data, 1)
        assert "low" in result["summary"].lower() or "40" in result["summary"]

    def test_fallback_high_rpe_volume_too_high(self, reviewer):
        data = self._make_weekly_data(avg_rpe=9.0)
        result = reviewer._generate_review_fallback(data, 1)
        assert result["volume_assessment"] == VolumeAssessment.TOO_HIGH

    def test_fallback_low_rpe_volume_too_low(self, reviewer):
        data = self._make_weekly_data(avg_rpe=5.0)
        result = reviewer._generate_review_fallback(data, 1)
        assert result["volume_assessment"] == VolumeAssessment.TOO_LOW

    def test_fallback_moderate_rpe_appropriate(self, reviewer):
        data = self._make_weekly_data(avg_rpe=7.0)
        result = reviewer._generate_review_fallback(data, 1)
        assert result["volume_assessment"] == VolumeAssessment.APPROPRIATE

    def test_fallback_low_readiness_compromised(self, reviewer):
        data = self._make_weekly_data(avg_readiness=50.0)
        result = reviewer._generate_review_fallback(data, 1)
        assert result["recovery_status"] == RecoveryStatus.COMPROMISED

    def test_fallback_mid_readiness_adequate(self, reviewer):
        data = self._make_weekly_data(avg_readiness=70.0)
        result = reviewer._generate_review_fallback(data, 1)
        assert result["recovery_status"] == RecoveryStatus.ADEQUATE

    def test_fallback_high_readiness_optimal(self, reviewer):
        data = self._make_weekly_data(avg_readiness=80.0)
        result = reviewer._generate_review_fallback(data, 1)
        assert result["recovery_status"] == RecoveryStatus.OPTIMAL

    def test_fallback_coach_message_includes_week_number(self, reviewer):
        data = self._make_weekly_data()
        result = reviewer._generate_review_fallback(data, 3)
        assert "3" in result["coach_message"]

    def test_fallback_returns_expected_keys(self, reviewer):
        data = self._make_weekly_data()
        result = reviewer._generate_review_fallback(data, 1)
        for key in ["summary", "planned_sessions", "completed_sessions", "adherence_rate",
                    "avg_rpe", "avg_readiness", "strengths", "weaknesses",
                    "recovery_status", "volume_assessment", "next_week_adjustments",
                    "coach_message"]:
            assert key in result

    def test_fallback_adjustments_have_ai_note(self, reviewer):
        data = self._make_weekly_data()
        result = reviewer._generate_review_fallback(data, 1)
        adj = result["next_week_adjustments"]
        assert isinstance(adj, NextWeekAdjustments)
        assert "ai" in (adj.special_notes or "").lower()

    def test_get_coach_system_prompt(self, reviewer):
        prompt = reviewer._get_coach_system_prompt()
        assert "coach" in prompt.lower() or "crossfit" in prompt.lower()
        assert len(prompt) > 100

    def test_build_review_prompt_accumulation(self, reviewer):
        profile = {"name": "Test", "fitness_level": "intermediate", "preferences": {"goals": [], "weaknesses": []}}
        data = self._make_weekly_data()
        prompt = reviewer._build_review_prompt(profile, data, 2, None)
        assert "Accumulation" in prompt
        assert "Test" in prompt

    def test_build_review_prompt_deload(self, reviewer):
        profile = {"name": "Athlete", "fitness_level": "rx", "preferences": {}}
        data = self._make_weekly_data()
        prompt = reviewer._build_review_prompt(profile, data, 4, None)
        assert "Deload" in prompt

    def test_build_review_prompt_intensification(self, reviewer):
        profile = {"name": "Athlete", "fitness_level": "rx", "preferences": {}}
        data = self._make_weekly_data()
        prompt = reviewer._build_review_prompt(profile, data, 6, "Feeling strong")
        assert "Intensification" in prompt
        assert "Feeling strong" in prompt

    def test_build_review_prompt_test_week(self, reviewer):
        profile = {"name": "Athlete", "fitness_level": "rx", "preferences": {}}
        data = self._make_weekly_data()
        prompt = reviewer._build_review_prompt(profile, data, 8, None)
        assert "Test Week" in prompt

    def test_parse_review_response(self, reviewer):
        data = self._make_weekly_data()
        review_data = {
            "summary": "Good week overall.",
            "strengths": [{"movement": "back_squat", "improvement": "PR hit", "confidence": "high"}],
            "weaknesses": [{"movement": "snatch", "issue": "technique", "suggested_focus": "skill work"}],
            "recovery_status": "optimal",
            "volume_assessment": "appropriate",
            "progressions_detected": ["Back squat +5kg"],
            "next_week_adjustments": {
                "volume_change_pct": 5,
                "intensity_change": "increase",
                "focus_movements": ["snatch"],
                "special_notes": "Push intensity",
                "add_skill_work_minutes": 15,
                "add_mobility_work": True
            },
            "coach_message": "Great work this week!"
        }
        result = reviewer._parse_review_response(review_data, data)
        assert result["summary"] == "Good week overall."
        assert result["recovery_status"] == RecoveryStatus.OPTIMAL
        assert result["volume_assessment"] == VolumeAssessment.APPROPRIATE
        assert len(result["strengths"]) == 1
        assert result["next_week_adjustments"].volume_change_pct == 5
        assert result["coach_message"] == "Great work this week!"

    def test_parse_review_response_defaults(self, reviewer):
        data = self._make_weekly_data()
        result = reviewer._parse_review_response({}, data)
        assert "summary" in result
        assert result["coach_message"] == "Keep up the great work!"
