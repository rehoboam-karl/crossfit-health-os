"""
Tests for Review API
Tests session feedback and AI-powered weekly reviews
"""
import pytest
from httpx import AsyncClient
from datetime import date
from uuid import uuid4
from unittest.mock import patch, AsyncMock, Mock


class TestSessionFeedback:
    """Test session feedback submission"""
    
    @pytest.mark.asyncio
    async def test_create_session_feedback(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test submitting post-workout feedback"""
        session_id = str(uuid4())
        
        # Mock existing session
        mock_supabase.set_mock_data("workout_sessions", {
            "id": session_id,
            "user_id": str(mock_user_uuid),
            "workout_type": "strength"
        })
        
        payload = {
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
            "movements_feedback": [
                {
                    "movement": "back_squat",
                    "prescribed_sets": 5,
                    "prescribed_reps": 5,
                    "prescribed_weight_kg": 112.0,
                    "actual_sets": 5,
                    "actual_reps": [5, 5, 5, 5, 4],
                    "actual_weight_kg": [112.0, 112.0, 112.0, 112.0, 110.0],
                    "technique_quality": 8,
                    "notes": "Last set dropped weight"
                }
            ]
        }
        
        response = await authenticated_client.post("/api/v1/review/feedback", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["rpe_score"] == 8
        assert data["session_id"] == session_id
    
    @pytest.mark.asyncio
    async def test_create_feedback_unauthorized_session(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test creating feedback for another user's session"""
        session_id = str(uuid4())
        other_user_id = str(uuid4())
        
        # Mock session belonging to different user
        mock_supabase.set_mock_data("workout_sessions", {
            "id": session_id,
            "user_id": other_user_id,
            "workout_type": "strength"
        })
        
        payload = {
            "session_id": session_id,
            "date": date.today().isoformat(),
            "rpe_score": 8,
            "difficulty": "appropriate",
            "technique_quality": 7,
            "pacing": "good",
            "energy_level_pre": 8,
            "energy_level_post": 5
        }
        
        response = await authenticated_client.post("/api/v1/review/feedback", json=payload)
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_get_session_feedback(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test getting feedback for a session"""
        from datetime import datetime
        session_id = str(uuid4())
        
        feedback_data = {
            "id": str(uuid4()),
            "user_id": str(mock_user_uuid),
            "session_id": session_id,
            "date": date.today().isoformat(),
            "rpe_score": 7,
            "difficulty": "appropriate",
            "technique_quality": 8,
            "pacing": "good",
            "energy_level_pre": 7,
            "energy_level_post": 5,
            "would_repeat": True,
            "notes": "Good session",
            "movements_feedback": [],
            "created_at": datetime.utcnow().isoformat()
        }
        mock_supabase.set_mock_data("session_feedback", feedback_data)
        
        response = await authenticated_client.get(f"/api/v1/review/feedback/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["rpe_score"] == 7
    
    @pytest.mark.asyncio
    async def test_list_feedback(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test listing all session feedback"""
        from datetime import datetime
        feedbacks = [
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "session_id": str(uuid4()),
                "date": "2026-02-01",
                "rpe_score": 7,
                "difficulty": "appropriate",
                "technique_quality": 7,
                "pacing": "good",
                "energy_level_pre": 8,
                "energy_level_post": 6,
                "would_repeat": True,
                "movements_feedback": [],
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "session_id": str(uuid4()),
                "date": "2026-02-02",
                "rpe_score": 8,
                "difficulty": "hard_but_manageable",
                "technique_quality": 8,
                "pacing": "good",
                "energy_level_pre": 7,
                "energy_level_post": 5,
                "would_repeat": True,
                "movements_feedback": [],
                "created_at": datetime.utcnow().isoformat()
            }
        ]
        mock_supabase.set_mock_data("session_feedback", feedbacks)
        
        response = await authenticated_client.get("/api/v1/review/feedback")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2


class TestWeeklyReview:
    """Test AI-powered weekly review generation"""
    
    @pytest.mark.asyncio
    async def test_generate_weekly_review(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test generating weekly review with mocked AI"""
        with patch("app.api.v1.review.weekly_reviewer.generate_weekly_review", new_callable=AsyncMock) as mock_reviewer:
            from app.models.review import WeeklyReview, NextWeekAdjustments, PerformanceHighlight, PerformanceChallenge
            from datetime import datetime
            
            mock_review = WeeklyReview(
                id=uuid4(),
                user_id=mock_user_uuid,
                week_number=3,
                week_start_date=date(2026, 2, 3),
                week_end_date=date(2026, 2, 9),
                summary="Strong week with consistent training",
                planned_sessions=5,
                completed_sessions=5,
                adherence_rate=100.0,
                avg_rpe=7.5,
                avg_readiness=80.0,
                strengths=[
                    PerformanceHighlight(
                        movement="squat",
                        improvement="Increased weight by 5kg",
                        confidence="high"
                    )
                ],
                weaknesses=[
                    PerformanceChallenge(
                        movement="squat",
                        issue="Depth consistency",
                        suggested_focus="Mobility work"
                    )
                ],
                recovery_status="optimal",
                volume_assessment="appropriate",
                next_week_adjustments=NextWeekAdjustments(
                    volume_change_pct=0,
                    intensity_change="maintain",
                    focus_movements=["squat"]
                ),
                coach_message="Great week! Keep it up.",
                created_at=datetime.utcnow()
            )
            
            mock_reviewer.return_value = mock_review
            
            payload = {
                "week_number": 3,
                "week_start_date": "2026-02-03",
                "week_end_date": "2026-02-09",
                "athlete_notes": "Felt strong this week"
            }
            
            response = await authenticated_client.post("/api/v1/review/weekly", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["week_number"] == 3
            assert data["adherence_rate"] == 100.0
            assert "strengths" in data
            assert "weaknesses" in data
    
    @pytest.mark.asyncio
    async def test_get_latest_review(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test getting latest weekly review"""
        review_data = {
            "id": str(uuid4()),
            "user_id": str(mock_user_uuid),
            "week_number": 3,
            "week_start_date": "2026-02-03",
            "week_end_date": "2026-02-09",
            "summary": "Strong week overall",
            "planned_sessions": 5,
            "completed_sessions": 5,
            "adherence_rate": 100.0,
            "avg_rpe": 7.5,
            "avg_readiness": 80.0,
            "strengths": [],
            "weaknesses": [],
            "recovery_status": "optimal",
            "volume_assessment": "appropriate",
            "progressions_detected": [],
            "next_week_adjustments": {
                "volume_change_pct": 0,
                "intensity_change": "maintain",
                "focus_movements": []
            },
            "coach_message": "Great work",
            "ai_model_used": "claude-3-5-sonnet",
            "created_at": "2026-02-09T12:00:00"
        }
        mock_supabase.set_mock_data("weekly_reviews", [review_data])
        
        response = await authenticated_client.get("/api/v1/review/weekly/latest")
        
        assert response.status_code == 200
        data = response.json()
        assert data["week_number"] == 3
    
    @pytest.mark.asyncio
    async def test_get_latest_review_not_found(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test getting latest review when none exist"""
        mock_supabase.set_mock_data("weekly_reviews", [])
        
        response = await authenticated_client.get("/api/v1/review/weekly/latest")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_list_weekly_reviews(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test listing all weekly reviews"""
        reviews = [
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "week_number": 1,
                "week_start_date": "2026-01-06",
                "week_end_date": "2026-01-12",
                "summary": "Good start",
                "planned_sessions": 5,
                "completed_sessions": 4,
                "adherence_rate": 80.0,
                "avg_rpe": 7.0,
                "avg_readiness": 75.0,
                "strengths": [],
                "weaknesses": [],
                "recovery_status": "adequate",
                "volume_assessment": "appropriate",
                "progressions_detected": [],
                "next_week_adjustments": {
                    "volume_change_pct": 0,
                    "intensity_change": "maintain",
                    "focus_movements": []
                },
                "coach_message": "Good start",
                "ai_model_used": "claude-3-5-sonnet",
                "created_at": "2026-01-12T12:00:00"
            },
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "week_number": 2,
                "week_start_date": "2026-01-13",
                "week_end_date": "2026-01-19",
                "summary": "Perfect week",
                "planned_sessions": 5,
                "completed_sessions": 5,
                "adherence_rate": 100.0,
                "avg_rpe": 7.5,
                "avg_readiness": 82.0,
                "strengths": [],
                "weaknesses": [],
                "recovery_status": "optimal",
                "volume_assessment": "appropriate",
                "progressions_detected": [],
                "next_week_adjustments": {
                    "volume_change_pct": 0,
                    "intensity_change": "maintain",
                    "focus_movements": []
                },
                "coach_message": "Excellent work",
                "ai_model_used": "claude-3-5-sonnet",
                "created_at": "2026-01-19T12:00:00"
            }
        ]
        mock_supabase.set_mock_data("weekly_reviews", reviews)
        
        response = await authenticated_client.get("/api/v1/review/weekly")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
    
    @pytest.mark.asyncio
    async def test_get_review_by_week(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test getting review for specific week number"""
        review_data = {
            "id": str(uuid4()),
            "user_id": str(mock_user_uuid),
            "week_number": 5,
            "week_start_date": "2026-02-10",
            "week_end_date": "2026-02-16",
            "summary": "Strong week",
            "planned_sessions": 5,
            "completed_sessions": 5,
            "adherence_rate": 100.0,
            "avg_rpe": 8.0,
            "avg_readiness": 85.0,
            "strengths": [],
            "weaknesses": [],
            "recovery_status": "optimal",
            "volume_assessment": "appropriate",
            "progressions_detected": [],
            "next_week_adjustments": {
                "volume_change_pct": 0,
                "intensity_change": "maintain",
                "focus_movements": []
            },
            "coach_message": "Great work",
            "ai_model_used": "claude-3-5-sonnet",
            "created_at": "2026-02-16T12:00:00"
        }
        mock_supabase.set_mock_data("weekly_reviews", [review_data])
        
        response = await authenticated_client.get("/api/v1/review/weekly/5")
        
        assert response.status_code == 200
        data = response.json()
        assert data["week_number"] == 5


class TestApplyReviewAdjustments:
    """Test applying review recommendations to next week"""
    
    @pytest.mark.asyncio
    async def test_apply_review_adjustments(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test applying review adjustments to generate next week's program"""
        review_id = str(uuid4())
        
        # Mock review
        review_data = {
            "id": review_id,
            "user_id": str(mock_user_uuid),
            "week_number": 3,
            "week_start_date": "2026-02-03",
            "week_end_date": "2026-02-09",
            "summary": "Week review",
            "planned_sessions": 5,
            "completed_sessions": 5,
            "adherence_rate": 100.0,
            "avg_rpe": 8.0,
            "avg_readiness": 75.0,
            "strengths": [],
            "weaknesses": [],
            "recovery_status": "compromised",
            "volume_assessment": "too_high",
            "progressions_detected": [],
            "next_week_adjustments": {
                "volume_change_pct": -10,
                "intensity_change": "decrease",
                "focus_movements": ["squat", "deadlift"]
            },
            "coach_message": "Focus on recovery",
            "ai_model_used": "claude-3-5-sonnet",
            "created_at": "2026-02-09T12:00:00"
        }
        mock_supabase.set_mock_data("weekly_reviews", review_data)
        
        # Mock active schedule
        schedule_data = {
            "id": str(uuid4()),
            "user_id": str(mock_user_uuid),
            "schedule": {
                "monday": {
                    "day": "monday",
                    "sessions": [{"time": "06:00:00", "duration_minutes": 90}],
                    "rest_day": False
                }
            },
            "active": True
        }
        mock_supabase.set_mock_data("weekly_schedules", [schedule_data])
        
        # Mock user
        user_data = {
            "id": str(mock_user_uuid),
            "fitness_level": "intermediate"
        }
        mock_supabase.set_mock_data("users", [user_data])
        
        # Mock AI programmer
        with patch("app.core.engine.ai_programmer.ai_programmer.generate_weekly_program", new_callable=AsyncMock) as mock_ai:
            from app.models.training import WorkoutTemplate, Methodology, WorkoutType, DayOfWeek, Movement
            from datetime import datetime
            
            mock_template = WorkoutTemplate(
                id=uuid4(),
                name="Adjusted Workout",
                methodology=Methodology.HWPO,
                difficulty_level="intermediate",
                workout_type=WorkoutType.STRENGTH,
                duration_minutes=90,
                movements=[Movement(movement="squat", sets=5, reps=5)],
                tags=["review_adjusted"],
                equipment_required=[],
                created_at=datetime.utcnow(),
                is_public=False
            )
            
            mock_ai.return_value = {
                DayOfWeek.MONDAY: mock_template
            }
            
            response = await authenticated_client.post(f"/api/v1/review/weekly/{review_id}/apply")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "adjustments_applied" in data
            assert data["adjustments_applied"]["volume_change_pct"] == -10
    
    @pytest.mark.asyncio
    async def test_apply_adjustments_unauthorized(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test applying adjustments to another user's review"""
        review_id = str(uuid4())
        other_user_id = str(uuid4())
        
        # Mock review belonging to different user
        review_data = {
            "id": review_id,
            "user_id": other_user_id,
            "week_number": 3
        }
        mock_supabase.set_mock_data("weekly_reviews", review_data)
        
        response = await authenticated_client.post(f"/api/v1/review/weekly/{review_id}/apply")
        
        assert response.status_code == 403
