"""Central configuration — all modules import from here."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

VAULT_PATH = Path(os.getenv("VAULT_PATH", "/Users/acer/Documents/Obsidian Vault"))
DAILY_FOLDER = os.getenv("DAILY_FOLDER", "Daily")
GOOGLE_CREDENTIALS_FILE = Path(os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"))
GOOGLE_TOKEN_FILE = Path(os.getenv("GOOGLE_TOKEN_FILE", "token.json"))
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")


def which_integrations_available() -> dict[str, bool]:
    return {
        "google": GOOGLE_TOKEN_FILE.exists() or GOOGLE_CREDENTIALS_FILE.exists(),
        "notion": bool(NOTION_API_KEY),
        "anthropic": bool(ANTHROPIC_API_KEY),
    }
