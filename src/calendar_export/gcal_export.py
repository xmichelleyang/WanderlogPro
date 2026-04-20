"""Google Calendar export for WanderlogPro itineraries."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from wanderlogpro.calendar_export.models import CalendarTrip, ItineraryDay, ItineraryItem

SCOPES = ["https://www.googleapis.com/auth/calendar"]
DEFAULT_START_HOUR = 10
DEFAULT_DURATION_MINUTES = 60

TOKEN_DIR = Path.home() / ".wanderlogpro"
TOKEN_PATH = TOKEN_DIR / "token.json"
_CREDENTIALS_PATH = TOKEN_DIR / "credentials.json"


def _load_client_config() -> dict:
    """Load OAuth2 client config from credentials.json or environment.

    Checks (in order):
    1. WANDERLOGPRO_CLIENT_ID + WANDERLOGPRO_CLIENT_SECRET env vars
    2. ~/.wanderlogpro/credentials.json
    3. ./credentials.json in current directory

    Raises:
        SystemExit: If no credentials are found.
    """
    client_id = os.environ.get("WANDERLOGPRO_CLIENT_ID", "")
    client_secret = os.environ.get("WANDERLOGPRO_CLIENT_SECRET", "")

    if client_id and client_secret:
        return {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }

    for path in [_CREDENTIALS_PATH, Path("credentials.json")]:
        if path.exists():
            with open(path) as f:
                return json.load(f)

    raise SystemExit(
        "❌ No Google OAuth2 credentials found.\n\n"
        "Set up credentials using ONE of these methods:\n\n"
        "  Option 1 — credentials.json file:\n"
        f"    Place credentials.json in ~/.wanderlogpro/ or current directory.\n"
        "    Download from: https://console.cloud.google.com/apis/credentials\n\n"
        "  Option 2 — Environment variables:\n"
        "    export WANDERLOGPRO_CLIENT_ID='your-client-id'\n"
        "    export WANDERLOGPRO_CLIENT_SECRET='your-client-secret'\n\n"
        "  See the calendar_export README for full setup instructions."
    )


def authenticate() -> Credentials:
    """Authenticate with Google Calendar API via OAuth2.

    Uses a cached token at ~/.wanderlogpro/token.json. If expired or
    missing, opens a browser for the OAuth2 consent flow.

    Returns:
        Authenticated Google credentials.

    Raises:
        SystemExit: If the user cancels or auth times out.
    """
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(
                _load_client_config(), SCOPES
            )
            try:
                creds = flow.run_local_server(
                    port=0,
                    timeout_seconds=120,
                    open_browser=True,
                )
            except KeyboardInterrupt:
                raise SystemExit("\n⚠️  Authentication cancelled.")
            except Exception as e:
                raise SystemExit(
                    f"\n❌ Authentication failed: {e}\n"
                    "   If you see 'access_denied', add your Google account as a test user:\n"
                    "   → Google Cloud Console → APIs & Services → OAuth consent screen → Test users"
                )

            if not creds:
                raise SystemExit(
                    "\n❌ Authentication timed out (120s).\n"
                    "   Run the command again and complete the Google sign-in in your browser."
                )

        TOKEN_PATH.write_text(creds.to_json())

    return creds


def get_calendar_service(creds: Credentials):
    """Build and return a Google Calendar API service client."""
    return build("calendar", "v3", credentials=creds)


def create_trip_calendar(service, trip_name: str, timezone: str = "UTC") -> str:
    """Create a secondary Google Calendar for the trip.

    Args:
        service: Google Calendar API service instance.
        trip_name: Name of the trip.
        timezone: IANA timezone for the calendar.

    Returns:
        The calendar ID of the newly created calendar.
    """
    calendar_body = {
        "summary": f"{trip_name} — WanderlogPro",
        "description": f"Itinerary for {trip_name}, exported by WanderlogPro.",
        "timeZone": timezone,
    }
    created = service.calendars().insert(body=calendar_body).execute()
    return created["id"]


def build_event(
    item: ItineraryItem,
    start_dt: datetime,
    end_dt: datetime,
    has_explicit_time: bool,
    timezone: str = "",
) -> dict:
    """Build a Google Calendar event body for an itinerary item.

    Args:
        item: The itinerary item.
        start_dt: Event start datetime.
        end_dt: Event end datetime.
        has_explicit_time: Whether the item had an explicit start time
            (from Wanderlog or user-set). If True, title gets [!] prefix.
        timezone: IANA timezone for the event. If empty, no timeZone is set.

    Returns:
        Google Calendar event resource dict.
    """
    title = f"[!]{item.name}" if has_explicit_time else item.name

    description_parts = []
    if item.address:
        description_parts.append(f"📍 {item.address}")
    if item.notes:
        description_parts.append(item.notes)
    description = "\n".join(description_parts)

    start_body: dict = {"dateTime": start_dt.isoformat()}
    end_body: dict = {"dateTime": end_dt.isoformat()}
    if timezone:
        start_body["timeZone"] = timezone
        end_body["timeZone"] = timezone

    event = {
        "summary": title,
        "start": start_body,
        "end": end_body,
    }

    if description:
        event["description"] = description
    if item.address:
        event["location"] = item.address
    if item.travel_mode:
        event["_travel_mode"] = item.travel_mode

    return event


def schedule_day(
    day: ItineraryDay, timezone: str = "", start_hour: int = DEFAULT_START_HOUR,
) -> list[dict]:
    """Schedule all items in a day and return Google Calendar event bodies.

    Scheduling rules:
    - First item starts at ``start_hour`` unless it has an explicit start time.
    - Each item's duration comes from Wanderlog (fallback: 60 minutes).
    - Travel time gaps are inserted between consecutive events.
    - Explicit start times override the sequential calculation.

    Args:
        day: An ItineraryDay with ordered items.
        timezone: IANA timezone for events. Empty for dry-run (no tz).
        start_hour: Hour of the day (0–23) at which auto-scheduled events
            begin when no explicit time is set. Defaults to 10 (10 AM).

    Returns:
        List of Google Calendar event resource dicts.
    """
    if not day.items:
        return []

    base_date = datetime.fromisoformat(day.date)
    current_time = base_date.replace(hour=start_hour, minute=0, second=0)
    events: list[dict] = []

    for i, item in enumerate(day.items):
        has_explicit_time = bool(item.start_time)

        if has_explicit_time:
            start_dt = _parse_item_time(day.date, item.start_time)
        else:
            start_dt = current_time

        duration = item.duration_minutes if item.duration_minutes > 0 else DEFAULT_DURATION_MINUTES

        if item.end_time:
            end_dt = _parse_item_time(day.date, item.end_time)
        else:
            end_dt = start_dt + timedelta(minutes=duration)

        events.append(build_event(item, start_dt, end_dt, has_explicit_time, timezone))

        # Advance current_time for the next item
        travel = item.travel_minutes_to_next if item.travel_minutes_to_next > 0 else 0
        current_time = end_dt + timedelta(minutes=travel)

    return events


def _parse_item_time(date_str: str, time_str: str) -> datetime:
    """Parse a date + time string into a datetime.

    Handles common formats:
    - "HH:MM" or "H:MM"
    - "HH:MM:SS"
    - Full ISO datetime string
    """
    time_str = str(time_str).strip()

    # Full ISO datetime
    if "T" in time_str:
        try:
            return datetime.fromisoformat(time_str)
        except ValueError:
            pass

    # Time only — combine with date
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p"):
        try:
            t = datetime.strptime(time_str, fmt).time()
            d = datetime.fromisoformat(date_str).date()
            return datetime.combine(d, t)
        except ValueError:
            continue

    # Fallback: treat as 10 AM
    return datetime.fromisoformat(date_str).replace(
        hour=DEFAULT_START_HOUR, minute=0, second=0
    )


def preview_trip_events(
    trip: CalendarTrip, start_hour: int = DEFAULT_START_HOUR,
) -> list[tuple[str, list[dict]]]:
    """Build all scheduled events without calling the Google Calendar API.

    Reuses schedule_day() for each day and returns the results grouped by day.

    Args:
        trip: A CalendarTrip with itinerary days.
        start_hour: Hour of the day (0–23) at which auto-scheduled events
            begin. Defaults to 10 (10 AM).

    Returns:
        List of (date_string, events) tuples — one per day.
    """
    result: list[tuple[str, list[dict]]] = []
    for day in trip.days:
        events = schedule_day(day, start_hour=start_hour)
        if events:
            result.append((day.date, events))
    return result


def export_trip_to_gcal(
    trip: CalendarTrip,
    start_hour: int = DEFAULT_START_HOUR,
) -> tuple[str, int]:
    """Export a trip's itinerary to Google Calendar.

    Creates a new sub-calendar for the trip and adds all itinerary
    items as events with proper scheduling.

    Args:
        trip: A CalendarTrip with itinerary days.
        start_hour: Hour of the day (0–23) at which auto-scheduled events
            begin. Defaults to 10 (10 AM).

    Returns:
        Tuple of (calendar_id, event_count).
    """
    creds = authenticate()
    service = get_calendar_service(creds)

    tz = trip.timezone or "UTC"
    calendar_id = create_trip_calendar(service, trip.name, tz)
    event_count = 0

    for day in trip.days:
        events = schedule_day(day, tz, start_hour=start_hour)
        for event in events:
            service.events().insert(
                calendarId=calendar_id, body=event
            ).execute()
            event_count += 1

    return calendar_id, event_count
