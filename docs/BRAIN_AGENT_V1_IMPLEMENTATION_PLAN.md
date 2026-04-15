# idli V1 — Engineering Code Spec

## 1. Purpose

This document is the implementation spec for idli V1 in this repository.

It replaces the earlier high-level plan with a tighter engineering contract:

- exact product scope
- exact repo/module layout
- exact runtime responsibilities
- exact CLI, HTTP, and WebSocket contracts
- exact vault conversion rules
- exact migration strategy from the current codebase
- exact delivery phases and acceptance tests
- resolved product decisions and locked engineering defaults

This spec is authoritative for idli V1 unless later amended.

## 2. Product Summary

idli is a local-first personal agent harness on top of an Obsidian vault.

The user should be able to:

1. initialize or convert an Obsidian vault into idli format
2. start a local Python server
3. interact through a minimal browser chat UI
4. have Claude Code or Codex operate directly on the vault
5. generate daily notes from Gmail, Calendar, Notion, vault data, and news
6. end a session and persist only a summary into `thoughts/`

The user should not need to open Obsidian files manually for normal operation.

## 3. Locked Product Decisions

These decisions are already confirmed:

- implementation language: Python only
- product name: `brain`
- supported V1 agents: Claude Code and Codex
- V1 session model: single active session, single browser tab
- storage model: Obsidian vault is the primary database
- external integrations remain in repo: Gmail, Google Calendar, Notion, news
- V1 priority: Obsidian-first product; integrations are supporting systems
- agent permissions: broad normal read/write behavior inside the vault, controlled by prompt rules rather than hard sandboxing
- vault initialization: support both fresh vault creation and non-destructive conversion of existing vaults
- daily note generation stays first-class in both CLI and web UI
- session storage: summary only, written to `thoughts/`
- deployment target: macOS first
- preserve existing vault folder names through config rather than auto-migrating them
- support mapping existing user folders into idli config when they already match Brain concepts
- refuse daily note overwrite by default if today’s note already exists
- cancel active agent execution and summarize partial history when ending a session
- reconnect browser refreshes to the same in-memory session
- rely on `system/CLAUDE.md` as the canonical prompt file for Claude
- inject the canonical prompt content into Codex requests rather than inventing a second prompt-file convention in V1
- use Gmail/Calendar/Notion/news only for daily note generation by default, not normal chat prompts
- add `pyproject.toml` in V1
- add an installable `brain` console script in V1
- keep `main.py` as a temporary compatibility wrapper during migration

## 4. V1 Goals

### 4.1 In scope

- Python package-based application
- local server with browser UI
- single-file frontend
- WebSocket streaming
- Claude Code backend
- Codex backend
- vault-aware prompt construction
- session memory for one active session
- summarized session persistence
- vault initialization and conversion
- daily note generation from existing integrations
- local CLI entrypoint `brain`

### 4.2 Explicitly out of scope

- multi-user support
- auth/login
- mobile app
- Obsidian plugin
- VPS deployment
- Gemini backend
- raw transcript persistence
- scheduled/background jobs
- vector search / embeddings / RAG
- deep server-side policy engine for tool restrictions

## 5. Current Repo Baseline

The current repository is a flat Python toolset:

- [main.py](/Users/sanjit/Desktop/san/todos-with-obsidian/main.py)
- [chat.py](/Users/sanjit/Desktop/san/todos-with-obsidian/chat.py)
- [daily_note.py](/Users/sanjit/Desktop/san/todos-with-obsidian/daily_note.py)
- [context_builder.py](/Users/sanjit/Desktop/san/todos-with-obsidian/context_builder.py)
- [obsidian_reader.py](/Users/sanjit/Desktop/san/todos-with-obsidian/obsidian_reader.py)
- [config.py](/Users/sanjit/Desktop/san/todos-with-obsidian/config.py)
- [setup.py](/Users/sanjit/Desktop/san/todos-with-obsidian/setup.py)
- integration clients:
  - [gmail_client.py](/Users/sanjit/Desktop/san/todos-with-obsidian/gmail_client.py)
  - [calendar_client.py](/Users/sanjit/Desktop/san/todos-with-obsidian/calendar_client.py)
  - [notion_client.py](/Users/sanjit/Desktop/san/todos-with-obsidian/notion_client.py)
  - [news_client.py](/Users/sanjit/Desktop/san/todos-with-obsidian/news_client.py)

Useful current assets:

- vault reading/parsing already exists
- daily note generation already exists
- integration setup flow already exists
- prompt/context aggregation exists, though for API chat rather than local agent CLIs

Primary mismatch:

- current chat path is Anthropic API terminal chat
- target product is local server + browser UI + local agent CLI harness

