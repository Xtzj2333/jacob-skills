---
name: chat-substitute-html
description: Use when Claude's reply to Jacob would be a long or multi-paragraph chat message, a tradeoff discussion, or carries decisions Claude needs back. Per CLAUDE.md §3, this is the default reply channel — chat is reserved for brief pointers, single-sentence answers, acknowledgments, and clarifying questions. Skip when the HTML is itself the deliverable (e.g., literature reviews, study mockups, demos, info pages, frontend tools) — those need full creative range, not this skill's review-conversation conventions. Examples illustrative, not exhaustive: if Jacob would keep, edit, share, or hand it off, it's a deliverable.
---

# chat-substitute-html

> Conventions for HTMLs that stand in for chat (CLAUDE.md §3 makes HTML the default reply channel; if CLAUDE.md and this skill disagree, CLAUDE.md wins). Form mechanics — radios, toolbar, persistence, archive chips — come from `decision-forms-html`. This skill fires in almost every chat, mostly for small one-shot answer pages; everything below scales down to that case — the machinery (archive file, chips, sweep) exists only once a page actually iterates.

## When to use vs. when to skip

| Situation | This skill? |
|---|---|
| Multi-turn review where status evolves between renders | ✓ |
| One long structured reply with decisions needed | ✓ |
| Single-decision standalone ask | ✓ |
| HTML that IS the deliverable (lit review, mockup, demo, info page, frontend tool) — single render | ✗ — design freely |
| HTML deliverable being iterated on across renders | ✓ — pair with a separate `_chat-substitute.html` (below); keep furniture out of the deliverable |
| Finished brief Jacob reads straight through | ✗ — `markdown-report-builder` for .docx/.pdf |
| Finished doc Jacob leaves inline margin comments on | ✗ — Jacob calls `commented-edit-roundtrip` when needed |
| Throwaway content Jacob never reopens | ✗ — inline chat |

If unsure, prefer this skill for anything iterative ("we'll come back to this," "what about X?"). Skip aggressively when the HTML is a deliverable — review furniture restricts design freedom where the structure IS the point.

## Pair, don't pollute: deliverable + chat-substitute alongside

When the task produces both a keepable artifact and iterative conversation about it, keep them in separate files: `<topic>.html` (the deliverable, designed freely, only current best content) and `<topic>_chat-substitute.html` alongside (what changed, what to look at, decisions needed). Spin up the pair as soon as you're about to revise an existing deliverable — don't wait for Jacob to ask "what changed?". (Origin incident: a deliverable re-rendered 4+ times with corrections accreting inside it, until current vs. superseded was indistinguishable.)

Default location: the owning project's `reports (claude)/<topic>_chat-substitute.html` — stable un-prefixed name, row in that folder's CATALOG.md (see `reports-catalog`). Claude-infrastructure work uses `~/Claude/reports/<topic>/` instead.

## Dashboard & ledger

The live file is a **dashboard**: what's open, plus what changed this render. Git and the `_ARCHIVE` file are the **ledger**: everything else. Content moves to `<topic>_chat-substitute_ARCHIVE.html` (append-only, timestamped, linked from the live footer; created at first re-render — a one-shot page never needs it) **in the same render it resolves**. Never let the live file accumulate history — that is how boards rot into unreadable scrolls.

**Resolved means traceable to a recorded Jacob action** — a form answer, a change literally made together, an explicit confirmation, a stated decision. It never means "it appeared in a rendered report": Jacob skims; opened ≠ read. Three states follow:

- **Resolved** → archive silently, leaving one line in a small "recently archived" list on the live page (pull-back is one ask away).
- **Unsure** (looks done but never confirmed; half-done) → stays live with an **"Archive this?"** chip (`decision-forms-html` mechanics: click persists, marks ride the next Copy-all paste, the next render executes them). Chips are for genuine uncertainty only — a page where every section carries one is Claude outsourcing judgment.
- **Open** → stays, re-surfaced every render until Jacob acts. Silence is not consent — for decisions *and* for important findings that were only ever displayed.

The meta block and footer obey the same rule: they describe *this* render; earlier renders' meta paragraphs and source lists are record → archive.

## The render procedure

**Step 0 — ledger sweep** (no-op on a first render): execute any archive marks from Jacob's last paste; move resolved sections, stale meta, and old footer sources to the archive; chip the genuinely unsure. Do this *before* writing new content — the sweep is the price of appending.

