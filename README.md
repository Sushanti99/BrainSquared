# todos-with-obsidian

An open-source Python tool that connects your **Gmail, Google Calendar, and Notion** to your **Obsidian vault** — generating a daily note with everything you need to do today, plus an AI chat interface powered by Claude.

## What it does

**`python main.py daily`** — writes `Daily/YYYY-MM-DD.md` to your vault with:
- Today's Google Calendar events
- Unread emails from the last 24 hours (as checkboxes)
- Open Notion tasks
- Open tasks from your Obsidian notes

**`python main.py chat`** — starts an interactive chat where Claude has full context of your vault, emails, calendar, and Notion tasks. Ask it to prioritize your day, summarize your emails, or plan the week.

```
You: what should I focus on today?
Claude: Based on your calendar (2 meetings, first at 14:00) and the 3 overdue Notion tasks...
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure your `.env`

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
VAULT_PATH=/Users/yourname/Documents/Obsidian Vault
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Connect integrations (each is optional)

#### Gmail + Google Calendar

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → enable **Gmail API** and **Google Calendar API**
3. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID** (Desktop app)
4. Download `credentials.json` and place it in this folder
5. On first run, a browser window opens for consent — after that, `token.json` is saved automatically

#### Notion

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) → New integration
2. Copy the **Internal Integration Secret** → paste as `NOTION_API_KEY` in `.env`
3. Open your tasks database in Notion → copy the ID from the URL (the 32-char hex string) → paste as `NOTION_DATABASE_ID`
4. In Notion, open the database → click `···` → **Add connections** → select your integration

#### Claude (chat only)

Get an API key from [console.anthropic.com](https://console.anthropic.com) → paste as `ANTHROPIC_API_KEY`.

---

## Usage

```bash
# Generate today's daily note
python main.py daily

# Start AI chat with all your data
python main.py chat

# Use a different vault
python main.py daily --vault /path/to/your/vault
```

### Chat commands

Inside `python main.py chat`:

| Command    | Description                                    |
|------------|------------------------------------------------|
| `/daily`   | Generate today's daily note from inside chat   |
| `/refresh` | Reload all data sources and reset conversation |
| `/help`    | Show available commands                        |
| `/quit`    | Exit                                           |

---

## Daily note format

The generated note is Obsidian-native — all tasks are checkboxes, vault tasks link back to their source notes, and the frontmatter is compatible with Dataview queries.

```markdown
---
date: 2026-04-07
type: daily
generated: true
sources: [calendar, gmail, notion, obsidian]
---

# Daily Note — Tuesday, April 7 2026

## Calendar — Today's Events
- 10:00–11:00 :: Team standup
- 14:30–15:00 :: 1:1 with advisor

## Email — Action Items
- [ ] Re: Q2 proposal *(from: alice@company.com)*

## Notion Tasks
- [ ] Write architecture doc · Due: 2026-04-10 · [Open](https://notion.so/...)

## Open Obsidian Tasks
- [ ] Publish Substack piece *(from: [[X/writing+working/writing for the sake of writing]])*
```

---

## Project structure

```
├── main.py              Entry point (daily / chat subcommands)
├── obsidian_reader.py   Reads and parses the Obsidian vault
├── gmail_client.py      Gmail OAuth2 integration
├── calendar_client.py   Google Calendar integration
├── notion_client.py     Notion API integration
├── context_builder.py   Aggregates all sources into a context bundle
├── daily_note.py        Renders and writes the daily markdown note
├── chat.py              Interactive Claude chat CLI
├── config.py            Central config, reads from .env
├── requirements.txt
└── .env.example
```

---

## Contributing

PRs welcome. The codebase is intentionally simple — no frameworks, no async, no vector DBs. Each integration is a single file and fails independently, so it's easy to add new sources (Linear, GitHub Issues, etc.) by following the same pattern.

---

## License

MIT
