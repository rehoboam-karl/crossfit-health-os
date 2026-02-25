"""
Tests for Nutrition API
Tests meal logging and macro tracking
"""
import pytest
from httpx import AsyncClient
from datetime import datetime
from uuid import uuid4


class TestMealLogging:
    """Test meal logging functionality"""
    
    @pytest.mark.asyncio
    async def test_log_meal(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test logging a meal"""
        payload = {
            "meal_type": "breakfast",
            "logged_at": datetime.utcnow().isoformat(),
            "description": "Oatmeal with berries",
            "calories": 350,
            "protein_g": 12,
            "carbs_g": 55,
            "fat_g": 8
        }
        
        response = await authenticated_client.post("/api/v1/nutrition/meals", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data or data != {}  # Should return created meal
    
    @pytest.mark.asyncio
    async def test_get_todays_meals(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test getting today's meals"""
        meals = [
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "meal_type": "breakfast",
                "logged_at": datetime.utcnow().isoformat(),
                "calories": 350,
                "protein_g": 12,
                "carbs_g": 55,
                "fat_g": 8
            },
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "meal_type": "lunch",
                "logged_at": datetime.utcnow().isoformat(),
                "calories": 600,
                "protein_g": 45,
                "carbs_g": 50,
                "fat_g": 20
            }
        ]
        mock_supabase.set_mock_data("meal_logs", meals)
        
        response = await authenticated_client.get("/api/v1/nutrition/meals/today")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_todays_meals_empty(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test getting today's meals when none logged"""
        mock_supabase.set_mock_data("meal_logs", [])
        
        response = await authenticated_client.get("/api/v1/nutrition/meals/today")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestMacroSummary:
    """Test macro tracking summary"""
    
    @pytest.mark.asyncio
    async def test_get_macro_summary(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test getting today's macro summary"""
        meals = [
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "calories": 350,
                "protein_g": 12,
                "carbs_g": 55,
                "fat_g": 8
            },
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "calories": 600,
                "protein_g": 45,
                "carbs_g": 50,
                "fat_g": 20
            }
        ]
        mock_supabase.set_mock_data("meal_logs", meals)
        
        response = await authenticated_client.get("/api/v1/nutrition/macros/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should sum all meals
        assert data["calories"] == 950
        assert data["protein_g"] == 57
        assert data["carbs_g"] == 105
        assert data["fat_g"] == 28
        assert data["meals_logged"] == 2
    
    @pytest.mark.asyncio
    async def test_get_macro_summary_no_meals(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test macro summary with no meals logged"""
        mock_supabase.set_mock_data("meal_logs", [])
        
        response = await authenticated_client.get("/api/v1/nutrition/macros/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return zeros
        assert data["calories"] == 0
        assert data["protein_g"] == 0
        assert data["carbs_g"] == 0
        assert data["fat_g"] == 0
        assert data["meals_logged"] == 0
    
    @pytest.mark.asyncio
    async def test_get_macro_summary_partial_data(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test macro summary with meals missing some macro data"""
        meals = [
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "calories": 350,
                "protein_g": None,  # Missing protein
                "carbs_g": 55,
                "fat_g": 8
            }
        ]
        mock_supabase.set_mock_data("meal_logs", meals)
        
        response = await authenticated_client.get("/api/v1/nutrition/macros/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle None values
        assert data["calories"] == 350
        assert data["protein_g"] == 0  # None treated as 0
        assert data["carbs_g"] == 55
