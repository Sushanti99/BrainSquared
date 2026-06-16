<p align="center">
  <img src="brain-logo.png" alt="brain²" width="120">
</p>

<h1 align="center">BrainSquared</h1>

<p align="center">One interface for every app you use. Powered by AI that knows your context.</p>

<p align="center">
  <a href="https://github.com/Sushanti99/BrainSquared/releases/latest"><img src="https://img.shields.io/github/v/release/Sushanti99/BrainSquared?label=download" alt="Download"></a>
  <a href="https://pypi.org/project/brainsquared/"><img src="https://img.shields.io/pypi/v/brainsquared" alt="PyPI"></a>
  <img src="https://img.shields.io/pypi/pyversions/brainsquared" alt="Python">
  <img src="https://img.shields.io/github/license/Sushanti99/BrainSquared" alt="License">
</p>

---

Most of your day is spent context-switching. You check Gmail, switch to Slack, open Notion for a task, look at your calendar, review a GitHub PR — and repeat. Each app only knows its own slice of your life.

BrainSquared connects all of them. It builds a living knowledge base from your tools — using LLMs to maintain and update it like a wiki, not a data dump — and gives you one place to read, act, and stay on top of everything. Need to reply to an email? See what's on your calendar? Get reminded about a Slack thread you never answered? Close out an issue? BrainSquared surfaces it all, lets you act on it, and learns from it.

Everything runs locally. No cloud middleman. Your data stays yours.

---

## Get started

### Option 1 — Mac App

The easiest way. No terminal required.

**[Download BrainSquared.dmg →](https://github.com/Sushanti99/BrainSquared/releases/latest)**

**1. Download and install**

Download `BrainSquared.dmg`, open it, and drag BrainSquared to your Applications folder.

**2. First launch**

Because this build isn't notarized yet, macOS will show a security warning on first open:
- Right-click BrainSquared in Applications → **Open**
- Go to **System Settings → Privacy & Security** → scroll down → **Open Anyway**

You only need to do this once.

**3. Set up your vault**

BrainSquared walks you through:
- Choosing a folder where it stores your notes (pick an existing Obsidian vault or create a new one)
- Entering your Anthropic API key (stored securely in your Keychain)
- Automatically installing the `claude-code` and `codex` CLIs

**4. Start using it**

Once set up, BrainSquared opens directly to the interface every time. Connect your tools from the Integrations tab, generate your daily note, and chat with the agent that knows your full context.

---

### Option 2 — localhost (CLI)

Run it directly from the terminal. Full control over every option.

**Prerequisites:** [Claude Code](https://claude.ai/code) (or Codex) installed and authenticated.

**1. Install**

```bash
pip install brainsquared
```

**2. Create your vault**

Starting fresh:
```bash
brain init --vault ~/my-vault
```

Or seed it from your existing tools first:
```bash
brain seed --vault ~/my-vault \
           --from-obsidian ~/path/to/existing-vault \
           --from-gmail \
           --from-calendar \
           --from-notion
```

**3. Start**

```bash
brain start --vault ~/my-vault
```

Opens `http://localhost:6683` in your browser. Use `--port N` to override the default.

**4. Connect your tools**

Go to the **Integrations** tab in the UI. Connect Gmail, Google Calendar, Notion, and more — no config files needed.

**5. Generate your daily note**

Go to the **Tasks** tab and click **Generate Daily**. BrainSquared pulls your tasks, events, emails, and open PRs into one view.

**All CLI commands**

```bash
brain seed    --vault PATH  [--from-obsidian PATH] [--from-notion] [--from-gmail] [--from-calendar] [--dry-run]
brain init    --vault PATH  [--agent claude-code|codex]
brain start   --vault PATH  [--agent claude-code|codex] [--port N] [--no-open]
brain daily   --vault PATH  [--force]
brain status  --vault PATH
```

---

## How it works

```
Mac App / Browser  ──►  brain² Server  ──►  Claude Code / Codex CLI
                                                    │
                                       Local Knowledge Base (Obsidian vault)
                                                    │
                          Gmail · Calendar · GitHub · Slack · Notion · Linear · ...
```

BrainSquared treats your tools as sources of truth and your local vault as a continuously updated knowledge base. When you connect a new integration, the AI reads your existing notes and makes surgical edits — updating what's relevant, adding only what has no home yet. Nothing gets overwritten wholesale.

Every day you get a unified view of what needs your attention. You act on it. What you finish disappears tomorrow. What you don't comes back.

---

## Integrations

Gmail, Google Calendar, GitHub, Notion, Slack, Linear — with more on the way. Connect them through the UI. No config files, no manual credential wrangling.

---

## Development

```bash
git clone https://github.com/Sushanti99/BrainSquared
cd BrainSquared
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

To build the Mac app:
```bash
pip install pyinstaller
pyinstaller brain.spec           # builds dist/BrainServer
cd macos && xcodegen generate    # regenerates Xcode project
```

---

## Roadmap

- [ ] Notarized Mac app (no security warning on install)
- [ ] More integrations — Jira, Figma, Zoom, iMessage, and more
- [ ] Action layer — reply to emails, send Slack messages, create tasks, directly from BrainSquared
- [ ] VPS deployment with remote vault sync
- [ ] Mobile access via Tailscale
- [ ] Scheduled background updates
