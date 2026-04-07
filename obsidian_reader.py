"""
Obsidian vault reader — reads and parses all markdown notes from a local vault.
"""

import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


VAULT_PATH = Path("/Users/acer/Documents/Obsidian Vault")


@dataclass
class ObsidianNote:
    path: Path
    relative_path: str
    title: str
    content: str
    raw_content: str
    frontmatter: dict
    tags: list[str]
    links: list[str]          # [[wikilinks]]
    tasks: list[dict]         # {text, done, line}
    folder: str


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and return (metadata, body)."""
    if not text.startswith("---"):
        return {}, text

    end = text.find("\n---", 3)
    if end == -1:
        return {}, text

    yaml_block = text[4:end].strip()
    body = text[end + 4:].lstrip("\n")
    metadata = {}

    for line in yaml_block.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            metadata[key.strip()] = val.strip()

    return metadata, body


def extract_tags(text: str, frontmatter: dict) -> list[str]:
    """Extract #tags from body and tags field from frontmatter."""
    tags = set()

    # Inline tags like #todo #project
    for match in re.finditer(r"(?<!\S)#([a-zA-Z0-9_/-]+)", text):
        tags.add(match.group(1))

    # Frontmatter tags field (comma-separated or single)
    if "tags" in frontmatter:
        raw = frontmatter["tags"]
        for t in re.split(r"[,\s]+", raw):
            t = t.strip().lstrip("#")
            if t:
                tags.add(t)

    return sorted(tags)


def extract_links(text: str) -> list[str]:
    """Extract [[wikilink]] targets."""
    return re.findall(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]", text)


def extract_tasks(text: str) -> list[dict]:
    """Extract markdown tasks: - [ ] and - [x]."""
    tasks = []
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"\s*-\s+\[([ xX])\]\s+(.*)", line)
        if m:
            tasks.append({
                "done": m.group(1).lower() == "x",
                "text": m.group(2).strip(),
                "line": i,
            })
    return tasks


def read_note(path: Path, vault_root: Path) -> ObsidianNote:
    """Parse a single .md file into an ObsidianNote."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    frontmatter, body = parse_frontmatter(raw)

    title = frontmatter.get("title") or path.stem
    relative = str(path.relative_to(vault_root))
    folder = str(path.parent.relative_to(vault_root)) if path.parent != vault_root else ""

    return ObsidianNote(
        path=path,
        relative_path=relative,
        title=title,
        content=body,
        raw_content=raw,
        frontmatter=frontmatter,
        tags=extract_tags(body, frontmatter),
        links=extract_links(body),
        tasks=extract_tasks(body),
        folder=folder,
    )


def read_vault(vault_path: Path = VAULT_PATH) -> list[ObsidianNote]:
    """Read all .md files from the vault, skipping the .obsidian config dir."""
    notes = []
    for md_file in sorted(vault_path.rglob("*.md")):
        # Skip .obsidian internal files
        if ".obsidian" in md_file.parts:
            continue
        try:
            notes.append(read_note(md_file, vault_path))
        except Exception as e:
            print(f"[warn] Could not read {md_file}: {e}")
    return notes


def get_notes_with_tag(tag: str, vault_path: Path = VAULT_PATH) -> list[ObsidianNote]:
    return [n for n in read_vault(vault_path) if tag in n.tags]


def get_notes_with_tasks(vault_path: Path = VAULT_PATH, only_open: bool = False) -> list[ObsidianNote]:
    notes = []
    for note in read_vault(vault_path):
        tasks = [t for t in note.tasks if not t["done"]] if only_open else note.tasks
        if tasks:
            notes.append(note)
    return notes


def get_notes_in_folder(folder: str, vault_path: Path = VAULT_PATH) -> list[ObsidianNote]:
    return [n for n in read_vault(vault_path) if n.folder.startswith(folder)]


def search_notes(query: str, vault_path: Path = VAULT_PATH) -> list[ObsidianNote]:
    """Case-insensitive full-text search."""
    q = query.lower()
    return [n for n in read_vault(vault_path) if q in n.content.lower() or q in n.title.lower()]


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"

    if cmd == "summary":
        notes = read_vault()
        folders: dict[str, int] = {}
        total_tasks = 0
        for n in notes:
            folders[n.folder or "(root)"] = folders.get(n.folder or "(root)", 0) + 1
            total_tasks += len(n.tasks)
        print(f"Vault: {VAULT_PATH}")
        print(f"Notes: {len(notes)}  |  Tasks found: {total_tasks}")
        print("\nFolders:")
        for folder, count in sorted(folders.items()):
            print(f"  {folder or '(root)':<40} {count} notes")

    elif cmd == "tasks":
        only_open = "--open" in sys.argv
        notes = get_notes_with_tasks(only_open=only_open)
        label = "open" if only_open else "all"
        print(f"Notes with {label} tasks:\n")
        for n in notes:
            tasks = [t for t in n.tasks if not t["done"]] if only_open else n.tasks
            print(f"  {n.relative_path}")
            for t in tasks:
                status = "[ ]" if not t["done"] else "[x]"
                print(f"    {status} {t['text']}")

    elif cmd == "search" and len(sys.argv) > 2:
        results = search_notes(sys.argv[2])
        print(f"Results for '{sys.argv[2]}':\n")
        for n in results:
            print(f"  {n.relative_path}")

    elif cmd == "tag" and len(sys.argv) > 2:
        results = get_notes_with_tag(sys.argv[2])
        print(f"Notes tagged #{sys.argv[2]}:\n")
        for n in results:
            print(f"  {n.relative_path}")

    elif cmd == "folder" and len(sys.argv) > 2:
        results = get_notes_in_folder(sys.argv[2])
        print(f"Notes in '{sys.argv[2]}':\n")
        for n in results:
            print(f"  {n.relative_path}")

    else:
        print("Usage:")
        print("  python obsidian_reader.py summary")
        print("  python obsidian_reader.py tasks [--open]")
        print("  python obsidian_reader.py search <query>")
        print("  python obsidian_reader.py tag <tag>")
        print("  python obsidian_reader.py folder <folder-name>")
