"""
Pydantic models for Health domain
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, date
from uuid import UUID


class RecoveryMetricCreate(BaseModel):
    """Create recovery metric"""
    date: date
    sleep_duration_hours: Optional[float] = None
    sleep_quality_score: Optional[int] = Field(None, ge=1, le=100)
    hrv_rmssd_ms: Optional[int] = None
    resting_heart_rate_bpm: Optional[int] = None
    stress_level: Optional[int] = Field(None, ge=1, le=10)
    muscle_soreness: Optional[int] = Field(None, ge=1, le=10)
    energy_level: Optional[int] = Field(None, ge=1, le=10)
    mood_score: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = None


class RecoveryMetric(RecoveryMetricCreate):
    """Recovery metric response"""
    id: UUID
    user_id: int
    hrv_baseline_ms: Optional[int] = None
    hrv_ratio: Optional[float] = None
    resting_hr_baseline_bpm: Optional[int] = None
    readiness_score: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BiomarkerReadingCreate(BaseModel):
    """Create biomarker reading (API schema — free-form name, not FK to biomarker_types)."""
    biomarker_name: str
    test_date: date
    value: Optional[float] = None
    unit: str = ""
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    status: str = "normal"
    category: str = "other"
    lab_name: Optional[str] = None
    notes: Optional[str] = None


class BiomarkerReading(BiomarkerReadingCreate):
    """Biomarker reading response"""
    id: UUID
    user_id: int
    source: Optional[str] = None
    pdf_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
