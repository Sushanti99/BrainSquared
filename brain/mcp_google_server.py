"""
MCP server exposing Gmail and Google Calendar tools to Claude Code.

Run as a stdio MCP server — launched automatically via mcp_config.py.
Uses the existing token.json + credentials.json from the brain setup.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from mcp.server.fastmcp import FastMCP

CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "")
TOKEN_FILE = os.environ.get("GOOGLE_TOKEN_FILE", "")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]

mcp = FastMCP("brain-google")


def _get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = None
    if TOKEN_FILE and Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            if TOKEN_FILE:
                Path(TOKEN_FILE).write_text(creds.to_json())
        else:
            raise RuntimeError(
                "Google token missing or expired. Re-connect Gmail in the brain² Integrations tab."
            )
    return creds


# ── Gmail tools ───────────────────────────────────────────────────────────────

@mcp.tool()
def list_emails(days: int = 1, max_results: int = 20, query: str = "") -> str:
    """List recent emails. days=how far back, query=Gmail search string (e.g. 'from:foo@bar.com')."""
    from googleapiclient.discovery import build

    creds = _get_credentials()
    service = build("gmail", "v1", credentials=creds)

    after = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    q = f"after:{after}"
    if query:
        q += f" {query}"

    result = service.users().messages().list(
        userId="me", q=q, maxResults=max_results
    ).execute()

    items = []
    for msg in result.get("messages", []):
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["Subject", "From", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        items.append({
            "id": msg["id"],
            "subject": headers.get("Subject", "(no subject)"),
            "from": headers.get("From", ""),
            "date": headers.get("Date", ""),
            "snippet": detail.get("snippet", ""),
        })

    return json.dumps(items, indent=2) if items else "No emails found."


@mcp.tool()
def get_email(message_id: str) -> str:
    """Get the full body of an email by its message ID."""
    from googleapiclient.discovery import build

    creds = _get_credentials()
    service = build("gmail", "v1", credentials=creds)

    detail = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()

    headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}

    def _extract_body(payload: dict) -> str:
        import base64
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            for part in payload["parts"]:
                result = _extract_body(part)
                if result:
                    return result
        data = payload.get("body", {}).get("data", "")
        if data:
            import base64
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        return ""

    body = _extract_body(detail["payload"])
    return json.dumps({
        "id": message_id,
        "subject": headers.get("Subject", ""),
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "date": headers.get("Date", ""),
        "body": body[:4000],
    }, indent=2)


@mcp.tool()
def search_emails(query: str, max_results: int = 10) -> str:
    """Search emails using Gmail search syntax (e.g. 'from:sushantii.kerani subject:meeting')."""
    from googleapiclient.discovery import build

    creds = _get_credentials()
    service = build("gmail", "v1", credentials=creds)

    result = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    items = []
    for msg in result.get("messages", []):
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["Subject", "From", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        items.append({
            "id": msg["id"],
            "subject": headers.get("Subject", "(no subject)"),
            "from": headers.get("From", ""),
            "date": headers.get("Date", ""),
            "snippet": detail.get("snippet", ""),
        })

    return json.dumps(items, indent=2) if items else "No emails matched your search."


# ── Calendar tools ─────────────────────────────────────────────────────────────

@mcp.tool()
def get_events(days_back: int = 0, days_forward: int = 7, timezone_name: str = "America/Los_Angeles") -> str:
    """Get calendar events. days_back=0 means start from today, days_forward=how many days ahead."""
    from googleapiclient.discovery import build

    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds)

    tz = ZoneInfo(timezone_name)
    today = date.today()
    time_min = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=tz) - timedelta(days=days_back)
    time_max = time_min + timedelta(days=days_forward)

    result = service.events().list(
        calendarId="primary",
        timeMin=time_min.isoformat(),
        timeMax=time_max.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=50,
    ).execute()

    events = []
    for e in result.get("items", []):
        start = e["start"].get("dateTime", e["start"].get("date", ""))
        end = e["end"].get("dateTime", e["end"].get("date", ""))
        events.append({
            "title": e.get("summary", "(no title)"),
            "start": start,
            "end": end,
            "location": e.get("location", ""),
            "description": e.get("description", "")[:500],
            "all_day": "T" not in start,
        })

    return json.dumps(events, indent=2) if events else "No events found."


@mcp.tool()
def get_todays_events(timezone_name: str = "America/Los_Angeles") -> str:
    """Get all of today's calendar events."""
    return get_events(days_back=0, days_forward=1, timezone_name=timezone_name)


if __name__ == "__main__":
    mcp.run(transport="stdio")
