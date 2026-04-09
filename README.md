# todos-with-obsidian

Connects your **Gmail, Google Calendar, Notion, and Apple Notes** to your **Obsidian vault** — generating a personalised daily note every morning with everything you need: today's events, unread emails, open tasks, recent Apple Notes updates, and a reading list curated to your interests.

No AI API key needed. No database IDs to copy. One command to set up.

---

## What you get each morning

```markdown
# Daily Note — Tuesday, April 7 2026

## Calendar — Today's Events
- 09:00–09:30 :: Standup
- 14:00–15:00 :: Product review with design team
- 18:00–19:00 :: Gym

## Email — Action Items
- [ ] Follow up on contract draft *(from: legal@company.com)*
- [ ] Respond to interview request *(from: recruiter@startup.io)*

## Notion Tasks
- [ ] Finish Q2 roadmap · Due: Apr 9 · [Open](https://notion.so/...)
- [ ] Review pull request for onboarding flow

## Apple Notes
### Open Checklists
- [ ] Renew car insurance *(from: Admin/April)*

### Recently Edited (24h)
- Project ideas *(Work, updated 21:10)*

## Open Obsidian Tasks
- [ ] Read chapter 3 of [[Thinking Fast and Slow]] *(from: [[Books/reading-list]])*
- [ ] Write up notes from yesterday's user interview

## Reading — Today's Links
- [The Bitter Lesson, 5 Years Later](https://arxiv.org/...) *(arXiv AI)*
- [Why most productivity systems fail after 30 days](https://every.to/...) *(Every)*
- [OpenAI announces new reasoning model](https://techcrunch.com/...) *(TechCrunch)*
```

The reading list is personalised — it reads your vault tags, note titles, and folder names to figure out what you care about, then ranks today's articles from Hacker News, arXiv, TechCrunch, and others accordingly. No configuration needed.

---

## Setup — one command

```bash
git clone https://github.com/Sushanti99/todos-with-obsidian.git
cd todos-with-obsidian
pip install -r requirements.txt
python setup.py
```

`setup.py` opens a browser for each service and saves your credentials to `.env`. It handles:
- **Google** — opens Cloud Console, watches for `credentials.json`, then runs the OAuth browser flow automatically
- **Notion** — opens the integrations page, you paste one key, done
- **Apple Notes (macOS)** — local integration via Notes app permissions (no API key)

Each integration is optional. If you skip one, that section just says *"not connected"* in your daily note.

---

## Run it

```bash
python main.py daily
```

That's it. Open Obsidian and your note is there.

---

## Using Claude Code as your AI layer

If you use [Claude Code](https://claude.ai/code), you don't need any extra API key for AI features. Claude Code can read your vault directly — so once your daily note is generated, just open Claude Code in your vault directory and ask:

```
what should i focus on today?
summarise my open tasks
what emails need a reply?
```

Claude Code has full access to your vault, your daily note, and anything you ask it to cross-reference. It's the fastest way to think through your day without leaving your terminal.

```bash
cd "/path/to/your/Obsidian Vault"
claude
```

**To run it every morning automatically**, add a cron job:

```bash
# open crontab
crontab -e

# add this line — runs at 8am daily
0 8 * * * cd /path/to/todos-with-obsidian && python main.py daily
```

**To use a different vault:**

```bash
python main.py daily --vault /path/to/your/vault
```

---

## Personalising your reading list

The reading list works out of the box with no config — it learns your interests from your vault.

To add custom RSS feeds, add this to your `.env`:

```env
NEWS_FEEDS=https://yourblog.com/rss,https://somepodcast.com/feed
```

Default sources: Hacker News · TechCrunch · The Verge · arXiv AI · VentureBeat · MIT Technology Review

---

## Apple Notes setup (macOS)

Apple Notes integration is local and optional. On first run, macOS may ask permission to let Terminal/Python control Notes.

If you don't see Apple Notes data in your daily note:
1. Open **System Settings → Privacy & Security → Automation**
2. Enable automation access for your terminal app (or Python) to control **Notes**
3. Run `python main.py daily` again

---

## Google setup (if you get stuck)

After running `setup.py`, if you see a 403 error about APIs not enabled:

1. [Enable Gmail API](https://console.cloud.google.com/apis/library/gmail.googleapis.com)
2. [Enable Google Calendar API](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com)
3. Wait 60 seconds, run `python main.py daily` again

---

## Project structure

```
setup.py             One-command setup (opens browser for each integration)
main.py              Entry point — run `python main.py daily`
obsidian_reader.py   Reads and parses the Obsidian vault
gmail_client.py      Gmail OAuth2 integration
calendar_client.py   Google Calendar integration
notion_client.py     Notion API — reads all pages and databases shared with integration
apple_notes_client.py Apple Notes local integration (macOS via osascript)
news_client.py       Fetches and ranks articles from RSS/HN by vault interests
context_builder.py   Aggregates all sources into one bundle
daily_note.py        Renders and writes the daily markdown note
config.py            Central config, reads from .env
```

---

## Contributing

PRs welcome. The codebase is intentionally flat and simple — no frameworks, no async, no vector DBs. Each integration is a single file that fails independently, so adding new sources (Linear, GitHub Issues, Spotify, etc.) is straightforward.

---

## License

MIT