**Step 1 — write what's open and new.** Title + meta (render number, what changed since last reopen — this render only). Demote answered questions to a slim "your answer" block with verbatim choice + comment; full fieldsets only for open asks. An "already done this turn" callout when the turn produced completions Jacob doesn't need to act on. Bulky supporting material goes in collapsibles (next section).

**Step 2 — TOC.** Required on every render, directly after the meta, one labeled row per live section (anchor + optional one-line gloss). Labels, smallest set that fits:

| Label | Meaning |
|---|---|
| `NEW` | Added or substantively rewritten this render |
| `UPDATED` | Meaningful change this render ("new" would overstate it) |
| `OPEN` | Unanswered ask or unresolved question |
| `LOCKED` | Decision locked this render (drop next render) |
| `RESOLVED` | Closed this render (drop next render; section archives at the next sweep) |
| (none) | Unchanged, nothing open |

`NEW`/`UPDATED`/`LOCKED`/`RESOLVED` never carry forward; `OPEN` persists until answered. A "what's new" callout only when the deltas need more than TOC labels — don't duplicate.

**Step 3 — validate, then reopen.** Anchors resolve (keep anchor IDs stable across renders); stale labels stripped; long prose not in `<pre>` (that's for code/ASCII); no style bleed; every claimed change actually present; reader-facing text passes the plain-language rules below. Then `open` the file unasked whenever the render changed substantially.

## Collapse bulk — but archive the resolved

Jacob's rule: use `<details>` aggressively for bulky *current* material — verbatim exhibits, code, long tables, per-item receipts, secondary context — so the page skims clean, with the `<summary>` styled obviously clickable (affordance cue like ▸, border/hover; a plain-text summary line reads as static text and gets missed). The distinction that keeps this from becoming hoarding: collapsibles hold **supporting detail for live content**; **resolved content goes to the archive file**, not into a collapsed block on the live page.

## Plain language everywhere Jacob reads — titles, legends, chips, tags, prose

Jacob is a UChicago social-psych researcher, not a software engineer. Every section title encodes user-visible function ("How sign-in becomes simpler"), not tool-name ("auth-refactor"). Every section opens with a plain-English WHAT / WHY / SO-WHAT sentence before naming any tool or file. Decision-card legends are plain-English questions Jacob would write himself.

The same rule covers every smaller piece of reader-facing text — chips, card tags, `<details>` summaries, callout labels. A label names what the content means to the reader, not the workflow step that produced it: "How each open question was resolved (July 15)", not "sign-off resolution (2026-07-15)".

Summary prose is short sentences, one idea per sentence. A change is spelled out — "H3 moves from primary to secondary because Tony registered it as a simple main effect" — not compressed into arrows or codenames ("H3 ↓ SECONDARY"). Supporting detail lives in a `<details>` block or a follow-on sentence, not in stacked mid-sentence parentheticals. No session-jargon anywhere Jacob's eyes land.

## Decision asks

Each ask sits at the end of the subtask where the choice arises — not bundled at the bottom — carrying: question, brief context, Claude's recommendation (flagged), and the form fieldset (`decision-forms-html`, lifted verbatim; namespace the STORAGE_KEY per page).

**Jacob's comments don't clean themselves up.** His typed comments live in browser localStorage, so applying a round doesn't remove them from the page and his next Copy-all re-sends them. Any surface with free-text comment boxes gets the applied-comment lifecycle from `decision-forms-html` (processed-comment registry → auto-clear on open, with undo + archive); each render that applies a round appends that round's comments verbatim to the registry.

## Phase boundary

On a true pivot (review wraps, new phase of work), rename the live file to `_ARCHIVE` and start a fresh slim one that links back. Surface this proactively when the last decision locks. Archiving never waits for a phase boundary — the per-render sweep already handles resolved content.

## Don'ts

- Generic markdown-rendered HTML — that's just a worse PDF; the interactive status structure is the point.
- External fonts or CSS — self-contained, offline-portable.
- "Date generated" footers or print styles.
- Ornament without function — every visual element encodes status or role.
- Decisions tracked in chat instead of the HTML — lock in the HTML first, then mention in chat.
- Static "trigger phrase" chips in place of real forms — they skip persistence and one-paste-captures-all. (The archive chip is not this: it's a persisted control, not a request to type.)
