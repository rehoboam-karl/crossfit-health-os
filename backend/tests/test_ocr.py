"""
Tests for app/core/integrations/ocr.py
"""
import pytest
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch


class TestImageToBase64:
    @pytest.mark.asyncio
    async def test_converts_bytes_to_base64(self):
        from app.core.integrations.ocr import _image_to_base64
        data = b"hello world"
        result = await _image_to_base64(data)
        assert result == base64.b64encode(data).decode("utf-8")

    @pytest.mark.asyncio
    async def test_empty_bytes(self):
        from app.core.integrations.ocr import _image_to_base64
        result = await _image_to_base64(b"")
        assert result == ""


class TestPdfToImages:
    @pytest.mark.asyncio
    async def test_no_pdf2image_falls_back_to_raw(self):
        from app.core.integrations.ocr import _pdf_to_images
        raw = b"fake pdf bytes"
        with patch.dict("sys.modules", {"pdf2image": None}):
            result = await _pdf_to_images(raw)
        assert result == [raw]

    @pytest.mark.asyncio
    async def test_pdf_conversion_error_raises(self):
        from app.core.integrations.ocr import _pdf_to_images

        def bad_convert(*args, **kwargs):
            raise Exception("conversion error")

        mock_pdf2image = MagicMock()
        mock_pdf2image.convert_from_bytes.side_effect = bad_convert

        with patch.dict("sys.modules", {"pdf2image": mock_pdf2image}):
            with pytest.raises(ValueError, match="Could not convert PDF"):
                await _pdf_to_images(b"pdf content")


class TestParseLabReport:
    @pytest.mark.asyncio
    async def test_image_jpeg_parsed(self):
        from app.core.integrations.ocr import parse_lab_report

        biomarkers = [
            {"name": "Hemoglobin", "value": 14.5, "unit": "g/dL",
             "reference_min": 12.0, "reference_max": 17.0, "status": "normal", "category": "hematology"},
            {"name": "Glucose", "value": 95.0, "unit": "mg/dL",
             "reference_min": 70.0, "reference_max": 100.0, "status": "normal", "category": "metabolic"},
        ]

        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(biomarkers)

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.core.integrations.ocr.client", mock_client):
            result = await parse_lab_report(b"\xff\xd8jpeg_bytes", "test.jpg", "image/jpeg")

        assert isinstance(result, list)
        assert len(result) == 2
        names = {r["name"] for r in result}
        assert "Hemoglobin" in names
        assert "Glucose" in names

    @pytest.mark.asyncio
    async def test_png_media_type_detection(self):
        from app.core.integrations.ocr import parse_lab_report

        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps([
            {"name": "TSH", "value": 2.1, "unit": "mIU/L",
             "reference_min": 0.4, "reference_max": 4.0, "status": "normal", "category": "thyroid"}
        ])

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.core.integrations.ocr.client", mock_client):
            # PNG magic bytes
            result = await parse_lab_report(b"\x89PNG_bytes", "test.png", "image/png")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_markdown_json_stripped(self):
        from app.core.integrations.ocr import parse_lab_report

        biomarkers = [{"name": "Iron", "value": 80.0, "unit": "mcg/dL",
                       "reference_min": 60.0, "reference_max": 170.0, "status": "normal", "category": "hematology"}]
        content = "```json\n" + json.dumps(biomarkers) + "\n```"

        mock_response = MagicMock()
        mock_response.choices[0].message.content = content

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.core.integrations.ocr.client", mock_client):
            result = await parse_lab_report(b"img_bytes", "test.jpg", "image/jpeg")

        assert len(result) == 1
        assert result[0]["name"] == "Iron"

    @pytest.mark.asyncio
    async def test_api_error_returns_empty(self):
        from app.core.integrations.ocr import parse_lab_report

        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")

        with patch("app.core.integrations.ocr.client", mock_client):
            result = await parse_lab_report(b"img_bytes", "test.jpg", "image/jpeg")

        assert result == []

    @pytest.mark.asyncio
    async def test_duplicate_biomarkers_deduplicated(self):
        from app.core.integrations.ocr import parse_lab_report

        # Two pages, both have "Hemoglobin" — last one wins
        page_biomarkers = [
            {"name": "Hemoglobin", "value": 14.0, "unit": "g/dL",
             "reference_min": 12.0, "reference_max": 17.0, "status": "normal", "category": "hematology"}
        ]
        # Simulate 2-page PDF (2 images returned)
        with patch("app.core.integrations.ocr._pdf_to_images", AsyncMock(
            return_value=[b"page1", b"page2"]
        )):
            call_count = 0
            async def mock_create(**kwargs):
                nonlocal call_count
                call_count += 1
                m = MagicMock()
                m.choices[0].message.content = json.dumps(page_biomarkers)
                return m

            mock_client = AsyncMock()
            mock_client.chat.completions.create.side_effect = mock_create

            with patch("app.core.integrations.ocr.client", mock_client):
                result = await parse_lab_report(b"pdf", "test.pdf", "application/pdf")

        # Deduplication: only one "Hemoglobin"
        names = [r["name"] for r in result]
        assert names.count("Hemoglobin") == 1

    @pytest.mark.asyncio
    async def test_unexpected_response_type_logged(self):
        from app.core.integrations.ocr import parse_lab_report

        # Returns a dict instead of list
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({"error": "bad format"})

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.core.integrations.ocr.client", mock_client):
            result = await parse_lab_report(b"img", "test.jpg", "image/jpeg")

        assert result == []
