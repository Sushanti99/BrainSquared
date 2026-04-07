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
        + (["obsidian"] if bundle.vault_notes else [])
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
