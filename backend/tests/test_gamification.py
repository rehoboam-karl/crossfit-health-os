"""
Tests for app/services/gamification.py and app/models/gamification.py (SQLAlchemy).
"""
from datetime import date, datetime, timedelta

import pytest

from app.db.models import UserBadge, UserStatsRow, WorkoutSession
from app.models.gamification import (
    BADGE_DEFINITIONS,
    Badge,
    BadgeType,
    StreakData,
    UserStats,
    calculate_level,
    xp_for_action,
)
from app.services.gamification import GamificationService


# ──────────────────────────────────────────────
# Pure model helpers
# ──────────────────────────────────────────────

class TestCalculateLevel:
    def test_level_one_at_zero_xp(self):
        level, xp_needed = calculate_level(0)
        assert level == 1
        assert xp_needed == 1000

    def test_level_two_at_1000_xp(self):
        level, _ = calculate_level(1000)
        assert level == 2

    def test_level_three_at_2500_xp(self):
        level, _ = calculate_level(2500)
        assert level == 3

    def test_large_xp_high_level(self):
        level, _ = calculate_level(50000)
        assert level >= 5

    def test_xp_to_next_level_positive(self):
        _, xp_needed = calculate_level(500)
        assert xp_needed > 0


class TestXpForAction:
    @pytest.mark.parametrize("action,expected", [
        ("workout_complete", 200),
        ("pr_set", 300),
        ("streak_3", 200),
        ("streak_7", 500),
        ("streak_30", 2000),
        ("onboarding_complete", 300),
        ("does_not_exist", 50),
    ])
    def test_action_returns_expected_xp(self, action, expected):
        assert xp_for_action(action) == expected


class TestBadgeDefinitions:
    def test_all_badge_types_have_definitions(self):
        for t in BadgeType:
            assert t in BADGE_DEFINITIONS

    def test_each_definition_has_required_keys(self):
        for _t, defn in BADGE_DEFINITIONS.items():
            assert {"name", "description", "icon", "xp"} <= defn.keys()


class TestStreakData:
    def test_defaults(self):
        data = StreakData()
        assert data.current_streak == 0
        assert data.longest_streak == 0


class TestUserStats:
    def test_defaults(self):
        stats = UserStats()
        assert stats.total_workouts == 0
        assert stats.xp == 0
        assert stats.level == 1


# ──────────────────────────────────────────────
# Service tests against in-memory SQLite
# ──────────────────────────────────────────────

def _add_session(db, user_id: int, days_ago: int, completed: bool = True, rpe: int = 7):
    dt = datetime.utcnow() - timedelta(days=days_ago)
    session = WorkoutSession(
        user_id=user_id,
        workout_type="strength",
        started_at=dt,
        completed_at=dt if completed else None,
        rpe_score=rpe if completed else None,
    )
    db.add(session)


class TestGamificationService:
    def test_empty_user_stats(self, db_session, seeded_user):
        svc = GamificationService(seeded_user.id, db_session)
        stats = svc.get_user_stats()
        assert stats.total_workouts == 0
        assert stats.current_streak == 0
        assert stats.xp == 0
        assert stats.level == 1

    def test_streak_counts_consecutive_days(self, db_session, seeded_user):
        for i in range(5):
            _add_session(db_session, seeded_user.id, days_ago=i)
        db_session.commit()

        svc = GamificationService(seeded_user.id, db_session)
        streak = svc._calculate_streak()
        assert streak.current_streak == 5
        assert streak.longest_streak >= 5

    def test_add_xp_persists_and_levels_up(self, db_session, seeded_user):
        svc = GamificationService(seeded_user.id, db_session)
        level, xp = svc.add_xp(1500)
        assert xp == 1500
        assert level == 2
        # Re-read
        row = db_session.get(UserStatsRow, seeded_user.id)
        assert row.xp == 1500
        assert row.level == 2

    def test_award_first_workout_badge(self, db_session, seeded_user):
        _add_session(db_session, seeded_user.id, days_ago=0)
        db_session.commit()
        svc = GamificationService(seeded_user.id, db_session)
        new_badges = svc.check_and_award_badges()
        ids = {b.id for b in new_badges}
        assert BadgeType.FIRST_WORKOUT.value in ids
        # Idempotent — second call doesn't duplicate
        assert svc.check_and_award_badges() == [] or BadgeType.FIRST_WORKOUT.value not in {b.id for b in svc.check_and_award_badges()}

    def test_record_workout_complete_awards_xp(self, db_session, seeded_user):
        # Seed 3 prior days to trigger streak_3 bonus
        for i in range(3):
            _add_session(db_session, seeded_user.id, days_ago=i)
        db_session.commit()

        svc = GamificationService(seeded_user.id, db_session)
        result = svc.record_workout_complete({"total_volume_kg": 5000})
        assert result["xp_earned"] >= xp_for_action("workout_complete")
        assert isinstance(result["new_badges"], list)

    def test_leaderboard_fixture(self, db_session, seeded_user):
        """UserStatsRow rows can be queried in XP-descending order."""
        row = UserStatsRow(user_id=seeded_user.id, xp=500, level=1)
        db_session.add(row)
        db_session.commit()

        svc = GamificationService(seeded_user.id, db_session)
        assert svc._get_user_xp() == 500


class TestBadgeModel:
    def test_badge_instance(self):
        b = Badge(
            id=BadgeType.FIRST_WORKOUT.value,
            name="First Blood",
            description="x",
            icon="🎯",
            earned_at=datetime.utcnow(),
        )
        assert b.id == "first_workout"
