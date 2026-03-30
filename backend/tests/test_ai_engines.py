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

class TestAITrainingProgrammerFallback:
    @pytest.fixture
    def programmer(self):
        with patch("app.core.engine.ai_programmer.AsyncOpenAI"):
            from app.core.engine.ai_programmer import AITrainingProgrammer
            p = AITrainingProgrammer()
            p.client = None  # Force fallback mode
            return p

    def test_fallback_returns_dict_for_all_days(self, programmer):
        days = [DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY, DayOfWeek.FRIDAY]
        durations = {DayOfWeek.MONDAY: 90, DayOfWeek.WEDNESDAY: 60, DayOfWeek.FRIDAY: 60}
        result = programmer._generate_fallback_program(days, durations)
        assert DayOfWeek.MONDAY in result
        assert DayOfWeek.WEDNESDAY in result
        assert DayOfWeek.FRIDAY in result

    def test_fallback_skips_sunday(self, programmer):
        """Sunday is not in fallback_workouts, so it's skipped"""
        days = [DayOfWeek.SUNDAY, DayOfWeek.MONDAY]
        durations = {DayOfWeek.SUNDAY: 60, DayOfWeek.MONDAY: 60}
        result = programmer._generate_fallback_program(days, durations)
        assert DayOfWeek.MONDAY in result
        assert DayOfWeek.SUNDAY not in result

    def test_strength_workout_long_session(self, programmer):
        template = programmer._create_strength_workout(90)
        assert template.workout_type == WorkoutType.STRENGTH
        assert len(template.movements) >= 3

    def test_strength_workout_short_session(self, programmer):
        template = programmer._create_strength_workout(45)
        assert template.workout_type == WorkoutType.STRENGTH
        assert len(template.movements) == 2

    def test_metcon_workout(self, programmer):
        template = programmer._create_metcon_workout(60)
        assert template.workout_type == WorkoutType.METCON
        assert len(template.movements) == 6  # Fran: 21-15-9

    def test_skill_workout(self, programmer):
        template = programmer._create_skill_workout(60)
        assert template.workout_type == WorkoutType.SKILL
        assert len(template.movements) > 0

    def test_mixed_workout(self, programmer):
        template = programmer._create_mixed_workout(60)
        assert template.workout_type == WorkoutType.MIXED

    def test_conditioning_workout(self, programmer):
        template = programmer._create_conditioning_workout(60)
        assert template.workout_type == WorkoutType.CONDITIONING

    @pytest.mark.asyncio
    async def test_generate_weekly_program_no_client_uses_fallback(self, programmer):
        user_profile = {"fitness_level": "intermediate", "weight_kg": 80, "preferences": {"goals": ["strength"], "weaknesses": []}}
        days = [DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY]
        durations = {DayOfWeek.MONDAY: 60, DayOfWeek.WEDNESDAY: 60}
        result = await programmer.generate_weekly_program(
            user_profile=user_profile,
            methodology=Methodology.HWPO,
            training_days=days,
            session_durations=durations,
            week_number=1
        )
        assert DayOfWeek.MONDAY in result

    def test_normalize_workout_type_direct_match(self, programmer):
        result = programmer._normalize_workout_type("strength")
        assert result == WorkoutType.STRENGTH

    def test_normalize_workout_type_metcon_keywords(self, programmer):
        result = programmer._normalize_workout_type("AMRAP 12min")
        assert result == WorkoutType.METCON

    def test_normalize_workout_type_strength_with_metcon(self, programmer):
        result = programmer._normalize_workout_type("strength + metcon")
        assert result == WorkoutType.MIXED

    def test_normalize_workout_type_unknown_defaults_mixed(self, programmer):
        result = programmer._normalize_workout_type("totally_unknown")
        assert result == WorkoutType.MIXED

    def test_normalize_skill(self, programmer):
        result = programmer._normalize_workout_type("gymnastics skill work")
        assert result == WorkoutType.SKILL

    def test_normalize_conditioning(self, programmer):
        result = programmer._normalize_workout_type("aerobic conditioning")
        assert result == WorkoutType.CONDITIONING

    def test_build_programming_context(self, programmer):
        user_profile = {
            "fitness_level": "advanced",
            "weight_kg": 85,
            "preferences": {"goals": ["strength"], "weaknesses": ["snatch"]}
        }
        days = [DayOfWeek.MONDAY]
        durations = {DayOfWeek.MONDAY: 90}
        context = programmer._build_programming_context(
            user_profile, Methodology.HWPO, days, durations, 1, ["snatch"], None
        )
        assert context["user"]["fitness_level"] == "advanced"
        assert context["program"]["phase"] == "accumulation"
        assert "snatch" in context["program"]["focus_movements"]

    def test_build_programming_context_phase_deload(self, programmer):
        user_profile = {"fitness_level": "intermediate", "weight_kg": 80, "preferences": {}}
        context = programmer._build_programming_context(
            user_profile, Methodology.CUSTOM, [], {}, 4, None, None
        )
        assert context["program"]["phase"] == "deload"

    def test_build_programming_context_phase_intensification(self, programmer):
        user_profile = {"fitness_level": "intermediate", "weight_kg": 80, "preferences": {}}
        context = programmer._build_programming_context(
            user_profile, Methodology.CUSTOM, [], {}, 6, None, None
        )
        assert context["program"]["phase"] == "intensification"

    def test_build_programming_context_phase_test_week(self, programmer):
        user_profile = {"fitness_level": "intermediate", "weight_kg": 80, "preferences": {}}
        context = programmer._build_programming_context(
            user_profile, Methodology.CUSTOM, [], {}, 8, None, None
        )
        assert context["program"]["phase"] == "test_week"

    def test_system_prompt_contains_methodology_guidance(self, programmer):
        prompt = programmer._get_system_prompt()
        assert "HWPO" in prompt
        assert "Mayhem" in prompt
        assert "CompTrain" in prompt

    def test_parse_ai_response(self, programmer):
        program_json = {
            "workouts": {
                "monday": {
                    "name": "Heavy Squat Day",
                    "workout_type": "strength",
                    "duration_minutes": 90,
                    "description": "Heavy squats",
                    "target_stimulus": "max strength",
                    "parts": [
                        {
                            "part_name": "Strength",
                            "movements": [
                                {"movement": "back_squat", "sets": 5, "reps": 5, "intensity": "80%", "rest": "3min"}
                            ]
                        }
                    ]
                }
            }
        }
        result = programmer._parse_ai_response(program_json, [DayOfWeek.MONDAY])
        assert DayOfWeek.MONDAY in result
        assert result[DayOfWeek.MONDAY].name == "Heavy Squat Day"
        assert len(result[DayOfWeek.MONDAY].movements) == 1


# ─────────────────────────────────────────────
# WeeklyReviewEngine tests
# ─────────────────────────────────────────────

class TestWeeklyReviewEngineFallback:
    @pytest.fixture
    def reviewer(self):
        with patch("app.core.engine.weekly_reviewer.supabase_client"):
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
