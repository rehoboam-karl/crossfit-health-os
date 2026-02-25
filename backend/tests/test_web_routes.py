"""
Tests for Web Routes (HTML Pages)
Tests that all web pages return 200 OK
"""
import pytest
from httpx import AsyncClient


class TestPublicPages:
    """Test public web pages"""
    
    @pytest.mark.asyncio
    async def test_home_page(self, async_client: AsyncClient):
        """Test landing page"""
        response = await async_client.get("/")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_login_page(self, async_client: AsyncClient):
        """Test login page"""
        response = await async_client.get("/login")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_register_page(self, async_client: AsyncClient):
        """Test registration page"""
        response = await async_client.get("/register")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_forgot_password_page(self, async_client: AsyncClient):
        """Test forgot password page"""
        response = await async_client.get("/forgot-password")
        assert response.status_code == 200


class TestDashboardPages:
    """Test dashboard pages"""
    
    @pytest.mark.asyncio
    async def test_dashboard_home(self, async_client: AsyncClient):
        """Test main dashboard page"""
        response = await async_client.get("/dashboard")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_workouts_page(self, async_client: AsyncClient):
        """Test workouts page"""
        response = await async_client.get("/dashboard/workouts")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_schedule_page(self, async_client: AsyncClient):
        """Test schedule page"""
        response = await async_client.get("/dashboard/schedule")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_health_page(self, async_client: AsyncClient):
        """Test health/biometrics page"""
        response = await async_client.get("/dashboard/health")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_nutrition_page(self, async_client: AsyncClient):
        """Test nutrition page"""
        response = await async_client.get("/dashboard/nutrition")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_reviews_page(self, async_client: AsyncClient):
        """Test reviews page"""
        response = await async_client.get("/dashboard/reviews")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_profile_page(self, async_client: AsyncClient):
        """Test profile page"""
        response = await async_client.get("/dashboard/profile")
        assert response.status_code == 200


class TestAuthCallbackPages:
    """Test authentication callback pages"""
    
    @pytest.mark.asyncio
    async def test_auth_callback(self, async_client: AsyncClient):
        """Test Supabase auth callback handler"""
        response = await async_client.get(
            "/auth/callback?token=test_token&type=signup&redirect_to=/dashboard"
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_auth_verify(self, async_client: AsyncClient):
        """Test auth verify route"""
        response = await async_client.get("/auth/verify?token=test_token&type=email")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_auth_handler(self, async_client: AsyncClient):
        """Test auth handler for URL hash tokens"""
        response = await async_client.get("/auth/handler")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_update_password_page(self, async_client: AsyncClient):
        """Test update password page"""
        response = await async_client.get("/update-password")
        assert response.status_code == 200


class TestAPIHealthEndpoints:
    """Test API health check endpoints"""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, async_client: AsyncClient):
        """Test root API endpoint"""
        response = await async_client.get("/api")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_health_check(self, async_client: AsyncClient):
        """Test detailed health check"""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data
