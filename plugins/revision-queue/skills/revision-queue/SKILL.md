---
name: revision-queue
description: Manage a multi-round revision workflow with two coordinated files — an open-discussion TODO list and an append-only chronological change log. Use when a user is iterating on a manuscript, codebase, or any artifact across many small decisions and wants to keep "what's open" and "what's done" cleanly separated, with full audit trail. Pairs naturally with `commented-edit-roundtrip`. (See "Optional async pattern" for a 3rd file when you need an approved-but-not-executed queue.)
---

# revision-queue

A state machine for revision items. **Default: 2 files** (open todos + append-only log) for the common interactive case where Claude applies edits live as the user approves them. Extends to 3 files (adding a queued-action layer) for asynchronous handoff cases.

## Configuration — `USER_NAME`

This skill names its working files after the user. Set the environment variable `USER_NAME` (in `~/.claude/CLAUDE.md`, your shell rc, or a project-local CLAUDE.md) to your preferred prefix:

```
USER_NAME=jacob          # files become jacob_todos.md, jacob_actions.md
USER_NAME=tony           # files become tony_todos.md, tony_actions.md
```

If `USER_NAME` is unset, the skill defaults to `user`, producing `user_todos.md` and `user_actions.md`. Below, `<USER>` is shorthand for whatever `USER_NAME` resolves to.

**Core invariant:** every TODO is in exactly one place — either open in `<USER>_todos.md` or resolved in `completed_actions_log.md`. Never duplicated, never lost. (Sub-items inside a TODO body can resolve incrementally — see "Sub-items, partial resolution, and corrections" below — but the parent TODO is still in exactly one place.)

## Vocabulary the user may use (treat as synonyms)

Users rarely use the same word twice for the same thing. Recognize these as the same skill operations:

| User says… | Means… |
|---|---|
| "TODO" / "to-do" / "todo" / "cue" / "queue" / "revision queue" / "revision cue" | A row in `<USER>_todos.md` |
| "process" / "close" / "resolve" / "clear" / "mark done" / "fold in" / "merge in" | Move from `<USER>_todos.md` → log entry; remove from todos |
| "open" / "active" / "live" / "pending" | Still in `<USER>_todos.md`, not yet resolved |
| "later" / "defer" / "punt" / "set aside" / "next cycle" | Move (or file) under the **# Later** heading; still open, not blocking now |
| "demote" | Move Active → Later |
| "promote" | Move Later → Active |
| "add a later TODO" / "add to later" | File a new TODO directly under **# Later** without ever sitting in Active |
| "log" / "audit trail" / "what shipped" / "the change log" | `completed_actions_log.md` |
| "comment" / "margin comment" / "the docx" | The user's decisions, recorded in `*.docx` margin comments — read via `commented-edit-roundtrip` |

When the user says "process these" or "are these done — if so, process," they want you to: confirm each is actually resolved, then run the close/log step for those that are. If any are not actually done, **flag them; do not silently process**.

## When to Use

- Long-running revision projects: manuscripts going through reviewer rounds, codebases under iterative refactor, documents that get edited across many sessions.
- Workflows where the user authors the artifact and Claude proposes edits: the TODO list is where Claude surfaces questions/options and the user decides; the log is the audit trail of what shipped.
- Anywhere you'd otherwise be tempted to keep a single "todo.md" that mixes open discussion and already-done items into one drifting file.

## When NOT to Use

- One-shot edits with no follow-up — overhead isn't worth it.
- Workflows where the user is the sole author and there's no decision-by-Claude phase (no TODOs to discuss, just commits).
- Tasks better captured as Git commits + PR descriptions than a per-project markdown queue.

## The default 2-file state machine

```
                  ┌─────────────────────────────────┐
                  │      <USER>_todos.md/docx       │
                  │   (open discussion + decisions)  │
                  │                                  │
   new question   │  - artifact (screenshot/quote)  │
   ──────────────→│  - issue                        │
                  │  - options + recommendation     │
                  │  - user's decision (via docx    │
                  │    margin comment, typically)   │
                  └────────────────┬─────────────────┘
                                   │
                                   │  apply edit + log result
                                   ↓
                  ┌──────────────────────────────────┐
                  │    completed_actions_log.md      │
                  │  (append-only, dated, tagged     │
                  │   TYPE: ACTION or TYPE: TODO)    │
                  └──────────────────────────────────┘
```

Each file has a fixed role:

- **`<USER>_todos.md`** — open discussion. One section per TODO with the artifact (screenshot/quote/diff), the issue, the options, Claude's recommendation. The user signals decisions by leaving margin comments in the corresponding `.docx` (Claude reads those via `commented-edit-roundtrip`).
- **`completed_actions_log.md`** — append-only chronological audit. One entry per resolved item. Each entry carries a `[TYPE: ACTION]` or `[TYPE: TODO]` tag and (when applicable) a cross-link to the originating TODO #.

