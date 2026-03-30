"""
Tests for Integrations API endpoints
Tests HealthKit sync, Google Calendar OAuth and sync
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4


class TestHealthKitSync:
    """Test HealthKit sync endpoint"""

    @pytest.mark.asyncio
    async def test_sync_healthkit_success(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test successful HealthKit data sync"""
        data = {
            "hrv": [{"timestamp": "2026-03-30T07:00:00Z", "value": 65}],
            "sleep": [{"start": "2026-03-29T23:00:00Z", "end": "2026-03-30T07:00:00Z", "quality": 80}],
        }

        with patch(
            "app.api.v1.integrations.sync_healthkit_data",
            new_callable=AsyncMock,
            return_value={"count": 5},
        ):
            response = await authenticated_client.post(
                "/api/v1/integrations/healthkit/sync", json=data
            )

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert result["records_synced"] == 5

    @pytest.mark.asyncio
    async def test_sync_healthkit_empty_data(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test HealthKit sync with empty data dict"""
        with patch(
            "app.api.v1.integrations.sync_healthkit_data",
            new_callable=AsyncMock,
            return_value={"count": 0},
        ):
            response = await authenticated_client.post(
                "/api/v1/integrations/healthkit/sync", json={}
            )

        assert response.status_code == 200
        result = response.json()
        assert result["records_synced"] == 0

    @pytest.mark.asyncio
    async def test_sync_healthkit_missing_count_in_result(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test HealthKit sync when result has no count key"""
        with patch(
            "app.api.v1.integrations.sync_healthkit_data",
            new_callable=AsyncMock,
            return_value={},
        ):
            response = await authenticated_client.post(
                "/api/v1/integrations/healthkit/sync", json={"hrv": []}
            )

        assert response.status_code == 200
        # Should default to 0
        assert response.json()["records_synced"] == 0


class TestCalendarOAuthUrl:
    """Test GET /calendar/oauth/url"""

    @pytest.mark.asyncio
    async def test_get_oauth_url_returns_auth_url(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user
    ):
        """Test OAuth URL endpoint returns a URL"""
        response = await authenticated_client.get("/api/v1/integrations/calendar/oauth/url")

        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        assert isinstance(data["auth_url"], str)
        assert "accounts.google.com" in data["auth_url"]

    @pytest.mark.asyncio
    async def test_get_oauth_url_contains_user_state(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user
    ):
        """Test OAuth URL contains user ID as state"""
        response = await authenticated_client.get("/api/v1/integrations/calendar/oauth/url")

        assert response.status_code == 200
        url = response.json()["auth_url"]
        assert mock_user["id"] in url


class TestCalendarOAuthCallback:
    """Test GET /calendar/oauth/callback"""

    @pytest.mark.asyncio
    async def test_callback_with_error_redirects(self, async_client: AsyncClient):
        """Test OAuth error redirects to profile error page"""
        response = await async_client.get(
            "/api/v1/integrations/calendar/oauth/callback?error=access_denied",
            follow_redirects=False,
        )
        assert response.status_code in [302, 307]
        assert "calendar=error" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_callback_missing_code_returns_400(self, async_client: AsyncClient):
        """Test callback without code returns 400"""
        response = await async_client.get(
            "/api/v1/integrations/calendar/oauth/callback?state=user123",
        )
        assert response.status_code == 400
        assert "Missing" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_callback_missing_state_returns_400(self, async_client: AsyncClient):
        """Test callback without state returns 400"""
        response = await async_client.get(
            "/api/v1/integrations/calendar/oauth/callback?code=auth_code_abc",
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_callback_success_stores_refresh_token(
        self, async_client: AsyncClient, mock_supabase
    ):
        """Test successful callback stores refresh token and redirects"""
        tokens = {"access_token": "at_abc", "refresh_token": "rt_xyz"}

        with patch(
            "app.api.v1.integrations.exchange_code",
            new_callable=AsyncMock,
            return_value=tokens,
        ):
            response = await async_client.get(
                "/api/v1/integrations/calendar/oauth/callback?code=auth_code&state=user123",
                follow_redirects=False,
            )

        assert response.status_code in [302, 307]
        assert "calendar=connected" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_callback_no_refresh_token_still_redirects(
        self, async_client: AsyncClient, mock_supabase
    ):
        """Test callback when response has no refresh_token still succeeds"""
        tokens = {"access_token": "at_abc"}  # No refresh_token

        with patch(
            "app.api.v1.integrations.exchange_code",
            new_callable=AsyncMock,
            return_value=tokens,
        ):
            response = await async_client.get(
                "/api/v1/integrations/calendar/oauth/callback?code=auth_code&state=user123",
                follow_redirects=False,
            )

        assert response.status_code in [302, 307]
        assert "calendar=connected" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_callback_exchange_failure_redirects_error(
        self, async_client: AsyncClient, mock_supabase
    ):
        """Test callback handles exchange failure gracefully"""
        with patch(
            "app.api.v1.integrations.exchange_code",
            new_callable=AsyncMock,
            side_effect=Exception("Token exchange failed"),
        ):
            response = await async_client.get(
                "/api/v1/integrations/calendar/oauth/callback?code=bad_code&state=user123",
                follow_redirects=False,
            )

        assert response.status_code in [302, 307]
        assert "calendar=error" in response.headers.get("location", "")


class TestCalendarSync:
    """Test POST /calendar/sync"""

    @pytest.mark.asyncio
    async def test_sync_not_connected_returns_400(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test sync when calendar not connected returns 400"""
        with patch(
            "app.api.v1.integrations.sync_calendar_events",
            new_callable=AsyncMock,
            return_value={"status": "not_connected", "created": 0, "message": "Google Calendar not connected"},
        ):
            response = await authenticated_client.post("/api/v1/integrations/calendar/sync")

        assert response.status_code == 400
        assert "not connected" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_sync_success_returns_event_count(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test successful calendar sync returns event count"""
        with patch(
            "app.api.v1.integrations.sync_calendar_events",
            new_callable=AsyncMock,
            return_value={"status": "success", "created": 5},
        ):
            response = await authenticated_client.post("/api/v1/integrations/calendar/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["events_created"] == 5

    @pytest.mark.asyncio
    async def test_sync_zero_events_created(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test sync with zero events (all rest days) returns success"""
        with patch(
            "app.api.v1.integrations.sync_calendar_events",
            new_callable=AsyncMock,
            return_value={"status": "success", "created": 0},
        ):
            response = await authenticated_client.post("/api/v1/integrations/calendar/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["events_created"] == 0


class TestCalendarDisconnect:
    """Test DELETE /calendar/disconnect"""

    @pytest.mark.asyncio
    async def test_disconnect_returns_success(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test calendar disconnect clears refresh token"""
        response = await authenticated_client.delete("/api/v1/integrations/calendar/disconnect")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "disconnected" in data["message"].lower()
