"""Gmail integration — fetches recent unread emails as action items."""
from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import config

# Both Google scopes must be requested together in a single flow.
# If you add a new scope later, delete token.json and re-authenticate.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def get_credentials() -> Credentials:
    creds = None
    if config.GOOGLE_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(config.GOOGLE_TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not config.GOOGLE_CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    "Google token expired and credentials.json not found. "
                    "Re-run setup.py to re-authenticate."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(config.GOOGLE_CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
        config.GOOGLE_TOKEN_FILE.write_text(creds.to_json())
    return creds


def get_action_items(max_results: int = 20) -> list[dict]:
    """Return recent unread emails from the last 24 hours as potential action items."""
    if not config.GOOGLE_TOKEN_FILE.exists() and not config.GOOGLE_CREDENTIALS_FILE.exists():
        return []
    try:
        creds = get_credentials()
        service = build("gmail", "v1", credentials=creds)

        after = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
        result = service.users().messages().list(
            userId="me", q=f"is:unread after:{after}", maxResults=max_results
        ).execute()

        items = []
        for msg in result.get("messages", []):
            detail = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["Subject", "From", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            items.append({
                "subject": headers.get("Subject", "(no subject)"),
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
                "snippet": detail.get("snippet", ""),
            })

        return items
    except Exception as e:
        print(f"  [gmail] skipped: {e}")
        return []


def get_context_threads(days: int = 90, max_results: int = 60) -> dict:
    """Return broader email context for vault seeding — top senders and recent thread subjects."""
    if not config.GOOGLE_TOKEN_FILE.exists() and not config.GOOGLE_CREDENTIALS_FILE.exists():
        return {"top_senders": [], "recent_subjects": []}
    try:
        creds = get_credentials()
        service = build("gmail", "v1", credentials=creds)

        after = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
        result = service.users().messages().list(
            userId="me", q=f"after:{after}", maxResults=max_results
        ).execute()

        sender_counts: dict[str, int] = {}
        subjects: list[str] = []

        for msg in result.get("messages", []):
            detail = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["Subject", "From"]
            ).execute()
            headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            sender = headers.get("From", "")
            subject = headers.get("Subject", "")
            if sender:
                sender_counts[sender] = sender_counts.get(sender, 0) + 1
            if subject and subject not in subjects:
                subjects.append(subject)

        top_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        return {
            "top_senders": [{"name": s, "count": c} for s, c in top_senders],
            "recent_subjects": subjects[:30],
        }
    except Exception as e:
        print(f"  [gmail] context skipped: {e}")
        return {"top_senders": [], "recent_subjects": []}
