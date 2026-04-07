"""Google Calendar integration — fetches today's events."""
from datetime import datetime, date
from zoneinfo import ZoneInfo
from googleapiclient.discovery import build
from gmail_client import get_credentials
import config


def get_todays_events(timezone_name: str = "America/Los_Angeles") -> list[dict]:
    """Return today's calendar events sorted by start time."""
    if not config.GOOGLE_CREDENTIALS_FILE.exists():
        return []
    try:
        creds = get_credentials()
        service = build("calendar", "v3", credentials=creds)

        tz = ZoneInfo(timezone_name)
        today = date.today()
        time_min = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=tz).isoformat()
        time_max = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=tz).isoformat()

        result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = []
        for e in result.get("items", []):
            start = e["start"].get("dateTime", e["start"].get("date", ""))
            end = e["end"].get("dateTime", e["end"].get("date", ""))

            def fmt(dt_str: str) -> str:
                return datetime.fromisoformat(dt_str).strftime("%H:%M") if "T" in dt_str else "All-day"

            events.append({
                "title": e.get("summary", "(no title)"),
                "start": fmt(start),
                "end": fmt(end),
                "location": e.get("location", ""),
                "description": e.get("description", ""),
                "all_day": "T" not in start,
            })

        return events
    except Exception as e:
        print(f"  [calendar] skipped: {e}")
        return []
