"""
Tests for app/api/v1/diet.py (SQLAlchemy).

The old `scheduled_notifications`-based reminder flow was dropped in the
migration; the `/reminders` endpoint now always returns an empty list.
"""
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.v1.diet import convert_to_24h, extract_pdf_text


# ─────────────────────────────────────────────
# Utility function tests
# ─────────────────────────────────────────────

class TestConvertTo24h:
    def test_pm_conversion(self):
        assert convert_to_24h("2:30pm") == "14:30"

    def test_am_passthrough(self):
        assert convert_to_24h("7:00am") == "07:00"

    def test_noon_stays_12(self):
        assert convert_to_24h("12:00pm") == "12:00"

    def test_midnight_becomes_zero(self):
        assert convert_to_24h("12:00am") == "00:00"

    def test_no_minutes_defaults_to_00(self):
        assert convert_to_24h("9am") == "09:00"

    def test_invalid_format_returns_original(self):
        assert convert_to_24h("morning") == "morning"

    def test_1pm_becomes_13(self):
        assert convert_to_24h("1:00pm") == "13:00"

    def test_uppercase_am_pm(self):
        assert convert_to_24h("3:00PM") == "15:00"


class TestExtractPdfText:
    def test_no_pdf_library_returns_empty(self):
        with patch.dict("sys.modules", {"pdfplumber": None, "fitz": None}):
            result = extract_pdf_text(b"fake pdf content")
            assert isinstance(result, str)

    def test_returns_string(self):
        result = extract_pdf_text(b"%PDF-1.4 fake content")
        assert isinstance(result, str)


# ─────────────────────────────────────────────
# Endpoint tests using db_session + seeded_user
# ─────────────────────────────────────────────

class TestGetCurrentDietPlan:
    @pytest.mark.asyncio
    async def test_no_plan_returns_has_plan_false(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        response = await authenticated_client.get("/api/v1/diet/current")
        assert response.status_code == 200
        assert response.json()["has_plan"] is False

    @pytest.mark.asyncio
    async def test_with_plan_returns_has_plan_true(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        from app.db.models import UserDietPlan

        db_session.add(UserDietPlan(
            user_id=seeded_user.id,
            file_name="diet.pdf",
            daily_calories=2500,
            protein_g=160,
            carbs_g=300,
            fat_g=80,
            meals=[{"name": "breakfast", "time": "08:00", "foods": ["oatmeal", "banana"], "calories": 350}],
            supplements=["whey", "creatine", "omega3", "vitD", "magnesium", "zinc"],
            notes="Drink lots of water",
            active=True,
        ))
        db_session.commit()

        response = await authenticated_client.get("/api/v1/diet/current")
        assert response.status_code == 200
        data = response.json()
        assert data["has_plan"] is True
        assert data["plan"]["daily_calories"] == 2500
        assert len(data["plan"]["supplements"]) <= 5  # capped

    @pytest.mark.asyncio
    async def test_meal_formatting(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        from app.db.models import UserDietPlan

        db_session.add(UserDietPlan(
            user_id=seeded_user.id,
            file_name="diet.pdf",
            daily_calories=2200,
            meals=[{
                "name": "pre_workout",
                "time": "17:00",
                "foods": ["banana", "oat", "peanut_butter", "extra1", "extra2"],
                "calories": 300,
            }],
            active=True,
        ))
        db_session.commit()

        response = await authenticated_client.get("/api/v1/diet/current")
        data = response.json()
        meal = data["plan"]["meals"][0]
        assert "_" not in meal["name"]  # title-cased
        assert len(meal["foods"]) <= 3   # capped


class TestDeleteDietPlan:
    @pytest.mark.asyncio
    async def test_delete_returns_success(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        from app.db.models import UserDietPlan
        db_session.add(UserDietPlan(user_id=seeded_user.id, file_name="x.pdf", active=True))
        db_session.commit()

        response = await authenticated_client.delete("/api/v1/diet/current")
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_delete_message(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        response = await authenticated_client.delete("/api/v1/diet/current")
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()


class TestGetDietReminders:
    @pytest.mark.asyncio
    async def test_returns_empty_list(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        response = await authenticated_client.get("/api/v1/diet/reminders")
        assert response.status_code == 200
        assert response.json() == {"reminders": []}
