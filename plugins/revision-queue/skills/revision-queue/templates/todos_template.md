---
title: "<PROJECT> — Open To-Do List"
subtitle: "Open items needing your decision or input"
date: "YYYY-MM-DD"
---

# How to use this document

Each item below has these sections (some are optional):

- **The artifact** — the actual table image, screenshot, or prose quote we're discussing
- **Issue** — what's wrong / what's deferred
- **Options** *(or **Decision points** / **What I'm waiting on from you**)* — at least two if there's a real choice; one with a clear recommendation otherwise
- **My recommendation** — Claude's pick, with one-sentence rationale
- **When to revisit** *(Later items only)* — the trigger that should pull this back to Active
- **Your response** — fill this in; I'll read and act on it (or comment in the docx margin)

Just type your decision under "Your response" for any item. Strike through, add new items, or rearrange — I'll pick up whatever's there.

**Active vs. Later.** Items above the **# Later** heading are the current-round queue. Items under **# Later** are open and unresolved but explicitly not blocking now. New items can be filed directly into Later (e.g., "future cleanup," "after submission") — they don't have to start in Active.

**Lifecycle.** When a TODO gets resolved (either by approving a code edit or by inaction/compliment/prior fix), it is **removed from this file** and appended to the project's completed-actions log with a TYPE tag. This file shows only **open** items; the change log is the audit trail. Code edits that are approved but not yet executed sit in the project's actions file (3-file async pattern only) until a fresh Claude session runs them.

Sub-items inside a TODO (numbered 1, 2, 3 … or lettered a, b, c …) can resolve incrementally: mark them with `~~strikethrough~~` + `[PARTIALLY RESOLVED YYYY-MM-DD: ...]`. The parent stays open until all sub-items close.

TODO numbers are stable across rounds — they don't renumber on cleanup, so cross-references like "see TODO 7" stay anchored.

Manuscript / artifact path: `<path/to/main/file>`

---

# <Section header for grouping, e.g. "Quick wins (ready-to-apply patches)">

## TODO 1 — <DECISION ID if any>: <Short title>

**Issue:** <one or two sentences describing what's wrong / deferred>

**The artifact:**

> <verbatim quote OR screenshot path: ![](path/to/screenshot.png)>

**Options:**

- (i) <option 1 — describe the trade-off>
- (ii) <option 2 — describe the trade-off>

**My recommendation:** <i / ii / something else>, because <one sentence>.

**Your response (...):**

---