The user maintains `.md` as the source; `.docx` mirrors are generated by pandoc so the user can read in Word.

## Procedure

### 1. Set up a new project

```bash
USER_NAME="${USER_NAME:-user}"
mkdir -p Projects/<project>-revisions
cp ${CLAUDE_PLUGIN_ROOT}/skills/revision-queue/templates/todos_template.md \
   "Projects/<project>-revisions/${USER_NAME}_todos.md"
cp ${CLAUDE_PLUGIN_ROOT}/skills/revision-queue/templates/completed_actions_log_template.md \
   Projects/<project>-revisions/completed_actions_log.md
bash ${CLAUDE_PLUGIN_ROOT}/skills/revision-queue/scripts/regen_docx.sh \
   Projects/<project>-revisions
```

### 2. Add a TODO

Append a `## TODO N — title` section to `<USER>_todos.md`. Required subsections:

- **The artifact** — paste a screenshot, quote, or diff so the user can see what you mean
- **Issue** — what's wrong / what's deferred
- **Options** — at least two if there's a real choice; one with a clear recommendation otherwise
- **My recommendation** — Claude's pick, with one-sentence rationale

Then `bash regen_docx.sh <dir>` so the user sees the update on their side.

### 3. Read the user's decisions

The user records decisions via **docx margin comments**, not by editing the markdown. Use `commented-edit-roundtrip`'s `read_docx_comments.py` to extract them, filter by `(author, date)`.

### 4. Apply the edit and log it

When `commented-edit-roundtrip` Mode A (perpetual inbox) is in use, edits land on the **inbox** (`revisions/[inbox] <manuscript>.md`), not directly on canonical. Use `apply_edit_to_inbox.py` so any displaced inbox comments are archived with full context. Canonical advances only at explicit promotion (`promote_inbox_to_canonical.py`). For projects without a perpetual inbox, edit the target file directly with `Edit` / `Write` / `Bash`.

Then append a `[TYPE: ACTION]` entry to `completed_actions_log.md` and remove the TODO row from `<USER>_todos.md`. The ACTION entry's `File:` field should point at the edited file (the inbox `.md` for inbox-routed edits, the canonical otherwise).

For TODO resolutions that don't involve a code edit (compliment, prior-fix, decline, inaction):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/revision-queue/scripts/close_todo.py \
    --dir Projects/<project>-revisions \
    --todo-id 11 \
    --reason "Misread of source: was a reply, not a delete request" \
    --resolution "no-action"
```

The script appends a `[TYPE: TODO]` entry to the log and removes the TODO from `<USER>_todos.md`.

### 5. Verify state

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/revision-queue/scripts/verify_state.py \
    --dir Projects/<project>-revisions
```

Checks:
- No duplicate TODO IDs in `<USER>_todos.md`.
- Log entries are in chronological order (date headings ascending).
- Each `.docx` is newer than its `.md` source.
- Every "resolves TODO X" cross-link in the log points to a TODO that's no longer in `<USER>_todos.md`.

Exits 0 on success; 1 with a diagnostic on any violation.

### 6. Regenerate docx mirrors

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/revision-queue/scripts/regen_docx.sh \
    Projects/<project>-revisions
```

Run after any `.md` edit so the user's `.docx` view is current.

## Organizing the open queue (optional but useful as it grows)

`<USER>_todos.md` accepts H1 category headings to group TODOs. Numbering remains stable across moves between sections — only the section is different.

A common split once the queue gets ≈ 8+ items:

```markdown
# Editorial calls — your judgment
## TODO 9 — ...
## TODO 10 — ...

# Data-pending
## TODO 11 — ...

[ ... other "active now" categories ... ]

# Later — to address before submission, not blocking now

*Open items the user explicitly set aside for a later cycle. Still need to be resolved before the artifact ships, but not part of the current round's decision queue.*

## TODO 4 — ...
## TODO 20 — ...

# New items / questions for me

