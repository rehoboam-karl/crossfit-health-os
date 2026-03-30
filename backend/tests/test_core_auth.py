"""
Tests for app/core/auth.py - get_current_user function
Tests authentication validation logic.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from uuid import uuid4


@pytest.fixture
def mock_credentials():
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="mock_token_123")


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self, mock_credentials):
        from app.core.auth import get_current_user

        auth_user_id = str(uuid4())
        user_profile = {
            "id": str(uuid4()),
            "auth_user_id": auth_user_id,
            "email": "test@example.com",
            "name": "Test User"
        }

        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = MagicMock(
            user=MagicMock(id=auth_user_id)
        )
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[user_profile]
        )

        with patch("app.core.auth.supabase_client", mock_client):
            result = await get_current_user(mock_credentials)

        assert result["id"] == user_profile["id"]
        assert result["email"] == user_profile["email"]

    @pytest.mark.asyncio
    async def test_no_user_in_auth_response_raises_401(self, mock_credentials):
        from app.core.auth import get_current_user

        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = MagicMock(user=None)

        with patch("app.core.auth.supabase_client", mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_none_auth_response_raises_401(self, mock_credentials):
        from app.core.auth import get_current_user

        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = None

        with patch("app.core.auth.supabase_client", mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_profile_not_found_raises_404(self, mock_credentials):
        from app.core.auth import get_current_user

        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = MagicMock(
            user=MagicMock(id=str(uuid4()))
        )
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        with patch("app.core.auth.supabase_client", mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_jwt_error_raises_401(self, mock_credentials):
        from app.core.auth import get_current_user
        from jose import JWTError

        mock_client = MagicMock()
        mock_client.auth.get_user.side_effect = JWTError("invalid token")

        with patch("app.core.auth.supabase_client", mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_generic_exception_raises_500(self, mock_credentials):
        from app.core.auth import get_current_user

        mock_client = MagicMock()
        mock_client.auth.get_user.side_effect = RuntimeError("unexpected error")

        with patch("app.core.auth.supabase_client", mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)

        assert exc_info.value.status_code == 500
