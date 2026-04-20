"""
Tests for Nutrition API — meal logging and macro tracking (SQLAlchemy).
"""
from datetime import datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestMealLogging:
    @pytest.mark.asyncio
    async def test_log_meal(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        payload = {
            "meal_type": "breakfast",
            "logged_at": datetime.utcnow().isoformat(),
            "description": "Oatmeal with berries",
            "calories": 350,
            "protein_g": 12,
            "carbs_g": 55,
            "fat_g": 8,
        }
        response = await authenticated_client.post("/api/v1/nutrition/meals", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["meal_type"] == "breakfast"
        assert data["calories"] == 350

    @pytest.mark.asyncio
    async def test_get_todays_meals(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        from app.db.models import MealLog
        for meal_type, cal in [("breakfast", 350), ("lunch", 600)]:
            db_session.add(MealLog(
                user_id=seeded_user.id,
                meal_type=meal_type,
                calories=cal,
                protein_g=20,
                carbs_g=40,
                fat_g=10,
            ))
        db_session.commit()

        response = await authenticated_client.get("/api/v1/nutrition/meals/today")
        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.asyncio
    async def test_get_todays_meals_empty(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        response = await authenticated_client.get("/api/v1/nutrition/meals/today")
        assert response.status_code == 200
        assert response.json() == []


class TestMacroSummary:
    @pytest.mark.asyncio
    async def test_get_macro_summary(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        from app.db.models import MealLog
        db_session.add(MealLog(
            user_id=seeded_user.id, calories=350, protein_g=12, carbs_g=55, fat_g=8,
        ))
        db_session.add(MealLog(
            user_id=seeded_user.id, calories=600, protein_g=45, carbs_g=50, fat_g=20,
        ))
        db_session.commit()

        response = await authenticated_client.get("/api/v1/nutrition/macros/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["calories"] == 950
        assert data["protein_g"] == 57
        assert data["carbs_g"] == 105
        assert data["fat_g"] == 28
        assert data["meals_logged"] == 2

    @pytest.mark.asyncio
    async def test_get_macro_summary_no_meals(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        response = await authenticated_client.get("/api/v1/nutrition/macros/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["calories"] == 0
        assert data["meals_logged"] == 0

    @pytest.mark.asyncio
    async def test_get_macro_summary_partial_data(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        from app.db.models import MealLog
        db_session.add(MealLog(
            user_id=seeded_user.id,
            calories=350,
            protein_g=None,  # missing
            carbs_g=55,
            fat_g=8,
        ))
        db_session.commit()

        response = await authenticated_client.get("/api/v1/nutrition/macros/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["calories"] == 350
        assert data["protein_g"] == 0
        assert data["carbs_g"] == 55
