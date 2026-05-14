---
name: html-review-builder
description: Build interactive HTML review reports — Claude's primary channel for any reply that would be too long, too multi-paragraph, or too feedback-shaped for chat. Trigger whenever Claude needs to show Jacob something requiring his feedback or rework: audits, planning docs, refactor proposals, ship asks, multi-turn reviews where decisions get locked across sittings, any reply with more than one status update or a decision attached, anything chat would mangle. Different from `markdown-report-builder` (which renders finished docs to .docx/.pdf) — this is the *living* artifact. Use this skill even when not explicitly asked.
---

# html-review-builder

> This skill captures **what to encode** in review HTMLs — page roles, behavioral rules, anti-patterns. It deliberately does *not* prescribe **what they should look like**. Palette, typography, component CSS, exact markup — all Claude's choice each render, varying as the topic and mood call for. Functional contracts below are the only stable surface.

## Choosing between this and `markdown-report-builder`

| Situation | Skill |
|---|---|
| Multi-turn live review, status evolves between renders | `html-review-builder` (this one) |
| Finished brief Jacob will read straight through | `markdown-report-builder` (.docx/.pdf) |
| Finished doc Jacob will leave inline margin comments on | `markdown-report-builder` (.docx for Word) |
| Anything Claude builds and Jacob never re-opens | inline chat is fine; no skill needed |

If unsure, prefer this skill for anything iterative ("we'll come back to this," "let me think about it," "what about X?").

## Functional contracts

### Output location

Stable path so reopening hits the same file each time. Default: `<working-directory>/<topic>_review.html`.

### Plain-language section titles and openings (load-bearing)

Jacob is a UChicago social-psych researcher, not a software engineer. He can't decode jargon-heavy section titles like "commit + push sequence" or "manuscript-rules.md capture" — they assume tooling knowledge he doesn't have, and from such a heading he can't tell whether to engage or skip.

- Every section title encodes user-visible function, not tool name. Answer "what does this do for me?", not "what is this called in code?" Tool names, commands, and file paths come *after* the function is established.
- Every section opens with a plain-English WHAT / WHY / SO-WHAT sentence before naming any tool, file, or command.
- Analogies encouraged for unfamiliar concepts; render them in a visually distinct block so they're scannable.
- TOC hint text also uses function-language.

The test: before publishing, ask — would a researcher who has never used git, Python, or the command line understand what each section is *about* from its title alone? If no, rewrite.

Failure shape: titles like "Item 4 — auth-refactor" — internal labels with no user-visible meaning. Success shape: titles like "How sign-in becomes simpler" — what changes for the reader.

**Decision-card legends follow the same rule.** A `<fieldset class="decision-form">` legend is a plain-English question Jacob would naturally ask coming back to the doc cold — not session-invented jargon. Failure: *"Act on the fired trigger,"* *"Resume the sync sequence."* Success: *"Should I update the sync tool so it can also make HTML?"*, *"Are you going to install this today?"* The cold-read test applies: if Jacob walks away for two days and reopens the doc, every legend should still parse without re-loading the session's internal vocabulary.

### Page roles, top to bottom

The *roles* and their *order* are the contract. Visual treatment is Claude's choice.

