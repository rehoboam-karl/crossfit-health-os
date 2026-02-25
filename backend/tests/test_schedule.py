"""
Tests for Schedule API
Tests weekly schedule CRUD and AI program generation
"""
import pytest
from httpx import AsyncClient
from datetime import date, time
from uuid import uuid4
from unittest.mock import patch, AsyncMock


class TestWeeklySchedule:
    """Test weekly training schedule CRUD"""
    
    @pytest.mark.asyncio
    async def test_create_weekly_schedule(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test creating a weekly training schedule"""
        payload = {
            "name": "HWPO 5x per week",
            "methodology": "hwpo",
            "schedule": {
                "monday": {
                    "day": "monday",
                    "sessions": [
                        {"time": "06:00:00", "duration_minutes": 90, "workout_type": "strength"}
                    ],
                    "rest_day": False
                },
                "tuesday": {
                    "day": "tuesday",
                    "sessions": [
                        {"time": "06:00:00", "duration_minutes": 60, "workout_type": "metcon"}
                    ],
                    "rest_day": False
                },
                "wednesday": {
                    "day": "wednesday",
                    "sessions": [],
                    "rest_day": True
                },
                "thursday": {
                    "day": "thursday",
                    "sessions": [
                        {"time": "06:00:00", "duration_minutes": 75, "workout_type": "mixed"}
                    ],
                    "rest_day": False
                },
                "friday": {
                    "day": "friday",
                    "sessions": [
                        {"time": "06:00:00", "duration_minutes": 60, "workout_type": "metcon"}
                    ],
                    "rest_day": False
                },
                "saturday": {
                    "day": "saturday",
                    "sessions": [
                        {"time": "09:00:00", "duration_minutes": 90, "workout_type": "mixed"}
                    ],
                    "rest_day": False
                },
                "sunday": {
                    "day": "sunday",
                    "sessions": [],
                    "rest_day": True
                }
            },
            "start_date": "2026-02-10",
            "active": True
        }
        
        response = await authenticated_client.post("/api/v1/schedule/weekly", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "HWPO 5x per week"
        assert data["methodology"] == "hwpo"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_get_active_schedule(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test getting active weekly schedule"""
        from datetime import datetime
        schedule_data = {
            "id": str(uuid4()),
            "user_id": str(mock_user_uuid),
            "name": "Active Schedule",
            "methodology": "hwpo",
            "schedule": {},
            "start_date": "2026-02-01",
            "active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        mock_supabase.set_mock_data("weekly_schedules", [schedule_data])
        
        response = await authenticated_client.get("/api/v1/schedule/weekly/active")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Active Schedule"
        assert data["active"] is True
    
    @pytest.mark.asyncio
    async def test_get_active_schedule_not_found(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test getting active schedule when none exists"""
        mock_supabase.set_mock_data("weekly_schedules", [])
        
        response = await authenticated_client.get("/api/v1/schedule/weekly/active")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_list_schedules(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test listing all schedules"""
        from datetime import datetime
        schedules = [
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "name": "Schedule 1",
                "methodology": "hwpo",
                "schedule": {},
                "start_date": "2026-01-01",
                "active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "name": "Schedule 2",
                "methodology": "mayhem",
                "schedule": {},
                "start_date": "2026-01-15",
                "active": False,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        ]
        mock_supabase.set_mock_data("weekly_schedules", schedules)
        
        response = await authenticated_client.get("/api/v1/schedule/weekly")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
    
    @pytest.mark.asyncio
    async def test_update_schedule(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test updating a weekly schedule"""
        schedule_id = str(uuid4())
        
        # Mock existing schedule
        from datetime import datetime
        mock_supabase.set_mock_data("weekly_schedules", {
            "id": schedule_id,
            "user_id": str(mock_user_uuid),
            "name": "Old Name",
            "methodology": "hwpo",
            "schedule": {},
            "start_date": "2026-02-01",
            "active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        })
        
        update_payload = {
            "name": "Updated Schedule",
            "methodology": "hwpo",
            "schedule": {},
            "start_date": "2026-02-01",
            "active": True
        }
        
        response = await authenticated_client.patch(
            f"/api/v1/schedule/weekly/{schedule_id}",
            json=update_payload
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_delete_schedule(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test deleting a schedule"""
        schedule_id = str(uuid4())
        
        # Mock existing schedule
        mock_supabase.set_mock_data("weekly_schedules", {
            "id": schedule_id,
            "user_id": str(mock_user_uuid),
            "name": "To Delete",
            "methodology": "hwpo",
            "schedule": {},
            "start_date": "2026-02-01",
            "active": False
        })
        
        response = await authenticated_client.delete(f"/api/v1/schedule/weekly/{schedule_id}")
        
        assert response.status_code == 204


class TestMealPlanGeneration:
    """Test automatic meal plan generation from training schedule"""
    
    @pytest.mark.asyncio
    async def test_generate_meal_plan(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test generating meal plan from training schedule"""
        schedule_id = str(uuid4())
        
        # Mock training schedule
        from datetime import datetime
        schedule_data = {
            "id": schedule_id,
            "user_id": str(mock_user_uuid),
            "name": "HWPO Schedule",
            "methodology": "hwpo",
            "schedule": {
                "monday": {
                    "day": "monday",
                    "sessions": [
                        {"time": "06:00:00", "duration_minutes": 90, "workout_type": "strength"}
                    ],
                    "rest_day": False
                },
                "sunday": {
                    "day": "sunday",
                    "sessions": [],
                    "rest_day": True
                }
            },
            "start_date": "2026-02-01",
            "active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        mock_supabase.set_mock_data("weekly_schedules", schedule_data)
        
        response = await authenticated_client.post(
            f"/api/v1/schedule/weekly/{schedule_id}/meal-plan"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "meal_plans" in data
        assert "training_schedule_id" in data
    
    @pytest.mark.asyncio
    async def test_get_meal_plan(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test getting meal plan for a schedule"""
        schedule_id = str(uuid4())
        
        from datetime import datetime
        meal_plan_data = {
            "id": str(uuid4()),
            "user_id": str(mock_user_uuid),
            "training_schedule_id": schedule_id,
            "meal_plans": {},
            "pre_workout_offset_minutes": -60,
            "post_workout_offset_minutes": 30,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        mock_supabase.set_mock_data("weekly_meal_plans", [meal_plan_data])
        
        response = await authenticated_client.get(
            f"/api/v1/schedule/weekly/{schedule_id}/meal-plan"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["training_schedule_id"] == schedule_id


class TestAIProgramGeneration:
    """Test AI-powered weekly program generation"""
    
    @pytest.mark.asyncio
    async def test_generate_ai_program(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid, mock_openai
    ):
        """Test AI program generation with mocked AI"""
        # Mock user profile
        user_data = {
            "id": str(mock_user_uuid),
            "fitness_level": "intermediate",
            "preferences": {"methodology": "hwpo"}
        }
        mock_supabase.set_mock_data("users", user_data)
        
        # Mock active schedule
        from datetime import datetime
        schedule_data = {
            "id": str(uuid4()),
            "user_id": str(mock_user_uuid),
            "name": "Active Schedule",
            "methodology": "hwpo",
            "schedule": {
                "monday": {
                    "day": "monday",
                    "sessions": [{"time": "06:00:00", "duration_minutes": 90}],
                    "rest_day": False
                }
            },
            "start_date": "2026-02-01",
            "active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        mock_supabase.set_mock_data("weekly_schedules", [schedule_data])
        
        # Mock the AI programmer
        with patch("app.api.v1.schedule.ai_programmer.generate_weekly_program", new_callable=AsyncMock) as mock_ai:
            from app.models.training import WorkoutTemplate, Methodology, WorkoutType, DayOfWeek, Movement
            from datetime import datetime
            
            mock_template = WorkoutTemplate(
                id=uuid4(),
                name="AI Generated Workout",
                methodology=Methodology.HWPO,
                difficulty_level="intermediate",
                workout_type=WorkoutType.STRENGTH,
                duration_minutes=90,
                movements=[Movement(movement="squat", sets=5, reps=5)],
                tags=["ai_generated"],
                equipment_required=[],
                created_at=datetime.utcnow(),
                is_public=False
            )
            
            mock_ai.return_value = {
                DayOfWeek.MONDAY: mock_template
            }
            
            payload = {
                "methodology": "hwpo",
                "week_number": 1,
                "focus_movements": ["squat", "deadlift"],
                "include_previous_week": False
            }
            
            response = await authenticated_client.post(
                "/api/v1/schedule/weekly/generate-ai",
                json=payload
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "success"
            assert "workouts" in data
    
    @pytest.mark.asyncio
    async def test_generate_ai_program_no_active_schedule(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test AI generation when no active schedule exists"""
        # Mock user but no active schedule
        user_data = {
            "id": str(mock_user_uuid),
            "fitness_level": "intermediate"
        }
        mock_supabase.set_mock_data("users", user_data)
        mock_supabase.set_mock_data("weekly_schedules", [])
        
        payload = {
            "methodology": "hwpo",
            "week_number": 1
        }
        
        response = await authenticated_client.post(
            "/api/v1/schedule/weekly/generate-ai",
            json=payload
        )
        
        assert response.status_code == 404
        assert "active schedule" in response.json()["detail"].lower()
