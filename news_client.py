"""News client — fetches articles from the past 24 hours, ranked by vault interests.

No auth required. Sources: Hacker News, RSS feeds.
Add custom feeds via NEWS_FEEDS in .env (comma-separated URLs).
"""
import re
import time
import requests
import feedparser
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import config

DEFAULT_FEEDS = [
    ("Hacker News",    "https://news.ycombinator.com/rss"),
    ("TechCrunch",     "https://techcrunch.com/feed/"),
    ("The Verge",      "https://www.theverge.com/rss/index.xml"),
    ("arXiv AI",       "https://export.arxiv.org/rss/cs.AI"),
    ("VentureBeat",    "https://feeds.feedburner.com/venturebeat/SZYF"),
    ("MIT Tech Review","https://www.technologyreview.com/feed/"),
]

MAX_ARTICLES = 10
HOURS_BACK = 24


# ── date parsing ──────────────────────────────────────────────────────────────

def _parse_date(entry: dict) -> datetime | None:
    """Try every common date field feedparser exposes."""
    for field in ("published", "updated", "created"):
        val = entry.get(field)
        if val:
            try:
                return parsedate_to_datetime(val).astimezone(timezone.utc)
            except Exception:
                pass
        parsed = entry.get(f"{field}_parsed")
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


# ── fetch ─────────────────────────────────────────────────────────────────────

def _fetch_feed(name: str, url: str, cutoff: datetime) -> list[dict]:
    try:
        # Fetch with timeout via requests, pass content to feedparser
        resp = requests.get(url, timeout=8, headers={"User-Agent": "BrainSquared/1.0"})
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        articles = []
        for entry in feed.entries:
            pub = _parse_date(entry)
            if pub and pub < cutoff:
                continue  # too old

            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary = re.sub(r"<[^>]+>", "", entry.get("summary", ""))[:200].strip()

            if title and link:
                articles.append({
                    "title": title,
                    "url": link,
                    "summary": summary,
                    "published": pub,
                    "source": name,
                })
        return articles

    except Exception as e:
        return []


# ── interest extraction ───────────────────────────────────────────────────────

def extract_interests(vault_notes: list) -> list[str]:
    """
    Derive interest keywords from the vault: tags, folder names, note titles.
    Returns a deduplicated lowercase list, filtered to meaningful words.
    """
    stopwords = {
        "the", "and", "for", "with", "from", "that", "this", "have", "will",
        "your", "into", "been", "when", "what", "about", "which", "they",
        "notes", "note", "daily", "untitled", "draft", "misc",
    }
    keywords = set()

    for note in vault_notes:
        # Tags are the highest-signal interest indicators
        for tag in note.tags:
            keywords.add(tag.lower().replace("-", " ").replace("/", " "))

        # Folder names (e.g. "AI interpretability", "job applications")
        if note.folder:
            for part in re.split(r"[/\\]", note.folder):
                part = part.strip().lower()
                if len(part) > 3 and part not in stopwords:
                    keywords.add(part)

        # Meaningful words from note titles
        for word in re.split(r"[\s\-_]+", note.title.lower()):
            word = re.sub(r"[^a-z0-9]", "", word)
            if len(word) > 4 and word not in stopwords:
                keywords.add(word)

    return sorted(keywords)


# ── relevance scoring ─────────────────────────────────────────────────────────

def _score(article: dict, keywords: list[str]) -> int:
    text = (article["title"] + " " + article["summary"]).lower()
    return sum(1 for kw in keywords if kw in text)


def rank_articles(articles: list[dict], interests: list[str]) -> list[dict]:
    """Sort articles by keyword overlap with vault interests. Deduplicate by URL."""
    seen = set()
    unique = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    scored = sorted(unique, key=lambda a: _score(a, interests), reverse=True)
    return scored


# ── public API ────────────────────────────────────────────────────────────────

def get_reading_list(vault_notes: list, max_articles: int = MAX_ARTICLES) -> list[dict]:
    """
    Return the top N articles from the past 24 hours, ranked by relevance
    to the user's vault interests. No auth required.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS_BACK)

    # Load extra feeds from .env if configured
    extra = [
        ("Custom", url.strip())
        for url in (getattr(config, "NEWS_FEEDS", "") or "").split(",")
        if url.strip()
    ]
    feeds = DEFAULT_FEEDS + extra

    # Fetch all feeds (with a small delay to be polite)
    all_articles = []
    for name, url in feeds:
        all_articles.extend(_fetch_feed(name, url, cutoff))
        time.sleep(0.2)

    interests = extract_interests(vault_notes)
    ranked = rank_articles(all_articles, interests)

    return ranked[:max_articles]
