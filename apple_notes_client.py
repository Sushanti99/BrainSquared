"""Apple Notes integration (macOS only).

Reads local Apple Notes data via osascript and returns:
- open checklist-like tasks from note bodies
- recently edited notes
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import config

JXA_SCRIPT = r"""
function valueOrEmpty(fn) {
  try { return fn(); } catch (e) { return ""; }
}

function walkFolder(folder, accountName, prefix, out) {
  var folderName = valueOrEmpty(function () { return folder.name(); });
  var folderPath = prefix ? (prefix + "/" + folderName) : folderName;

  var notes = valueOrEmpty(function () { return folder.notes(); }) || [];
  for (var i = 0; i < notes.length; i++) {
    var note = notes[i];
    var modified = valueOrEmpty(function () { return note.modificationDate(); });
    var modifiedIso = "";
    try { modifiedIso = (new Date(modified)).toISOString(); } catch (e) {}
    out.push({
      account: accountName,
      folder: folderPath,
      title: valueOrEmpty(function () { return note.name(); }),
      body_html: valueOrEmpty(function () { return note.body(); }),
      plaintext: valueOrEmpty(function () { return note.plaintext(); }),
      modified_at: modifiedIso,
      note_id: valueOrEmpty(function () { return note.id(); }),
    });
  }

  var subfolders = valueOrEmpty(function () { return folder.folders(); }) || [];
  for (var j = 0; j < subfolders.length; j++) {
    walkFolder(subfolders[j], accountName, folderPath, out);
  }
}

var app = Application("Notes");
var rows = [];
var accounts = app.accounts();
for (var i = 0; i < accounts.length; i++) {
  var account = accounts[i];
  var accountName = valueOrEmpty(function () { return account.name(); });
  var folders = valueOrEmpty(function () { return account.folders(); }) || [];
  for (var j = 0; j < folders.length; j++) {
    walkFolder(folders[j], accountName, "", rows);
  }
}
JSON.stringify(rows);
"""

_STRIP_TAGS_RE = re.compile(r"<[^>]+>")
_SPACES_RE = re.compile(r"\s+")
_HTML_UNCHECKED_RE = re.compile(
    r"<li[^>]*>\s*<input[^>]*type=['\"]checkbox['\"][^>]*(?!checked)[^>]*>\s*(.*?)</li>",
    re.IGNORECASE | re.DOTALL,
)


def _parse_datetime(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _clean_text(text: str) -> str:
    text = _STRIP_TAGS_RE.sub(" ", text or "")
    return _SPACES_RE.sub(" ", text).strip()


def _recent_snippet(plaintext: str, max_len: int = 140) -> str:
    for line in (plaintext or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^[-*]\s+\[[ xX]\]\s+", stripped):
            continue
        if any(stripped.startswith(prefix) for prefix in ("☐", "◻", "□", "☑", "✅", "✓")):
            continue
        return stripped[:max_len]
    return ""


def _extract_unchecked_tasks(body_html: str, plaintext: str) -> list[str]:
    items: list[str] = []

    # Prefer explicit checkbox HTML if present.
    for m in _HTML_UNCHECKED_RE.finditer(body_html or ""):
        candidate = _clean_text(m.group(1))
        if candidate:
            items.append(candidate)

    # Fallback for plaintext checklist markers.
    for line in (plaintext or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.search(r"^[-*]\s+\[[xX]\]\s+", stripped):
            continue
        if any(tok in stripped for tok in ("☑", "✅", "✔", "✓")):
            continue

        unchecked = None
        m_md = re.search(r"^[-*]\s+\[\s\]\s+(.+)$", stripped)
        if m_md:
            unchecked = m_md.group(1).strip()
        else:
            m_sym = re.search(r"^[\u2610\u25FB\u25FD]\s*(.+)$", stripped)
            if m_sym:
                unchecked = m_sym.group(1).strip()

        if unchecked:
            items.append(unchecked)

    unique: list[str] = []
    seen = set()
    for item in items:
        norm = item.lower()
        if norm in seen:
            continue
        seen.add(norm)
        unique.append(item)
    return unique


def _folder_allowed(folder: str) -> bool:
    folder_l = (folder or "").strip().lower()
    include = [f.lower() for f in config.APPLE_NOTES_INCLUDE_FOLDERS]
    exclude = [f.lower() for f in config.APPLE_NOTES_EXCLUDE_FOLDERS]

    if include and folder_l not in include:
        return False
    if exclude and folder_l in exclude:
        return False
    return True


def _run_notes_query() -> list[dict]:
    if sys.platform != "darwin":
        return []
    proc = subprocess.run(
        ["/usr/bin/osascript", "-l", "JavaScript", "-e", JXA_SCRIPT],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip() or "unknown osascript error"
        raise RuntimeError(stderr)
    raw = (proc.stdout or "").strip()
    if not raw:
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        return []
    return data


def get_apple_notes_data() -> dict:
    """Return Apple Notes tasks and recent notes. Never raises."""
    if not config.APPLE_NOTES_ENABLED:
        return {"tasks": [], "recent_notes": []}
    if sys.platform != "darwin":
        return {"tasks": [], "recent_notes": []}

    try:
        rows = _run_notes_query()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, config.APPLE_NOTES_RECENT_HOURS))

        tasks: list[dict] = []
        recent_notes: list[dict] = []

        for row in rows:
            account = (row.get("account") or "").strip()
            folder = (row.get("folder") or "").strip()
            if not _folder_allowed(folder):
                continue

            title = (row.get("title") or "").strip() or "(Untitled)"
            modified_raw = (row.get("modified_at") or "").strip()
            modified_dt = _parse_datetime(modified_raw)
            note_id = (row.get("note_id") or "").strip()
            body_html = row.get("body_html") or ""
            plaintext = row.get("plaintext") or ""

            if modified_dt and modified_dt >= cutoff:
                recent_notes.append(
                    {
                        "title": title,
                        "folder": folder,
                        "account": account,
                        "modified_at": modified_dt.isoformat(),
                        "note_id": note_id,
                        "snippet": _recent_snippet(plaintext),
                    }
                )

            for task_text in _extract_unchecked_tasks(body_html, plaintext):
                tasks.append(
                    {
                        "title": task_text,
                        "note_title": title,
                        "folder": folder,
                        "account": account,
                        "modified_at": modified_dt.isoformat() if modified_dt else "",
                        "note_id": note_id,
                    }
                )

        tasks.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
        recent_notes.sort(key=lambda x: x.get("modified_at", ""), reverse=True)

        return {
            "tasks": tasks[: max(1, config.APPLE_NOTES_MAX_TASKS)],
            "recent_notes": recent_notes[: max(1, config.APPLE_NOTES_MAX_RECENT)],
        }
    except Exception as e:
        print(f"  [apple_notes] skipped: {e}")
        return {"tasks": [], "recent_notes": []}
