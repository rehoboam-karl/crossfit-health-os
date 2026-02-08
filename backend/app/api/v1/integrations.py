"""
Integrations API Endpoints
HealthKit, Google Calendar, Todoist
"""
from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID

from app.core.auth import get_current_user
from app.core.integrations.healthkit import sync_healthkit_data
from app.core.integrations.calendar import sync_calendar_events

router = APIRouter()


@router.post("/healthkit/sync")
async def sync_healthkit(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Sync data from Apple HealthKit
    Receives HRV, sleep, workout data from iOS app
    """
    user_id = UUID(current_user["id"])
    
    result = await sync_healthkit_data(user_id, data)
    
    return {
        "status": "success",
        "records_synced": result.get("count", 0)
    }


@router.post("/calendar/sync")
async def sync_google_calendar(
    current_user: dict = Depends(get_current_user)
):
    """
    Sync workout schedule to Google Calendar
    Creates calendar events for upcoming workouts
    """
    user_id = UUID(current_user["id"])
    
    result = await sync_calendar_events(user_id)
    
    return {
        "status": "success",
        "events_created": result.get("created", 0)
    }


@router.get("/calendar/oauth/url")
async def get_calendar_oauth_url():
    """Get Google Calendar OAuth URL for authorization"""
    # TODO: Implement OAuth flow
    return {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
    }
