---
name: chat-substitute-html
description: Use when Claude's reply to Jacob would be a long or multi-paragraph chat message, or carries decisions Claude needs back. This is the default reply channel — chat is reserved for brief interactions. Skip when the HTML is itself the deliverable (e.g., literature reviews, study mockups, demos, info pages, frontend tools) — those need full creative range, not a reply substitute.
---

# chat-substitute-html

A chat-substitute is a normal chat reply in a better medium: the same message, delivered as an HTML page, because the chat box strips structure and forces Jacob to scroll a transcript. Nothing more. It is not a template — no mandated sections, banners, pills, or layout; write it the way you'd write the chat reply.

The rules below exist only where the medium actually differs from chat:

1. **Stable path, and reopen it.** Path, filename, and catalog row per `reports-catalog`. Chat reaches Jacob by itself; a file doesn't — reopen it unasked (CLAUDE.md §3) whenever it changes substantially. Skip for minor word fixes.

2. **Asks are forms.** A decision Jacob needs to answer gets a real fieldset, placed where the question arises, with Claude's recommendation flagged. `decision-forms-html` owns every form, chip, and comment mechanic.

3. **The page is this moment's message, not a growing dossier.** A re-rendered file accumulates where chat scrolls away, so sweep on every render: open asks stay; anything Jacob has acted on, moved past, or that a later round superseded moves whole to `<topic>_chat-substitute_ARCHIVE.html`, leaving a one-line "Previously" pointer. The conversation is the evidence — an answered question is archive. Blocks carry an archive chip and comment box so Jacob can dismiss and annotate himself; his marks override what you kept, never replace the sweep. One home per item — no duplicates. Folding current detail into `<details>` is not sweeping.

4. **One genre per file.** The moment a chat-substitute wants to be a board, dashboard, tracker, or index — something Jacob returns to rather than a message he reads once — split that out as a named deliverable, designed freely, and let the reply point at it. Deliverables stay clean of review furniture; their conversation lives in the paired chat-substitute. Renaming an existing tracked file needs Jacob's OK.

5. **Self-contained.** No external fonts, CSS, or scripts — these are local files reopened weeks later; CDNs rot. Everything inline.