Conclusion:

idli V1 is a structured refactor and product pivot, not a full rewrite from zero.

## 6. Architecture Overview

### 6.1 Runtime layers

1. Vault layer
   - file system operations over an Obsidian vault
   - source of truth for notes, daily tasks, references, and session summaries

2. idli server layer
   - Python web server
   - config loading
   - prompt construction
   - backend process orchestration
   - session state
   - summary persistence

3. Agent backend layer
   - Claude Code adapter
   - Codex adapter
   - backend-specific streaming parsers

4. Browser UI layer
   - static HTML
   - WebSocket chat client
   - markdown rendering
   - daily-note and end-session controls

### 6.2 Recommended server stack

- `FastAPI`
- `uvicorn`
- `PyYAML`
- `python-dotenv`
- `markdown-it-py` or frontend-side CDN markdown renderer
- `asyncio.create_subprocess_exec`

Rationale:

- WebSocket support is required
- async subprocess streaming is required
- static asset serving is trivial
- no database is needed

## 7. Target Repo Layout

```text
brain/
├── __init__.py
├── cli.py
├── app_config.py
├── env_config.py
├── init_vault.py
├── vault.py
├── prompts.py
├── agent_backends.py
├── session.py
├── summarizer.py
├── daily.py
├── server.py
├── models.py
├── utils.py
├── web/
│   └── index.html
└── templates/
    ├── CLAUDE.md
    ├── brain.config.yaml
    └── daily_note.md

tests/
├── test_init_vault.py
├── test_app_config.py
├── test_daily.py
├── test_prompt_builder.py
├── test_session.py
├── test_server_ws.py
└── test_backends.py

docs/
├── PRODUCT_SPEC_BRAIN_AGENT.md
└── BRAIN_AGENT_V1_IMPLEMENTATION_PLAN.md
```

### 7.1 Why `app_config.py` and `env_config.py`

The current repo already has a top-level [config.py](/Users/sanjit/Desktop/san/todos-with-obsidian/config.py). Reusing the same name inside `brain/` would be workable, but it increases migration confusion.

Use:

- `brain/app_config.py` for `brain.config.yaml`
- `brain/env_config.py` for `.env` integration credentials

This avoids ambiguous imports during the migration.

## 8. Data Model and Folder Contracts

### 8.1 Required vault folders

idli V1 expects these folders to exist:

- `daily/`
- `core/`
- `references/`
- `thoughts/`
- `system/`

### 8.2 Conversion rules for existing vaults

idli V1 must support an existing vault without destructive modification.

Rules:

1. Never rename existing folders automatically.
2. Never move existing user notes automatically.
3. Only create missing idli folders/files.
4. If a compatible `system/brain.config.yaml` already exists, load it as-is.
5. If `system/CLAUDE.md` already exists, do not overwrite it without explicit flag.
6. If an existing vault uses a different daily note folder, store that in config rather than forcing a migration immediately.
7. If an existing vault already has folders that correspond to daily, core, references, or thoughts, support mapping them into config instead of duplicating structure blindly.

This is important because the current code defaults to `Daily` while the idli spec uses `daily`.

### 8.3 Folder naming compatibility

idli V1 must support:

- canonical folder names in config
- a default canonical structure for new vaults
- legacy/custom folder names in existing vaults through config

Minimum configurable folder keys:

- `daily_folder`
- `core_folder`
- `references_folder`
- `thoughts_folder`
- `system_folder`

### 8.4 Thoughts summary contract

Output path:

`<thoughts_folder>/YYYY-MM-DD-session-N.md`

Required contents:

```markdown
---
date: 2026-04-11
session: 1
agent: claude-code
duration_minutes: 14
---

# Session Summary

## Topics Discussed
- ...

## Decisions Made
- ...

## Files Modified
- ...

## Action Items
- ...
```

Raw transcript is not stored in V1.

## 9. Configuration Spec

### 9.1 `system/brain.config.yaml`

Canonical V1 schema:

```yaml
agent: claude-code

server:
  host: 127.0.0.1
  port: 3000
  auto_open_browser: true

vault:
  path: /absolute/path/to/vault
  daily_folder: daily
  core_folder: core
  references_folder: references
  thoughts_folder: thoughts
  system_folder: system

session:
  single_session: true
  history_turn_limit: 10
  summarize_on_end: true
  auto_save_summary: true
  inactivity_timeout_seconds: 120

agents:
  claude-code:
    command: claude
    args:
      - -p
      - --output-format
      - stream-json
    allowed_tools:
      - Read
      - Edit
      - Bash
      - Glob
      - Grep

  codex:
    command: codex
    args:
      - exec
      - --json

integrations:
  enable_daily_context: true
  include_in_prompt: false
```

