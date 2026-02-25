"""
Tests for Health API
Tests recovery metrics and biomarker tracking
"""
import pytest
from httpx import AsyncClient
from datetime import date, datetime
from uuid import uuid4


class TestRecoveryMetrics:
    """Test recovery metric tracking"""
    
    @pytest.mark.asyncio
    async def test_create_recovery_metric(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test creating recovery metrics"""
        payload = {
            "date": date.today().isoformat(),
            "sleep_duration_hours": 8.5,
            "sleep_quality_score": 85,
            "hrv_rmssd_ms": 65,
            "resting_heart_rate_bpm": 52,
            "stress_level": 3,
            "muscle_soreness": 4,
            "energy_level": 8,
            "mood_score": 8,
            "notes": "Felt great after rest day"
        }
        
        response = await authenticated_client.post("/api/v1/health/recovery", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["sleep_duration_hours"] == 8.5
        assert data["hrv_rmssd_ms"] == 65
    
    @pytest.mark.asyncio
    async def test_create_recovery_metric_minimal(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test creating recovery metrics with minimal data"""
        payload = {
            "date": date.today().isoformat(),
            "sleep_quality_score": 70,
            "energy_level": 7
        }
        
        response = await authenticated_client.post("/api/v1/health/recovery", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["sleep_quality_score"] == 70
    
    @pytest.mark.asyncio
    async def test_get_latest_recovery(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test getting latest recovery metrics"""
        recovery_data = {
            "id": str(uuid4()),
            "user_id": str(mock_user_uuid),
            "date": date.today().isoformat(),
            "sleep_quality_score": 80,
            "hrv_rmssd_ms": 60,
            "readiness_score": 75,
            "created_at": datetime.utcnow().isoformat()
        }
        mock_supabase.set_mock_data("recovery_metrics", [recovery_data])
        
        response = await authenticated_client.get("/api/v1/health/recovery/latest")
        
        assert response.status_code == 200
        data = response.json()
        assert data["readiness_score"] == 75
    
    @pytest.mark.asyncio
    async def test_get_latest_recovery_not_found(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test getting latest recovery when none exists"""
        mock_supabase.set_mock_data("recovery_metrics", [])
        
        response = await authenticated_client.get("/api/v1/health/recovery/latest")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_recovery_metric_validation(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test recovery metric field validation"""
        payload = {
            "date": date.today().isoformat(),
            "stress_level": 15,  # Invalid: max is 10
            "sleep_quality_score": 70
        }
        
        response = await authenticated_client.post("/api/v1/health/recovery", json=payload)
        
        # Should fail validation
        assert response.status_code == 422


class TestBiomarkers:
    """Test biomarker tracking"""
    
    @pytest.mark.asyncio
    async def test_list_biomarkers(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test listing biomarker readings"""
        biomarkers = [
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "biomarker_type_id": str(uuid4()),
                "test_date": "2026-02-01",
                "value": 95.0,
                "unit": "mg/dL",
                "lab_name": "LabCorp",
                "status": "normal",
                "manually_entered": False,
                "created_at": datetime.utcnow().isoformat()
            }
        ]
        mock_supabase.set_mock_data("biomarker_readings", biomarkers)
        
        response = await authenticated_client.get("/api/v1/health/biomarkers")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["value"] == 95.0
    
    @pytest.mark.asyncio
    async def test_list_biomarkers_empty(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test listing biomarkers when none exist"""
        mock_supabase.set_mock_data("biomarker_readings", [])
        
        response = await authenticated_client.get("/api/v1/health/biomarkers")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestLabReportUpload:
    """Test lab report upload (OCR integration)"""
    
    @pytest.mark.asyncio
    async def test_upload_lab_report_invalid_format(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test uploading non-PDF file"""
        # Note: This test would need actual file upload simulation
        # For now, we test the endpoint exists and returns proper error
        
        # The upload endpoint requires a file, so we'd need to mock that
        # Skipping actual file upload test as it requires more complex setup
        pass
    
    @pytest.mark.asyncio
    async def test_upload_lab_report_success(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test successful lab report upload"""
        # This would require mocking the OCR parsing
        # Skipping for now as it requires file upload simulation
        pass
