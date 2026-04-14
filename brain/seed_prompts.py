"""Prompt construction for brain seed."""

from __future__ import annotations

from datetime import date

from brain.models import VaultPaths


def build_seed_prompt(vault_paths: VaultPaths) -> str:
    today = date.today().isoformat()
    seed_input_rel = f"{vault_paths.system.name}/_seed_input.md"
    daily_rel = f"{vault_paths.daily.name}/{today}.md"
    core_rel = vault_paths.core.name
    refs_rel = vault_paths.references.name

    return f"""You are setting up a Brain vault for the first time.

Read the file {seed_input_rel} — it contains a snapshot of the user's existing data: notes, tasks, emails, calendar events, and pages from their tools.

Your job: create a minimal, useful set of notes the user can build on top of. Write directly into the vault.

## What to create

**{core_rel}/** — 3 to 5 notes, no more. Good candidates:
- `profile.md` — who this person is, their role, focus areas (infer from the data)
- `projects.md` — ongoing projects and what they're working on right now
- `interests.md` — recurring topics, technologies, or domains that show up across sources
- `people.md` — key collaborators or contacts if they appear frequently (skip if sparse)

**{refs_rel}/** — only if there's concrete reference material worth keeping (links, docs, resources). Skip if there isn't.

**{daily_rel}** — today's daily note with a brief useful overview: top tasks, calendar events, anything actionable from the data.

## Rules
- Keep notes short and dense. Users don't like essays.
- Prefer 3 good notes over 10 mediocre ones.
- Use [[wikilinks]] between related notes where natural.
- Don't create empty or nearly-empty notes — if there's not enough signal, skip it.
- Don't create folders beyond what's listed above.

When you're done, delete {seed_input_rel}.
"""