### 9.2 Config loading rules

Load order:

1. explicit `--config` path if supplied
2. `<vault>/system/brain.config.yaml`
3. fail with a clear error

Validation rules:

- vault path must exist for `start`, `status`, and `daily`
- missing vault path is allowed during `init`
- agent must be one of `claude-code` or `codex`
- port must be an integer in valid range
- history turn limit must be positive

### 9.3 `.env`

Keep `.env` for:

- `GOOGLE_CREDENTIALS_FILE`
- `GOOGLE_TOKEN_FILE`
- `NOTION_API_KEY`
- `NEWS_FEEDS`
- any agent auth environment variables the CLIs already use

idli server behavior should not depend on `.env` except for optional integrations and CLI auth env passthrough.

## 10. CLI Spec

Use `argparse` for V1 to minimize dependencies and preserve current repo style.

### 10.1 `brain init`

Purpose:

- create a new idli-compatible vault
- or convert an existing vault non-destructively

Flags:

- `--vault PATH`
- `--agent claude-code|codex`
- `--force-create-daily`
- `--overwrite-system-files`

Behavior:

1. resolve target path
2. if path does not exist, create it
3. create missing idli folders
4. detect and persist folder mappings for existing compatible user folders where applicable
5. write default `CLAUDE.md` and `brain.config.yaml` if absent
6. optionally create today’s daily note
7. print exactly what was created vs reused

Exit conditions:

- success: exit 0
- invalid path or permissions issue: exit non-zero with precise message

### 10.2 `brain start`

Purpose:

- start the local idli server

Flags:

- `--vault PATH`
- `--config PATH`
- `--agent claude-code|codex`
- `--port INT`
- `--no-open`

Behavior:

1. load config
2. validate agent binary exists
3. validate vault structure
4. start FastAPI/uvicorn
5. optionally open browser on macOS

### 10.3 `brain status`

Purpose:

- show readiness of vault, config, integrations, and configured backend

Output should include:

- vault path
- configured agent
- agent binary path and version
- server port
- folder mapping
- integration availability:
  - Google credentials present or missing
  - Notion configured or missing
  - news feeds configured or default-only

### 10.4 `brain daily`

Purpose:

- generate today’s daily note directly from CLI

Flags:

- `--vault PATH`
- `--config PATH`
- `--force`

Behavior:

1. load integrations
2. build daily context
3. render/write daily note
4. print output path

## 11. HTTP and WebSocket API Spec

### 11.1 HTTP routes

- `GET /`
  - serves the single-file web UI

- `GET /api/status`
  - returns server, session, vault, and integration status

- `POST /api/daily`
  - generates today’s daily note
  - returns JSON with file path and status

- `POST /api/session/end`
  - ends the active session
  - triggers summarization

### 11.2 WebSocket route

- `GET /ws`

Single connection only in V1.

If a second client connects while one is active:

- server rejects the connection with an error payload and closes it

### 11.3 Client -> server WebSocket messages

Schema:

```json
{ "type": "message", "content": "User text" }
```

Optional future-safe message types:

- `ping`
- `cancel`

V1 required behavior:

- if a message arrives while an agent run is already active, reject with `busy`

### 11.4 Server -> client WebSocket messages

Required types:

```json
{ "type": "session", "session_id": "2026-04-11-session-1", "agent": "claude-code" }
{ "type": "status", "state": "thinking" }
{ "type": "chunk", "content": "partial text" }
{ "type": "done", "content": "full text" }
{ "type": "error", "message": "Readable error message" }
{ "type": "busy", "message": "Agent run already in progress" }
```

Optional:

```json
{ "type": "daily_generated", "path": "daily/2026-04-11.md" }
```

## 12. Frontend Spec

File:

- `brain/web/index.html`

Constraints:

- single file only
- inline CSS and JS only
- no build step
- no React/Vue/Svelte

Required UI elements:

- header with:
  - product name
  - current agent
  - session ID
  - `Generate Daily` button
  - `End & Summarize` button
- scrollable message list
- input textarea
- send button

Required interactions:

- Enter sends
- Shift+Enter inserts newline
- responses stream into the active assistant bubble
- input is disabled during backend execution
- visible thinking state
- errors displayed inline

Frontend library policy:

- Markdown rendering may use a CDN library
- syntax highlighting is optional in V1

## 13. Session Model

### 13.1 Session lifecycle

States:

- `idle`
- `connected`
- `running`
- `summarizing`
- `closed`

### 13.2 Session object

Minimum fields:

