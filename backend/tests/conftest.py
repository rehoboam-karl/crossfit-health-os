"""
Pytest configuration and shared fixtures
Provides mocked clients for all tests
"""
import sys
from unittest.mock import Mock, AsyncMock, MagicMock, patch

# Mock supabase module before any app imports
sys.modules['supabase'] = Mock()
sys.modules['supabase'].create_client = Mock()
sys.modules['supabase'].Client = Mock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from uuid import uuid4, UUID
from datetime import datetime, date

# Import the FastAPI app
from app.main import app
from app.core.auth import get_current_user
from app.db.supabase import supabase_client


# ============================================
# Mock User Fixture
# ============================================

@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    return {
        "id": str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "test@example.com",
        "name": "Test Athlete",
        "fitness_level": "intermediate",
        "birth_date": "1990-01-01",
        "weight_kg": 80.0,
        "height_cm": 175.0,
        "preferences": {
            "goals": ["strength", "conditioning"],
            "methodology": "hwpo",
            "weaknesses": []
        }
    }


@pytest.fixture
def mock_user_uuid(mock_user):
    """Return user ID as UUID"""
    return UUID(mock_user["id"])


# ============================================
# Override get_current_user dependency
# ============================================

@pytest.fixture
def override_auth(mock_user):
    """Override authentication dependency to bypass auth checks"""
    async def _get_current_user_override():
        return mock_user
    
    # Override the dependency
    app.dependency_overrides[get_current_user] = _get_current_user_override
    
    yield mock_user
    
    # Clean up
    app.dependency_overrides.clear()


# ============================================
# Mock Supabase Client
# ============================================

class MockSupabaseResponse:
    """Mock Supabase response object"""
    def __init__(self, data=None, error=None):
        self.data = data or []
        self.error = error


class MockSupabaseQuery:
    """Mock Supabase query builder"""
    def __init__(self, table_name, mock_data=None):
        self.table_name = table_name
        self.mock_data = mock_data or {}
        self._filters = {}
        self._single = False
        self._order_by = None
        self._limit_val = None
        self._offset_val = 0
    
    def select(self, *args):
        return self
    
    def insert(self, data):
        # Return inserted data with generated ID
        if isinstance(data, list):
            result = []
            for item in data:
                item["id"] = str(uuid4())
                item["created_at"] = datetime.utcnow().isoformat()
                result.append(item)
            self.mock_data["response"] = result
        else:
            data["id"] = str(uuid4())
            data["created_at"] = datetime.utcnow().isoformat()
            self.mock_data["response"] = [data]
        return self
    
    def update(self, data):
        self.mock_data["update_data"] = data
        # Merge update data with existing mock data if available
        if "response" in self.mock_data and self.mock_data["response"]:
            existing = self.mock_data["response"]
            if isinstance(existing, dict):
                merged = {**existing, **data}
                merged["updated_at"] = datetime.utcnow().isoformat()
                self.mock_data["response"] = [merged]
            elif isinstance(existing, list) and existing:
                merged = {**existing[0], **data}
                merged["updated_at"] = datetime.utcnow().isoformat()
                self.mock_data["response"] = [merged]
            else:
                self.mock_data["response"] = [data] if data else []
        else:
            self.mock_data["response"] = [data] if data else []
        return self
    
    def upsert(self, data, **kwargs):
        if isinstance(data, list):
            result = []
            for item in data:
                if "id" not in item:
                    item["id"] = str(uuid4())
                if "created_at" not in item:
                    item["created_at"] = datetime.utcnow().isoformat()
                result.append(item)
            self.mock_data["response"] = result
        else:
            if "id" not in data:
                data["id"] = str(uuid4())
            if "created_at" not in data:
                data["created_at"] = datetime.utcnow().isoformat()
            self.mock_data["response"] = [data]
        return self
    
    def delete(self):
        self.mock_data["response"] = []
        return self
    
    def eq(self, column, value):
        self._filters[column] = value
        return self
    
    def gte(self, column, value):
        self._filters[f"{column}__gte"] = value
        return self
    
    def lte(self, column, value):
        self._filters[f"{column}__lte"] = value
        return self
    
    def order(self, column, **kwargs):
        self._order_by = (column, kwargs)
        return self
    
    def limit(self, limit):
        self._limit_val = limit
        return self
    
    def range(self, start, end):
        self._offset_val = start
        self._limit_val = end - start + 1
        return self
    
    def single(self):
        self._single = True
        return self
    
    def execute(self):
        """Execute the query and return mock response"""
        # Check if mock_data has explicit response
        if "response" in self.mock_data:
            data = self.mock_data["response"]
            if self._single and data:
                return MockSupabaseResponse(data=data[0] if isinstance(data, list) else data)
            return MockSupabaseResponse(data=data)
        
        # Otherwise return empty
        if self._single:
            return MockSupabaseResponse(data=None)
        return MockSupabaseResponse(data=[])


