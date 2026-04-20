"""
Timezone-aware date utilities.

Avoid `date.today()` / `datetime.utcnow()` throughout the codebase — they return
UTC-naive values that create off-by-one bugs for users in non-UTC timezones
(e.g., a São Paulo user scheduling a workout at 22:00 local gets tomorrow's date).
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Optional

DEFAULT_TIMEZONE = "America/Sao_Paulo"


def _resolve_tz(user: Optional[dict]) -> ZoneInfo:
    tz_name = None
    if user:
        tz_name = user.get("timezone") or (user.get("preferences") or {}).get("timezone")
    try:
        return ZoneInfo(tz_name or DEFAULT_TIMEZONE)
    except ZoneInfoNotFoundError:
        return ZoneInfo(DEFAULT_TIMEZONE)


def user_now(user: Optional[dict] = None) -> datetime:
    """Current datetime in the user's timezone (or default)."""
    return datetime.now(_resolve_tz(user))


def user_today(user: Optional[dict] = None) -> date:
    """Current date in the user's timezone (or default)."""
    return user_now(user).date()


def snap_to_monday(d: date) -> date:
    """Return the Monday of the ISO week that contains `d`. weekday(): Mon=0 … Sun=6."""
    return d - timedelta(days=d.weekday())


def week_bounds(d: date) -> tuple[date, date]:
    """Return (Monday, Sunday) for the week that contains `d`."""
    monday = snap_to_monday(d)
    return monday, monday + timedelta(days=6)
