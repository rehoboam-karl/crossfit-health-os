"""
Tests for app/core/auth.py::get_current_user (local JWT + SQLAlchemy).

Covers: valid token, missing/invalid sub, expired/invalid JWT, missing user.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from app.core.auth import get_current_user
from app.core.config import settings
from app.db.models import User


def _make_token(sub: str | int, secret: str | None = None, algorithm: str | None = None) -> str:
    payload = {
        "sub": str(sub),
        "email": "test@example.com",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(
        payload,
        secret or settings.SECRET_KEY,
        algorithm=algorithm or settings.JWT_ALGORITHM,
    )


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self, db_session, seeded_user):
        token = _make_token(seeded_user.id)
        result = await get_current_user(_creds(token), db_session)
        assert result["id"] == seeded_user.id
        assert result["email"] == seeded_user.email

    @pytest.mark.asyncio
    async def test_missing_sub_raises_401(self, db_session, seeded_user):
        payload = {
            "email": "x@y.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        with pytest.raises(HTTPException) as exc:
            await get_current_user(_creds(token), db_session)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_sub_raises_401(self, db_session, seeded_user):
        token = _make_token("not-an-int")
        with pytest.raises(HTTPException) as exc:
            await get_current_user(_creds(token), db_session)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self, db_session, seeded_user):
        payload = {
            "sub": str(seeded_user.id),
            "email": seeded_user.email,
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        with pytest.raises(HTTPException) as exc:
            await get_current_user(_creds(token), db_session)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_tampered_signature_raises_401(self, db_session, seeded_user):
        token = _make_token(seeded_user.id, secret="different-secret")
        with pytest.raises(HTTPException) as exc:
            await get_current_user(_creds(token), db_session)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(self, db_session, seeded_user):
        token = _make_token(seeded_user.id + 999)
        with pytest.raises(HTTPException) as exc:
            await get_current_user(_creds(token), db_session)
        assert exc.value.status_code == 404