```python
SessionState(
    session_id: str,
    started_at: datetime,
    agent_name: str,
    history: list[Turn],
    running: bool,
    websocket_connected: bool,
    modified_files: set[str],
)
```

### 13.3 Turn model

```python
Turn(
    role: Literal["user", "assistant"],
    content: str,
    created_at: datetime,
)
```

### 13.4 Message concurrency policy

Only one agent run at a time.

If the UI sends another message while a run is active:

- do not queue it
- return `busy`

This avoids hidden state complexity in V1.

### 13.5 End session behavior

When ending a session:

1. reject if no session exists
2. if a run is active, cancel it and preserve partial history
3. summarize history
4. write summary file
5. clear in-memory state
6. notify client

This is locked V1 behavior.

## 14. Agent Backend Spec

## 14.1 Shared backend interface

Each backend adapter must implement:

```python
class AgentBackend(Protocol):
    name: str

    def validate_installation(self) -> BackendValidationResult: ...
    def version(self) -> str: ...
    def build_command(self, prompt: str, app_cfg: AppConfig) -> list[str]: ...
    async def stream(self, prompt: str, cwd: Path, env: dict[str, str]) -> AsyncIterator[BackendEvent]: ...
    async def summarize(self, prompt: str, cwd: Path, env: dict[str, str]) -> str: ...
```

### 14.2 Common backend event model

```python
BackendEvent(
    type: Literal["status", "chunk", "done", "error"],
    content: str | None = None,
    raw: dict | str | None = None,
)
```

### 14.3 Claude Code adapter

Command strategy:

```bash
claude -p \
  --output-format stream-json \
  --allowedTools Read Edit Bash Glob Grep \
  --append-system-prompt "<system prompt or safety append>" \
  "<user payload>"
```

Implementation notes:

- prefer passing the main prompt as the user payload
- if using `CLAUDE.md` in the vault and Claude auto-loads it, do not duplicate it blindly
- parse JSON events line-by-line
- only emit user-visible text chunks to the websocket

Important:

The exact event schema from Claude must be verified during implementation and codified in tests.

### 14.4 Codex adapter

Command strategy:

```bash
codex exec \
  --json \
  -C <vault_path> \
  "<prompt>"
```

Implementation notes:

- parse JSONL events line-by-line
- normalize final answer and any intermediate text events
- decide whether to allow Codex’s own browsing/tools based on local CLI defaults

Important:

Codex event schema must be captured from real runs and frozen in tests.

### 14.5 Working directory

Always run the backend with the vault root as working directory.

This guarantees:

- vault file operations are relative to the vault
- `CLAUDE.md` auto-discovery can work when supported

### 14.6 Timeout policy

V1 timeout behavior:

- no-output timeout: 120 seconds
- hard process timeout: open question

If timeout is hit:

- kill the subprocess
- send `error` to the client
- keep session history intact

## 15. Prompt Construction Spec

File:

- `brain/prompts.py`

### 15.1 Prompt builder contract

Input:

- app config
- session state
- user message
- today’s daily note content
- list of core notes
- optional integration digest

Output:

- final string prompt for the backend

### 15.2 Prompt sections

1. operating instruction block
2. current date
3. vault context
4. recent session history
5. optional integration digest
6. current user message

### 15.3 Operating instruction block

Source:

- primarily `system/CLAUDE.md`
- for non-Claude backends, inject the full content explicitly
- for Claude, rely on `system/CLAUDE.md`

V1 rule:

- `system/CLAUDE.md` is the canonical prompt source
- Claude should rely on that file at vault runtime
- Codex should receive the same canonical prompt content through explicit injection
- do not add a second prompt-file convention such as `AGENTS.md` in V1 unless backend behavior is later verified and intentionally adopted

### 15.4 Vault context rules

Always include:

- today’s date
- today’s daily note if it exists
- the configured daily note path if it does not
- list of `core/` filenames
- note that `thoughts/` is archival

Do not include:

- entire contents of all core notes
- all previous summaries

### 15.5 Recent history policy

Default:

- last 10 turns max

Future-safe behavior:

- older history may later become a condensed summary, but not in V1 initial implementation unless needed

### 15.6 Supplemental integration context

This is disabled by default in V1 chat prompts.

Allowed content:

- today’s calendar summary
- unread email action item count
- open Notion task count

V1 rule:

- integrations are used for daily note generation by default
- they are not included in standard chat prompts unless explicitly enabled later

## 16. Daily Note Generation Spec

File:

- `brain/daily.py`

### 16.1 Input sources

- Obsidian vault tasks
- Google Calendar
- Gmail
- Notion
- ranked news/articles

### 16.2 Rendering requirements

Daily note must:

