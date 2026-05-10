"""Prompt construction."""

from __future__ import annotations

from datetime import date
from brain.models import AppConfig, DailyContext, EnvConfig, SessionState, VaultPaths
from brain.vault import list_core_notes, read_daily_note


def _build_tools_section(env_cfg: EnvConfig | None) -> str:
    """Describe all MCP tools available to the agent based on connected integrations."""
    import os as _os

    lines = [
        "## Available Tools",
        "You have access to the following tools. Use them proactively — do not answer from memory alone when real data is available.",
        "",
        "**Vault / Obsidian** (always connected):",
        "- Read, create, and edit markdown notes in the user's vault using standard file tools.",
        "- When asked to create a note, write it to the correct vault folder. When asked about notes or tasks, read the relevant files first.",
        "- Daily notes live in the daily folder; core notes in the system folder; thoughts in the thoughts folder.",
        "",
    ]

    if env_cfg and env_cfg.google_token_file.exists():
        lines += [
            "**Gmail & Calendar** (Google connected) — call these when the user asks about emails or calendar:",
            "- `search_emails(query, from_sender, max_results)` — search Gmail. Use Gmail query syntax: `from:boss@co.com`, `subject:invoice`, `is:unread`, `after:2024/01/01`. Use `from_sender='email@domain.com'` as a shortcut for sender search.",
            "- `list_emails(days, max_results, query)` — list recent emails from the last N days.",
            "- `get_email(message_id)` — fetch full body of a specific email by ID.",
            "- `get_events(days_back, days_forward, timezone_name)` — fetch calendar events in a date range.",
            "- `get_todays_events(timezone_name)` — today's calendar events only.",
            "",
        ]

    has_github = bool(_os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN") or _os.environ.get("GITHUB_TOKEN"))
    if has_github:
        lines += [
            "**GitHub** (connected) — call these when the user asks about code, PRs, issues, or repos:",
            "- `list_issues(owner, repo, state)` — list issues for a repo.",
            "- `get_issue(owner, repo, issue_number)` — get details of a specific issue.",
            "- `list_pull_requests(owner, repo, state)` — list pull requests.",
            "- `get_pull_request(owner, repo, pull_number)` — get PR details and diff.",
            "- `list_notifications()` — get unread GitHub notifications.",
            "- `search_repositories(query)` — search GitHub repos.",
            "",
        ]

    has_notion = bool(_os.environ.get("NOTION_API_KEY"))
    if has_notion:
        lines += [
            "**Notion** (connected) — call these when the user asks about Notion pages, tasks, or databases:",
            "- Search and retrieve Notion pages and database entries using the available Notion MCP tools.",
            "- When the user asks to find or update a Notion page, use the MCP tools rather than guessing.",
            "",
        ]

    has_slack = bool(_os.environ.get("SLACK_BOT_TOKEN"))
    if has_slack:
        lines += [
            "**Slack** (connected) — call these when the user asks about Slack messages or channels:",
            "- List channels, read channel history, and search messages using the available Slack MCP tools.",
            "- When the user asks about a conversation or message in Slack, fetch it via MCP.",
            "",
        ]

    has_linear = bool(_os.environ.get("LINEAR_API_KEY"))
    if has_linear:
        lines += [
            "**Linear** (connected) — call these when the user asks about tickets, sprints, or engineering tasks:",
            "- Use the Linear MCP tools to list, search, and read issues and projects.",
            "- When the user mentions a ticket, sprint, or Linear issue, fetch it via MCP rather than guessing.",
            "",
        ]

    return "\n".join(lines)


def _format_history_turn(turn) -> str:
    speaker = turn.role.upper()
    if turn.agent_name:
        speaker = f"{speaker} ({turn.agent_name})"
    return f"{speaker}: {turn.content}"


def load_canonical_prompt(vault_paths: VaultPaths) -> str:
    prompt_path = vault_paths.system / "CLAUDE.md"
    if not prompt_path.exists():
        return ""
    return prompt_path.read_text(encoding="utf-8").strip()


def build_chat_prompt(
    app_cfg: AppConfig,
    session_state: SessionState,
    user_message: str,
    vault_paths: VaultPaths,
    integration_digest: DailyContext | None = None,
    *,
    inject_canonical_prompt: bool,
    live_integration_context: str | None = None,
    env_cfg: EnvConfig | None = None,
) -> str:
    today = date.today().isoformat()
    daily_content = read_daily_note(vault_paths, today)
    core_notes = list_core_notes(vault_paths)
    history = session_state.history[-app_cfg.session.history_turn_limit :]

    sections: list[str] = []
    if inject_canonical_prompt:
        canonical_prompt = load_canonical_prompt(vault_paths)
        if canonical_prompt:
            sections.append("## Operating Instructions")
            sections.append(canonical_prompt)

    sections.append(_build_tools_section(env_cfg))

    sections.append("## Current Date")
    sections.append(today)

    sections.append("## Vault Context")
    if daily_content:
        sections.append(f"Today's daily note exists at {app_cfg.vault.daily_folder}/{today}.md")
        sections.append(daily_content[:4000])
    else:
        sections.append(
            f"Today's daily note does not yet exist. If needed, create {app_cfg.vault.daily_folder}/{today}.md."
        )

    core_names = [note.relative_path for note in core_notes]
    sections.append("Core notes:")
    if core_names:
        sections.extend(f"- {name}" for name in core_names[:50])
    else:
        sections.append("- none")
    sections.append(f"Thought summaries are archival in {app_cfg.vault.thoughts_folder}/.")

    sections.append("## Recent Session History")
    if history:
        for turn in history:
            sections.append(_format_history_turn(turn))
    else:
        sections.append("No prior turns in this session.")

    if app_cfg.integrations.include_in_prompt and integration_digest is not None:
        sections.append("## Integration Digest")
        sections.append(
            f"Calendar items: {len(integration_digest.calendar_events)} | "
            f"Unread emails: {len(integration_digest.email_items)} | "
            f"Open Notion tasks: {len(integration_digest.notion_tasks)}"
        )

    if live_integration_context:
        sections.append("## Live Integration Data")
        sections.append(live_integration_context)

    sections.append("## Current User Message")
    sections.append(user_message)
    return "\n\n".join(sections)


def build_codex_prompt(
    app_cfg: AppConfig,
    session_state: SessionState,
    user_message: str,
    vault_paths: VaultPaths,
    integration_digest: DailyContext | None = None,
    live_integration_context: str | None = None,
) -> str:
    return build_chat_prompt(
        app_cfg,
        session_state,
        user_message,
        vault_paths,
        integration_digest,
        inject_canonical_prompt=True,
        live_integration_context=live_integration_context,
    )
