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
    Upload lab report PDF and extract biomarkers via OCR
    Uses OpenAI GPT-4 Vision for intelligent parsing
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    # Parse PDF with OCR
    biomarkers = await parse_lab_report(file)
    
    # TODO: Store in Supabase Storage and save readings
    
    return {
        "status": "success",
        "biomarkers_found": len(biomarkers),
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
