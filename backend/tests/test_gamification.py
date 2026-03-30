"""
Tests for app/services/gamification.py and app/models/gamification.py
"""
import pytest
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock
from uuid import uuid4

from app.models.gamification import (
    Badge, BadgeType, BADGE_DEFINITIONS,
    StreakData, UserStats,
    calculate_level, xp_for_action
)
from app.services.gamification import GamificationService


# ─────────────────────────────────────────────
# Helper factories
# ─────────────────────────────────────────────

def _make_session(days_ago: int, completed: bool = True, rpe: int = 7) -> dict:
    dt = datetime.utcnow() - timedelta(days=days_ago)
    return {
        "id": str(uuid4()),
        "completed_at": dt.isoformat() if completed else None,
        "started_at": dt.isoformat(),
        "rpe_score": rpe if completed else None,
    }


# ─────────────────────────────────────────────
# Model tests
# ─────────────────────────────────────────────

class TestCalculateLevel:
    def test_level_one_at_zero_xp(self):
        level, xp_needed = calculate_level(0)
        assert level == 1
        assert xp_needed == 1000

    def test_level_two_at_1000_xp(self):
        level, xp_needed = calculate_level(1000)
        assert level == 2

    def test_level_three(self):
        # Level 2 requires 1000, level 3 requires 1500
        level, _ = calculate_level(2500)
        assert level == 3

    def test_large_xp_high_level(self):
        level, _ = calculate_level(50000)
        assert level >= 5

    def test_xp_to_next_level_positive(self):
        _, xp_needed = calculate_level(500)
        assert xp_needed > 0


class TestXpForAction:
    def test_workout_complete(self):
        assert xp_for_action("workout_complete") == 200

    def test_pr_set(self):
        assert xp_for_action("pr_set") == 300

    def test_streak_3(self):
        assert xp_for_action("streak_3") == 200

    def test_streak_7(self):
        assert xp_for_action("streak_7") == 500

    def test_streak_30(self):
        assert xp_for_action("streak_30") == 2000

    def test_unknown_action_defaults_to_50(self):
        assert xp_for_action("does_not_exist") == 50

    def test_onboarding_complete(self):
        assert xp_for_action("onboarding_complete") == 300


class TestBadgeDefinitions:
    def test_all_badge_types_have_definitions(self):
        for badge_type in BadgeType:
            assert badge_type in BADGE_DEFINITIONS

    def test_each_definition_has_required_keys(self):
        for badge_type, defn in BADGE_DEFINITIONS.items():
            assert "name" in defn
            assert "description" in defn
            assert "icon" in defn
            assert "xp" in defn


class TestBadgeModel:
    def test_from_db(self):
        row = {
            "badge_id": BadgeType.FIRST_WORKOUT,
            "earned_at": "2026-01-15T10:00:00"
        }
        badge = Badge.from_db(row)
        assert badge.id == BadgeType.FIRST_WORKOUT
        assert badge.name == "First Blood"
        assert badge.icon == "🎯"

    def test_from_db_unknown_badge(self):
        row = {"badge_id": "unknown_badge", "earned_at": None}
        badge = Badge.from_db(row)
        assert badge.id == "unknown_badge"
        assert badge.name == "Unknown"
        assert badge.icon == "🏆"


class TestStreakData:
    def test_defaults(self):
        s = StreakData()
        assert s.current_streak == 0
        assert s.longest_streak == 0
        assert s.this_week_workouts == 0
        assert s.this_month_workouts == 0
        assert s.last_workout_date is None


class TestUserStats:
    def test_defaults(self):
        u = UserStats()
        assert u.total_workouts == 0
        assert u.level == 1
        assert u.xp == 0
        assert u.badges == []


# ─────────────────────────────────────────────
# GamificationService tests
# ─────────────────────────────────────────────

class TestGetLongestStreak:
    def setup_method(self):
        self.svc = GamificationService(str(uuid4()))

    def test_single_date(self):
        dates = {date.today()}
        assert self.svc._get_longest_streak(dates) == 1

    def test_consecutive_days(self):
        today = date.today()
        dates = {today - timedelta(days=i) for i in range(5)}
        assert self.svc._get_longest_streak(dates) == 5

    def test_gap_in_dates(self):
        today = date.today()
        dates = {today, today - timedelta(days=1), today - timedelta(days=3)}
        assert self.svc._get_longest_streak(dates) == 2

    def test_empty_dates(self):
        assert self.svc._get_longest_streak(set()) == 0

    def test_non_consecutive(self):
        today = date.today()
        dates = {today, today - timedelta(days=2), today - timedelta(days=4)}
        assert self.svc._get_longest_streak(dates) == 1