- write to the configured daily folder
- use today’s date filename `YYYY-MM-DD.md`
- be idempotent enough for repeated generation in one day
- preserve or clearly define overwrite behavior

### 16.3 Overwrite behavior

Locked V1 behavior:

- refuse overwrite by default if today’s note already exists
- do not silently overwrite even if the note appears generated
- do not attempt section-level patching in V1
- reserve `--force` for a later explicit overwrite path

### 16.4 Daily note template

Required sections:

- calendar
- email
- notion tasks
- open obsidian tasks
- reading links

Optional:

- generated timestamp
- metadata frontmatter

### 16.5 UI behavior

When `Generate Daily` is clicked:

1. call `POST /api/daily`
2. show success or failure inline
3. optionally inject a system message into chat with the file path

## 17. Summary Generation Spec

File:

- `brain/summarizer.py`

### 17.1 Summary prompt

The summarizer must ask the active backend to produce:

- topics discussed
- decisions made
- files modified
- action items

Format:

- valid markdown
- concise
- not a transcript

### 17.2 File modification tracking

This is a weak point in the current plan and must be handled explicitly.

V1 implementation options:

1. parse backend output for mentioned files
2. snapshot vault mtimes before and after each run
3. combine both

Recommended:

- snapshot candidate file mtimes before/after each backend run
- record changed paths within the vault

This should not rely only on parsing model text.

### 17.3 Fallback summary

If agent-based summarization fails:

- generate a server-side fallback markdown summary using:
  - session metadata
  - user prompts
  - assistant responses
  - tracked modified files

## 18. Vault and File Utility Spec

File:

- `brain/vault.py`

Responsibilities:

- resolve configured vault folders
- read/write note files
- read daily note
- list core notes
- list thought summaries
- detect compatible vault structure
- snapshot file mtimes for modified-file tracking
- create folders safely

### 18.1 Existing parser migration

Move logic from [obsidian_reader.py](/Users/sanjit/Desktop/san/todos-with-obsidian/obsidian_reader.py) into `brain/vault.py` incrementally.

Preserve:

- frontmatter parsing
- task extraction
- tag extraction
- wiki-link extraction

Fix:

- hardcoded machine-specific default paths
- folder naming assumptions

## 19. Safety and Guardrails Spec

idli V1 will not implement strong sandboxing. Therefore the prompt contract is part of the product surface.

Default `system/CLAUDE.md` must explicitly instruct the agent:

- operate within the vault
- do not delete large sets of files
- do not delete or rewrite core notes without explicit instruction
- do not modify system config or prompt files unless explicitly asked
- prefer additive edits
- when updating notes, preserve user-authored content and structure where possible

This is product-critical and not optional.

## 20. Migration Strategy

### 20.1 Phase 0 rule

Do not break existing `python main.py daily` immediately.

### 20.2 Migration steps

1. add new `brain/` package
2. move reusable code into package modules
3. make `main.py` call into new modules where sensible
4. leave old wrappers in place until the new CLI is stable
5. only remove old paths after the new CLI is verified

### 20.3 `setup.py`

Current issue:

- [setup.py](/Users/sanjit/Desktop/san/todos-with-obsidian/setup.py) is an onboarding script, not packaging metadata

V1 plan:

- keep it temporarily
- later either:
  - rename to `bootstrap.py`
  - or fold into `brain init` / `brain setup`

This does not block idli V1.

## 21. Dependency Plan

Current dependencies are in [requirements.txt](/Users/sanjit/Desktop/san/todos-with-obsidian/requirements.txt).

Add likely V1 dependencies:

- `fastapi`
- `uvicorn`
- `PyYAML`

Potential additions:

- `pytest`
- `httpx`
- `websockets` or FastAPI test utilities

Prefer keeping the stack minimal.

## 21.1 Packaging Spec

V1 will add a real Python package definition.

Required files:

- `pyproject.toml`
- `brain/__init__.py`
- `brain/cli.py`

Required packaging behavior:

- installable in editable mode for local development
- console entrypoint named `brain`
- temporary backward compatibility for `python main.py ...`

Recommended `pyproject.toml` responsibilities:

- project metadata
- runtime dependencies
- optional test dependencies if needed
- console script registration:
  - `brain = brain.cli:main`

Why this is locked for V1:

- it gives the product a stable CLI surface
- it matches the desired user-facing command model
- it prevents the codebase from being structured around legacy one-file entrypoints

## 22. Testing Plan

### 22.1 Unit tests

- config loading and validation
- vault folder resolution
- prompt generation
- daily note rendering
- session ID generation
- summary fallback formatting

### 22.2 Integration tests

- `brain init` against empty temp vault
- `brain init` against existing temp vault
- `brain daily` writes expected path
- `GET /api/status` returns readiness payload
- websocket single-session enforcement

