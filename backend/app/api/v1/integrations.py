"""
Integrations API Endpoints
HealthKit, Google Calendar
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from uuid import UUID
import logging

from app.core.auth import get_current_user
from app.core.integrations.healthkit import sync_healthkit_data
from app.core.integrations.calendar import (
    get_oauth_url,
    exchange_code,
    sync_calendar_events,
)
from app.db.supabase import supabase_client

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================
# HealthKit
# ============================================

@router.post("/healthkit/sync")
async def sync_healthkit(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Sync data from Apple HealthKit.
    Receives HRV, sleep, workout data from iOS app.
    """
    user_id = UUID(current_user["id"])
    result = await sync_healthkit_data(user_id, data)
    return {
        "status": "success",
        "records_synced": result.get("count", 0)
    }


# ============================================
# Google Calendar
# ============================================

@router.get("/calendar/oauth/url")
async def get_calendar_oauth_url(
    current_user: dict = Depends(get_current_user)
):
    """
    Get Google Calendar OAuth URL for authorization.
    Frontend redirects user to this URL to grant calendar access.
    """
    state = current_user["id"]  # pass user_id as state
    url = get_oauth_url(state=state)
    return {"auth_url": url}


@router.get("/calendar/oauth/callback")
async def calendar_oauth_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
):
    """
    OAuth2 callback from Google.
    Exchanges code for tokens and stores refresh_token.
    """
    if error:
        logger.warning(f"Calendar OAuth error: {error}")
        return RedirectResponse(url="/dashboard/profile?calendar=error")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    try:
        tokens = await exchange_code(code)
        refresh_token = tokens.get("refresh_token")

        if refresh_token:
            # Store refresh token in user profile
            supabase_client.table("users").update({
                "google_calendar_refresh_token": refresh_token
            }).eq("id", state).execute()

        return RedirectResponse(url="/dashboard/profile?calendar=connected")

    except Exception as e:
        logger.error(f"Calendar OAuth exchange failed: {e}", exc_info=True)
        return RedirectResponse(url="/dashboard/profile?calendar=error")


@router.post("/calendar/sync")
async def sync_google_calendar(
    current_user: dict = Depends(get_current_user)
):
    """
    Sync workout schedule to Google Calendar.
    Creates calendar events for next 7 days of training.
    """
    user_id = UUID(current_user["id"])
    result = await sync_calendar_events(user_id)

    if result.get("status") == "not_connected":
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Google Calendar not connected")
        )

    return {
        "status": "success",
        "events_created": result.get("created", 0),
        "message": f"Created {result['created']} calendar events for the next 7 days"
    }


@router.delete("/calendar/disconnect")
async def disconnect_calendar(
    current_user: dict = Depends(get_current_user)
):
    """Remove Google Calendar connection."""
    supabase_client.table("users").update({
        "google_calendar_refresh_token": None
    }).eq("id", current_user["id"]).execute()

    return {"status": "success", "message": "Google Calendar disconnected"}
