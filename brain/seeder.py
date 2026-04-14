"""brain seed — collect data from existing tools and synthesize a pre-populated vault."""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import shutil
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from brain.app_config import default_app_config
from brain.env_config import load_env_config
from brain.init_vault import initialize_vault
from brain.models import EnvConfig, VaultPaths
from brain.seed_prompts import build_seed_prompt
from brain.vault import resolve_vault_paths


@dataclass(slots=True)
class SeedSources:
    from_obsidian: Path | None = None
    from_notion: bool = False
    from_gmail: bool = False
    from_calendar: bool = False


@dataclass(slots=True)
class SeedResult:
    vault_path: Path
    sources_used: list[str] = field(default_factory=list)
    notes_created: list[str] = field(default_factory=list)


# ── collection ─────────────────────────────────────────────────────────────────

def collect_obsidian_notes(source_path: Path) -> str:
    """Read non-daily, non-generated notes from an existing vault."""
    if not source_path.exists():
        return ""

    sections: list[str] = []
    daily_like = {"daily", "日記", "journal"}

    for md_file in sorted(source_path.rglob("*.md")):
        # Skip daily notes folder and generated files
        parts_lower = {p.lower() for p in md_file.parts}
        if parts_lower & daily_like:
            continue
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore").strip()
        except OSError:
            continue
        if not text or "generated: true" in text[:200]:
            continue
        rel = md_file.relative_to(source_path)
        sections.append(f"### {rel}\n{text[:1500]}")
        if len(sections) >= 60:
            break

    if not sections:
        return ""
    return "## Existing Obsidian Notes\n\n" + "\n\n".join(sections)


def collect_notion_context(env_cfg: EnvConfig) -> str:
    """Fetch Notion tasks and page content."""
    if not env_cfg.notion_api_key:
        return ""
    try:
        notion = _load_legacy("notion_client", env_cfg)
        sections: list[str] = []

        tasks = notion.get_open_tasks()
        if tasks:
            task_lines = "\n".join(f"- {t['title']}" + (f" [{t['status']}]" if t.get("status") else "") for t in tasks[:40])
            sections.append(f"### Open Tasks\n{task_lines}")

        if hasattr(notion, "get_pages_content"):
            pages = notion.get_pages_content(max_pages=15)
            if pages:
                page_parts = []
                for p in pages:
                    body = p.get("content", "").strip()
                    entry = f"**{p['title']}**"
                    if body:
                        entry += f"\n{body[:600]}"
                    page_parts.append(entry)
                sections.append("### Pages\n" + "\n\n".join(page_parts))

        if not sections:
            return ""
        return "## Notion\n\n" + "\n\n".join(sections)
    except Exception as e:
        print(f"  [notion] skipped: {e}")
        return ""


def collect_gmail_context(env_cfg: EnvConfig) -> str:
    """Fetch broader Gmail context to understand interests and commitments."""
    token_ok = env_cfg.google_token_file.exists() or env_cfg.google_credentials_file.exists()
    if not token_ok:
        return ""
    try:
        gmail = _load_legacy("gmail_client", env_cfg)

        if hasattr(gmail, "get_context_threads"):
            ctx = gmail.get_context_threads(days=90, max_results=60)
        else:
            # Fall back to action items only
            items = gmail.get_action_items(max_results=20)
            if not items:
                return ""
            lines = "\n".join(f"- {i['subject']} (from: {i['from']})" for i in items)
            return f"## Gmail (recent unread)\n\n{lines}"

        parts: list[str] = []
        if ctx.get("top_senders"):
            lines = "\n".join(f"- {s['name']} ({s['count']} messages)" for s in ctx["top_senders"])
            parts.append(f"### Frequent contacts\n{lines}")
        if ctx.get("recent_subjects"):
            lines = "\n".join(f"- {s}" for s in ctx["recent_subjects"][:25])
            parts.append(f"### Recent thread subjects\n{lines}")

        if not parts:
            return ""
        return "## Gmail (last 90 days)\n\n" + "\n\n".join(parts)
    except Exception as e:
        print(f"  [gmail] skipped: {e}")
        return ""


def collect_calendar_context(env_cfg: EnvConfig) -> str:
    """Fetch calendar events over a wider range to surface projects and commitments."""
    token_ok = env_cfg.google_token_file.exists() or env_cfg.google_credentials_file.exists()
    if not token_ok:
        return ""
    try:
        calendar = _load_legacy("calendar_client", env_cfg)

        if hasattr(calendar, "get_events_range"):
            events = calendar.get_events_range(days_back=30, days_forward=60)
        else:
            events = calendar.get_todays_events()

        if not events:
            return ""

        recurring = [e for e in events if e.get("recurring")]
        one_off = [e for e in events if not e.get("recurring")]

        parts: list[str] = []
        if recurring:
            lines = "\n".join(f"- {e['title']}" for e in _deduplicate_events(recurring)[:15])
            parts.append(f"### Recurring commitments\n{lines}")
        if one_off:
            lines = "\n".join(f"- {e.get('date', '')} {e['title']}" for e in one_off[:20])
            parts.append(f"### Upcoming events\n{lines}")

        return "## Calendar (past 30 days + next 60 days)\n\n" + "\n\n".join(parts)
    except Exception as e:
        print(f"  [calendar] skipped: {e}")
        return ""


