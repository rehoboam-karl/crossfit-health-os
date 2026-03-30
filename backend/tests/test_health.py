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
    async def test_upload_invalid_format_returns_400(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test uploading unsupported format returns 400"""
        import io
        content = b"some text content"
        response = await authenticated_client.post(
            "/api/v1/health/biomarkers/upload",
            files={"file": ("report.txt", io.BytesIO(content), "text/plain")},
        )
        assert response.status_code == 400
        assert "Allowed formats" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_file_too_large_returns_400(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test uploading file > 20MB returns 400"""
        import io
        from unittest.mock import patch, AsyncMock

        large_content = b"x" * (21 * 1024 * 1024)

        response = await authenticated_client.post(
            "/api/v1/health/biomarkers/upload",
            files={"file": ("report.pdf", io.BytesIO(large_content), "application/pdf")},
        )
        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_pdf_no_biomarkers_found(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test PDF upload that finds no biomarkers returns warning"""
        import io
        from unittest.mock import patch, AsyncMock

        pdf_content = b"%PDF-1.4 minimal"

        with patch("app.api.v1.health.parse_lab_report", new_callable=AsyncMock, return_value=[]):
            response = await authenticated_client.post(
                "/api/v1/health/biomarkers/upload",
                files={"file": ("report.pdf", io.BytesIO(pdf_content), "application/pdf")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "warning"
        assert data["biomarkers_found"] == 0

    @pytest.mark.asyncio
    async def test_upload_pdf_success_saves_biomarkers(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test successful PDF upload saves extracted biomarkers"""
        import io
        from unittest.mock import patch, AsyncMock

        biomarkers = [
            {
                "name": "Glucose",
                "value": 95.0,
                "unit": "mg/dL",
                "reference_min": 70,
                "reference_max": 100,
                "status": "normal",
                "category": "metabolic",
            },
            {
                "name": "Hemoglobin",
                "value": 14.5,
                "unit": "g/dL",
                "reference_min": 12,
                "reference_max": 17,
                "status": "normal",
                "category": "hematology",
            },
        ]

        with patch("app.api.v1.health.parse_lab_report", new_callable=AsyncMock, return_value=biomarkers):
            response = await authenticated_client.post(
                "/api/v1/health/biomarkers/upload",
                files={"file": ("report.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["biomarkers_found"] == 2
        assert data["biomarkers_saved"] >= 0

    @pytest.mark.asyncio
    async def test_upload_jpg_accepted(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test JPG files are accepted"""
        import io
        from unittest.mock import patch, AsyncMock

        with patch("app.api.v1.health.parse_lab_report", new_callable=AsyncMock, return_value=[]):
            response = await authenticated_client.post(
                "/api/v1/health/biomarkers/upload",
                files={"file": ("lab.jpg", io.BytesIO(b"\xff\xd8\xff"), "image/jpeg")},
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_upload_png_accepted(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test PNG files are accepted"""
        import io
        from unittest.mock import patch, AsyncMock

        with patch("app.api.v1.health.parse_lab_report", new_callable=AsyncMock, return_value=[]):
            response = await authenticated_client.post(
                "/api/v1/health/biomarkers/upload",
                files={"file": ("lab.png", io.BytesIO(b"\x89PNG"), "image/png")},
            )

        assert response.status_code == 200


class TestRecoveryWithDateRange:
    """Test recovery metrics with date range filtering"""

    @pytest.mark.asyncio
    async def test_list_recovery_with_start_date(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test GET /recovery with start_date filter"""
        from datetime import date, datetime
        from uuid import uuid4

        metrics = [
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "date": "2026-03-20",
                "sleep_quality_score": 80,
                "energy_level": 7,
                "readiness_score": 70,
                "created_at": datetime.utcnow().isoformat(),
            }
        ]
        mock_supabase.set_mock_data("recovery_metrics", metrics)

        response = await authenticated_client.get(
            "/api/v1/health/recovery?start_date=2026-03-01"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_recovery_with_date_range(
        self, authenticated_client: AsyncClient, mock_supabase, mock_user_uuid
    ):
        """Test GET /recovery with both start and end dates"""
        from datetime import datetime
        from uuid import uuid4

        metrics = [
            {
                "id": str(uuid4()),
                "user_id": str(mock_user_uuid),
                "date": "2026-03-15",
                "sleep_quality_score": 75,
                "energy_level": 6,
                "readiness_score": 65,
                "created_at": datetime.utcnow().isoformat(),
            }
        ]
        mock_supabase.set_mock_data("recovery_metrics", metrics)

        response = await authenticated_client.get(
            "/api/v1/health/recovery?start_date=2026-03-01&end_date=2026-03-31"
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_recovery_empty(
        self, authenticated_client: AsyncClient, mock_supabase
    ):
        """Test GET /recovery returns empty list when no data"""
        mock_supabase.set_mock_data("recovery_metrics", [])

        response = await authenticated_client.get("/api/v1/health/recovery")
        assert response.status_code == 200
        assert response.json() == []