*Free-form catch-all for items the user wants to surface.*
```

When this pattern is in use, add a one-sentence "Active vs. Later" pointer to the "How to use this document" section so the user knows which bucket they're reading. Promotion/demotion between Active and Later is a single-edit move; the TODO body is unchanged and the ID is preserved.

The user — not Claude — decides when to demote a TODO to Later. Default: leave items in their original Active section unless explicitly told otherwise.

### Filing directly into Later (vs. demoting from Active)

A TODO can be **born in Later** — it does not have to start in Active and get demoted. Use this when:

- The user surfaces a future cleanup or long-horizon plan and explicitly does not want it on the current decision queue ("note this for later," "add a later TODO," "future merge to fold X into Y").
- A new decision is identifiable but explicitly bundled with a future trigger (e.g., "after submission," "when we revisit Z").
- The work is real and tracked, but pulling it into Active would make the current round noisier.

When filing directly into Later, the body should usually include two extra subsections that don't appear in normal Active TODOs:

- **When to revisit** — the trigger that should pull it back to Active (date, milestone, dependent TODO).
- **Recommended trigger** *(optional)* — Claude's suggestion for when to act, especially if it bundles with another open TODO.

The user (not Claude) still decides what counts as "Later." If you're unsure whether a new TODO belongs in Active or Later, file it in Active and ask in the body — don't pre-emptively bury something the user wants to see now.

### Status sentinels you may see in TODO titles

These are informal annotations the user (or Claude, with sign-off) appends to a TODO title to signal current state without changing the ID or section:

| Sentinel | Meaning |
|---|---|
| `(active priority)` | Open and needs attention this cycle |
| `(later)` / `(deferred)` | Open but explicitly set aside; lives under # Later |
| `(planned, not yet executed)` / `(designed, do-not-run-yet)` | Body is complete; user has not authorized execution |
| `(partially resolved YYYY-MM-DD)` | Some sub-items closed inline; parent stays open |
| `[MERGED YYYY-MM-DD — see ...]` | Code/content has shipped but the parent TODO is being kept around briefly to document residual cleanup debts (which usually live in a follow-on TODO) |
| `[opened YYYY-MM-DD]` | TODO was added in a specific batch; helps disambiguate when the same conceptual item has been re-filed across rounds |

Sentinels are advisory — they help a Claude session resuming cold get oriented before reading the body. They don't replace removing the TODO from `<USER>_todos.md` when fully resolved.

## Entry-format conventions

### Log entry — `[TYPE: ACTION]`

```markdown
### Entry N — [TYPE: ACTION] <title> (resolves TODO X / Shige #Y)
- **File:** path/to/file.tex
- **Line(s):** LLL–MMM
- **Before:**
  > <verbatim, multiline OK>
- **After:**
  > <verbatim, multiline OK>
- **Why:** <one to two sentences — include originating TODO/Shige #>
- **Verification:** <recompile note + grep / pdftotext check>
```

### Log entry — `[TYPE: TODO]`

```markdown
### Entry N — [TYPE: TODO] TODO X: <title>
- **Resolution:** <no-action / compliment / prior-fix / declined / deferred-cancelled>
- **Why:** <one to two sentences — include originating TODO/Shige #>
```

### Batch heading

```markdown
## Batch YYYY-MM-DD — <short label>

### Source
<pointer to input that drove the batch — e.g., "5 user comments on <USER>_todos.docx (timestamps 23:15–23:18).">

### Summary
<one paragraph>

---

<entries here>
```

## Sub-items, partial resolution, and corrections within a TODO body

A TODO body is not always a single yes/no decision. Three patterns recur:

### Sub-items

A TODO can carry numbered (1, 2, 3 …) or lettered (a, b, c …) sub-items when one decision-thread legitimately has parts. Examples:

- An audit TODO with 6 cleanup debts (item 1, item 2, …).
- A migration TODO with phases 21(a), 21(b), 21(c).

Sub-items live inside the parent TODO's body, share its ID, and can resolve incrementally without removing the parent. Don't promote sub-items into their own top-level TODOs unless they grow large enough to need their own decision queue.

### Partial resolution

When some sub-items of an open TODO have shipped but others haven't, mark the resolved ones inline. Two equivalent forms:

- **Strikethrough + bracketed annotation:**
  ```markdown
  6. ~~Cross-wave paragraph word count: +116 words to Bucket A~~
     [PARTIALLY RESOLVED 2026-04-29: paragraph relocated to Appendix D lead-in; word-count breakdown split out to standalone PDF; trim still tracked in TODO 15.]
  ```
- **Plain dated note** (when no original text needs to be struck):
  ```markdown
  Sub-item 21(a) — Verification round ✅ DONE 2026-04-28
  ```

The parent TODO stays in `<USER>_todos.md` until *all* sub-items are resolved or the user explicitly closes it. When the parent is finally closed, the log entry should reference the sub-item resolutions in `Why:` so the audit trail captures the incremental closure.

**Do not** silently delete a sub-item that has been resolved. Leave a strikethrough/annotation so the user (and future Claude) can reconstruct what shipped vs. what's still open without cross-referencing the log.

### Time-stamped corrections

When a TODO body sits open across multiple sessions and the situation changes — a misread is corrected, a sub-item is reframed, a new constraint surfaces — append a dated correction line **above** (or as the first child of) the affected subsection rather than rewriting silently:

```markdown
**Correction (YYYY-MM-DD, second round of margin comments).** I previously
misread your guidance and demoted #8 and #13 to Later — that was wrong;
they're priorities and stay Active.
```

This preserves the audit trail in-place. If the correction is large enough that the original framing has become misleading, add the correction note **and** rewrite the affected subsection — but never just rewrite.

### Cross-references between TODOs

TODOs commonly point at each other: "bundled with TODO 15," "see TODO 25," "supersedes TODO 7." Two rules:

1. **Use stable IDs in cross-refs.** Never substitute a description ("the cleanup TODO") for the number — descriptions drift.
2. **Don't auto-rewrite cross-refs when a TODO closes.** A closed TODO is in the log; cross-refs from open TODOs to a closed one are still meaningful as historical pointers. (The log itself contains the resolution, so following the cross-ref still works.)

When you remove a TODO from `<USER>_todos.md`, search for its number in the rest of the file and the log. If another open TODO carries an active dependency on it (e.g., "blocked by TODO X"), update that cross-ref to point at the resolving log entry — don't just leave a dangling number.

## Optional async pattern (3-file extension)

For workflows where decisions must be **queued** for execution by a different session — e.g., overnight loops that need a fresh morning session to run them, or batches the user wants to review-then-batch-execute — add a third file: `<USER>_actions.md`.

In this mode:
- TODO is approved → Claude writes a self-contained `## ACTION N` block to `<USER>_actions.md` (with file path, exact find-text, exact replace-text, verification grep, recompile flag).
- A different session loads `<USER>_actions.md` and runs `execute_action.py` to apply each block, log it, and remove it from the queue.
- The TODO row stays in `<USER>_todos.md` with a `⏳ queued for execution as ACTION N` note until execution.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/revision-queue/scripts/execute_action.py \
    --dir Projects/<project>-revisions --all --regen-docx