def _deduplicate_events(events: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for e in events:
        t = e["title"]
        if t not in seen:
            seen.add(t)
            out.append(e)
    return out


# ── seed input file ────────────────────────────────────────────────────────────

def write_seed_input(vault_paths: VaultPaths, sections: list[str]) -> Path:
    """Write collected data to system/_seed_input.md."""
    today = date.today().isoformat()
    content = f"# Seed Input\n_Generated {today} — delete after processing._\n\n"
    content += "\n\n".join(s for s in sections if s.strip())
    seed_path = vault_paths.system / "_seed_input.md"
    seed_path.write_text(content, encoding="utf-8")
    return seed_path


# ── synthesis via claude CLI ───────────────────────────────────────────────────

async def _synthesize(vault_paths: VaultPaths) -> None:
    """Run claude CLI via stdin to synthesize seed_input.md into vault notes."""
    claude_bin = shutil.which("claude")
    if not claude_bin:
        raise RuntimeError("claude CLI not found on PATH. Install Claude Code first.")

    prompt = build_seed_prompt(vault_paths)
    allowed_tools = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]

    cmd = [
        claude_bin, "--print",
        "--output-format", "stream-json",
        "--verbose",
        "--allowedTools", *allowed_tools,
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(vault_paths.root),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await asyncio.wait_for(
        process.communicate(prompt.encode()),
        timeout=300,
    )

    if process.returncode != 0:
        err = stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"claude exited {process.returncode}: {err}")


# ── orchestration ──────────────────────────────────────────────────────────────

def run_seed(
    vault_path: Path,
    agent: str,
    sources: SeedSources,
    dry_run: bool = False,
) -> SeedResult:
    """Collect data, write seed input, run agent synthesis."""
    vault_path = vault_path.expanduser().resolve()

    # Warn if vault already has notes
    existing_notes = list(vault_path.rglob("*.md")) if vault_path.exists() else []
    # Exclude system files from the count
    existing_notes = [p for p in existing_notes if "system" not in p.parts]
    if existing_notes:
        print(f"\nVault at {vault_path} already contains {len(existing_notes)} note(s).")
        answer = input("  Seed will add new notes and may overwrite existing ones. Continue? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return SeedResult(vault_path=vault_path)

    print(f"Initializing vault at {vault_path} ...")
    initialize_vault(vault_path, agent=agent)
    vault_paths = resolve_vault_paths(
        default_app_config(vault_path, agent)
    )

    env_cfg = load_env_config()

    # Configure legacy config module so integration clients can find credentials
    cfg = _load_legacy("config")
    cfg.VAULT_PATH = vault_path
    cfg.GOOGLE_CREDENTIALS_FILE = env_cfg.google_credentials_file
    cfg.GOOGLE_TOKEN_FILE = env_cfg.google_token_file
    cfg.NOTION_API_KEY = env_cfg.notion_api_key

    result = SeedResult(vault_path=vault_path)
    sections: list[str] = []

    if sources.from_obsidian:
        print(f"  Collecting Obsidian notes from {sources.from_obsidian} ...")
        text = collect_obsidian_notes(sources.from_obsidian)
        if text:
            sections.append(text)
            result.sources_used.append(f"Obsidian ({sources.from_obsidian})")

    if sources.from_notion:
        print("  Collecting Notion ...")
        text = collect_notion_context(env_cfg)
        if text:
            sections.append(text)
            result.sources_used.append("Notion")

    if sources.from_gmail:
        print("  Collecting Gmail (last 90 days) ...")
        text = collect_gmail_context(env_cfg)
        if text:
            sections.append(text)
            result.sources_used.append("Gmail")

    if sources.from_calendar:
        print("  Collecting Calendar ...")
        text = collect_calendar_context(env_cfg)
        if text:
            sections.append(text)
            result.sources_used.append("Calendar")

    if not sections:
        print("No source data collected. Run with at least one --from-* flag.")
        return result

    print(f"\nSources: {', '.join(result.sources_used)}")

    seed_path = write_seed_input(vault_paths, sections)
    print(f"Seed input written to {seed_path.relative_to(vault_path)}")

    if dry_run:
        print("\n[dry-run] Skipping agent synthesis. Seed input left in place.")
        return result

    print("\nSynthesizing vault with Claude CLI...")
    asyncio.run(_synthesize(vault_paths))

    notes_created = [
        str(p.relative_to(vault_path))
        for p in vault_paths.root.rglob("*.md")
        if p.parent != vault_paths.system
    ]
    result.notes_created.extend(notes_created)
    print(f"\nVault ready. Notes: {', '.join(notes_created) or 'none'}")

    return result


# ── helpers ────────────────────────────────────────────────────────────────────

def _load_legacy(module_name: str, env_cfg: EnvConfig | None = None):  # noqa: ARG001
    """Load a legacy root-level module by name."""
    if module_name in sys.modules:
        return sys.modules[module_name]
    project_root = Path(__file__).resolve().parent.parent
    module_path = project_root / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {module_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
