# brainsquared — brand & design system

**v1.0 · handover spec · 2026-04-22**

> A complete design system for brainsquared, an AI-powered personal notebook that wraps Claude Code / Codex subscriptions with an Obsidian vault and third-party integrations. This document is written so a coding agent can implement the UI directly. Every token, component, and rule is defined.

---

## 1. product in one sentence

**brainsquared is your existing AI subscription, squared.** It turns Claude Code or Codex into a persistent, notebook-first workspace backed by your own Obsidian vault, wired into Gmail, Calendar, GitHub, Slack, Linear, and Notion. The AI is the first brain. brainsquared is the second. `brain × brain = brain²`.

## 2. the aesthetic, in one paragraph

**Modern sticky-notes on a clean desk.** Crisp white (or deep charcoal) paper. Pastel cards scattered at playful angles. Handwritten display type for emotional moments, precise geometric sans for every bit of actual UI. Faint pencil scribbles in the background and hand-drawn arrows connecting things that need connecting. One hard-black primary button per screen to anchor everything. When things overlap, they go glassy — soft translucent blurs with subtle backdrop saturation. **Playful but never childish. Warm but never twee. Modern and opinionated.**

Audience: SV-adjacent engineers, PMs, and students under 35. People who read arXiv and also carry a Leuchtturm1917.

## 3. color tokens

### light mode (default)

```css
:root {
  /* Surfaces */
  --paper: #FAFAF7;           /* app background */
  --paper-raised: #FFFFFF;    /* cards, panels */
  --paper-sunken: #F0EEE8;    /* inputs, pressed states */

  /* Ink */
  --ink: #111111;             /* primary text, primary buttons */
  --ink-muted: #5A5A5A;       /* secondary text, metadata */
  --ink-faint: #9E9E9E;       /* tertiary text, placeholders */
  --ink-ghost: #D0D0D0;       /* scribbles, margin annotations */
  --rule: rgba(17,17,17,0.08);/* borders, hairlines */

  /* Sticky note palette — 6 pastels */
  --card-blue: #D4E8F5;
  --card-peach: #FAE0CE;
  --card-mint: #D4EED9;
  --card-lavender: #E3DBF1;
  --card-yellow: #FAF0C8;
  --card-rose: #F5D4DC;

  /* Sticky note pills — darker version of each card */
  --pill-blue: #A8D0E8;
  --pill-peach: #F3C89E;
  --pill-mint: #A8D9B2;
  --pill-lavender: #C6B8E0;
  --pill-yellow: #EDD88A;
  --pill-rose: #E8A8B8;

  /* System */
  --accent: #7BC47F;          /* connected / success (one color only) */
  --warning: #E8B547;         /* unsaved changes */
  --danger: #E86B5A;          /* destructive confirms */
}
```

### dark mode

The rule for dark mode: **desaturate and darken the same pastels so they read as moody, not candy.** Same names, same roles, just shifted values.

```css
.dark, [data-theme="dark"] {
  --paper: #0E0E0D;
  --paper-raised: #181816;
  --paper-sunken: #0A0A09;

  --ink: #F4F2EA;
  --ink-muted: #9E9A90;
  --ink-faint: #5C5A54;
  --ink-ghost: #2A2A27;
  --rule: rgba(244,242,234,0.08);

  --card-blue: #1F3040;
  --card-peach: #3D2B1F;
  --card-mint: #1E3328;
  --card-lavender: #2C2640;
  --card-yellow: #3A3220;
  --card-rose: #3A2328;

  --pill-blue: #4A6D8A;
  --pill-peach: #8B5D38;
  --pill-mint: #4F8466;
  --pill-lavender: #6B5A99;
  --pill-yellow: #8A7A38;
  --pill-rose: #8B4E5A;

  --accent: #6BC47F;
  --warning: #D4A03E;
  --danger: #D9604F;
}
```

**Dark mode body background** gets two soft radial gradients for atmosphere — optional but recommended:

