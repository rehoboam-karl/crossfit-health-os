"""
Health API Endpoints
Biomarker tracking, lab results, recovery metrics
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List
from uuid import UUID
from datetime import date

from app.models.health import (
    RecoveryMetricCreate,
    RecoveryMetric,
    BiomarkerReadingCreate,
    BiomarkerReading
)
from app.db.supabase import supabase_client
from app.core.auth import get_current_user
from app.core.integrations.ocr import parse_lab_report

router = APIRouter()


@router.post("/recovery", response_model=RecoveryMetric)
async def create_recovery_metric(
    metric: RecoveryMetricCreate,
    current_user: dict = Depends(get_current_user)
):
    """Record daily recovery metrics"""
    user_id = UUID(current_user["id"])
    
    metric_data = metric.model_dump()
    metric_data["user_id"] = str(user_id)
    
    response = supabase_client.table("recovery_metrics").upsert(
        metric_data,
        on_conflict="user_id,date"
    ).execute()
    
    if response.data:
        return RecoveryMetric(**response.data[0])
    
    raise HTTPException(status_code=500, detail="Failed to record metrics")


@router.get("/recovery", response_model=List[RecoveryMetric])
async def list_recovery_metrics(
    start_date: date = None,
    end_date: date = None,
    limit: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """
    Get recovery metrics for date range

    Query params:
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    - limit: Max results (default 30)
    """
    user_id = UUID(current_user["id"])

    query = supabase_client.table("recovery_metrics").select("*").eq(
        "user_id", str(user_id)
    )

    if start_date:
        query = query.gte("date", start_date.isoformat())

    if end_date:
        query = query.lte("date", end_date.isoformat())

    response = query.order("date", desc=True).limit(limit).execute()

    return [RecoveryMetric(**m) for m in response.data]


@router.get("/recovery/latest", response_model=RecoveryMetric)
async def get_latest_recovery(
    current_user: dict = Depends(get_current_user)
):
    """Get today's recovery metrics"""
    user_id = UUID(current_user["id"])

    response = supabase_client.table("recovery_metrics").select("*").eq(
        "user_id", str(user_id)
    ).order("date", desc=True).limit(1).execute()

    if response.data:
        return RecoveryMetric(**response.data[0])

    raise HTTPException(status_code=404, detail="No recovery data found")


@router.post("/biomarkers/upload")
async def upload_lab_report(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload lab report (PDF or image) and extract biomarkers via GPT-4o Vision.
    Automatically parses values, reference ranges, and status.
    Cost: ~$0.05–0.15 per report depending on pages.
    """
    allowed = (".pdf", ".jpg", ".jpeg", ".png")
    if not any(file.filename.lower().endswith(ext) for ext in allowed):
        raise HTTPException(status_code=400, detail="Allowed formats: PDF, JPG, PNG")

    file_bytes = await file.read()
    if len(file_bytes) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")

    # Parse with GPT-4o Vision
    biomarkers = await parse_lab_report(
        file_bytes=file_bytes,
        filename=file.filename,
        content_type=file.content_type or "",
    )

    if not biomarkers:
        return {
            "status": "warning",
            "message": "No biomarkers found in the uploaded file",
            "biomarkers_found": 0,
            "biomarkers": []
        }

    # Store parsed biomarkers in database
    user_id = str(UUID(current_user["id"]))
    today = date.today().isoformat()
    saved = 0

    for bm in biomarkers:
        try:
            reading = {
                "user_id": user_id,
                "biomarker_name": bm.get("name", "Unknown"),
                "value": bm.get("value"),
                "unit": bm.get("unit", ""),
                "reference_min": bm.get("reference_min"),
                "reference_max": bm.get("reference_max"),
                "status": bm.get("status", "normal"),
                "category": bm.get("category", "other"),
                "test_date": today,
                "source": "ocr_upload",
            }
            supabase_client.table("biomarker_readings").insert(reading).execute()
            saved += 1
        except Exception:
            pass  # skip duplicates / validation errors

    return {
        "status": "success",
        "biomarkers_found": len(biomarkers),
        "biomarkers_saved": saved,
        "biomarkers": biomarkers
    }


@router.get("/biomarkers", response_model=List[BiomarkerReading])
async def list_biomarkers(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """List user's biomarker readings"""
    user_id = UUID(current_user["id"])
    
    response = supabase_client.table("biomarker_readings").select("*").eq(
        "user_id", str(user_id)
    ).order("test_date", desc=True).limit(limit).execute()
    
    return [BiomarkerReading(**b) for b in response.data]
