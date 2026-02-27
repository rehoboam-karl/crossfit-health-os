"""
Tests for Authentication API
Tests registration, login, logout, password reset
"""
import pytest
from httpx import AsyncClient


class TestRegistration:
    """Test user registration"""
    
    @pytest.mark.asyncio
    async def test_register_success(self, async_client: AsyncClient, mock_supabase):
        """Test successful user registration"""
        # Set mock data for user check (no existing user)
        mock_supabase.set_mock_data("users", [])
        
        payload = {
            "email": "newuser@example.com",
            "password": "SecurePass123",
            "confirm_password": "SecurePass123",
            "name": "New Athlete",
            "birth_date": "1995-03-15",
            "weight_kg": 75.0,
            "height_cm": 180.0,
            "fitness_level": "beginner",
            "goals": ["strength"]
        }
        
        response = await async_client.post("/api/v1/auth/register", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@example.com"
    
    @pytest.mark.asyncio
    async def test_register_password_mismatch(self, async_client: AsyncClient):
        """Test registration with password mismatch"""
        payload = {
            "email": "test@example.com",
            "password": "SecurePass123",
            "confirm_password": "DifferentPass123",
            "name": "Test User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=payload)
        
        assert response.status_code == 400
        assert "Passwords do not match" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_weak_password(self, async_client: AsyncClient):
        """Test registration with weak password"""
        payload = {
            "email": "test@example.com",
            "password": "weak",
            "confirm_password": "weak",
            "name": "Test User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=payload)
        
        assert response.status_code == 422  # Validation error (pydantic min_length)
    
    @pytest.mark.asyncio
    async def test_register_no_uppercase(self, async_client: AsyncClient):
        """Test registration password without uppercase"""
        payload = {
            "email": "test@example.com",
            "password": "weakpass123",
            "confirm_password": "weakpass123",
            "name": "Test User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=payload)
        
        assert response.status_code == 400
        assert "uppercase" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client: AsyncClient, mock_supabase):
        """Test registration with existing email"""
        # Set mock data for existing user
        mock_supabase.set_mock_data("users", [{"email": "existing@example.com"}])
        
        payload = {
            "email": "existing@example.com",
            "password": "SecurePass123",
            "confirm_password": "SecurePass123",
            "name": "Duplicate User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=payload)
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()


class TestLogin:
    """Test user login"""
    
    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, mock_supabase, mock_user):
        """Test successful login"""
        # Set mock user profile data
        mock_supabase.set_mock_data("users", mock_user)
        
        payload = {
            "email": "test@example.com",
            "password": "SecurePass123"
        }
        
        response = await async_client.post("/api/v1/auth/login", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, async_client: AsyncClient, mock_supabase):
        """Test login with invalid credentials"""
        # Mock auth to fail
        mock_supabase.auth.sign_in_with_password = lambda x: None
        
        payload = {
            "email": "wrong@example.com",
            "password": "WrongPass123"
        }
        
        response = await async_client.post("/api/v1/auth/login", json=payload)
        
        # Should return 401 or 500 depending on implementation
        assert response.status_code in [401, 500]
    
    @pytest.mark.asyncio
    async def test_login_missing_fields(self, async_client: AsyncClient):
        """Test login with missing fields"""
        payload = {"email": "test@example.com"}
        
        response = await async_client.post("/api/v1/auth/login", json=payload)
        
        assert response.status_code == 422  # Validation error


class TestPasswordReset:
    """Test password reset functionality"""
    
    @pytest.mark.asyncio
    async def test_forgot_password(self, async_client: AsyncClient, mock_supabase):
        """Test forgot password request"""
        payload = {"email": "test@example.com"}
        
        response = await async_client.post("/api/v1/auth/forgot-password", json=payload)
        
        # Should always return 200 for security (don't reveal if email exists)
        assert response.status_code == 200
        assert "message" in response.json()
    
    @pytest.mark.asyncio
    async def test_reset_password_success(self, async_client: AsyncClient, mock_supabase):
        """Test password reset with valid token"""
        payload = {
            "token": "valid_reset_token",
            "new_password": "NewSecurePass123",
            "confirm_password": "NewSecurePass123"
        }
        
        response = await async_client.post("/api/v1/auth/reset-password", json=payload)
        
        assert response.status_code == 200
        assert "message" in response.json()
    
    @pytest.mark.asyncio
    async def test_reset_password_mismatch(self, async_client: AsyncClient):
        """Test password reset with password mismatch"""
        payload = {
            "token": "valid_token",
            "new_password": "NewPass123",
            "confirm_password": "DifferentPass123"
        }
        
        response = await async_client.post("/api/v1/auth/reset-password", json=payload)
        
        assert response.status_code == 400
        assert "do not match" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_reset_password_weak(self, async_client: AsyncClient):
        """Test password reset with weak password"""
        payload = {
            "token": "valid_token",
            "new_password": "weak",
            "confirm_password": "weak"
        }
        
        response = await async_client.post("/api/v1/auth/reset-password", json=payload)
        
        assert response.status_code == 422


class TestLogout:
    """Test logout functionality"""
    
    @pytest.mark.asyncio
    async def test_logout(self, async_client: AsyncClient, mock_supabase):
        """Test logout"""
        response = await async_client.post("/api/v1/auth/logout")
        
        assert response.status_code == 200
        assert "message" in response.json()


class TestTokenRefresh:
    """Test token refresh"""
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, async_client: AsyncClient, mock_supabase):
        """Test token refresh"""
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "mock_refresh_token_123"}
        )

        # Should return new token
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