```css
body.dark {
  background-image:
    radial-gradient(ellipse at top left, rgba(107,90,153,0.08), transparent 50%),
    radial-gradient(ellipse at bottom right, rgba(75,132,102,0.06), transparent 50%);
  background-attachment: fixed;
}
```

### color usage rules

1. **The six sticky colors are interchangeable by semantic role.** No fixed mapping (e.g. "peach = mail forever"). Just pick one color per card type per view and use it consistently within the screen. Vary across screens.
2. **One black primary button per screen.** Maximum. If you need two primary actions, reconsider the screen.
3. **`--accent` green is only for "connected" / "success" states.** Not a decorative color.
4. **Pastels never fill the whole background.** They're always cards on `--paper`.
5. **In dark mode, never layer three pastels on top of each other.** The visual weight accumulates too fast.

## 4. typography

### font stack

Load in order via Google Fonts:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Kalam:wght@400;700&family=Caveat:wght@400;500;600&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

### the four faces

| font | role | usage |
|---|---|---|
| **Kalam 700** | display (handwritten) | wordmark, hero headlines, one page title per view, daily note title |
| **Caveat 400/500** | scribble (handwritten) | background marginalia only, hand-drawn annotations, "ghost text" |
| **Inter 400/500/600/700** | UI sans | everything functional: nav, buttons, body copy, form labels, card content, task text |
| **JetBrains Mono 400/500** | utility mono | `agent: codex`, timestamps, status lines, section eyebrows, file paths, tech metadata |

### strict rules about handwriting

Handwritten fonts (Kalam, Caveat) are **loud and tiring** if overused. Apply them sparingly:

- ✅ Wordmark (`brain²`)
- ✅ One hero/page headline per screen, max
- ✅ Faint background scribbles (Caveat, ghost color)
- ✅ The big number on the `End & Summarize` stamp

- ❌ NEVER in body copy
- ❌ NEVER in buttons
- ❌ NEVER in form labels or input placeholders
- ❌ NEVER for lists of things (tasks, integrations, etc.)

Everything else is Inter. When in doubt, Inter.

### type scale

| role | size | weight | font | tracking | line-height |
|---|---|---|---|---|---|
| hero headline | 68–96px | 700 | Kalam | -0.015em | 1.05 |
| page title | 38–56px | 700 | Kalam | -0.01em | 1.1 |
| section title | 24–28px | 700 | Inter | -0.02em | 1.2 |
| card title (h3) | 19–22px | 700 | Inter | -0.02em | 1.2 |
| body | 15–16px | 400 | Inter | -0.005em | 1.55 |
| small body | 13–14px | 400 | Inter | -0.005em | 1.5 |
| eyebrow | 10–11px UPPER | 700 | Inter | 0.14–0.18em | 1.3 |
| utility / mono | 10–12px | 400/500 | JetBrains Mono | 0.04–0.08em | 1.4 |
| scribble | 22–28px | 400 | Caveat | 0 | 1 |

### the "²" superscript

Whenever you render the wordmark, the `²` is a span with:

```css
font-size: 0.55em;
transform: translateY(-0.6em);
display: inline-block;
margin-left: 2px;
```

Not an actual `<sup>` tag — the typographic positioning needs to be manual with Kalam.

## 5. the logo

Three asset files. All ship.

- **`wordmark.svg`** — full `brain²` in Kalam for nav, landing, letterhead
- **`mark-avatar.svg`** — 512×512 `b²` on white, framed by a pastel-gradient rounded square. For Twitter, Discord, social avatars
- **`favicon.svg`** — 64×64 `b²` on white, no frame. Ships alongside 16/32/192 PNG exports
- **`twitter-banner.svg`** — 1500×500 with the equation and marginalia, ready for X/Twitter header

### construction of the mark

The `b²` glyph is just Kalam bold, letter `b` plus a `²` character, with the `²` rendered at ~50% scale and raised by ~0.6em. Do not re-letter it. Kalam's natural imperfection *is* the logo.

