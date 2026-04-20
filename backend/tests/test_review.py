"""
Tests for Review API — session feedback + weekly reviews (SQLAlchemy).
"""
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient


def _sample_feedback_payload(session_id: str) -> dict:
    return {
        "session_id": session_id,
        "date": date.today().isoformat(),
        "rpe_score": 8,
        "difficulty": "hard_but_manageable",
        "technique_quality": 7,
        "pacing": "good",
        "energy_level_pre": 8,
        "energy_level_post": 4,
        "would_repeat": True,
        "notes": "Squats felt strong",
        "movements_feedback": [],
    }


class TestSessionFeedback:
    @pytest.mark.asyncio
    async def test_create_session_feedback(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        from app.db.models import WorkoutSession as WS
        ws = WS(user_id=seeded_user.id, workout_type="strength", started_at=datetime.utcnow())
        db_session.add(ws)
        db_session.commit()
        db_session.refresh(ws)

        response = await authenticated_client.post(
            "/api/v1/review/feedback", json=_sample_feedback_payload(str(ws.id))
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["rpe_score"] == 8
        assert data["session_id"] == str(ws.id)

    @pytest.mark.asyncio
    async def test_create_feedback_unauthorized_session(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        from app.db.models import User, WorkoutSession as WS
        # Seed a second user + their session.
        other = User(
            id=999, email="other@x.com", password_hash="h", name="Other",
            fitness_level="beginner", timezone="UTC",
        )
        db_session.add(other)
        db_session.commit()
        ws = WS(user_id=other.id, workout_type="strength", started_at=datetime.utcnow())
        db_session.add(ws)
        db_session.commit()
        db_session.refresh(ws)

        response = await authenticated_client.post(
            "/api/v1/review/feedback", json=_sample_feedback_payload(str(ws.id))
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_session_feedback(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        from app.db.models import SessionFeedback, WorkoutSession as WS
        ws = WS(user_id=seeded_user.id, workout_type="metcon", started_at=datetime.utcnow())
        db_session.add(ws)
        db_session.commit()
        db_session.refresh(ws)

        fb = SessionFeedback(
            user_id=seeded_user.id, session_id=ws.id, date=date.today(),
            rpe_score=7, difficulty="appropriate", technique_quality=8,
            pacing="good", energy_level_pre=7, energy_level_post=5,
        )
        db_session.add(fb)
        db_session.commit()

        response = await authenticated_client.get(f"/api/v1/review/feedback/{ws.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["rpe_score"] == 7
        assert data["session_id"] == str(ws.id)

    @pytest.mark.asyncio
    async def test_list_feedback(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        from app.db.models import SessionFeedback, WorkoutSession as WS
        ws_ids = []
        for i in range(2):
            ws = WS(user_id=seeded_user.id, workout_type="strength", started_at=datetime.utcnow())
            db_session.add(ws)
            db_session.flush()
            ws_ids.append(ws.id)
            db_session.add(SessionFeedback(
                user_id=seeded_user.id, session_id=ws.id, date=date.today() - timedelta(days=i),
                rpe_score=7 + i, difficulty="appropriate", technique_quality=7,
                pacing="good", energy_level_pre=8, energy_level_post=5,
            ))
        db_session.commit()

        response = await authenticated_client.get("/api/v1/review/feedback")
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestWeeklyReview:
    @pytest.mark.asyncio
    async def test_generate_weekly_review(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        from app.models.review import (
            NextWeekAdjustments, PerformanceChallenge, PerformanceHighlight, WeeklyReview,
        )
        with patch(
            "app.api.v1.review.weekly_reviewer.generate_weekly_review", new_callable=AsyncMock
        ) as mock_reviewer:
            mock_reviewer.return_value = WeeklyReview(
                id=uuid4(),
                user_id=seeded_user.id,
                week_number=3,
                week_start_date=date(2026, 2, 3),
                week_end_date=date(2026, 2, 9),
                summary="Strong week",
                planned_sessions=5,
                completed_sessions=5,
                adherence_rate=100.0,
                avg_rpe=7.5,
                avg_readiness=80.0,
                strengths=[PerformanceHighlight(movement="squat", improvement="+5kg", confidence="high")],
                weaknesses=[PerformanceChallenge(movement="squat", issue="depth", suggested_focus="mobility")],
                recovery_status="optimal",
                volume_assessment="appropriate",
                next_week_adjustments=NextWeekAdjustments(
                    volume_change_pct=0, intensity_change="maintain", focus_movements=["squat"],
                ),
                coach_message="Great week!",
                created_at=datetime.utcnow(),
            )
            response = await authenticated_client.post(
                "/api/v1/review/weekly",
                json={
                    "week_number": 3,
                    "week_start_date": "2026-02-03",
                    "week_end_date": "2026-02-09",
                },
            )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["week_number"] == 3
        assert data["adherence_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_get_latest_review(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        from app.db.models import WeeklyReview as WR
        db_session.add(WR(
            user_id=seeded_user.id,
            week_number=3,
            week_start_date=date(2026, 2, 3),
            week_end_date=date(2026, 2, 9),
            summary="Strong week",
            planned_sessions=5, completed_sessions=5, adherence_rate=100.0,
            avg_rpe=7.5, avg_readiness=80.0,
            recovery_status="optimal", volume_assessment="appropriate",
            next_week_adjustments={"volume_change_pct": 0, "intensity_change": "maintain", "focus_movements": []},
            coach_message="Great work",
        ))
        db_session.commit()

        response = await authenticated_client.get("/api/v1/review/weekly/latest")
        assert response.status_code == 200
        assert response.json()["week_number"] == 3

    @pytest.mark.asyncio
    async def test_get_latest_review_not_found(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        response = await authenticated_client.get("/api/v1/review/weekly/latest")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_weekly_reviews(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        from app.db.models import WeeklyReview as WR
        for wk in [1, 2]:
            db_session.add(WR(
                user_id=seeded_user.id,
                week_number=wk,
                week_start_date=date(2026, 1, 6) + timedelta(days=7 * (wk - 1)),
                week_end_date=date(2026, 1, 12) + timedelta(days=7 * (wk - 1)),
                summary="w", planned_sessions=5, completed_sessions=5, adherence_rate=100,
                avg_rpe=7, avg_readiness=75,
                recovery_status="adequate", volume_assessment="appropriate",
                next_week_adjustments={"volume_change_pct": 0, "intensity_change": "maintain", "focus_movements": []},
                coach_message="ok",
            ))
        db_session.commit()

        response = await authenticated_client.get("/api/v1/review/weekly")
        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.asyncio
    async def test_get_review_by_week(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        from app.db.models import WeeklyReview as WR
        db_session.add(WR(
            user_id=seeded_user.id,
            week_number=5,
            week_start_date=date(2026, 2, 10),
            week_end_date=date(2026, 2, 16),
            summary="w5", planned_sessions=5, completed_sessions=5, adherence_rate=100,
            avg_rpe=8, avg_readiness=85,
            recovery_status="optimal", volume_assessment="appropriate",
            next_week_adjustments={"volume_change_pct": 0, "intensity_change": "maintain", "focus_movements": []},
            coach_message="Great work",
        ))
        db_session.commit()

        response = await authenticated_client.get("/api/v1/review/weekly/5")
        assert response.status_code == 200
        assert response.json()["week_number"] == 5


class TestApplyReviewAdjustments:
    @pytest.mark.asyncio
    async def test_apply_review_adjustments(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        from app.db.models import Macrocycle, Microcycle, WeeklyReview as WR

        review = WR(
            user_id=seeded_user.id,
            week_number=3,
            week_start_date=date(2026, 2, 3),
            week_end_date=date(2026, 2, 9),
            summary="Week review",
            planned_sessions=5, completed_sessions=5, adherence_rate=100,
            avg_rpe=8, avg_readiness=75,
            recovery_status="compromised", volume_assessment="too_high",
            next_week_adjustments={
                "volume_change_pct": -10,
                "intensity_change": "decrease",
                "focus_movements": ["squat", "deadlift"],
            },
            coach_message="Focus on recovery",
        )
        db_session.add(review)

        macro = Macrocycle(
            user_id=seeded_user.id, name="m", methodology="hwpo",
            start_date=date(2026, 2, 3), end_date=date(2026, 3, 2),
            block_plan=[{"type": "accumulation", "weeks": 4}], active=True,
        )
        db_session.add(macro)
        db_session.flush()

        micro = Microcycle(
            macrocycle_id=macro.id, user_id=seeded_user.id,
            start_date=date(2026, 2, 10), end_date=date(2026, 2, 16),
            week_index_in_macro=4,
        )
        db_session.add(micro)
        db_session.commit()
        db_session.refresh(review)

        with patch(
            "app.core.engine.ai_programmer.ai_programmer.generate_microcycle_program",
            new_callable=AsyncMock,
        ) as mock_ai:
            mock_ai.return_value = 3
            response = await authenticated_client.post(f"/api/v1/review/weekly/{review.id}/apply")

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "success"
        assert data["adjustments_applied"]["volume_change_pct"] == -10
        assert data["workouts_generated"] == 3

    @pytest.mark.asyncio
    async def test_apply_adjustments_unauthorized(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        from app.db.models import User, WeeklyReview as WR

        other = User(id=999, email="other@x.com", password_hash="h", name="Other",
                     fitness_level="beginner", timezone="UTC")
        db_session.add(other)
        db_session.commit()

        review = WR(
            user_id=other.id,
            week_number=3,
            week_start_date=date(2026, 2, 3),
            week_end_date=date(2026, 2, 9),
            summary="other's review",
            planned_sessions=0, completed_sessions=0, adherence_rate=0,
            avg_rpe=0, avg_readiness=0,
            recovery_status="adequate", volume_assessment="appropriate",
            next_week_adjustments={"volume_change_pct": 0, "intensity_change": "maintain", "focus_movements": []},
            coach_message="x",
        )
        db_session.add(review)
        db_session.commit()
        db_session.refresh(review)

        response = await authenticated_client.post(f"/api/v1/review/weekly/{review.id}/apply")
        assert response.status_code == 403
