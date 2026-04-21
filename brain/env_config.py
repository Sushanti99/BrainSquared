"""Environment-backed integration configuration."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from brain.models import EnvConfig


def _find_dotenv() -> Path | None:
    """Search project root (brain package location) then CWD and parents for a .env file."""
    project_root = Path(__file__).resolve().parent.parent
    candidate = project_root / ".env"
    if candidate.exists():
        return candidate
    here = Path.cwd()
    for directory in [here, *here.parents]:
        candidate = directory / ".env"
        if candidate.exists():
            return candidate
    return None


def load_env_config(env_file: str | Path | None = None) -> EnvConfig:
    if env_file is None:
        dotenv_path = _find_dotenv()
        load_dotenv(dotenv_path)
    else:
        dotenv_path = Path(env_file)
        load_dotenv(dotenv_path)

    base = dotenv_path.parent if dotenv_path else Path.cwd()

    def _resolve(value: str) -> Path:
        p = Path(value).expanduser()
        return p if p.is_absolute() else (base / p).resolve()

    google_credentials = _resolve(os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"))
    google_token = _resolve(os.getenv("GOOGLE_TOKEN_FILE", "token.json"))
    notion_api_key = os.getenv("NOTION_API_KEY", "")
    news_feeds = [item.strip() for item in os.getenv("NEWS_FEEDS", "").split(",") if item.strip()]

    raw_env = {
        "GOOGLE_CREDENTIALS_FILE": str(google_credentials),
        "GOOGLE_TOKEN_FILE": str(google_token),
        "NOTION_API_KEY": notion_api_key,
        "NEWS_FEEDS": ",".join(news_feeds),
    }

    return EnvConfig(
        google_credentials_file=google_credentials,
        google_token_file=google_token,
        notion_api_key=notion_api_key,
        news_feeds=news_feeds,
        raw_env=raw_env,
    )


def integration_status(env_cfg: EnvConfig) -> dict[str, bool]:
    return {
        "google": env_cfg.google_token_file.exists() or env_cfg.google_credentials_file.exists(),
        "notion": bool(env_cfg.notion_api_key),
        "news": bool(env_cfg.news_feeds),
    }
