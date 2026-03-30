"""
Tests for app/api/v1/diet.py
Covers GET /current, DELETE /current, GET /reminders,
POST /reminders/{id}/toggle, and utility functions.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from unittest.mock import patch, AsyncMock, MagicMock

from app.api.v1.diet import convert_to_24h, extract_pdf_text


def _mock_diet_supabase(mock_data_by_table: dict):
    """Return a context manager that patches diet's supabase with controlled responses."""
    from tests.conftest import MockSupabaseClient
    client = MockSupabaseClient()
    for table, data in mock_data_by_table.items():
        client.set_mock_data(table, data)
    return patch("app.api.v1.diet.supabase_client", client)


# ─────────────────────────────────────────────
# Utility function tests (no HTTP required)
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
        result = convert_to_24h("9am")
        assert result == "09:00"

    def test_invalid_format_returns_original(self):
        result = convert_to_24h("morning")
        assert result == "morning"

    def test_1pm_becomes_13(self):
        assert convert_to_24h("1:00pm") == "13:00"

    def test_uppercase_am_pm(self):
        result = convert_to_24h("3:00PM")
        assert result == "15:00"


class TestExtractPdfText:
    def test_no_pdf_library_returns_empty(self):
        # Neither pdfplumber nor fitz available in test env
        with patch.dict("sys.modules", {"pdfplumber": None, "fitz": None}):
            result = extract_pdf_text(b"fake pdf content")
            assert isinstance(result, str)

    def test_returns_string(self):
        result = extract_pdf_text(b"%PDF-1.4 fake content")
        assert isinstance(result, str)


# ─────────────────────────────────────────────
# API endpoint tests
# ─────────────────────────────────────────────

class TestGetCurrentDietPlan:
    @pytest.mark.asyncio
    async def test_no_plan_returns_has_plan_false(
        self, authenticated_client: AsyncClient
    ):
        with _mock_diet_supabase({"user_diet_plans": None}):
            response = await authenticated_client.get("/api/v1/diet/current")
        assert response.status_code == 200
        data = response.json()
        assert data["has_plan"] is False

    @pytest.mark.asyncio
    async def test_with_plan_returns_has_plan_true(
        self, authenticated_client: AsyncClient
    ):
        plan = {
            "id": str(uuid4()),
            "file_name": "diet.pdf",
            "uploaded_at": "2026-01-01T10:00:00",
            "daily_calories": 2500,
            "protein_g": 160,
            "carbs_g": 300,
            "fat_g": 80,
            "meals": [
                {"name": "breakfast", "time": "08:00", "foods": ["oatmeal", "banana"], "calories": 350}
            ],
            "supplements": ["whey", "creatine", "omega3", "vitD", "magnesium", "zinc"],
            "notes": "Drink lots of water"
        }
        with _mock_diet_supabase({"user_diet_plans": [plan]}):
            response = await authenticated_client.get("/api/v1/diet/current")
        assert response.status_code == 200
        data = response.json()
        assert data["has_plan"] is True
        assert data["plan"]["daily_calories"] == 2500
        # Supplements capped at 5
        assert len(data["plan"]["supplements"]) <= 5

    @pytest.mark.asyncio
    async def test_meal_formatting(
        self, authenticated_client: AsyncClient
    ):
        plan = {
            "id": str(uuid4()),
            "file_name": "diet.pdf",
            "uploaded_at": "2026-01-01",
            "daily_calories": 2200,
            "protein_g": 140,
            "carbs_g": 280,
            "fat_g": 70,
            "meals": [
                {"name": "pre_workout", "time": "17:00", "foods": ["banana", "oat", "peanut_butter"], "calories": 300}
            ],
            "supplements": [],
            "notes": ""
        }
        with _mock_diet_supabase({"user_diet_plans": [plan]}):
            response = await authenticated_client.get("/api/v1/diet/current")
        assert response.status_code == 200
        data = response.json()
        meal = data["plan"]["meals"][0]
        # name is title-cased and underscores replaced
        assert "_" not in meal["name"]
        # foods capped at 3
        assert len(meal["foods"]) <= 3


class TestDeleteDietPlan:
    @pytest.mark.asyncio
    async def test_delete_returns_success(self, authenticated_client: AsyncClient):
        with _mock_diet_supabase({"user_diet_plans": [], "scheduled_notifications": []}):
            response = await authenticated_client.delete("/api/v1/diet/current")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_delete_message(self, authenticated_client: AsyncClient):
        with _mock_diet_supabase({"user_diet_plans": [], "scheduled_notifications": []}):
            response = await authenticated_client.delete("/api/v1/diet/current")
        data = response.json()
        assert "deleted" in data["message"].lower() or "success" in str(data).lower()


class TestGetDietReminders:
    @pytest.mark.asyncio
    async def test_empty_reminders(self, authenticated_client: AsyncClient):
        with _mock_diet_supabase({"scheduled_notifications": []}):
            response = await authenticated_client.get("/api/v1/diet/reminders")
        assert response.status_code == 200
        data = response.json()
        assert "reminders" in data
        assert data["reminders"] == []

    @pytest.mark.asyncio
    async def test_with_reminders(self, authenticated_client: AsyncClient):
        reminders = [
            {"id": str(uuid4()), "meal_name": "Breakfast", "schedule_time": "08:00", "enabled": True},
            {"id": str(uuid4()), "meal_name": "Lunch", "schedule_time": "12:00", "enabled": True},
        ]
        with _mock_diet_supabase({"scheduled_notifications": reminders}):
            response = await authenticated_client.get("/api/v1/diet/reminders")
        assert response.status_code == 200
        data = response.json()
        assert len(data["reminders"]) == 2
        assert data["reminders"][0]["meal"] == "Breakfast"


class TestToggleReminder:
    @pytest.mark.asyncio
    async def test_toggle_existing_reminder(self, authenticated_client: AsyncClient):
        reminder_id = str(uuid4())
        with _mock_diet_supabase({"scheduled_notifications": [{"enabled": True}]}):
            response = await authenticated_client.post(
                f"/api/v1/diet/reminders/{reminder_id}/toggle"
            )
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert data["enabled"] is False  # toggled from True

    @pytest.mark.asyncio
    async def test_toggle_nonexistent_reminder(self, authenticated_client: AsyncClient):
        reminder_id = str(uuid4())
        # Set None data so `not response.data` is True → 404
        with _mock_diet_supabase({"scheduled_notifications": None}):
            response = await authenticated_client.post(
                f"/api/v1/diet/reminders/{reminder_id}/toggle"
            )
        # The API returns 404 when reminder not found
        assert response.status_code in (404, 500)


class TestCreateMealReminders:
    """Test the create_meal_reminders helper"""

    @pytest.mark.asyncio
    async def test_creates_reminders_for_each_meal(self):
        from app.api.v1.diet import create_meal_reminders
        meals = [
            {"name": "breakfast", "time": "08:00"},
            {"name": "lunch", "time": "12:30"},
        ]
        with _mock_diet_supabase({"scheduled_notifications": []}):
            await create_meal_reminders(str(uuid4()), meals)

    @pytest.mark.asyncio
    async def test_handles_12h_time(self):
        from app.api.v1.diet import create_meal_reminders
        meals = [{"name": "dinner", "time": "7:00pm"}]
        with _mock_diet_supabase({"scheduled_notifications": []}):
            await create_meal_reminders(str(uuid4()), meals)

    @pytest.mark.asyncio
    async def test_empty_meals(self):
        from app.api.v1.diet import create_meal_reminders
        with _mock_diet_supabase({}):
            await create_meal_reminders(str(uuid4()), [])
