"""
Tests for Onboarding API
Tests complete onboarding flow, progress tracking, suggestions
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
from uuid import uuid4


@pytest.fixture
def mock_onboarding_supabase(mock_supabase):
    """Patch onboarding module's supabase_client with the shared mock"""
    with patch("app.api.v1.onboarding.supabase_client", mock_supabase):
        yield mock_supabase


class TestCompleteOnboarding:
    """Test complete onboarding endpoint"""

    @pytest.mark.asyncio
    async def test_complete_onboarding_success(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test successful onboarding completion"""
        payload = {
            "name": "Test Athlete",
            "fitness_level": "intermediate",
            "primary_goal": "strength",
            "available_days": ["monday", "wednesday", "friday"],
            "preferred_time": "morning",
            "training_duration": 60,
            "methodologies": ["hwpo"],
            "focus_weaknesses": ["snatch"],
            "has_gym_access": True,
            "has_barbell": True,
            "has_rings": False,
            "has_pullup_bar": True,
            "app_focus": "full",
            "nutrition_enabled": True,
        }

        with patch("app.api.v1.onboarding.GamificationService") as mock_gam:
            mock_instance = MagicMock()
            mock_instance.add_xp.return_value = (1, [])
            mock_gam.return_value = mock_instance

            response = await authenticated_client.post(
                "/api/v1/onboarding/complete", json=payload
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["xp_earned"] == 300
        assert data["schedule_created"] is True

    @pytest.mark.asyncio
    async def test_complete_onboarding_with_birth_date_young(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test onboarding with young birth date (high readiness)"""
        payload = {
            "name": "Young Athlete",
            "birth_date": "2004-01-01",
            "fitness_level": "beginner",
            "primary_goal": "conditioning",
            "methodologies": ["comptrain"],
        }

        with patch("app.api.v1.onboarding.GamificationService") as mock_gam:
            mock_instance = MagicMock()
            mock_instance.add_xp.return_value = (1, [])
            mock_gam.return_value = mock_instance

            response = await authenticated_client.post(
                "/api/v1/onboarding/complete", json=payload
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_complete_onboarding_prime_age(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test onboarding with prime age (25-34)"""
        payload = {
            "name": "Prime Athlete",
            "birth_date": "1997-06-15",
            "fitness_level": "intermediate",
            "primary_goal": "both",
            "methodologies": ["hwpo"],
        }

        with patch("app.api.v1.onboarding.GamificationService") as mock_gam:
            mock_instance = MagicMock()
            mock_instance.add_xp.return_value = (2, [])
            mock_gam.return_value = mock_instance

            response = await authenticated_client.post(
                "/api/v1/onboarding/complete", json=payload
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_complete_onboarding_mid_age(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test onboarding with mid-age athlete (35-44)"""
        payload = {
            "name": "Mid Age Athlete",
            "birth_date": "1987-03-10",
            "fitness_level": "advanced",
            "primary_goal": "health",
            "methodologies": ["mayhem"],
        }

        with patch("app.api.v1.onboarding.GamificationService") as mock_gam:
            mock_instance = MagicMock()
            mock_instance.add_xp.return_value = (1, [])
            mock_gam.return_value = mock_instance

            response = await authenticated_client.post(
                "/api/v1/onboarding/complete", json=payload
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_complete_onboarding_older_athlete(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test onboarding with older athlete (45+)"""
        payload = {
            "name": "Veteran Athlete",
            "birth_date": "1975-01-01",
            "fitness_level": "intermediate",
            "primary_goal": "health",
            "methodologies": ["hwpo"],
        }

        with patch("app.api.v1.onboarding.GamificationService") as mock_gam:
            mock_instance = MagicMock()
            mock_instance.add_xp.return_value = (1, [])
            mock_gam.return_value = mock_instance

            response = await authenticated_client.post(
                "/api/v1/onboarding/complete", json=payload
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_complete_onboarding_empty_methodologies(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test onboarding with empty methodologies → custom"""
        payload = {
            "name": "Custom Athlete",
            "fitness_level": "athlete",
            "primary_goal": "both",
            "methodologies": [],
        }

        with patch("app.api.v1.onboarding.GamificationService") as mock_gam:
            mock_instance = MagicMock()
            mock_instance.add_xp.return_value = (1, [])
            mock_gam.return_value = mock_instance

            response = await authenticated_client.post(
                "/api/v1/onboarding/complete", json=payload
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_complete_onboarding_afternoon_time(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test onboarding with afternoon preferred time"""
        payload = {
            "name": "Afternoon Athlete",
            "fitness_level": "intermediate",
            "primary_goal": "health",
            "preferred_time": "afternoon",
            "methodologies": ["mayhem"],
        }

        with patch("app.api.v1.onboarding.GamificationService") as mock_gam:
            mock_instance = MagicMock()
            mock_instance.add_xp.return_value = (1, [])
            mock_gam.return_value = mock_instance

            response = await authenticated_client.post(
                "/api/v1/onboarding/complete", json=payload
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_complete_onboarding_evening_time(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test onboarding with evening preferred time"""
        payload = {
            "name": "Evening Athlete",
            "fitness_level": "beginner",
            "primary_goal": "strength",
            "preferred_time": "evening",
            "methodologies": ["hwpo"],
        }

        with patch("app.api.v1.onboarding.GamificationService") as mock_gam:
            mock_instance = MagicMock()
            mock_instance.add_xp.return_value = (1, [])
            mock_gam.return_value = mock_instance

            response = await authenticated_client.post(
                "/api/v1/onboarding/complete", json=payload
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_complete_onboarding_all_days(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test onboarding with all seven days selected"""
        payload = {
            "name": "Daily Athlete",
            "fitness_level": "athlete",
            "primary_goal": "both",
            "available_days": [
                "monday", "tuesday", "wednesday", "thursday",
                "friday", "saturday", "sunday",
            ],
            "methodologies": ["hwpo"],
        }

        with patch("app.api.v1.onboarding.GamificationService") as mock_gam:
            mock_instance = MagicMock()
            mock_instance.add_xp.return_value = (3, [])
            mock_gam.return_value = mock_instance

            response = await authenticated_client.post(
                "/api/v1/onboarding/complete", json=payload
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_complete_onboarding_no_days(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test onboarding with no training days (all rest days)"""
        payload = {
            "name": "Rest Athlete",
            "fitness_level": "beginner",
            "primary_goal": "health",
            "available_days": [],
            "methodologies": ["hwpo"],
        }

        with patch("app.api.v1.onboarding.GamificationService") as mock_gam:
            mock_instance = MagicMock()
            mock_instance.add_xp.return_value = (1, [])
            mock_gam.return_value = mock_instance

            response = await authenticated_client.post(
                "/api/v1/onboarding/complete", json=payload
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_complete_onboarding_with_weight_height(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test onboarding with weight and height data"""
        payload = {
            "name": "Measured Athlete",
            "fitness_level": "intermediate",
            "primary_goal": "strength",
            "weight_kg": 85.5,
            "height_cm": 182.0,
            "methodologies": ["hwpo"],
        }

        with patch("app.api.v1.onboarding.GamificationService") as mock_gam:
            mock_instance = MagicMock()
            mock_instance.add_xp.return_value = (1, [])
            mock_gam.return_value = mock_instance

            response = await authenticated_client.post(
                "/api/v1/onboarding/complete", json=payload
            )

        assert response.status_code == 200
        data = response.json()
        assert data["profile"]["weight_kg"] == 85.5


class TestOnboardingProgress:
    """Test onboarding progress endpoint"""

    @pytest.mark.asyncio
    async def test_get_progress_initial(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test progress for new user (nothing completed)"""
        mock_onboarding_supabase.set_mock_data(
            "users", [{"onboarding_completed": False, "name": "Test"}]
        )
        mock_onboarding_supabase.set_mock_data("weekly_schedules", [])
        mock_onboarding_supabase.set_mock_data("workout_sessions", [])

        response = await authenticated_client.get("/api/v1/onboarding/progress")

        assert response.status_code == 200
        data = response.json()
        assert data["total_steps"] == 5
        assert data["step"] == 1
        assert data["profile_complete"] is False
        assert data["schedule_created"] is False
        assert data["first_workout_done"] is False

    @pytest.mark.asyncio
    async def test_get_progress_profile_complete(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test progress when profile is completed"""
        mock_onboarding_supabase.set_mock_data(
            "users", [{"onboarding_completed": True, "name": "Test"}]
        )
        mock_onboarding_supabase.set_mock_data("weekly_schedules", [])
        mock_onboarding_supabase.set_mock_data("workout_sessions", [])

        response = await authenticated_client.get("/api/v1/onboarding/progress")

        assert response.status_code == 200
        data = response.json()
        assert data["profile_complete"] is True
        assert data["step"] >= 2

    @pytest.mark.asyncio
    async def test_get_progress_with_schedule(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test progress when schedule is also created"""
        mock_onboarding_supabase.set_mock_data(
            "users", [{"onboarding_completed": True, "name": "Test"}]
        )
        mock_onboarding_supabase.set_mock_data(
            "weekly_schedules", [{"id": str(uuid4())}]
        )
        mock_onboarding_supabase.set_mock_data("workout_sessions", [])

        response = await authenticated_client.get("/api/v1/onboarding/progress")

        assert response.status_code == 200
        data = response.json()
        assert data["schedule_created"] is True
        assert data["step"] >= 3

    @pytest.mark.asyncio
    async def test_get_progress_fully_complete(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test progress fully complete (first workout done)"""
        mock_onboarding_supabase.set_mock_data(
            "users", [{"onboarding_completed": True, "name": "Test"}]
        )
        mock_onboarding_supabase.set_mock_data(
            "weekly_schedules", [{"id": str(uuid4())}]
        )
        mock_onboarding_supabase.set_mock_data(
            "workout_sessions", [{"id": str(uuid4())}]
        )

        response = await authenticated_client.get("/api/v1/onboarding/progress")

        assert response.status_code == 200
        data = response.json()
        assert data["first_workout_done"] is True
        assert data["completed"] is True
        assert data["step"] == 5

    @pytest.mark.asyncio
    async def test_get_progress_handles_db_error(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test progress returns safe defaults on error"""
        # Don't set mock data — causes exception in endpoint
        # The endpoint has a broad except that returns defaults
        response = await authenticated_client.get("/api/v1/onboarding/progress")

        assert response.status_code == 200
        data = response.json()
        assert "step" in data
        assert "total_steps" in data


class TestOnboardingSuggestions:
    """Test onboarding suggestions endpoint"""

    @pytest.mark.asyncio
    async def test_get_suggestions_beginner_strength(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase, mock_user
    ):
        """Test suggestions for beginner with strength goal"""
        mock_onboarding_supabase.set_mock_data(
            "users",
            [{"id": mock_user["id"], "fitness_level": "beginner", "primary_goal": "strength"}],
        )

        response = await authenticated_client.get("/api/v1/onboarding/suggestions")

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) > 0
        # Beginner gets recovery tip
        types = [s.get("type") for s in data["suggestions"]]
        assert "tip" in types

    @pytest.mark.asyncio
    async def test_get_suggestions_intermediate_conditioning(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase, mock_user
    ):
        """Test suggestions for intermediate with conditioning goal"""
        mock_onboarding_supabase.set_mock_data(
            "users",
            [{"id": mock_user["id"], "fitness_level": "intermediate", "primary_goal": "conditioning"}],
        )

        response = await authenticated_client.get("/api/v1/onboarding/suggestions")

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        titles = [s["title"] for s in data["suggestions"]]
        assert any("Engine" in t or "Conditioning" in t or "Track" in t for t in titles)

    @pytest.mark.asyncio
    async def test_get_suggestions_advanced_strength(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase, mock_user
    ):
        """Test suggestions for advanced user with strength goal"""
        mock_onboarding_supabase.set_mock_data(
            "users",
            [{"id": mock_user["id"], "fitness_level": "advanced", "primary_goal": "strength"}],
        )

        response = await authenticated_client.get("/api/v1/onboarding/suggestions")

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        # Should contain "Compound Movements" tip and "Track Everything"
        titles = [s["title"] for s in data["suggestions"]]
        assert "Track Everything" in titles

    @pytest.mark.asyncio
    async def test_get_suggestions_user_not_found(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase
    ):
        """Test suggestions when user not found returns empty list"""
        mock_onboarding_supabase.set_mock_data("users", [])

        response = await authenticated_client.get("/api/v1/onboarding/suggestions")

        # Endpoint handles HTTP 404 by raising, or returns empty in outer except
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_suggestions_always_includes_track_tip(
        self, authenticated_client: AsyncClient, mock_onboarding_supabase, mock_user
    ):
        """Test that Track Everything tip is always included"""
        mock_onboarding_supabase.set_mock_data(
            "users",
            [{"id": mock_user["id"], "fitness_level": "athlete", "primary_goal": "both"}],
        )

        response = await authenticated_client.get("/api/v1/onboarding/suggestions")

        assert response.status_code == 200
        data = response.json()
        titles = [s["title"] for s in data["suggestions"]]
        assert "Track Everything" in titles


class TestCalculateReadinessFromAge:
    """Unit tests for helper function"""

    def test_no_birth_date_returns_default(self):
        from app.api.v1.onboarding import calculate_readiness_from_age
        assert calculate_readiness_from_age(None) == 70

    def test_invalid_date_returns_default(self):
        from app.api.v1.onboarding import calculate_readiness_from_age
        assert calculate_readiness_from_age("not-a-date") == 70

    def test_young_athlete_under_25(self):
        from app.api.v1.onboarding import calculate_readiness_from_age
        # 2004 → ~22 years old in 2026
        result = calculate_readiness_from_age("2004-01-01")
        assert result == 85

    def test_prime_age_25_to_34(self):
        from app.api.v1.onboarding import calculate_readiness_from_age
        # 1993 → ~33 years old in 2026
        result = calculate_readiness_from_age("1993-06-01")
        assert result == 75

    def test_mid_age_35_to_44(self):
        from app.api.v1.onboarding import calculate_readiness_from_age
        # 1985 → ~41 years old in 2026
        result = calculate_readiness_from_age("1985-01-01")
        assert result == 65

    def test_older_45_plus(self):
        from app.api.v1.onboarding import calculate_readiness_from_age
        # 1975 → ~51 years old in 2026
        result = calculate_readiness_from_age("1975-01-01")
        assert result == 55