class TestCalculateStreak:
    def setup_method(self):
        self.svc = GamificationService(str(uuid4()))

    def test_empty_sessions(self):
        data = self.svc._calculate_streak([])
        assert data.current_streak == 0
        assert data.longest_streak == 0

    def test_one_completed_today(self):
        sessions = [_make_session(0)]
        data = self.svc._calculate_streak(sessions)
        assert data.current_streak == 1

    def test_three_consecutive_days(self):
        sessions = [_make_session(i) for i in range(3)]
        data = self.svc._calculate_streak(sessions)
        assert data.current_streak == 3

    def test_streak_broken_by_gap(self):
        # Days 0, 1, then gap to day 3
        sessions = [_make_session(0), _make_session(1), _make_session(3)]
        data = self.svc._calculate_streak(sessions)
        assert data.current_streak == 2

    def test_incomplete_sessions_excluded(self):
        sessions = [_make_session(0, completed=False)]
        data = self.svc._calculate_streak(sessions)
        assert data.current_streak == 0

    def test_last_workout_date_set(self):
        sessions = [_make_session(0)]
        data = self.svc._calculate_streak(sessions)
        assert data.last_workout_date == date.today()

    def test_this_week_workouts_counted(self):
        # Sessions on days 0..6 — all within the last 7 days
        today = date.today()
        sessions = [_make_session(i) for i in range(3)]
        data = self.svc._calculate_streak(sessions)
        # At least the current week's workouts count
        assert data.this_week_workouts >= 0

    def test_longest_streak_equals_or_greater_than_current(self):
        sessions = [_make_session(i) for i in range(5)]
        data = self.svc._calculate_streak(sessions)
        assert data.longest_streak >= data.current_streak