### sizing rules

- Favicon: 16px minimum, drop the frame below 32px
- Avatar: 48px minimum for the framed version, below that fall back to favicon
- Wordmark: 22px minimum — below that, use the mark alone

## 6. the equation

The brand's central visual: **`Claude × Codex = brain²`**, rendered as four sticky notes.

This is the landing page hero. It's also a recurring motif in marketing (Twitter banner, documentation, onboarding). The structure:

1. **Left sticky (peach)** — Claude logo, pill reads `BRAIN`, rotated ~-3°
2. **`×` operator** in Kalam, 54–64px, plain black
3. **Middle sticky (blue)** — Codex logo, pill reads `BRAIN`, rotated ~+2°
4. **`×` operator**
5. **Future sticky (lavender, dashed border, "soon" badge)** — for Gemini and others
6. **`=` operator**
7. **Right sticky (mint, ~40% larger)** — `brain²` wordmark, pill reads `BRAIN²`, rotated ~-2°

Hover behavior on each sticky: translate up 4px, rotate to 0° (settles). 300ms `cubic-bezier(0.2, 0.8, 0.3, 1)`.

## 7. components

### 7.1 sticky card

The core primitive. Used for tasks, integrations, features, agent stats, everything.

```html
<div class="sticky sticky-blue">
  <span class="pill">LABEL</span>
  <h3>Card title</h3>
  <p>Body copy explaining the thing.</p>
</div>
```

```css
.sticky {
  border-radius: 22px;
  padding: 24px 22px 26px;
  background: var(--card-blue); /* or any --card-* */
  transform: rotate(-1.5deg);   /* vary: -2deg to 2deg, never 0 */
  box-shadow:
    0 1px 2px rgba(0,0,0,0.04),
    0 12px 32px -14px rgba(0,0,0,0.12);
  transition: transform 280ms cubic-bezier(0.2, 0.8, 0.3, 1);
}
.sticky:hover {
  transform: translateY(-4px) rotate(0deg);
}
.sticky .pill {
  display: inline-block;
  padding: 6px 14px;
  border-radius: 999px;
  font-family: 'Inter', sans-serif;
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.14em;
  color: var(--ink);
  background: var(--pill-blue); /* matching darker pill */
  margin-bottom: 14px;
}
.sticky h3 {
  font-family: 'Inter', sans-serif;
  font-weight: 700; font-size: 22px;
  letter-spacing: -0.02em; line-height: 1.2;
  margin: 0 0 12px;
}
.sticky p {
  font-size: 14px; line-height: 1.5;
  color: var(--ink); opacity: 0.78;
  margin: 0;
}
```

**Rotation variety rule:** in any grid of stickies, cycle through rotations `[-1.5deg, 1deg, -0.5deg, 1.5deg, 1deg, -1deg, -1.5deg, 0.5deg, -0.5deg]` — never 0°. This is what makes it feel scattered on a desk instead of tiled.

### 7.2 primary button

One hard-black pill per screen.

```html
<button class="btn-primary">
  Start your vault
  <span class="arrow">→</span>
</button>
```

```css
.btn-primary {
  background: var(--ink); color: var(--paper-raised);
  font-family: 'Inter', sans-serif; font-weight: 600;
  font-size: 16px;
  border: none; border-radius: 999px;
  padding: 16px 28px; cursor: pointer;
  display: inline-flex; align-items: center; gap: 14px;
  transition: transform 160ms;
}
.btn-primary:hover { transform: translateY(-2px); }
.btn-primary .arrow {
  width: 28px; height: 28px; border-radius: 50%;
  background: #333;       /* darker than button bg */
  display: flex; align-items: center; justify-content: center;
  font-size: 14px;
}
```

**Dark mode inverts:** button background becomes `--ink` (bone), text becomes `--paper` (charcoal), inner arrow circle becomes `#DDD`.

### 7.3 secondary button