```

This is **not the default** — only use when you have a real handoff between approval and execution. For interactive workflows where Claude approves and applies in the same session, skip this layer entirely.

The `actions_template.md`, `execute_action.py`, and the `--queue-actions` flag remain in the skill for this case.

## Failure modes (avoid these)

| Mode | What goes wrong | Fix |
|---|---|---|
| Treating "<USER>'s response" slots as the source of truth | User leaves them blank because they record decisions in docx margin comments instead | Always check `commented_*.docx` first via `commented-edit-roundtrip`'s `read_docx_comments.py` |
| Logging an ACTION before the edit succeeds | False audit trail; recompile fails but log says it worked | Recompile/verify before appending to log |
| Editing or deleting old log entries | Loses provenance; user can't reconstruct what was decided when | Log is append-only — fix mistakes by appending a correction entry, not by editing |
| Stale `.docx` mirrors | User reads outdated content in Word; their feedback is on a wrong baseline | Run `regen_docx.sh` after every batch; `verify_state.py` flags stale docx |
| Adding a `[TYPE: TODO]` entry without removing from todos | Open-list shows resolved items; verifier flags as duplicate ID | Always run `close_todo.py`; never edit log + todos by hand |
| TODO ID collision after deletions | Two TODOs share a number; cross-links become ambiguous | Don't reuse IDs. When you delete TODO 5, the next new TODO is TODO 15 (or whatever is next), not TODO 5 |
| Reconstructing the log from a final diff | Loses the per-edit `why` and the originating TODO ID | Log as you go (per resolution), not after a batch |
| Using the 3-file async pattern for interactive sessions | `<USER>_actions.md` becomes a 100-line shell with zero real ACTIONs; pure overhead | Default is 2-file. Only add `<USER>_actions.md` when there's a genuine handoff between approval and execution |
| Silently rewriting a TODO body when context changes | Future Claude (or the user) loses the audit trail of what the TODO said yesterday vs. today; misreads can't be reconstructed | Append a dated `**Correction (YYYY-MM-DD):** ...` line in place; only rewrite the body when the original framing has become actively misleading, and even then leave the correction note |
| Silently deleting resolved sub-items from a multi-part TODO body | Open list looks "thinner" than it really is; user can't tell from the parent what's already shipped vs. what's left | Strike through with `~~...~~` + a `[PARTIALLY RESOLVED YYYY-MM-DD: ...]` annotation; sub-items only disappear when the parent TODO is removed entirely |
| Auto-processing a batch the user said is "done" without verifying | False closure: a TODO marked "active priority" or "planned, not yet executed" still has open work | When the user lists TODOs as done, check each against current state of `<USER>_todos.md` and the log; flag any that aren't actually resolved before processing |

## Origin

Built 2026-04-26 from the educ-wellbeing manuscript revision workflow. Refactored 2026-04-27 from a 3-file default to a 2-file default after empirical observation: in interactive sessions where Claude both approves (reads user's docx comments) and executes (applies edits) in the same session, the middle ACTION queue layer was always empty. The 3-file pattern remains as an optional extension for genuine async handoffs.
