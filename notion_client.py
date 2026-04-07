"""Notion integration — fetches open tasks from all shared pages and databases.

Only requires NOTION_API_KEY. No database ID needed.
Share any page or database with your integration and it will be picked up automatically.
"""
import time
import requests
import config

NOTION_API = "https://api.notion.com/v1"
DONE_STATUSES = {"done", "complete", "completed", "closed", "cancelled"}


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }


def _get(url: str, **kwargs) -> dict:
    resp = requests.get(url, headers=_headers(), timeout=10, **kwargs)
    resp.raise_for_status()
    return resp.json()


def _post(url: str, body: dict) -> dict:
    resp = requests.post(url, headers=_headers(), json=body, timeout=10)
    resp.raise_for_status()
    return resp.json()


# ── title extraction ──────────────────────────────────────────────────────────

def _page_title(page: dict) -> str:
    """Extract title from a page or database row."""
    # Database row: look in properties
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            blocks = prop.get("title", [])
            if blocks:
                return blocks[0].get("text", {}).get("content", "")
    # Plain page: look in page-level title
    for block in page.get("title", []):
        if block.get("type") == "text":
            return block["text"].get("content", "")
    return "(untitled)"


def _is_done(properties: dict) -> bool:
    for prop in properties.values():
        t = prop.get("type")
        if t == "status":
            name = (prop.get("status") or {}).get("name", "").lower()
            if name in DONE_STATUSES:
                return True
        elif t == "select":
            name = (prop.get("select") or {}).get("name", "").lower()
            if name in DONE_STATUSES:
                return True
        elif t == "checkbox":
            if prop.get("checkbox"):
                return True
    return False


def _get_due(properties: dict) -> str:
    for prop in properties.values():
        if prop.get("type") == "date" and prop.get("date"):
            return prop["date"].get("start", "")
    return ""


def _get_status(properties: dict) -> str:
    for prop in properties.values():
        if prop.get("type") == "status":
            return (prop.get("status") or {}).get("name", "")
    return ""


# ── search: find everything shared with this integration ─────────────────────

def _search_all(filter_type: str) -> list[dict]:
    """Return all pages or databases visible to this integration."""
    results = []
    payload: dict = {
        "filter": {"value": filter_type, "property": "object"},
        "page_size": 100,
    }
    while True:
        data = _post(f"{NOTION_API}/search", payload)
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
        time.sleep(0.35)
    return results


# ── tasks from databases ──────────────────────────────────────────────────────

def _tasks_from_database(db_id: str) -> list[dict]:
    tasks = []
    payload: dict = {"page_size": 100}
    while True:
        data = _post(f"{NOTION_API}/databases/{db_id}/query", payload)
        for page in data.get("results", []):
            props = page.get("properties", {})
            if _is_done(props):
                continue
            title = _page_title(page)
            if not title or title == "(untitled)":
                continue
            tasks.append({
                "title": title,
                "status": _get_status(props),
                "due": _get_due(props),
                "url": page.get("url", ""),
                "source": "database",
            })
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
        time.sleep(0.35)
    return tasks


# ── tasks from page blocks (checkbox items) ───────────────────────────────────

def _tasks_from_page(page_id: str, page_url: str) -> list[dict]:
    """Extract unchecked to-do blocks from a plain page."""
    tasks = []
    url = f"{NOTION_API}/blocks/{page_id}/children"
    params: dict = {"page_size": 100}

    while True:
        data = _get(url, params=params)
        for block in data.get("results", []):
            if block.get("type") == "to_do":
                td = block["to_do"]
                if not td.get("checked", False):
                    text = "".join(
                        r.get("text", {}).get("content", "")
                        for r in td.get("rich_text", [])
                    )
                    if text:
                        tasks.append({
                            "title": text,
                            "status": "",
                            "due": "",
                            "url": page_url,
                            "source": "page",
                        })
        if not data.get("has_more"):
            break
        params["start_cursor"] = data["next_cursor"]
        time.sleep(0.35)

    return tasks


# ── public API ────────────────────────────────────────────────────────────────

def get_open_tasks() -> list[dict]:
    """
    Return all open tasks across every page and database shared with this integration.
    No database ID needed — share content with the integration and it appears here.
    """
    if not config.NOTION_API_KEY:
        return []

    tasks = []

    try:
        # Pull from all databases
        databases = _search_all("database")
        for db in databases:
            tasks.extend(_tasks_from_database(db["id"]))
            time.sleep(0.35)

        # Pull checkbox tasks from plain pages
        pages = _search_all("page")
        for page in pages:
            # Skip database rows (they show up in page search too)
            if page.get("parent", {}).get("type") == "database_id":
                continue
            tasks.extend(_tasks_from_page(page["id"], page.get("url", "")))
            time.sleep(0.35)

    except Exception as e:
        print(f"  [notion] skipped: {e}")

    return tasks
