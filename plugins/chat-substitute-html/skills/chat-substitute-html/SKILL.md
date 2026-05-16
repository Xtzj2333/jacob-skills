---
name: chat-substitute-html
description: Use when Claude's reply to Jacob would be a long or multi-paragraph chat message, a tradeoff discussion, or carries decisions Claude needs back. Per CLAUDE.md §3, this is the default reply channel — chat is reserved for brief pointers, single-sentence answers, acknowledgments, and clarifying questions. Skip when the HTML is itself the deliverable (e.g., literature reviews, study mockups, demos, info pages, frontend tools) — those need full creative range, not this skill's review-conversation conventions. Examples illustrative, not exhaustive: if Jacob would keep, edit, share, or hand it off, it's a deliverable.
---

# chat-substitute-html

> Conventions for HTMLs that stand in for chat. The page roles, the "what's new" pin, the locked-decision economy, the bi-file iteration pattern, the status banner — all the ways an iterating review document stays scannable across renders. Form mechanics themselves (radios, toolbar, persistence) come from `decision-forms-html`, which this skill cross-references.

## When to use vs. when to skip

| Situation | This skill? |
|---|---|
| Multi-turn review where status evolves between renders | ✓ |
| One long structured reply with decisions needed | ✓ |
| Single-decision standalone ask | ✓ |
| HTML that IS the deliverable (lit review, mockup, demo, info page, frontend tool) | ✗ — design freely |
| Finished brief Jacob reads straight through | ✗ — use `markdown-report-builder` for .docx/.pdf |
| Finished doc Jacob leaves inline margin comments on | ✗ — Jacob calls `commented-edit-roundtrip` manually when needed |
| Throwaway content Jacob never reopens | ✗ — inline chat |

If unsure, prefer this skill for anything iterative ("we'll come back to this," "let me think about it," "what about X?"). Skip aggressively when the HTML is a deliverable — review-conversation furniture (pins, status banners, decision forms) restricts Claude's design freedom for content where the structure IS the point.

## Output location

Stable path so reopening hits the same file each time. Default: `<working-directory>/<topic>_review.html`.

## Bi-file pattern (default rhythm)

Iterating reports use two files:

- **`<topic>_review.html`** — live. Slim, only currently open content. Re-rendered fresh each turn; new content goes here, old content moves out.
- **`<topic>_review_ARCHIVE.html`** — append-only ledger of resolved content with timestamps. Footer of the live file links to it.

The starting question each render is: *"what is currently open or new?"* — not *"what should I add to what's already here?"* Conservative archival: content Jacob has directly responded to or obviously read moves to the archive; prose he hasn't engaged with stays in the live file until he does.

Spin up the archive file on first re-render (not the first render). For a single-shot deliverable, no archive needed.

## Page roles, when present

Building blocks of a chat-substitute HTML. Not all renders need all of them — pick what fits.

1. **Title + meta** (source path, render number, what changed since last reopen).
2. **"Already done this turn" callout** — completions Jacob doesn't need to act on. Use when the turn produced concrete wins.
3. **"What's new in this render" pinned surface** — anchor-linked list of deltas since last reopen. Refreshes every render. "New" markers do NOT carry forward.
4. **Status banner** — when the doc has an action state at-a-glance ("ready to ship" vs "in progress"). Use a state pill on a horizontal band. Optional.
5. **Table of contents** — required for 3+ major sections; each `<h2>` gets a stable anchor ID.
6. **Body** — organized by section; status/verdict encoded visually for scan.
7. **Source-file footer** — italic block of paths Jacob can navigate to.

## Plain-language section titles and decision-card legends

Jacob is a UChicago social-psych researcher, not a software engineer. Every section title encodes user-visible function ("How sign-in becomes simpler"), not tool-name ("auth-refactor"). Every section opens with a plain-English WHAT / WHY / SO-WHAT sentence before naming any tool or file. Decision-card legends (the `<legend>` text on each form) are plain-English questions Jacob would write himself coming back cold.

Cold-read test: if Jacob walks away for two days and reopens, every section title and form legend should still parse without re-loading the session's internal vocabulary.

## Decision asks: progressive placement

When the report asks Jacob for a decision, each ask sits at the end of the subtask where the choice arises — not bundled at the bottom. Each ask carries: question, brief context, Claude's recommendation (flagged), and the answer mechanism (the form fieldset).

**Mechanics come from `decision-forms-html`** — lift its `references/form-pattern.js` verbatim. See that skill for the markup conventions, toolbar setup, and localStorage namespacing.

## Per-render rules

- **Demote answered questions on re-renders.** Show a slim "your answer" block with verbatim choice + comment. Reserve the full form for still-open questions.
- **Locked-decision economy.** Do not re-describe locked or declined decisions in full each render. Demote to one-liners in a `<details>` block. Same for superseded narratives — demote the diagnostic prose along with the resolved question.
- **"What's new" hygiene.** Per-render pin, not cumulative. Remove "new" markers from prior render's items. Locked decisions are status, not novelty — flag as locked, not new.
- **Anchor IDs stable.** `#extract-skill` works even if its section grows 5× across renders. Don't rename anchors.
- **Silence is NOT consent.** When Jacob's reply doesn't address an open question, surface it again next render — don't auto-resolve. "Locked" requires a quotable explicit yes.
- **Reopen after substantial updates.** When the file changes substantially (new sections, locked decisions, new diff, new ask), reopen it (`open <file>`) without being asked. Skip for minor word fixes.

## Phase boundary: archive + fresh slim doc

When all open items in a review resolve, rename the current file with an `_ARCHIVE` suffix and start a fresh slim file for the new phase. The fresh file references the archive in its source-file footer but doesn't duplicate resolved content. Surface this proactively in the render where the last decision locks — don't wait to be asked.

## Self-validate the render before declaring "done"

Before opening the file and saying it's ready:

1. **Long-form prose is not inside `<pre>`.** `<pre>` is for code or short ASCII fragments. Prose meant to be read goes in HTML (headings, paragraphs, lists, blockquotes) so it wraps and markdown markers don't render as literal `**` / `---` noise.
2. No accidental strikethrough, all-bold, or other style bleeds.
3. The "What's new" box matches reality — every claimed change is actually present.
4. All decision-card legends pass the cold-read test (no session-jargon).
5. Anchors in "What's new" actually resolve.

## Don'ts and known failure modes

- Don't make a generic markdown-rendered HTML — that's just a worse PDF. Interactive review structure (status surfaces, decision forms, pinned diffs) is the point.
- Don't import external fonts or CSS — self-contained, offline-portable.
- Don't add a "Date generated" footer or printable styles; this isn't a print artifact.
- Don't over-design. Every visual element encodes a decision-flow status or role. Ornament without function is noise.
- **Section "blow-up" without diff markers.** A section grows 3 → 30 lines and Jacob can't find what's new inside. Flag the new subsection within it and deep-anchor it from "What's new."
- **Decisions tracked in chat instead of HTML.** Lock decisions in the HTML first, then mention in chat that they're locked.
- **Static "trigger phrase" chips as a substitute for forms.** If the report poses a decision, it gets a real `<fieldset>` with radios + textarea (via `decision-forms-html`). Trigger-phrase chips asking Jacob to type words back into chat skip persistence and the one-paste-captures-all property.

## Where this skill fits

CLAUDE.md §3 ("Render before review") says HTML is the default reply channel. When that HTML is a chat-substitute, invoke this skill for the conventions. For the form mechanics inside it, this skill calls `decision-forms-html`. If CLAUDE.md and this skill disagree, CLAUDE.md wins.