```css
.btn-secondary {
  background: transparent; color: var(--ink);
  font-family: 'Inter', sans-serif; font-weight: 500;
  font-size: 16px;
  border: 1.5px solid var(--ink);
  border-radius: 999px; padding: 15px 24px;
  cursor: pointer; transition: all 160ms;
}
.btn-secondary:hover { background: var(--ink); color: var(--paper); }
```

### 7.4 tab bar

```html
<div class="tabs">
  <button>Home</button>
  <button class="active">Tasks</button>
  <button>Integrations</button>
</div>
```

```css
.tabs {
  display: flex; gap: 2px;
  background: var(--paper-sunken);
  border-radius: 999px; padding: 4px;
}
.tabs button {
  background: transparent; border: none;
  font-family: 'Inter', sans-serif;
  font-weight: 500; font-size: 14px;
  color: var(--ink-muted);
  padding: 9px 22px; border-radius: 999px;
  cursor: pointer; transition: all 180ms;
}
.tabs button:hover { color: var(--ink); }
.tabs button.active {
  background: var(--ink); color: var(--paper-raised);
}
```

### 7.5 composer (chat input)

```html
<div class="composer">
  <input type="text" placeholder="ask brain² to work on the vault…">
  <button class="send">Send <span class="arrow">→</span></button>
</div>
```

```css
.composer {
  background: var(--paper-sunken);
  border: 1px solid var(--rule);
  border-radius: 20px;
  padding: 14px 18px 14px 22px;
  display: flex; align-items: center; gap: 14px;
  transition: all 200ms;
}
.composer:focus-within {
  border-color: var(--ink);
  box-shadow: 0 0 0 4px rgba(17,17,17,0.06);
}
.composer input {
  flex: 1; border: none; background: transparent; outline: none;
  font-family: 'Inter', sans-serif; font-size: 15px;
  color: var(--ink);
}
.composer input::placeholder { color: var(--ink-faint); }
```

### 7.6 chat messages (glassy)

The one place we go full glassmorphic — chat messages. Each message is a small tinted glass panel, slightly rotated.

```css
.msg {
  max-width: 85%;
  padding: 14px 18px;
  border-radius: 18px;
  font-size: 15px; line-height: 1.55;
  backdrop-filter: blur(8px) saturate(120%);
  -webkit-backdrop-filter: blur(8px) saturate(120%);
}
.msg.user {
  background: rgba(212,232,245,0.7);   /* pastel with alpha */
  border: 1px solid rgba(168,208,232,0.5);
  align-self: flex-end;
  transform: rotate(0.5deg);
}
.msg.agent {
  background: rgba(250,224,206,0.65);
  border: 1px solid rgba(243,200,158,0.5);
  align-self: flex-start;
  transform: rotate(-0.5deg);
}
.msg.agent::before {
  content: "agent · codex";
  display: block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; letter-spacing: 0.1em;
  color: var(--ink-muted);
  margin-bottom: 6px; text-transform: lowercase;
}
```

**Dark mode versions** use lower alphas on the darker card colors (see `product-dark.html` for exact values).

### 7.7 task / checkbox

```html
<li>
  <input type="checkbox">
  <div class="body">
    Clean the car inside and out
    <span class="meta">general-notes</span>
  </div>
</li>
```

```css
li input[type="checkbox"] {
  appearance: none;
  width: 18px; height: 18px;
  border: 1.5px solid var(--ink-faint);
  border-radius: 5px;
  background: transparent;
  margin-top: 2px; cursor: pointer;
  flex-shrink: 0; position: relative;
  transition: all 160ms;
}
li input[type="checkbox"]:checked {
  background: var(--ink);
  border-color: var(--ink);
}
li input[type="checkbox"]:checked::after {
  content: ""; position: absolute;
  left: 5px; top: 1.5px; width: 4px; height: 9px;
  border: solid var(--paper); border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}
li.done .body {
  color: var(--ink-muted);
  text-decoration: line-through;
}
```