class MockSupabaseAuth:
    """Mock Supabase Auth"""
    def __init__(self):
        self.admin = Mock()
        self.admin.delete_user = Mock()
    
    def sign_up(self, credentials):
        user_id = str(uuid4())
        return Mock(
            user=Mock(id=user_id, email=credentials.get("email")),
            session=Mock(access_token=f"mock_token_{user_id}", expires_in=3600)
        )
    
    def sign_in_with_password(self, credentials):
        user_id = str(uuid4())
        return Mock(
            user=Mock(id=user_id, email=credentials.get("email")),
            session=Mock(access_token=f"mock_token_{user_id}", expires_in=3600)
        )
    
    def sign_out(self):
        return Mock()
    
    def get_user(self, token):
        return Mock(user=Mock(id=str(uuid4()), email="test@example.com"))
    
    def get_session(self):
        return Mock(
            access_token="mock_session_token",
            user=Mock(id=str(uuid4()), email="test@example.com"),
            expires_in=3600
        )

    def refresh_session(self, refresh_token):
        return Mock(
            session=Mock(
                access_token="mock_refreshed_token_" + str(uuid4())[:8],
                refresh_token="mock_new_refresh_token",
                user=Mock(id=str(uuid4()), email="test@example.com"),
                expires_in=3600
            )
        )
    
    def reset_password_email(self, email, **kwargs):
        return Mock()
    
    def update_user(self, data):
        return Mock()


class MockSupabaseClient:
    """Mock Supabase client"""
    def __init__(self):
        self.auth = MockSupabaseAuth()
        self._tables = {}
    
    def table(self, table_name):
        """Return mock query builder for table"""
        if table_name not in self._tables:
            self._tables[table_name] = {}
        return MockSupabaseQuery(table_name, self._tables[table_name])
    
    def set_mock_data(self, table_name, data):
        """Set mock data for a table"""
        self._tables[table_name] = {"response": data}


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    mock_client = MockSupabaseClient()
    
    with patch("app.db.supabase.supabase_client", mock_client):
        # Also patch imports in other modules
        with patch("app.core.auth.supabase_client", mock_client):
            with patch("app.api.v1.training.supabase_client", mock_client):
                with patch("app.api.v1.health.supabase_client", mock_client):
                    with patch("app.api.v1.nutrition.supabase_client", mock_client):
                        with patch("app.api.v1.schedule.supabase_client", mock_client):
                            with patch("app.api.v1.review.supabase_client", mock_client):
                                with patch("app.api.v1.users.supabase_client", mock_client):
                                    with patch("app.core.engine.adaptive.supabase_client", mock_client):
                                        with patch("app.core.engine.weekly_reviewer.supabase_client", mock_client):
                                            with patch("app.core.integrations.calendar.supabase_client", mock_client):
                                                with patch("app.core.integrations.healthkit.supabase_client", mock_client):
                                                    yield mock_client


# ============================================
# Mock OpenAI & Anthropic
# ============================================

@pytest.fixture
def mock_openai():
    """Mock OpenAI client"""
    with patch("openai.OpenAI") as mock:
        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=Mock(
            choices=[Mock(message=Mock(content="Mock AI response"))]
        ))
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic client"""
    with patch("anthropic.Anthropic") as mock:
        mock_client = Mock()
        mock_client.messages.create = AsyncMock(return_value=Mock(
            content=[Mock(text="Mock Claude response")]
        ))
        mock.return_value = mock_client
        yield mock_client


# ============================================
# AsyncClient for FastAPI testing
# ============================================

@pytest_asyncio.fixture
async def async_client(mock_supabase):
    """Async HTTP client for FastAPI app"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def authenticated_client(async_client, override_auth):
    """Authenticated async client with mocked user"""
    async_client.headers.update({"Authorization": "Bearer mock_token"})
    yield async_client
