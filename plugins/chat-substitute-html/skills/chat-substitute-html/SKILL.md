---
name: chat-substitute-html
description: Use when Claude's reply to Jacob would be a long or multi-paragraph chat message, or carries decisions Claude needs back. This is the default reply channel — chat is reserved for brief interactions. Skip when the HTML is itself the deliverable (e.g., literature reviews, study mockups, demos, info pages, frontend tools) — those need full creative range, not a reply substitute.
---

# chat-substitute-html

A chat-substitute is a normal chat reply in a better medium: the same message, delivered as an HTML page, because the chat box strips structure and forces Jacob to scroll a transcript. Nothing more.

The few rules below exist only where the medium actually differs from chat:

1. **Stable path, and reopen it.** `reports (claude)/<topic>_chat-substitute.html` in the owning project (catalog row per `reports-catalog`; Claude-infra work uses `~/Claude/reports/<topic>/`). Chat reaches Jacob by itself; a file doesn't — `open` it, unasked, whenever it changes substantially.

2. **Asks are forms.** A decision Jacob needs to answer gets a real fieldset via `decision-forms-html` (persistence + one-paste-captures-all), placed where the question arises, with Claude's recommendation flagged. That skill also carries the comment-box lifecycle and the archive chip.

3. **The page is the current reply.** A re-rendered file accumulates where chat scrolls away — so sweep before adding: open asks stay on the page; everything else moves whole to `<topic>_chat-substitute_ARCHIVE.html` (append-only, visible button near the top); bulky live detail goes in `<details>` folds. Important findings from earlier replies go in a clickable **"Previously"** fold as one-liners linking into the archive — Jacob skims, so this is his recall surface; it holds headlines, never content, and an item leaves once he's acted on it. **Every content block carries its own "Archive this?" chip, paired with a click-to-expand comment box** (one unit — markup and mechanics in `decision-forms-html`) so Jacob dismisses blocks himself, one by one, and can annotate any block in place — marks and card comments ride the copy-all paste and the next render executes/applies them; open-ask forms are the exception (they resolve by being answered, and already have their own comment box). The test: the page reads as this moment's message, not a growing dossier.

4. **One genre per file — the name is the test.** The moment a chat-substitute wants to be a board, dashboard, tracker, or index (standing status sections, a roadmap, an identity Jacob returns to rather than a message he reads once), split that content out as a named deliverable designed freely (renaming an existing tracked file needs Jacob's OK) and let the reply point at it. The boundary runs both ways: a deliverable stays clean of review furniture — forms, archive buttons, what's-new chatter — with its conversation in the paired chat-substitute.

5. **Self-contained.** No external fonts, CSS, or scripts — these are local files reopened weeks later; CDNs rot and the page would silently degrade. Everything inline.