1. **Title + meta** (source path, current vs. proposed version, etc.)
2. **"Already done this turn" callout** — completions Jacob doesn't need to act on, distinct in role from the "what's open" surface (optional, when the turn produced concrete wins)
3. **"What's new in this render" pinned surface** — anchor-linked list of deltas since last reopen; refreshes every render
4. **Status / ship-banner** — when the doc has an action state at-a-glance ("ready" vs "in progress")
5. **Table of contents** — required for renders with 3+ major sections; each `<h2>` gets a stable anchor ID
6. **Body** — organized by section. Status / verdict at-a-glance is functional: encode it visually somehow (color, pill, icon — Claude's call) so Jacob can scan
7. **Source-file footer** — italic block listing file paths referenced, so Jacob can navigate to underlying artifacts

### Decision asks: progressive placement + form-pattern answer mechanism

When the report asks Jacob for a decision, each ask sits at the end of the subtask where the choice arises, **not bundled at the bottom**. Each carries: the question, brief context, Claude's recommendation (flagged), and the answer mechanism. Jacob wants to engage section-by-section rather than holding the whole doc in working memory before deciding.

**The form pattern is the answer mechanism (load-bearing).** Each ask is a `<fieldset>` with radio options + an optional free-text comment box. A sticky toolbar at the bottom exposes three buttons: **Copy all responses** (Markdown), **Download JSON**, **Clear all**. Jacob fills out across however many sittings; when ready, he hits Copy and pastes one block of text back into chat.

**Why this is the default:**
- One paste captures *all* answers — no click+paste per decision.
- Free text per question captures nuance ("yes but with X tweak").
- Native HTML radios — visible at a glance, localStorage persists across sittings.

**Implementation:** lift `references/form-pattern.js` verbatim and drop into a `<script>` at the end of `<body>`. It implements every behavior (click-to-uncheck, localStorage persistence, copy/download/clear, per-question Clear, absorbed-content cleanup) and documents the known gotchas (Alpine.js load-order trap to avoid; namespace `STORAGE_KEY` per report if multiple form-bearing HTML files might be open simultaneously). Don't re-implement; adapt aesthetics freely.

**Per-render rules** (these govern how forms are *placed and demoted*, not how they *behave*):

- **Demote answered questions on re-renders.** When Jacob submits answers and you re-render, do *not* show the full fieldset for already-answered questions. Show a slim "your answer" block with verbatim choice + comment. Reserve the full form for still-open questions. Progress counter shows `X / Y answered` based only on the *currently-open* questions. Symptom that the demote went wrong: *"why is my last round's open-ended answer still here?"* — `restoreForm()` ghosted old text because localStorage wasn't cleared when the text was absorbed elsewhere; the JS has a cleanup hook for this, use it.
- **Use semantic decision-ids** (`migration-strategy`, `ship-vs-park`, `naming-convention`) — they end up in localStorage and the copied Markdown, and Jacob will scan them when reviewing.

### "What's new" hygiene

- **"new" labels are per-render, not cumulative.** When you re-render, *remove* "new" markers from the previous render's items — otherwise stickers accumulate and nothing stands out.
- **The pinned "What's new" box refreshes every render.** Write fresh; list 2–5 anchored items with one-line "what" descriptions. Don't carry forward last render's bullets.
- **Locked decisions** are status, not novelty — flag as locked, not new.
- **Anchor IDs stay stable across renders.** `#extract-skill` should still work even if the section grew 5×. Don't rename anchors.

### Reopen after substantial updates

Per CLAUDE.md §3: when the HTML changes substantially, Claude reopens it without being asked (`open <file>`). "Substantial" = new sections, locked decisions, new diff, new ask. Don't reopen for minor word fixes.

### Silence is NOT consent — re-surface unanswered asks

Load-bearing and easy to violate. When the report poses a question and Jacob's next message doesn't address it, **surface the ask again** — don't silently drop it, don't auto-resolve.

The trap: Jacob's reply addresses A and B but is silent on C, D, E. "Silence = agreement with my recommendation" is **wrong** — usually means he didn't see C/D/E because reports get long.

1. **No "locked" without an explicit yes you can quote.** Recommended-but-unanswered stays "still waiting," not "locked." Same if you're about to *act* on an inferred yes — stop and ask first.
2. **In "What's new," separate two lists cleanly:** *Locked this turn (with quote)* vs *Still waiting on your call.* Items only graduate when there's an explicit yes.
3. **Next chat turn, re-surface unaddressed asks** — "Earlier I asked X; want to weigh in, or punt?"

### Self-validate the render before saying "done"

Before opening the file and declaring it ready, **check it yourself** — headless browser, screenshot, or at minimum re-read the HTML source and mentally simulate the layout. Specifically:

1. **Long-form prose is not inside `<pre>`.** `<pre>` is for code, terminal output, or short ASCII fragments. For prose Jacob is meant to *read*, render as HTML (headings, paragraphs, lists, blockquotes) so it wraps and markdown markers don't appear as literal `**` / `---` noise. Symptom that this failed: prose appears struck-through, scrolls horizontally instead of wrapping, or shows literal markdown markers.
2. No accidental strikethrough, all-bold, or other style bleeds from a stray tag.
3. The "What's new" box matches reality — every claimed change is actually present.

If a check fails, fix before opening. A broken render wastes the user's time twice.

### Evolve an existing file vs. spin up fresh

**Evolve** when the task continues a multi-turn review arc and new content extends decisions already in flight. Refresh the "what's new" surface and "already done" callout per turn.

**Spin up fresh** when the turn is a focused one-off (single-decision ask, handoff, standalone reference), the content covers a loosely related topic, or the existing file is unwieldy (~1000+ lines or multiple decision arcs).

**Filenames:** use a descriptive name for the topic (e.g. `chat_blank_space_debug_review.html`, `claude_md_diagnosis_decisions.html`). The point is descriptiveness for Jacob's at-a-glance scan, not a strict taxonomy. When you spin up fresh, the predecessor stays in place for history — just stop appending.

### Locked-decision economy in evolving reports

Do **not** re-describe locked or declined decisions in full each render. After lock, demote to one-line in a summary list or default-collapsed `<details>` block. Reserve full detail only for items still actively in scope.

**Same goes when an investigation is *superseded*** — auto-resolved, fixed by something else, question rendered moot. Demote the diagnostic narrative (symptom, cause, verified-clean scaffolding) *with* the decision, not just the decision. The narrative existed to support the question; without the question, it's redundancy. Watch for the trap: adding a "resolution update" banner on top of fully-expanded sections without collapsing what's now resolved.

Why: iterative review reports get overwhelming as material accumulates. Reducing visible density per render keeps user attention on what's currently open rather than re-traversing what's settled.

How to apply each render: ask "what's actually open / changed since last render?" Make that the visual top. The "What's new" pin focuses on *deltas*, not status overviews.

**Phase boundary → archive + fresh slim doc.** When all open items in a review get resolved, rename the current file with an `_ARCHIVE` suffix (e.g., `todo_skill_redesign_review_ARCHIVE.html`) and start a fresh slim file for the new phase (e.g., `implementation_roadmap.html`). The fresh file references the archive in its source-file footer but does not duplicate resolved content. Surface this proactively in the render where the last decision gets locked — don't wait for the user to ask.

### Communication channel

Chat text stays tight. Anything multi-paragraph, anything visual, anything diff-shaped — put it in the HTML. Use chat to say *what just happened in the report* and *what's needed from Jacob*, not to duplicate report content.

## Don'ts and known failure modes

- Don't make a generic markdown-rendered HTML — that's just a worse PDF. The point of this format is the *interactive review structure*: status surfaces, decision forms, pinned diffs.
- Don't import external fonts or CSS — keep the file self-contained for portability and offline use.
- Don't add a "Date generated" footer or printable styles; this isn't meant to be printed.
- Don't add JavaScript unless it earns its keep — the form pattern is the main legitimate exception.
- Don't over-design. Every visual element should encode a decision-flow status or role. Ornament without function is noise.
- **Section "blow-up" without diff markers.** A section grows from 3 lines to 30 across renders and Jacob can't find what's new inside. Flag the new subsection within the grown section and reference it from the pinned "What's new" with a deep anchor.
- **Decisions tracked in chat instead of the HTML.** Lock decisions *in the HTML first*, then mention in chat that they're locked.
- **Audit items missing a verdict.** Every status-bearing row gets a status indicator.
- **"What's new" with broken anchors.** Verify after every restructure.
- **Static "trigger phrase" chips as a substitute for the form pattern.** If the report poses a decision, it gets a real `<fieldset>` with radios + textarea + the sticky toolbar. Rendering trigger words inside `<span class="trigger">` chips and asking Jacob to type them back into chat is *not* the answer mechanism — it skips persistence, skips Copy/Download/Clear, and re-introduces the one-paste-captures-all problem the form pattern exists to solve. The only legal place for static text chips is *inline mentions* in prose ("type `ship to claude.md` when ready"), never as the primary answer surface. Symptom of this failure: *"why is the interactive part not interactive here?"*

## Lifecycle

This skill captures the functional contracts of review HTMLs. The design surface (palette, typography, layout, ornament) is deliberately left to Claude's per-render judgment — codifying specific colors or CSS would converge every render to the same visual register and crowd out attention from the workflow rules that actually carry weight.

Update freely as conventions prove out or fail. The skill is a working artifact, not a fixed spec.

## Where this skill fits in the global rule hierarchy

CLAUDE.md §3 ("Render before review") says HTML is the default for review artifacts. When you build one, invoke this skill for the current best-practice conventions. If CLAUDE.md and this skill disagree, CLAUDE.md wins.