### 22.3 Backend parser tests

Must include recorded fixture lines for:

- Claude stream-json output
- Codex JSONL output

This is important. Backend parsing should not remain informal.

### 22.4 Manual test matrix

- macOS + Claude Code configured
- macOS + Codex configured
- missing Claude binary
- missing Codex binary
- missing Google credentials
- missing Notion key
- empty vault
- existing vault with custom daily folder

## 23. Delivery Plan

### Phase 1: Foundation

- create `brain/` package
- add `pyproject.toml`
- implement config loading
- implement vault init/conversion
- add templates
- implement `brain init`

Exit criteria:

- `brain init --vault <path>` works on empty and existing vaults

### Phase 1 Detailed File Plan

Files to create:

- `pyproject.toml`
- `brain/__init__.py`
- `brain/cli.py`
- `brain/app_config.py`
- `brain/env_config.py`
- `brain/models.py`
- `brain/utils.py`
- `brain/init_vault.py`
- `brain/vault.py`
- `brain/templates/CLAUDE.md`
- `brain/templates/brain.config.yaml`
- `brain/templates/daily_note.md`

Primary functions and classes:

- `brain.cli.main()`
- `brain.cli.build_parser()`
- `brain.cli.cmd_init(args)`
- `brain.cli.cmd_start(args)`
- `brain.cli.cmd_status(args)`
- `brain.cli.cmd_daily(args)`
- `brain.app_config.load_app_config(...)`
- `brain.app_config.write_default_app_config(...)`
- `brain.env_config.load_env_config()`
- `brain.init_vault.initialize_vault(...)`
- `brain.init_vault.detect_folder_mappings(...)`
- `brain.vault.resolve_vault_paths(...)`
- `brain.vault.ensure_directories(...)`
- `brain.vault.read_note(...)`
- `brain.vault.read_daily_note(...)`
- `brain.vault.list_core_notes(...)`

Implementation notes:

- define dataclasses first in `brain/models.py`
- build config loading before any server code
- implement vault mapping logic before daily note migration work
- keep top-level [config.py](/Users/sanjit/Desktop/san/todos-with-obsidian/config.py) untouched until compatibility wrapping is ready

### Phase 2: Server and UI

- add FastAPI app
- add static HTML UI
- add websocket session handling
- add `brain start`
- add browser auto-open

Exit criteria:

- browser UI loads locally
- second tab is rejected

### Phase 2 Detailed File Plan

Files to create:

- `brain/server.py`
- `brain/web/index.html`

Primary functions and classes:

- `brain.server.create_app(app_state)`
- `brain.server.run_server(app_cfg, env_cfg)`
- `brain.server.websocket_endpoint(...)`
- `brain.server.get_status(...)`
- `brain.server.post_daily(...)`
- `brain.server.post_end_session(...)`

Frontend responsibilities:

- websocket connect/reconnect logic
- render markdown responses
- maintain current displayed session state
- disable input during active run
- call `/api/daily`
- call `/api/session/end`

Implementation notes:

- build the server around a single application state object
- reject the second websocket immediately
- keep the HTTP API minimal and local-only

### Phase 3: Claude backend

- implement Claude adapter
- verify stream parser on real output
- connect backend to websocket
- enforce run-state locking

Exit criteria:

- one end-to-end chat works with Claude Code

### Phase 3 Detailed File Plan

Files to create:

- `brain/agent_backends.py`
- `tests/test_backends.py`

Primary functions and classes:

- `ClaudeCodeBackend`
- `BackendEvent`
- `BackendValidationResult`
- `parse_claude_stream_line(...)`
- `stream_backend_events(...)`

Implementation notes:

- capture real Claude JSON stream samples and freeze them as fixtures
- normalize chunks before they hit websocket code
- do not put Claude-specific parsing logic in `server.py`

### Phase 4: Session and summary

- add session model
- add summary writing
- add end-session route and UI button
- add modified-file tracking

Exit criteria:

- ending a session writes valid summary markdown to `thoughts/`

### Phase 4 Detailed File Plan

Files to create:

- `brain/session.py`
- `brain/summarizer.py`

Primary functions and classes:

- `SessionManager`
- `SessionState`
- `Turn`
- `SessionManager.get_or_create_session(...)`
- `SessionManager.attach_websocket(...)`
- `SessionManager.detach_websocket(...)`
- `SessionManager.start_run(...)`
- `SessionManager.finish_run(...)`
- `SessionManager.cancel_run(...)`
- `brain.summarizer.build_summary_prompt(...)`
- `brain.summarizer.write_session_summary(...)`
- `brain.vault.snapshot_vault_mtimes(...)`
- `brain.vault.diff_modified_files(...)`

