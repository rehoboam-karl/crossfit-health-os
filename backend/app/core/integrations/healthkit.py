"""
Apple HealthKit Integration
Receives HRV, sleep, workout data from iOS app
"""
from uuid import UUID
from datetime import datetime
from app.db.supabase import supabase_client


async def sync_healthkit_data(user_id: UUID, data: dict) -> dict:
    """
    Sync HealthKit data to recovery_metrics table
    
    Expected data format from iOS:
    {
        "hrv_rmssd_ms": 65,
        "resting_heart_rate_bpm": 48,
        "sleep_duration_hours": 7.5,
        "sleep_quality_score": 85,
        "workouts": [...]
    }
    """
    # Store raw HealthKit data
    healthkit_record = {
        "user_id": str(user_id),
        "data_type": data.get("type", "mixed"),
        "start_date": data.get("start_date", datetime.utcnow().isoformat()),
        "end_date": data.get("end_date", datetime.utcnow().isoformat()),
        "data": data,
        "device_name": data.get("device", "iPhone"),
        "source_app": "HealthKit"
    }
    
    response = supabase_client.table("healthkit_data").insert(
        healthkit_record
    ).execute()
    
    # TODO: Parse and update recovery_metrics table
    
    return {"count": 1, "status": "success"}
