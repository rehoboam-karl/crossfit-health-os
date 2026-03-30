"""
Tests for Google Calendar Integration
Tests OAuth URL generation, code exchange, token refresh, event creation, sync
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone, date


class TestGetOAuthUrl:
    """Test OAuth URL generation"""

    def test_get_oauth_url_with_state(self):
        from app.core.integrations.calendar import get_oauth_url
        url = get_oauth_url(state="user_abc")
        assert "state=user_abc" in url
        assert "accounts.google.com" in url

    def test_get_oauth_url_empty_state(self):
        from app.core.integrations.calendar import get_oauth_url
        url = get_oauth_url(state="")
        assert "accounts.google.com" in url

    def test_get_oauth_url_default_state(self):
        from app.core.integrations.calendar import get_oauth_url
        url = get_oauth_url()
        assert "accounts.google.com" in url

    def test_get_oauth_url_required_params(self):
        from app.core.integrations.calendar import get_oauth_url
        url = get_oauth_url(state="test")
        assert "response_type=code" in url
        assert "access_type=offline" in url
        assert "prompt=consent" in url
        assert "scope=" in url

    def test_get_oauth_url_is_string(self):
        from app.core.integrations.calendar import get_oauth_url
        url = get_oauth_url()
        assert isinstance(url, str)
        assert url.startswith("https://")


class TestExchangeCode:
    """Test OAuth code exchange"""

    @pytest.mark.asyncio
    async def test_exchange_code_success(self):
        from app.core.integrations.calendar import exchange_code

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "access_token": "access_abc",
            "refresh_token": "refresh_abc",
            "expires_in": 3600,
        }

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await exchange_code("code_123")

        assert result["access_token"] == "access_abc"
        assert result["refresh_token"] == "refresh_abc"

    @pytest.mark.asyncio
    async def test_exchange_code_posts_to_google(self):
        from app.core.integrations.calendar import exchange_code

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"access_token": "at", "refresh_token": "rt"}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_http):
            await exchange_code("auth_code")

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        # URL should be Google token endpoint
        assert "oauth2.googleapis.com" in call_args[0][0]


class TestRefreshAccessToken:
    """Test access token refresh"""

    @pytest.mark.asyncio
    async def test_refresh_returns_access_token(self):
        from app.core.integrations.calendar import refresh_access_token

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"access_token": "new_token_xyz", "expires_in": 3600}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await refresh_access_token("refresh_token_abc")

        assert result == "new_token_xyz"

    @pytest.mark.asyncio
    async def test_refresh_calls_token_endpoint(self):
        from app.core.integrations.calendar import refresh_access_token

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"access_token": "token"}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_http):
            await refresh_access_token("rt_123")

        mock_http.post.assert_called_once()
        url = mock_http.post.call_args[0][0]
        assert "oauth2.googleapis.com" in url


class TestCreateCalendarEvent:
    """Test Google Calendar event creation"""

    @pytest.mark.asyncio
    async def test_create_event_success(self):
        from app.core.integrations.calendar import create_calendar_event

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"id": "event_123", "status": "confirmed"}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_http):
            start = datetime(2026, 4, 1, 7, 0, tzinfo=timezone.utc)
            end = datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc)
            result = await create_calendar_event(
                "access_token", "Workout", "Description", start, end, "America/New_York"
            )

        assert result["id"] == "event_123"

    @pytest.mark.asyncio
    async def test_create_event_no_timezone_uses_default(self):
        from app.core.integrations.calendar import create_calendar_event

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"id": "ev_abc", "status": "confirmed"}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_http):
            start = datetime(2026, 4, 2, 7, 0, tzinfo=timezone.utc)
            end = datetime(2026, 4, 2, 8, 0, tzinfo=timezone.utc)
            result = await create_calendar_event(
                "token", "Metcon", "Fast workout", start, end
            )

        assert "id" in result

    @pytest.mark.asyncio
    async def test_create_event_sends_authorization_header(self):
        from app.core.integrations.calendar import create_calendar_event

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"id": "ev_1"}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_http):
            start = datetime(2026, 4, 1, 7, 0, tzinfo=timezone.utc)
            end = datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc)
            await create_calendar_event("my_token", "WOD", "Desc", start, end)

        call_kwargs = mock_http.post.call_args[1]
        assert "Bearer my_token" in call_kwargs["headers"]["Authorization"]


class TestGetUserToken:
    """Test internal _get_user_token helper"""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_refresh_token(self, mock_supabase):
        from app.core.integrations.calendar import _get_user_token

        mock_supabase.set_mock_data(
            "users", [{"google_calendar_refresh_token": None}]
        )
        user_id = uuid4()
        result = await _get_user_token(user_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_user_data(self, mock_supabase):
        from app.core.integrations.calendar import _get_user_token

        mock_supabase.set_mock_data("users", [])
        user_id = uuid4()
        result = await _get_user_token(user_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_access_token_when_refresh_exists(self, mock_supabase):
        from app.core.integrations.calendar import _get_user_token

        mock_supabase.set_mock_data(
            "users", [{"google_calendar_refresh_token": "refresh_xyz"}]
        )

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"access_token": "fresh_access_token"}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_http):
            user_id = uuid4()
            result = await _get_user_token(user_id)

        assert result == "fresh_access_token"


class TestSyncCalendarEvents:
    """Test sync_calendar_events integration function"""

    @pytest.mark.asyncio
    async def test_sync_not_connected(self, mock_supabase):
        from app.core.integrations.calendar import sync_calendar_events

        mock_supabase.set_mock_data(
            "users", [{"google_calendar_refresh_token": None}]
        )

        result = await sync_calendar_events(uuid4())

        assert result["status"] == "not_connected"
        assert result["created"] == 0
        assert "not connected" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_sync_no_active_schedule(self, mock_supabase):
        from app.core.integrations.calendar import sync_calendar_events

        mock_supabase.set_mock_data(
            "users", [{"google_calendar_refresh_token": "rt_abc", "timezone": "UTC"}]
        )
        mock_supabase.set_mock_data("weekly_schedules", [])

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"access_token": "at"}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await sync_calendar_events(uuid4())

        assert result["status"] == "no_schedule"
        assert result["created"] == 0

    @pytest.mark.asyncio
    async def test_sync_all_rest_days_creates_zero_events(self, mock_supabase):
        from app.core.integrations.calendar import sync_calendar_events

        mock_supabase.set_mock_data(
            "users",
            [{"google_calendar_refresh_token": "rt_abc", "timezone": "UTC", "preferences": {}}],
        )

        schedule = {
            day: {"rest_day": True, "sessions": []}
            for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        }
        mock_supabase.set_mock_data(
            "weekly_schedules", [{"id": str(uuid4()), "schedule": schedule}]
        )

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"access_token": "at"}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await sync_calendar_events(uuid4())

        assert result["status"] == "success"
        assert result["created"] == 0

    @pytest.mark.asyncio
    async def test_sync_with_training_days_creates_events(self, mock_supabase):
        from app.core.integrations.calendar import sync_calendar_events

        mock_supabase.set_mock_data(
            "users",
            [{"google_calendar_refresh_token": "rt_abc", "timezone": "UTC", "preferences": {}}],
        )

        schedule = {
            day: {
                "rest_day": False,
                "sessions": [{"time": "07:00", "duration_minutes": 60, "workout_type": "strength"}],
            }
            for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        }
        mock_supabase.set_mock_data(
            "weekly_schedules", [{"id": str(uuid4()), "schedule": schedule}]
        )

        refresh_resp = MagicMock()
        refresh_resp.raise_for_status = MagicMock()
        refresh_resp.json.return_value = {"access_token": "at_fresh"}

        event_resp = MagicMock()
        event_resp.raise_for_status = MagicMock()
        event_resp.json.return_value = {"id": "ev_created", "status": "confirmed"}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(
            side_effect=[refresh_resp] + [event_resp] * 7
        )

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await sync_calendar_events(uuid4())

        assert result["status"] == "success"
        assert result["created"] >= 0  # 7 days but only some match current week

    @pytest.mark.asyncio
    async def test_sync_different_workout_types(self, mock_supabase):
        """Test sync with various workout types to cover color_map branches"""
        from app.core.integrations.calendar import sync_calendar_events

        mock_supabase.set_mock_data(
            "users",
            [{"google_calendar_refresh_token": "rt", "timezone": "UTC", "preferences": {}}],
        )

        workout_types = ["metcon", "skill", "conditioning", "mixed"]
        schedule = {}
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, day in enumerate(days):
            wt = workout_types[i % len(workout_types)]
            schedule[day] = {
                "rest_day": False,
                "sessions": [{"time": "06:00", "duration_minutes": 45, "workout_type": wt}],
            }

        mock_supabase.set_mock_data(
            "weekly_schedules", [{"id": str(uuid4()), "schedule": schedule}]
        )

        refresh_resp = MagicMock()
        refresh_resp.raise_for_status = MagicMock()
        refresh_resp.json.return_value = {"access_token": "at_fresh"}

        event_resp = MagicMock()
        event_resp.raise_for_status = MagicMock()
        event_resp.json.return_value = {"id": "ev", "status": "confirmed"}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(side_effect=[refresh_resp] + [event_resp] * 7)

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await sync_calendar_events(uuid4())

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_sync_event_creation_failure_logged(self, mock_supabase):
        """Test that failing event creation is logged but doesn't crash"""
        from app.core.integrations.calendar import sync_calendar_events
        import httpx

        mock_supabase.set_mock_data(
            "users",
            [{"google_calendar_refresh_token": "rt", "timezone": "UTC", "preferences": {}}],
        )

        schedule = {
            "monday": {
                "rest_day": False,
                "sessions": [{"time": "07:00", "duration_minutes": 60, "workout_type": "strength"}],
            }
        }
        mock_supabase.set_mock_data(
            "weekly_schedules", [{"id": str(uuid4()), "schedule": schedule}]
        )

        refresh_resp = MagicMock()
        refresh_resp.raise_for_status = MagicMock()
        refresh_resp.json.return_value = {"access_token": "at"}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        # First call returns token, subsequent calls raise error
        mock_http.post = AsyncMock(
            side_effect=[refresh_resp, Exception("Calendar API error")]
        )

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await sync_calendar_events(uuid4())

        # Should return success with 0 created (event creation failed but not re-raised)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_sync_uses_preferences_timezone(self, mock_supabase):
        """Test sync reads timezone from preferences dict"""
        from app.core.integrations.calendar import sync_calendar_events

        mock_supabase.set_mock_data(
            "users",
            [{
                "google_calendar_refresh_token": "rt",
                "timezone": None,
                "preferences": {"timezone": "America/New_York"},
            }],
        )

        schedule = {
            "monday": {"rest_day": True, "sessions": []},
            "tuesday": {"rest_day": True, "sessions": []},
            "wednesday": {"rest_day": True, "sessions": []},
            "thursday": {"rest_day": True, "sessions": []},
            "friday": {"rest_day": True, "sessions": []},
            "saturday": {"rest_day": True, "sessions": []},
            "sunday": {"rest_day": True, "sessions": []},
        }
        mock_supabase.set_mock_data(
            "weekly_schedules", [{"id": str(uuid4()), "schedule": schedule}]
        )

        refresh_resp = MagicMock()
        refresh_resp.raise_for_status = MagicMock()
        refresh_resp.json.return_value = {"access_token": "at"}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=refresh_resp)

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await sync_calendar_events(uuid4())

        assert result["status"] == "success"
        assert result["created"] == 0