Implementation notes:

- session manager owns in-memory lifecycle
- server should call session manager methods, not mutate session data directly
- modified-file tracking should be file-system based, not model-text based

### Phase 5: Daily note integration

- port daily generation into package
- expose CLI and HTTP route
- add UI button
- align with configurable folder names

Exit criteria:

- daily note works from both CLI and UI

### Phase 5 Detailed File Plan

Files to create or migrate:

- `brain/daily.py`
- `brain/integration_context.py`
- compatibility wrappers from existing [daily_note.py](/Users/sanjit/Desktop/san/todos-with-obsidian/daily_note.py) and [context_builder.py](/Users/sanjit/Desktop/san/todos-with-obsidian/context_builder.py)

Primary functions and classes:

- `build_daily_context(...)`
- `generate_daily_note(...)`
- `render_daily_note(...)`
- `write_daily_note(...)`
- `daily_note_exists_for_today(...)`

Implementation notes:

- preserve the current source integrations first
- do not redesign integration clients in this phase
- enforce the default refusal behavior when today’s note already exists

### Phase 6: Codex backend

- implement Codex adapter
- verify JSONL parser
- add `brain status` backend diagnostics

Exit criteria:

- one end-to-end chat works with Codex

### Phase 6 Detailed File Plan

Primary functions and classes:

- `CodexBackend`
- `parse_codex_jsonl_line(...)`

Implementation notes:

- capture real Codex JSONL samples and freeze them as fixtures
- inject canonical prompt content from `system/CLAUDE.md`
- keep backend normalization identical at the websocket boundary

### Phase 7: Stabilization

- harden errors
- write tests
- update docs
- de-risk migration wrappers

Exit criteria:

- smoke tests and manual test matrix pass on macOS

### Phase 7 Detailed File Plan

Files to update:

- [main.py](/Users/sanjit/Desktop/san/todos-with-obsidian/main.py)
- [README.md](/Users/sanjit/Desktop/san/todos-with-obsidian/README.md)
- [requirements.txt](/Users/sanjit/Desktop/san/todos-with-obsidian/requirements.txt)
- tests under `tests/`

Primary tasks:

- wire `main.py` to the new package where useful
- document both `brain ...` and temporary legacy entrypoints
- verify installation flow
- verify editable install flow

## 23.1 File-by-File Ownership Plan

This section is the coding map for the implementation.

### `pyproject.toml`

Owns:

- package metadata
- dependencies
- console script registration

### `brain/models.py`

Owns:

- shared dataclasses
- typed payload models
- enums/literals where useful

Should contain:

- `AppConfig`
- `EnvConfig`
- `VaultPaths`
- `SessionState`
- `Turn`
- `BackendEvent`
- `BackendValidationResult`

### `brain/app_config.py`

Owns:

- YAML config loading
- validation
- config defaults
- config writing during init

### `brain/env_config.py`

Owns:

- `.env` loading for integrations
- exposing integration credential state to the app

### `brain/vault.py`

Owns:

- note parsing
- folder resolution
- daily/core/thought accessors
- safe write helpers
- mtime snapshots and diffing

### `brain/init_vault.py`

Owns:

- new-vault creation
- existing-vault mapping and non-destructive conversion
- template emission

### `brain/prompts.py`

Owns:

- runtime prompt composition
- loading canonical prompt text from `system/CLAUDE.md`
- prompt windowing for recent session history

Primary functions:

- `load_canonical_prompt(vault_paths)`
- `build_chat_prompt(...)`
- `build_codex_prompt(...)`

### `brain/agent_backends.py`

Owns:

- backend classes
- process spawning
- stream parsing
- backend validation/version reporting

### `brain/session.py`

Owns:

- session lifecycle
- active run state
- websocket attachment state
- cancellation handling

### `brain/summarizer.py`

Owns:

- summary prompt creation
- summary write pipeline
- fallback summary generation

### `brain/daily.py`

Owns:

- daily note orchestration
- existence checks
- rendering and writing

### `brain/integration_context.py`

Owns:

- collection of Gmail/Calendar/Notion/news context for daily notes
- integration-failure isolation

### `brain/server.py`

Owns:

- FastAPI app
- WebSocket endpoint
- HTTP routes
- bridging between session manager and backend streams

### `brain/web/index.html`

Owns:

- all client-side UI behavior
- WebSocket handling
- input state
- action buttons

### `main.py`

Owns only:

- temporary compatibility entrypoint during migration

It should not remain the center of the product.

## 23.2 Phase Execution Order

Implementation order should be exactly:

