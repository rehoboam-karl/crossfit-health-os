"""
Google Calendar Integration
Auto-schedule workouts and meal windows via Google Calendar API.

Flow:
1. User clicks "Connect Google Calendar" → redirected to Google OAuth
2. After consent, callback stores refresh_token in users table
3. sync_calendar_events() creates events for next 7 days of training
"""
import logging
from uuid import UUID
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.core.config import settings
from app.db.supabase import supabase_client

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"
SCOPES = "https://www.googleapis.com/auth/calendar.events"


def get_oauth_url(state: str = "") -> str:
    """Generate Google OAuth2 authorization URL."""
    params = {
        "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
        "redirect_uri": f"{settings.FRONTEND_URL}/api/v1/integrations/calendar/oauth/callback",
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{qs}"


async def exchange_code(code: str) -> dict:
    """Exchange authorization code for access + refresh tokens."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
            "client_secret": settings.GOOGLE_CALENDAR_CLIENT_SECRET,
            "redirect_uri": f"{settings.FRONTEND_URL}/api/v1/integrations/calendar/oauth/callback",
            "grant_type": "authorization_code",
        })
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(refresh_token: str) -> str:
    """Get a fresh access token from a refresh token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data={
            "refresh_token": refresh_token,
            "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
            "client_secret": settings.GOOGLE_CALENDAR_CLIENT_SECRET,
            "grant_type": "refresh_token",
        })
        resp.raise_for_status()
        return resp.json()["access_token"]


async def _get_user_token(user_id: UUID) -> Optional[str]:
    """Get a valid access token for a user, refreshing if needed."""
    row = supabase_client.table("users").select(
        "google_calendar_refresh_token"
    ).eq("id", str(user_id)).single().execute()

    refresh_token = (row.data or {}).get("google_calendar_refresh_token")
    if not refresh_token:
        return None

    return await refresh_access_token(refresh_token)


async def create_calendar_event(
    access_token: str,
    summary: str,
    description: str,
    start: datetime,
    end: datetime,
    color_id: str = "9",  # blueberry
) -> dict:
    """Create a single Google Calendar event."""
    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start.isoformat(), "timeZone": "America/Sao_Paulo"},
        "end": {"dateTime": end.isoformat(), "timeZone": "America/Sao_Paulo"},
        "colorId": color_id,
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 30},
            ],
        },
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GOOGLE_CALENDAR_API}/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            json=event,
        )
        resp.raise_for_status()
        return resp.json()


async def sync_calendar_events(user_id: UUID) -> dict:
    """
    Create Google Calendar events for the user's next 7 days of training.

    Reads active weekly schedule → maps training days to calendar events.
    Returns count of created events.
    """
    access_token = await _get_user_token(user_id)
    if not access_token:
        return {"created": 0, "status": "not_connected", "message": "Google Calendar not connected. Please authorize first."}

    # Fetch active schedule
    schedule_resp = supabase_client.table("weekly_schedules").select("*").eq(
        "user_id", str(user_id)
    ).eq("active", True).order("created_at", desc=True).limit(1).execute()

    if not schedule_resp.data:
        return {"created": 0, "status": "no_schedule", "message": "No active training schedule found."}

    schedule = schedule_resp.data[0]

    # Parse schedule data structure (it's a Dict[DayOfWeek, DailyTrainingSchedule])
    schedule_dict = schedule.get("schedule", {})
    today = datetime.now(timezone.utc).date()
    created = 0

    for offset in range(7):
        target_date = today + timedelta(days=offset)
        weekday = target_date.strftime("%A").lower()  # monday, tuesday, ...

        # Find matching day in schedule dictionary
        day_schedule = schedule_dict.get(weekday)
        if not day_schedule:
            continue

        # Check if it's a rest day
        if day_schedule.get("rest_day", False):
            continue

        sessions = day_schedule.get("sessions", [])
        for session in sessions:
            # Session structure: {time: "06:00", duration_minutes: 60, workout_type: "strength", notes: "..."}
            workout_type = session.get("workout_type", "training")
            session_type = workout_type.capitalize() if workout_type else "Training"
            duration_min = session.get("duration_minutes", 60)
            time_str = session.get("time", "06:00")

            # Handle time string (could be "HH:MM" or time object)
            if isinstance(time_str, str):
                hour, minute = map(int, time_str.split(":"))
            else:
                # It's already a time object
                hour = time_str.hour
                minute = time_str.minute
            start_dt = datetime(
                target_date.year, target_date.month, target_date.day,
                hour, minute, tzinfo=timezone.utc
            )
            end_dt = start_dt + timedelta(minutes=duration_min)

            summary = f"🏋️ {session_type} — CrossFit Health OS"
            description = (
                f"Type: {session_type}\n"
                f"Duration: {duration_min} min\n"
                f"Generated by CrossFit Health OS"
            )

            color_map = {
                "strength": "9",      # blueberry
                "metcon": "11",       # tomato
                "skill": "2",         # sage
                "conditioning": "7",  # peacock
                "mixed": "5",         # banana
            }
            color_id = color_map.get(workout_type.lower() if workout_type else "", "9")

            try:
                await create_calendar_event(
                    access_token, summary, description,
                    start_dt, end_dt, color_id,
                )
                created += 1
            except Exception as e:
                logger.error(f"Failed to create calendar event: {e}")

    return {"created": created, "status": "success"}