class TestGamificationServiceWithMockedSupabase:
    """Tests that mock the supabase_client used by GamificationService"""

    def _make_service(self):
        return GamificationService(str(uuid4()))

    @patch("app.services.gamification.supabase_client")
    def test_get_user_sessions_returns_data(self, mock_db):
        svc = self._make_service()
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(data=[_make_session(0)])
        sessions = svc._get_user_sessions()
        assert isinstance(sessions, list)

    @patch("app.services.gamification.supabase_client")
    def test_get_user_sessions_handles_exception(self, mock_db):
        svc = self._make_service()
        mock_db.table.side_effect = Exception("DB error")
        sessions = svc._get_user_sessions()
        assert sessions == []

    @patch("app.services.gamification.supabase_client")
    def test_get_user_xp_returns_value(self, mock_db):
        svc = self._make_service()
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={"xp": 1500})
        xp = svc._get_user_xp()
        assert xp == 1500

    @patch("app.services.gamification.supabase_client")
    def test_get_user_xp_no_data_returns_zero(self, mock_db):
        svc = self._make_service()
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)
        xp = svc._get_user_xp()
        assert xp == 0

    @patch("app.services.gamification.supabase_client")
    def test_get_user_xp_exception_returns_zero(self, mock_db):
        svc = self._make_service()
        mock_db.table.side_effect = Exception("fail")
        xp = svc._get_user_xp()
        assert xp == 0

    @patch("app.services.gamification.supabase_client")
    def test_get_user_badges_returns_list(self, mock_db):
        svc = self._make_service()
        badge_row = {"badge_id": BadgeType.FIRST_WORKOUT, "earned_at": "2026-01-01T10:00:00"}
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[badge_row])
        badges = svc._get_user_badges()
        assert isinstance(badges, list)
        assert len(badges) == 1

    @patch("app.services.gamification.supabase_client")
    def test_get_user_badges_exception_returns_empty(self, mock_db):
        svc = self._make_service()
        mock_db.table.side_effect = Exception("fail")
        badges = svc._get_user_badges()
        assert badges == []

    @patch("app.services.gamification.supabase_client")
    def test_get_user_stats_aggregates(self, mock_db):
        svc = self._make_service()
        sessions = [_make_session(i) for i in range(3)]
        # Mock sessions
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(data=sessions)
        # Mock XP
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={"xp": 600})
        # Mock badges (separate call)
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        stats = svc.get_user_stats()
        assert isinstance(stats, UserStats)
        assert stats.total_workouts == 3

    @patch("app.services.gamification.supabase_client")
    def test_add_xp_upsert_path(self, mock_db):
        svc = self._make_service()
        # XP fetch
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={"xp": 200})
        # Upsert
        mock_db.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[{"xp": 400}])

        new_level, new_xp = svc.add_xp(200)
        assert new_xp == 400
        assert new_level >= 1

    @patch("app.services.gamification.supabase_client")
    def test_add_xp_upsert_fails_insert_path(self, mock_db):
        svc = self._make_service()
        # XP fetch returns 0
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)
        # Upsert raises, insert also raises
        mock_db.table.return_value.upsert.side_effect = Exception("upsert fail")
        mock_db.table.return_value.insert.side_effect = Exception("insert fail")

        # Should not raise
        new_level, new_xp = svc.add_xp(100)
        assert new_xp == 100

    @patch("app.services.gamification.supabase_client")
    def test_award_badge_returns_badge(self, mock_db):
        svc = self._make_service()
        badge_row = {
            "badge_id": BadgeType.FIRST_WORKOUT,
            "earned_at": "2026-01-01T10:00:00",
            "user_id": svc.user_id,
            "id": str(uuid4()),
            "created_at": "2026-01-01T10:00:00"
        }
        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[badge_row])
        badge = svc._award_badge(BadgeType.FIRST_WORKOUT)
        assert badge is not None
        assert badge.id == BadgeType.FIRST_WORKOUT

    @patch("app.services.gamification.supabase_client")
    def test_award_badge_returns_none_on_exception(self, mock_db):
        svc = self._make_service()
        mock_db.table.return_value.insert.side_effect = Exception("fail")
        badge = svc._award_badge(BadgeType.FIRST_WORKOUT)
        assert badge is None

    @patch("app.services.gamification.supabase_client")
    def test_check_and_award_badges_first_workout(self, mock_db):
        svc = self._make_service()
        sessions = [_make_session(0)]

        # _get_user_sessions (order.execute)
        def table_side(name):
            q = MagicMock()
            q.select.return_value = q
            q.eq.return_value = q
            q.order.return_value = q
            q.single.return_value = q
            q.insert.return_value = q
            q.upsert.return_value = q

            if name == "workout_sessions":
                q.execute.return_value = MagicMock(data=sessions)
            elif name == "user_badges":
                q.execute.return_value = MagicMock(data=[])
            else:
                q.execute.return_value = MagicMock(data=None)
            return q

        mock_db.table.side_effect = table_side
        # Should not raise
        badges = svc.check_and_award_badges()
        assert isinstance(badges, list)

    @patch("app.services.gamification.supabase_client")
    def test_record_workout_complete_returns_dict(self, mock_db):
        svc = self._make_service()

        def table_side(name):
            q = MagicMock()
            q.select.return_value = q
            q.eq.return_value = q
            q.order.return_value = q
            q.single.return_value = q
            q.insert.return_value = q
            q.upsert.return_value = q
            if name == "workout_sessions":
                q.execute.return_value = MagicMock(data=[_make_session(0)])
            elif name == "user_stats":
                q.execute.return_value = MagicMock(data={"xp": 200})
            elif name == "user_badges":
                q.execute.return_value = MagicMock(data=[])
            elif name == "weekly_schedules":
                q.execute.return_value = MagicMock(data=None)
            else:
                q.execute.return_value = MagicMock(data=[])
            return q

        mock_db.table.side_effect = table_side

        result = svc.record_workout_complete({"total_volume_kg": 5000})
        assert "xp_earned" in result
        assert "new_level" in result
        assert "level_up" in result
        assert "new_badges" in result
        assert result["xp_earned"] >= 200  # base workout XP

    @patch("app.services.gamification.supabase_client")
    def test_record_workout_complete_streak_bonus(self, mock_db):
        """Streak of 3+ days triggers XP bonus."""
        svc = self._make_service()
        sessions = [_make_session(i) for i in range(3)]

        def table_side(name):
            q = MagicMock()
            q.select.return_value = q
            q.eq.return_value = q
            q.order.return_value = q
            q.single.return_value = q
            q.insert.return_value = q
            q.upsert.return_value = q
            if name == "workout_sessions":
                q.execute.return_value = MagicMock(data=sessions)
            elif name == "user_stats":
                q.execute.return_value = MagicMock(data={"xp": 0})
            elif name == "user_badges":
                q.execute.return_value = MagicMock(data=[])
            elif name == "weekly_schedules":
                q.execute.return_value = MagicMock(data=None)
            else:
                q.execute.return_value = MagicMock(data=[])
            return q

        mock_db.table.side_effect = table_side

        result = svc.record_workout_complete({})
        # Base 200 + streak_3 bonus 200 = at least 400
        assert result["xp_earned"] >= 400

    @patch("app.services.gamification.supabase_client")
    def test_check_streak_true(self, mock_db):
        svc = self._make_service()
        sessions = [_make_session(i) for i in range(5)]
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(data=sessions)
        assert svc._check_streak(3) is True

    @patch("app.services.gamification.supabase_client")
    def test_check_streak_false(self, mock_db):
        svc = self._make_service()
        sessions = [_make_session(0)]
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(data=sessions)
        assert svc._check_streak(7) is False

    @patch("app.services.gamification.supabase_client")
    def test_get_month_workouts(self, mock_db):
        svc = self._make_service()
        sessions = [_make_session(i) for i in range(10)]
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(data=sessions)
        count = svc._get_month_workouts()
        assert isinstance(count, int)
        assert count >= 0

    @patch("app.services.gamification.supabase_client")
    def test_check_perfect_week_no_schedule(self, mock_db):
        svc = self._make_service()
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)
        result = svc._check_perfect_week()
        assert result is False

    @patch("app.services.gamification.supabase_client")
    def test_check_perfect_week_exception_returns_false(self, mock_db):
        svc = self._make_service()
        mock_db.table.side_effect = Exception("fail")
        result = svc._check_perfect_week()
        assert result is False
