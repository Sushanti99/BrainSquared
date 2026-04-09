"""Aggregates all data sources into a context bundle for Claude."""
from dataclasses import dataclass, field
from datetime import date
import obsidian_reader
import gmail_client
import calendar_client
import notion_client
import apple_notes_client
import config


@dataclass
class ContextBundle:
    vault_notes: list = field(default_factory=list)
    calendar_events: list = field(default_factory=list)
    email_items: list = field(default_factory=list)
    notion_tasks: list = field(default_factory=list)
    apple_notes_tasks: list = field(default_factory=list)
    apple_notes_recent: list = field(default_factory=list)
    reading_list: list = field(default_factory=list)
    today: str = field(default_factory=lambda: date.today().isoformat())

    def to_prompt_text(self) -> str:
        parts = [f"Today is {self.today}.\n"]

        if self.calendar_events:
            parts.append("## Today's Calendar")
            for e in self.calendar_events:
                if e["all_day"]:
                    parts.append(f"- All-day: {e['title']}")
                else:
                    line = f"- {e['start']}–{e['end']}: {e['title']}"
                    if e["location"]:
                        line += f" @ {e['location']}"
                    parts.append(line)
            parts.append("")

        if self.email_items:
            parts.append("## Recent Unread Emails")
            for e in self.email_items:
                parts.append(f"- From: {e['from']} | {e['subject']}")
                if e["snippet"]:
                    parts.append(f"  {e['snippet'][:140]}")
            parts.append("")

        if self.notion_tasks:
            parts.append("## Notion Open Tasks")
            for t in self.notion_tasks:
                line = f"- {t['title']}"
                if t["due"]:
                    line += f" (due: {t['due']})"
                if t["status"]:
                    line += f" [{t['status']}]"
                parts.append(line)
            parts.append("")

        if self.apple_notes_tasks:
            parts.append("## Apple Notes Open Tasks")
            for t in self.apple_notes_tasks:
                line = f"- {t['title']} (from: {t['note_title']})"
                if t["folder"]:
                    line += f" [{t['folder']}]"
                parts.append(line)
            parts.append("")

        if self.apple_notes_recent:
            parts.append("## Apple Notes Recently Edited (24h)")
            for n in self.apple_notes_recent:
                line = f"- {n['title']}"
                if n["folder"]:
                    line += f" [{n['folder']}]"
                if n.get("snippet"):
                    line += f" — {n['snippet'][:100]}"
                parts.append(line)
            parts.append("")

        open_vault_tasks = [
            (note.relative_path, task["text"])
            for note in self.vault_notes
            for task in note.tasks
            if not task["done"]
        ]
        if open_vault_tasks:
            parts.append("## Open Obsidian Tasks")
            for path, text in open_vault_tasks[:30]:
                parts.append(f"- {text} (from: {path})")
            parts.append("")

        return "\n".join(parts)


def build_context() -> ContextBundle:
    """Fetch all data sources. Each source fails independently."""
    print("Loading data sources...")
    bundle = ContextBundle()

    try:
        all_notes = obsidian_reader.get_notes_with_tasks(
            vault_path=config.VAULT_PATH, only_open=True
        )
        # Exclude auto-generated daily notes to avoid feedback loops
        bundle.vault_notes = [n for n in all_notes if not n.frontmatter.get("generated")]
        print(f"  [obsidian] {len(bundle.vault_notes)} notes with open tasks")
    except Exception as e:
        print(f"  [obsidian] skipped: {e}")

    try:
        bundle.calendar_events = calendar_client.get_todays_events()
        print(f"  [calendar] {len(bundle.calendar_events)} events today")
    except Exception as e:
        print(f"  [calendar] skipped: {e}")

    try:
        bundle.email_items = gmail_client.get_action_items()
        print(f"  [gmail] {len(bundle.email_items)} unread emails")
    except Exception as e:
        print(f"  [gmail] skipped: {e}")

    try:
        bundle.notion_tasks = notion_client.get_open_tasks()
        print(f"  [notion] {len(bundle.notion_tasks)} open tasks")
    except Exception as e:
        print(f"  [notion] skipped: {e}")

    try:
        apple = apple_notes_client.get_apple_notes_data()
        bundle.apple_notes_tasks = apple.get("tasks", [])
        bundle.apple_notes_recent = apple.get("recent_notes", [])
        print(
            f"  [apple_notes] {len(bundle.apple_notes_tasks)} tasks, "
            f"{len(bundle.apple_notes_recent)} recent notes"
        )
    except Exception as e:
        print(f"  [apple_notes] skipped: {e}")

    try:
        from news_client import get_reading_list
        all_vault_notes = obsidian_reader.read_vault(vault_path=config.VAULT_PATH)
        bundle.reading_list = get_reading_list(all_vault_notes)
        print(f"  [news] {len(bundle.reading_list)} articles")
    except Exception as e:
        print(f"  [news] skipped: {e}")

    return bundle
