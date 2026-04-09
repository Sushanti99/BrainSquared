"""Generates a daily note in the Obsidian vault."""
import time
from datetime import date
from pathlib import Path
import config
from context_builder import ContextBundle


def generate(bundle: ContextBundle, vault_path: Path = config.VAULT_PATH) -> Path:
    """Write Daily/YYYY-MM-DD.md to the vault. Returns the written file path."""
    today = date.today()
    folder = vault_path / config.DAILY_FOLDER

    for attempt in range(3):
        try:
            folder.mkdir(parents=True, exist_ok=True)
            break
        except OSError:
            if attempt == 2:
                raise
            time.sleep(1)

    file_path = folder / f"{today.isoformat()}.md"

    sources = (
        (["calendar"] if bundle.calendar_events else [])
        + (["gmail"] if bundle.email_items else [])
        + (["notion"] if bundle.notion_tasks else [])
        + (["apple_notes"] if (bundle.apple_notes_tasks or bundle.apple_notes_recent) else [])
        + (["obsidian"] if bundle.vault_notes else [])
        + (["news"] if bundle.reading_list else [])
    )

    day_label = today.strftime("%A, %B %-d %Y")
    import datetime
    generated_at = datetime.datetime.now().strftime("%H:%M")

    lines = [
        "---",
        f"date: {today.isoformat()}",
        "type: daily",
        "generated: true",
        f"sources: [{', '.join(sources)}]",
        "---",
        "",
        f"# Daily Note — {day_label}",
        "",
        "## Calendar — Today's Events",
        "",
    ]

    if bundle.calendar_events:
        for e in bundle.calendar_events:
            if e["all_day"]:
                lines.append(f"- All-day :: {e['title']}")
            else:
                line = f"- {e['start']}–{e['end']} :: {e['title']}"
                if e["location"]:
                    line += f" @ {e['location']}"
                lines.append(line)
    else:
        lines.append("*No events today.*")

    lines += [
        "",
        "## Email — Action Items",
        "",
    ]

    if bundle.email_items:
        for e in bundle.email_items:
            lines.append(f"- [ ] {e['subject']} *(from: {e['from']})*")
    else:
        lines.append("*No unread emails in the last 24 hours.*")

    lines += [
        "",
        "## Notion Tasks",
        "",
    ]

    if bundle.notion_tasks:
        for t in bundle.notion_tasks:
            line = f"- [ ] {t['title']}"
            if t["due"]:
                line += f" · Due: {t['due']}"
            if t["url"]:
                line += f" · [Open]({t['url']})"
            lines.append(line)
    else:
        lines.append("*No open Notion tasks.*")

    lines += [
        "",
        "## Open Obsidian Tasks",
        "",
    ]

    open_vault_tasks = [
        (note.relative_path, task["text"])
        for note in bundle.vault_notes
        for task in note.tasks
        if not task["done"]
    ]

    if open_vault_tasks:
        for path, text in open_vault_tasks:
            lines.append(f"- [ ] {text} *(from: [[{Path(path).stem}]])*")
    else:
        lines.append("*No open tasks in vault.*")

    lines += [
        "",
        "## Apple Notes",
        "",
        "### Open Checklists",
        "",
    ]

    if bundle.apple_notes_tasks:
        for t in bundle.apple_notes_tasks:
            meta_parts = []
            if t.get("note_title"):
                meta_parts.append(t["note_title"])
            if t.get("folder"):
                meta_parts.append(t["folder"])
            meta = " · ".join(meta_parts)
            if meta:
                lines.append(f"- [ ] {t['title']} *(from: {meta})*")
            else:
                lines.append(f"- [ ] {t['title']}")
    else:
        lines.append("*No open checklist items found in Apple Notes.*")

    lines += [
        "",
        "### Recently Edited (24h)",
        "",
    ]

    if bundle.apple_notes_recent:
        for n in bundle.apple_notes_recent:
            folder = n.get("folder", "")
            modified_at = n.get("modified_at", "")
            if modified_at:
                try:
                    import datetime

                    mod_label = datetime.datetime.fromisoformat(
                        modified_at.replace("Z", "+00:00")
                    ).strftime("%H:%M")
                except Exception:
                    mod_label = modified_at
            else:
                mod_label = ""

            meta_parts = []
            if folder:
                meta_parts.append(folder)
            if mod_label:
                meta_parts.append(f"updated {mod_label}")
            meta = ", ".join(meta_parts)
            if meta:
                lines.append(f"- {n['title']} *({meta})*")
            else:
                lines.append(f"- {n['title']}")
    else:
        lines.append("*No recently edited Apple Notes in the last 24 hours.*")

    lines += [
        "",
        "## Reading — Today's Links",
        "",
    ]

    if bundle.reading_list:
        for a in bundle.reading_list:
            source = f" *({a['source']})*" if a.get("source") else ""
            lines.append(f"- [{a['title']}]({a['url']}){source}")
    else:
        lines.append("*No articles fetched.*")

    lines += [
        "",
        "---",
        f"*Generated at {generated_at} by todos-with-obsidian*",
    ]

    for attempt in range(3):
        try:
            file_path.write_text("\n".join(lines), encoding="utf-8")
            break
        except OSError:
            if attempt == 2:
                raise
            time.sleep(1)

    return file_path
