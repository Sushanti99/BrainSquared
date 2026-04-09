"""Central configuration — all modules import from here."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _as_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default

VAULT_PATH = Path(os.getenv("VAULT_PATH", "/Users/acer/Documents/Obsidian Vault"))
DAILY_FOLDER = os.getenv("DAILY_FOLDER", "Daily")
GOOGLE_CREDENTIALS_FILE = Path(os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"))
GOOGLE_TOKEN_FILE = Path(os.getenv("GOOGLE_TOKEN_FILE", "token.json"))
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")
NEWS_FEEDS = os.getenv("NEWS_FEEDS", "")

APPLE_NOTES_ENABLED = _as_bool("APPLE_NOTES_ENABLED", True)
APPLE_NOTES_RECENT_HOURS = _as_int("APPLE_NOTES_RECENT_HOURS", 24)
APPLE_NOTES_MAX_TASKS = _as_int("APPLE_NOTES_MAX_TASKS", 50)
APPLE_NOTES_MAX_RECENT = _as_int("APPLE_NOTES_MAX_RECENT", 20)
APPLE_NOTES_INCLUDE_FOLDERS = [
    x.strip() for x in os.getenv("APPLE_NOTES_INCLUDE_FOLDERS", "").split(",") if x.strip()
]
APPLE_NOTES_EXCLUDE_FOLDERS = [
    x.strip() for x in os.getenv("APPLE_NOTES_EXCLUDE_FOLDERS", "").split(",") if x.strip()
]


def which_integrations_available() -> dict[str, bool]:
    return {
        "google": GOOGLE_TOKEN_FILE.exists() or GOOGLE_CREDENTIALS_FILE.exists(),
        "notion": bool(NOTION_API_KEY),
        "anthropic": bool(ANTHROPIC_API_KEY),
        "apple_notes": APPLE_NOTES_ENABLED and sys.platform == "darwin",
    }
