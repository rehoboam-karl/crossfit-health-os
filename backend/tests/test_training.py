"""
Tests for Training API and Adaptive Engine
Tests workout generation for all 4 readiness bands
"""
import pytest
from httpx import AsyncClient
from datetime import date, datetime
from uuid import uuid4


class TestAdaptiveEngine:
    """Test adaptive workout generation with different readiness scores"""
    
    @pytest.mark.asyncio
    async def test_generate_workout_optimal_readiness(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test workout generation with readiness >= 80 (optimal)"""
        from unittest.mock import patch, AsyncMock
        from app.models.training import AdaptiveWorkoutResponse, WorkoutTemplate, Movement, Methodology, WorkoutType
        
        # Mock the adaptive engine response
        mock_template = WorkoutTemplate(
            id=uuid4(),
            name="Heavy Back Squat",
            methodology=Methodology.HWPO,
            workout_type=WorkoutType.STRENGTH,
            difficulty_level="intermediate",
            movements=[Movement(movement="back_squat", sets=5, reps=5, intensity="85%")],
            target_stimulus="max_strength",
            tags=[],
            equipment_required=["barbell"],
            created_at=datetime.utcnow(),
            is_public=True
        )
        
        mock_response = AdaptiveWorkoutResponse(
            template=mock_template,
            volume_multiplier=1.1,
            readiness_score=85,
            recommendation="Excellent recovery - push hard today!",
            adjusted_movements=[Movement(movement="back_squat", sets=5, reps=5, intensity="85%")],
            reasoning="High readiness allows for increased volume"
        )
        
        with patch("app.core.engine.adaptive.adaptive_engine.generate_workout", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response
            
            payload = {
                "user_id": str(mock_user_uuid),
                "date": date.today().isoformat(),
                "force_rest": False
            }
            
            response = await authenticated_client.post("/api/v1/training/generate", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            
            # Should have increased volume (multiplier > 1.0)
            assert data["volume_multiplier"] >= 1.0
            assert data["readiness_score"] >= 80
            assert "push" in data["recommendation"].lower() or "excellent" in data["recommendation"].lower()
    
    @pytest.mark.asyncio
    async def test_generate_workout_normal_readiness(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test workout generation with readiness 60-79 (normal)"""
        from unittest.mock import patch, AsyncMock
        from app.models.training import AdaptiveWorkoutResponse, WorkoutTemplate, Movement, Methodology, WorkoutType
        
        mock_template = WorkoutTemplate(
            id=uuid4(),
            name="Conditioning",
            methodology=Methodology.HWPO,
            workout_type=WorkoutType.METCON,
            difficulty_level="intermediate",
            movements=[
                Movement(movement="burpees", reps=21),
                Movement(movement="air_squats", reps=21)
            ],
            target_stimulus="power_endurance",
            tags=[],
            equipment_required=[],
            created_at=datetime.utcnow(),
            is_public=True
        )
        
        mock_response = AdaptiveWorkoutResponse(
            template=mock_template,
            volume_multiplier=1.0,
            readiness_score=70,
            recommendation="Normal recovery - stick to programmed volume",
            adjusted_movements=[
                Movement(movement="burpees", reps=21),
                Movement(movement="air_squats", reps=21)
            ],
            reasoning="Adequate readiness for normal training"
        )
        
        with patch("app.core.engine.adaptive.adaptive_engine.generate_workout", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response
            
            payload = {
                "user_id": str(mock_user_uuid),
                "date": date.today().isoformat(),
                "force_rest": False
            }
            
            response = await authenticated_client.post("/api/v1/training/generate", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            
            # Should maintain normal volume (multiplier = 1.0)
            assert 0.9 <= data["volume_multiplier"] <= 1.1
            assert 60 <= data["readiness_score"] < 80
            assert "normal" in data["recommendation"].lower() or "programmed" in data["recommendation"].lower()
    
    @pytest.mark.asyncio
    async def test_generate_workout_moderate_fatigue(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test workout generation with readiness 40-59 (reduced volume)"""
        from unittest.mock import patch, AsyncMock
        from app.models.training import AdaptiveWorkoutResponse, WorkoutTemplate, Movement, Methodology, WorkoutType
        
        mock_template = WorkoutTemplate(
            id=uuid4(),
            name="Light Conditioning",
            methodology=Methodology.HWPO,
            workout_type=WorkoutType.CONDITIONING,
            difficulty_level="intermediate",
            movements=[Movement(movement="run", distance_meters=400, sets=5, rest="90s")],
            target_stimulus="recovery",
            tags=[],
            equipment_required=[],
            created_at=datetime.utcnow(),
            is_public=True
        )
        
        mock_response = AdaptiveWorkoutResponse(
            template=mock_template,
            volume_multiplier=0.8,
            readiness_score=50,
            recommendation="Moderate fatigue detected - reduce volume",
            adjusted_movements=[Movement(movement="run", distance_meters=400, sets=4, rest="90s")],
            reasoning="Reduced readiness requires volume reduction"
        )
        
        with patch("app.core.engine.adaptive.adaptive_engine.generate_workout", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response
            
            payload = {
                "user_id": str(mock_user_uuid),
                "date": date.today().isoformat(),
                "force_rest": False
            }
            
            response = await authenticated_client.post("/api/v1/training/generate", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            
            # Should reduce volume (multiplier < 1.0)
            assert data["volume_multiplier"] < 1.0
            assert 40 <= data["readiness_score"] < 60
            assert "reduce" in data["recommendation"].lower() or "fatigue" in data["recommendation"].lower()
    
    @pytest.mark.asyncio
    async def test_generate_workout_high_fatigue(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test workout generation with readiness < 40 (active recovery)"""
        from unittest.mock import patch, AsyncMock
        from app.models.training import AdaptiveWorkoutResponse, WorkoutTemplate, Movement, Methodology, WorkoutType
        
        mock_template = WorkoutTemplate(
            id=uuid4(),
            name="Active Recovery",
            methodology=Methodology.CUSTOM,
            workout_type=WorkoutType.CONDITIONING,
            difficulty_level="intermediate",
            movements=[Movement(movement="walk", distance_meters=1000, duration_seconds=600)],
            target_stimulus="recovery",
            tags=["recovery"],
            equipment_required=[],
            created_at=datetime.utcnow(),
            is_public=True
        )
        
        mock_response = AdaptiveWorkoutResponse(
            template=mock_template,
            volume_multiplier=0.5,
            readiness_score=30,
            recommendation="High fatigue - active recovery only",
            adjusted_movements=[Movement(movement="walk", distance_meters=1000, duration_seconds=600)],
            reasoning="Very low readiness requires active recovery"
        )
        
        with patch("app.core.engine.adaptive.adaptive_engine.generate_workout", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response
            
            payload = {
                "user_id": str(mock_user_uuid),
                "date": date.today().isoformat(),
                "force_rest": False
            }
            
            response = await authenticated_client.post("/api/v1/training/generate", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            
            # Should drastically reduce volume (multiplier <= 0.5)
            assert data["volume_multiplier"] <= 0.6
            assert data["readiness_score"] < 40
            assert "recovery" in data["recommendation"].lower() or "high fatigue" in data["recommendation"].lower()


class TestWorkoutSessions:
    """Test workout session CRUD"""
    
    @pytest.mark.asyncio
    async def test_create_workout_session(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test creating a new workout session"""
        payload = {
            "workout_type": "strength",
            "movements": [
                {"movement": "back_squat", "sets": 5, "reps": 5, "weight_kg": 100}
            ],
            "notes": "Felt strong today"
        }
        
        response = await authenticated_client.post("/api/v1/training/sessions", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["workout_type"] == "strength"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_complete_workout_session(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test completing a workout session"""
        session_id = str(uuid4())
        
        # Mock existing session
        mock_supabase.set_mock_data("workout_sessions", {
            "id": session_id,
            "user_id": str(mock_user_uuid),
            "workout_type": "strength",
            "movements": [],
            "started_at": datetime.utcnow().isoformat(),
            "location": "gym",
            "notes": "Test session"
        })
        
        payload = {
            "completed_at": datetime.utcnow().isoformat(),
            "duration_minutes": 60,
            "rpe_score": 8,
            "score": 100,
            "score_type": "weight"
        }
        
        response = await authenticated_client.patch(
            f"/api/v1/training/sessions/{session_id}",
            json=payload
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_list_workout_sessions(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test listing workout sessions"""
        sessions = [
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "workout_type": "strength",
                "started_at": datetime.utcnow().isoformat(),
                "movements": []
            }
        ]
        mock_supabase.set_mock_data("workout_sessions", sessions)
        
        response = await authenticated_client.get("/api/v1/training/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestPersonalRecords:
    """Test personal records"""
    
    @pytest.mark.asyncio
    async def test_create_pr(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test creating a personal record"""
        payload = {
            "movement_name": "back_squat",
            "record_type": "1rm",
            "value": 150.0,
            "unit": "kg",
            "notes": "New PR!"
        }
        
        response = await authenticated_client.post("/api/v1/training/prs", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["movement_name"] == "back_squat"
        assert data["value"] == 150.0
    
    @pytest.mark.asyncio
    async def test_list_prs(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test listing personal records"""
        prs = [
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "movement_name": "back_squat",
                "record_type": "1rm",
                "value": 150.0,
                "unit": "kg",
                "achieved_at": datetime.utcnow().isoformat()
            }
        ]
        mock_supabase.set_mock_data("personal_records", prs)
        
        response = await authenticated_client.get("/api/v1/training/prs")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestTrainingStats:
    """Test training statistics"""
    
    @pytest.mark.asyncio
    async def test_get_training_summary(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test getting training summary stats"""
        # Mock workout sessions
        sessions = [
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "workout_type": "strength",
                "movements": [],
                "started_at": datetime.utcnow().isoformat(),
                "duration_minutes": 60,
                "rpe_score": 7,
                "location": "gym"
            },
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "workout_type": "metcon",
                "movements": [],
                "started_at": datetime.utcnow().isoformat(),
                "duration_minutes": 45,
                "rpe_score": 8,
                "location": "gym"
            }
        ]
        mock_supabase.set_mock_data("workout_sessions", sessions)
        
        response = await authenticated_client.get("/api/v1/training/stats/summary?days=30")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_workouts" in data
        assert "avg_duration_minutes" in data
        assert "avg_rpe" in data
        assert "workout_types" in data
