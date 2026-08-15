---
name: chat-substitute-html
description: Use when Claude's reply to Jacob would be a long or multi-paragraph chat message, or carries decisions Claude needs back. This is the default reply channel — chat is reserved for brief interactions. Skip when the HTML is itself the deliverable (e.g., literature reviews, study mockups, demos, info pages, frontend tools) — those need full creative range, not a reply substitute.
---

# chat-substitute-html

A chat-substitute is a normal chat reply in a better medium: the same message, delivered as an HTML page, because the chat box strips structure and forces Jacob to scroll a transcript. Nothing more.

The rules below exist only where the medium actually differs from chat:

1. **Stable path, and reopen it.** Path, filename, and catalog row per `reports-catalog`. Chat reaches Jacob by itself; a file doesn't — reopen it unasked (CLAUDE.md §3) whenever it changes substantially. Skip for minor word fixes.

2. **Asks are forms.** A decision Jacob needs to answer gets a real fieldset, placed where the question arises, with Claude's recommendation flagged. `decision-forms-html` owns every form, chip, and comment mechanic; don't restate them here.

3. **The page is this moment's message, not a growing dossier.** A re-rendered file accumulates where chat scrolls away, so sweeping is part of every render rather than a chore for later:

   - **Sweep generously — this is licensed, not presumptuous.** Open asks stay. Anything Jacob has acted on, moved past, or that a later round superseded moves whole to the archive. *The conversation is the evidence*: if he's answered the question, the question is archive; if he's bought the thing, the shopping analysis is archive.
   - **Create `<topic>_chat-substitute_ARCHIVE.html` in the same turn as the page itself, empty.** An archive deferred until it's "needed" never gets created, and the missing file hides the missing habit. Link it from every section, not once at the top.
   - **"Previously" fold** — one-liners linking into the archive. It holds headlines, never content; an item leaves once he's acted on it. This is Jacob's recall surface, because he skims.
   - **Every content block carries an archive chip and comment box**, so Jacob dismisses and annotates blocks himself. His marks are his override for what you kept — never the mechanism for what you should have swept.
   - **One home per item.** When the same fact would appear in two sections, keep it in one and let the other cross-reference or omit. When an item's twin is archived, the survivor goes with it or absorbs it.
   - **Pins are single-occupancy.** A new pin demotes the old one in the same edit.

   Folding bulky *current* detail into `<details>` is not sweeping — a page fixed only by folding is still a dossier.

4. **One genre per file — the name is the test.** The moment a chat-substitute wants to be a board, dashboard, tracker, or index (standing status sections, an identity Jacob returns to rather than a message he reads once), split that content out as a named deliverable designed freely, and let the reply point at it. Renaming an existing tracked file needs Jacob's OK. The boundary runs both ways: a deliverable stays clean of review furniture, with its conversation in the paired chat-substitute.

5. **Self-contained.** No external fonts, CSS, or scripts — these are local files reopened weeks later; CDNs rot and the page would silently degrade. Everything inline.
