# <PROJECT> — Completed Actions Log

**Purpose.** Append-only version-control log of every revision item that has been resolved on this project. Each batch is dated. Within a batch, entries are listed in execution order.

**Conventions.**
- **Append-only.** New entries go below the most recent batch heading; do not edit or delete prior entries.
- **Chronological order.** Batches are dated; within a batch, entries are listed in execution order.
- **TYPE field.** Each entry carries one of:
  - `[TYPE: ACTION]` — an executed code/text edit. Includes file → line(s) → before → after → why. Cross-links to the originating TODO if applicable (`resolves TODO X`).
  - `[TYPE: TODO]` — a discussion item resolved without code edits (compliments, prior-fix acknowledgments, resolved-by-inaction, declined). Includes the question + the resolution + why.
- **Working-doc invariant.** Once an entry lands in this log, the source row in `<USER>_actions.md` (for ACTIONs) or `<USER>_todos.md` (for TODOs) is removed. The log is the single source of truth for resolved items; the working docs only show open items.
- For deletions, `after` is `(removed)`.
- For citation reorders, list both `before` and `after` cite keys.

---

*(Append future batches below this line. Each batch must include the date, source-of-changes pointer, summary, per-entry diffs/resolutions with TYPE field, and verification where applicable.)*