### 7.8 section eyebrow

```html
<div class="section-eyebrow">INTEGRATIONS</div>
```

```css
.section-eyebrow {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-muted);
  margin-bottom: 10px;
}
```

### 7.9 status indicator (connected)

```html
<div class="status">
  <span class="status-dot"></span>
  CONNECTED · codex · session 2026-04-22-1
</div>
```

```css
.status {
  display: flex; gap: 8px; align-items: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; color: var(--ink-muted);
  letter-spacing: 0.06em; text-transform: uppercase;
}
.status-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 4px rgba(123,196,127,0.18);
}
```

### 7.10 scribbles (marginalia)

Hand-drawn text in the background of any large space. Use sparingly — 2–4 per screen max.

```html
<div class="scribble">today's loops</div>
```

```css
.scribble {
  position: absolute;
  font-family: 'Caveat', cursive;
  font-size: 22–28px;
  color: var(--ink-ghost);
  pointer-events: none;
  white-space: nowrap;
  transform: rotate(-4deg); /* vary: -5 to 5 deg, never 0 */
  z-index: 1;
}
```

**Arrow scribbles** (SVG):

```html
<svg class="arr" width="50" height="40" viewBox="0 0 50 40">
  <path d="M 5,20 Q 20,5 40,18 M 40,18 L 33,13 M 40,18 L 35,24"
        fill="none" stroke="#CCC" stroke-width="1.5" stroke-linecap="round"/>
</svg>
```

## 8. layout & spacing

- **Base unit:** 4px. All spacing is a multiple.
- **Corner radius:**
  - Inputs & small controls: `10px`
  - Cards, panels, chat messages: `18–22px`
  - The app frame and outer panes: `24px`
  - Primary button, pills, tab bar: `999px` (full pill)
- **Page frame:** the whole app lives inside a `max-width: 1440px` container with `20–28px` padding
- **Panes have breathing room:** 32px padding minimum on the outer pane surfaces
- **Sticky cards:** 22–24px padding, varying rotation (-2° to +2°, never 0°)

## 9. motion

Motion is subtle and springy.

- **Default ease:** `cubic-bezier(0.2, 0.8, 0.3, 1)` — a gentle overshoot
- **Duration:** 160ms (buttons), 200ms (UI changes), 280ms (card hovers), 400ms (theme switch)
- **Sticky hover:** `translateY(-4px) rotate(0deg)` — the card "straightens up"
- **Primary button hover:** `translateY(-2px)` — subtle lift
- **Task check:** checkbox fills, strikethrough animates in over 180ms, text fades to muted
- **Theme toggle:** body background/color transitions over 300–400ms

Never bounce. Never spin.

## 10. iconography

