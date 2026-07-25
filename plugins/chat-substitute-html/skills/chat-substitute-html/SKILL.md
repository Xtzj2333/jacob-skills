---
name: chat-substitute-html
description: Use when Claude's reply to Jacob would be a long or multi-paragraph chat message, a tradeoff discussion, or carries decisions Claude needs back. Per CLAUDE.md §3, this is the default reply channel — chat is reserved for brief pointers, single-sentence answers, acknowledgments, and clarifying questions. Skip when the HTML is itself the deliverable (e.g., literature reviews, study mockups, demos, info pages, frontend tools) — those need full creative range, not this skill's review-conversation conventions. Examples illustrative, not exhaustive: if Jacob would keep, edit, share, or hand it off, it's a deliverable.
---

# chat-substitute-html

A chat-substitute is Claude's chat message in a better medium: the same reply, delivered as an HTML page with decision forms, because the chat box strips structure and forces Jacob to scroll a transcript. It is **not a template**. No mandated sections, banners, status pills, TOCs, or layout — write it the way you'd write the chat reply, and use HTML's extra range (structure, collapsibles, forms) only where it helps this particular reply.

The few rules below exist only where the medium actually differs from chat:

1. **Stable path, and reopen it.** `reports (claude)/<topic>_chat-substitute.html` in the owning project (catalog row per `reports-catalog`; Claude-infra work uses `~/Claude/reports/<topic>/`). Chat reaches Jacob by itself; a file doesn't — `open` it, unasked, whenever it changes substantially.

2. **Asks are forms.** A decision Jacob needs to answer gets a real fieldset via `decision-forms-html` (persistence + one-paste-captures-all), placed where the question arises, with Claude's recommendation flagged. That skill also carries the comment-box lifecycle and the archive chip. Don't substitute static "type this back" chips for forms.

3. **The rot rule.** Chat scrolls away on its own; a re-rendered file accumulates — so on each re-render, sweep before adding. The live page keeps only what is **live**: open asks, important findings Jacob hasn't acknowledged (he skims — opened ≠ read, so these re-surface until he acts; silence is not consent), and supporting detail for those. Everything else moves to `<topic>_chat-substitute_ARCHIVE.html` (append-only, linked from the footer, created at first re-render), leaving a one-line "recently archived" mention — nothing is ever deleted, so importance is not the criterion; liveness is. What that means per content type: an **ask or finding** leaves only on a recorded Jacob action (form answer, change made together, explicit confirmation); **transient material** (past-render notes, narration, superseded context) leaves on its own — it was never waiting on him; when **unsure** which of those a thing is, keep it with an "Archive this?" chip and let him click. On a true pivot, archive the whole file and start fresh.

4. **Collapse bulk.** Put bulky supporting material (verbatim exhibits, code, long tables) in `<details>` with an obviously-clickable summary, so the page skims clean. Collapsibles are for live supporting detail; resolved content archives instead of hiding in a fold.

5. **Self-contained.** No external fonts, CSS, or scripts (the habitual CDN reach) — these pages are local files reopened weeks later; external assets need a network and rot as CDNs move, so the page would silently degrade. Everything inline.

6. **Deliverables stay clean.** If the HTML is a keepable artifact, design it freely and put the conversation in a paired `<topic>_chat-substitute.html` next to it, rather than bolting review furniture onto the artifact.