1. `pyproject.toml` and package skeleton
2. shared models and config loading
3. vault mapping/init logic
4. CLI commands for `init`, `status`, `daily` skeletons
5. server shell and static UI
6. session manager
7. Claude backend and streaming bridge
8. prompt builder
9. summarizer and modified-file tracking
10. daily note migration into package
11. Codex backend
12. status polish, docs, wrappers, tests

Reason:

- backend work depends on config, vault, session, and server contracts
- daily note migration can happen after the product shell exists
- Codex should not block the first end-to-end vertical slice

## 23.3 Definition of Done Per Phase

### Foundation done means

- editable install works
- `brain --help` works
- config file can be written and read
- new and existing vault paths are handled

### Server done means

- browser opens
- UI renders
- websocket connects
- second tab is rejected

### Claude backend done means

- user message reaches Claude
- text streams back live
- failure paths return readable errors

### Session done means

- refresh reconnects
- end-session cancels active run
- summary file is written

### Daily done means

- CLI generation works
- UI button works
- existing daily file is refused by default

### Codex done means

- Codex receives the canonical prompt
- JSONL parsing is stable
- websocket output is indistinguishable from Claude at the transport layer

### Stabilization done means

- tests pass
- docs match real commands
- legacy wrapper still works or is intentionally deprecated

## 24. Acceptance Criteria

idli V1 is complete only if all are true:

- user can run `brain init`
- user can run `brain start`
- browser UI loads at localhost
- exactly one active websocket session is allowed
- Claude Code backend works end-to-end
- Codex backend works end-to-end
- responses stream incrementally
- prompts include daily note and core-note awareness
- session end writes a markdown summary
- `brain daily` works
- daily note can be triggered from the UI
- missing optional integrations fail gracefully
- existing vault conversion is non-destructive

## 25. Resolved Decisions

All material product behavior and packaging decisions for V1 are now resolved.

### 25.1 Folder compatibility

Resolved:

1. Preserve existing folder names such as `Daily/` in config by default.
2. Support mapping existing equivalent folders into config; create canonical idli folders only when no mapping exists.

### 25.2 Daily note overwrite semantics

Resolved:

3. Refuse overwrite by default if today’s note already exists.
4. Do not overwrite automatically even if the note appears generated.
5. Do not attempt section-level updates in V1.

### 25.3 Session control

Resolved:

6. Cancel the process and summarize partial history.
7. Allow refresh to reconnect to the same in-memory session.

### 25.4 Agent prompt strategy

Resolved:

8. Claude should rely on `system/CLAUDE.md`.
9. Codex should receive the canonical prompt content through explicit injection.

### 25.5 Tool usage expectations

Resolved by engineering default:

10. `brain.config.yaml` should allow Claude tool customization from V1, with `Read/Edit/Bash/Glob/Grep` as defaults.
11. Codex should use its default local CLI behavior in V1 unless a concrete issue forces an explicit mode later.

### 25.6 Integrations in prompt context

Resolved:

12. Integrations should be used only for daily note generation in V1 by default.
13. If enabled later, keep prompt footprint to counts or top few items only.

### 25.7 Status command and UI detail

Resolved by engineering default:

14. `brain status` should show versions and relevant file paths; the UI should stay lighter and focus on readiness.
15. The UI should expose simple connected/not-connected integration indicators in V1.

### 25.8 Packaging and compatibility

Resolved:

16. Add `pyproject.toml` and an installable `brain` console script in V1, while keeping `main.py` as a temporary compatibility wrapper during migration.

## 26. Recommended Answers

If you want the fastest stable path, the recommended answers are:

1. preserve existing folder names in config; do not auto-migrate
2. support config mapping for existing folders
3. refuse overwrite by default if today’s note already exists
4. do not overwrite generated notes automatically in V1
5. do not attempt section patching in V1
6. cancel running process and summarize partial history
7. allow reconnect to the same active session after refresh
8. rely on `system/CLAUDE.md` for Claude
9. inject the canonical prompt content into Codex requests
10. keep Claude tools configurable in config, with safe defaults
11. use default Codex behavior first, then tighten only if needed
12. integrations should be daily-note-first, not in standard chat prompts
13. counts or top few items only
14. show versions and paths in CLI status
15. show simple connected/not connected indicators in the UI
16. add `pyproject.toml` and console script now, keep `main.py` as a temporary compatibility wrapper

## 27. Final Direction

The implementation can proceed directly from this spec.

The main execution risks are now engineering risks, not product ambiguity:

- backend stream parsing differences
- migration correctness
- websocket/session lifecycle bugs
- daily note compatibility with existing vaults

Those should be handled through phased implementation, fixtures, and tests rather than more planning.
