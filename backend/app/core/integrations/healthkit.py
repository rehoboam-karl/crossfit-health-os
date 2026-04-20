"""
Apple HealthKit Integration (SQLAlchemy).

Receives HRV, sleep, workout data from the iOS app and stores raw payloads
in `healthkit_data`.
"""
from datetime import datetime
from typing import Any, Dict

from app.db.models import HealthkitData as HealthkitDataDB
from app.db.session import SessionLocal


async def sync_healthkit_data(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store a HealthKit payload.

    Expected keys (iOS):
      - type (optional)
      - start_date / end_date (ISO strings; default to now)
      - device (optional)
      - hrv_rmssd_ms, resting_heart_rate_bpm, sleep_duration_hours, … (free-form)
    """
    def _parse_dt(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                return datetime.utcnow()
        return datetime.utcnow()

    row = HealthkitDataDB(
        user_id=int(user_id),
        data_type=data.get("type", "mixed"),
        start_date=_parse_dt(data.get("start_date")),
        end_date=_parse_dt(data.get("end_date")),
        data=data,
        device_name=data.get("device", "iPhone"),
        source_app="HealthKit",
    )
    with SessionLocal() as db:
        db.add(row)
        db.commit()
    return {"count": 1, "status": "success"}