- **Base set:** [Lucide](https://lucide.dev), 1.5px stroke, 20px grid
- **Colored brand emoji** (Gmail envelope, Calendar `17`, GitHub octocat) should be **replaced with monochrome Lucide icons** tinted `--ink-muted` on hover `--ink`. The one exception: the equation stickies on the landing page use each brand's actual logo color, because that's the point of the equation
- **Connected indicator:** a 7px `--accent` green dot with a soft glow ring
- **Settings, refresh, nav chevrons:** Lucide strokes

## 11. voice and copy

- Lowercase in chrome (nav, buttons, labels): `home`, `tasks`, `integrations`
- Sentence case in content: `Daily Note — Wednesday, April 22`
- Dry, precise, mildly funny. Never cheerful
- The agent speaks in lowercase too, casually: *"three things are still hanging…"*
- Agent identified in one line: `agent: codex · session 2026-04-22-1` in JetBrains Mono
- Empty states are written like margin notes: `"this page hasn't been written yet."`
- No "AI" word in the UI chrome — we do AI, we don't announce it

## 12. screens

This spec maps directly onto the three screens from the current product (see `current-reference-*.png` screenshots for layout reference):

### 12.1 home (vault) — redesigned from `current-reference-home.png`
- Top frame header with wordmark, tab bar, theme toggle, End & Summarize
- Left column: "Your vault" description + connected-tools pill row + "Seed from connected tools" sticky card
- Middle column: the VAULT tree (CORE, REFERENCES, THOUGHTS, DAILY sections)
- Right: content pane showing selected file, or "Select a file to read it." in placeholder italic

### 12.2 tasks — redesigned from `current-reference-tasks.png`
- Same header frame
- Left pane: "Daily Note" with Kalam title, date nav arrows, Regenerate button (lavender sticky pill), the note markdown (tasks list with checkboxes, section eyebrows for "Open Obsidian Tasks", "From Your Mail")
- Right pane: chat messages (glassy pastel bubbles, slight rotation), composer pill at bottom, status line with green dot

See `product-light.html` and `product-dark.html` for reference implementations.

### 12.3 integrations — redesigned from `current-reference-integrations.png`
- Same header frame
- Page title "connect your tools." in Kalam with a Caveat scribble nearby
- 3×3 or 4×3 grid of sticky-note integration cards, each rotated slightly differently
- Each card has: a pill label (MAIL, CALENDAR, etc.), an icon in a glassy rounded square, card title, description, status (connected / coming soon), and a Connect/Disconnect button

See `product-integrations.html` for reference.

## 13. files shipped

| file | purpose |
|---|---|
| `SPEC.md` | this document |
| `landing.html` | landing page with the equation hero |
| `product-light.html` | product UI in light mode, Tasks tab |
| `product-dark.html` | product UI in dark mode, Tasks tab |
| `product-integrations.html` | integrations grid, both themes via toggle |
| `wordmark.svg` | full `brain²` wordmark |
| `mark-avatar.svg` | 512×512 avatar with gradient frame |
| `favicon.svg` | 64×64 simple favicon |
| `twitter-banner.svg` | 1500×500 X/Twitter header |

## 14. implementation checklist for the coding agent

- [ ] Set up font loading via Google Fonts `<link>` (Kalam 700, Caveat 400/500, Inter 400-700, JetBrains Mono 400/500)
- [ ] Drop in the CSS tokens (section 3) as a single stylesheet
- [ ] Wire `data-theme="dark"` toggle via a small JS snippet (persist to localStorage)
- [ ] Build the 10 components in section 7 as reusable primitives
- [ ] Replace existing colored brand emoji in Integrations tab with Lucide icons tinted `--ink-muted`
- [ ] Add 2–4 scribbles and 0–2 arrow-SVGs per screen as decorative absolute-positioned elements
- [ ] Enforce rotation variety on sticky grids (use the array `[-1.5, 1, -0.5, 1.5, 1, -1, -1.5, 0.5, -0.5]` by `:nth-child`)
- [ ] Test that all interactive elements (buttons, tabs, inputs) have visible focus states — add `:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }` as a baseline

## 15. what NOT to do

Anti-patterns. The guardrails matter.

- ❌ Don't use Kalam for body copy. It's unreadable in paragraphs
- ❌ Don't put more than one primary (black) button per screen
- ❌ Don't rotate sticky cards to 0° — they look tiled, not tossed
- ❌ Don't use pure black (#000) or pure white (#FFF). Always the warmed-up values above
- ❌ Don't layer three pastel cards on top of each other (dark mode especially)
- ❌ Don't animate messages with per-character typing. Agent either has a reply or it doesn't
- ❌ Don't say "AI" in the UI. The product does AI, the UI doesn't announce it
- ❌ Don't show a sparkle / magic-wand icon anywhere
- ❌ Don't use emoji as functional icons (as opposed to brand logos in the equation)
- ❌ Don't use shadows that are too strong — the specified `0 12px 32px -14px rgba(0,0,0,0.12)` is the ceiling for normal cards

---

*handover document · brain² v1.0 · drafted 2026-04-22 · for the coding agent. if something is underspecified, err toward the reference HTML files. when in doubt, Inter.*
