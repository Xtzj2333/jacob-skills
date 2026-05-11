---
name: commented-edit-roundtrip
description: Round-trip editing between Claude and the user using Word margin comments. Two modes — (A) PERPETUAL INBOX: a single .docx the user keeps adding margin comments to forever; Claude processes comments into TODOs without renaming the file, so the user is never locked out of their commenting surface; (B) ROUND-TRIP REWRITE: Claude rewrites a .docx and returns a comments-on-original audit copy. Use when the user is iterating on a manuscript and wants to comment back on the side rather than reading a diff.
---

# commented-edit-roundtrip

Two modes:

- **Mode A — Perpetual inbox (preferred for ongoing collaboration).** The user keeps a single `.docx` open in Word indefinitely and adds margin comments whenever they have feedback. The inbox is a copy of the manuscript with `[inbox] ` prefixed to its filename (e.g., `revisions/[inbox] manuscript.docx`), so its name self-documents what it's an inbox for. Claude *processes* new comments out into the user's revision-queue TODOs without renaming the file. When the manuscript body changes enough to warrant it, Claude *refreshes* the inbox from the new manuscript while carrying forward un-received comments by anchor matching.
- **Mode B — Round-trip rewrite (one-shot).** The user submits a `.docx` for Claude to revise; Claude returns a rewritten output AND a separate `commented_<original>.docx` with margin annotations documenting every change. Used when the round-trip is finite (e.g., one editing pass on a snapshot).

Both modes share the same docx-comment plumbing (`read_docx_comments.py`, `inject_comments.py`).

## When to Use

- **Mode A:** ongoing manuscript collaboration where the user expects to keep commenting in the same Word window across many sessions while Claude makes edits to the manuscript body in parallel.
- **Mode B:** a single rewrite pass on a stable input where Claude needs to produce an audit trail of changes.
- Either mode: any task where the user wants to "see what changed" without reading a diff.

## When NOT to Use

- Brand-new authoring where there is no source (no round-trip needed)
- Throwaway scratch edits the user explicitly says they don't need to review

---

## Mode A — Perpetual inbox (inverted role model: edit on inbox, promote to canonical)

### File layout (4 surfaces, each with one owner)

| File | Owner | Lifecycle |
|---|---|---|
| `<project>/manuscript_repo/<manuscript>.{md,docx}` | **Safe baseline.** Last user-signed-off version. Untouched between promotions. | Advances only via `promote_inbox_to_canonical.py`. |
| `<project>/revisions/[inbox] <manuscript-basename>.md` | **Claude's editing surface.** Working markdown source for the inbox. | Persistent. Edited by `apply_edit_to_inbox.py`. |
| `<project>/revisions/[inbox] <manuscript-basename>.docx` | **User's commenting surface.** Rendered from the inbox .md, with carried-forward margin comments. | Persistent. Same path forever. Safe to keep open in Word (close briefly when applying edits). |
| `<project>/revisions/comment_archive/` (`INDEX.md` + per-comment files) | **Comment graveyard.** Append-only archive of comments displaced by overwriting edits. | Searchable: `grep -r <comment-id> revisions/comment_archive/`. |
| `<project>/revisions/todos [<shorthand>].{md,docx}` + `completed_actions_log [<shorthand>].{md,docx}` | Discussion + audit trail. | Managed by the `revision-queue` skill. Filenames resolved via `project-filename`. |

**Inverted role model.** This skill's earlier rev had Claude editing canonical directly and treating the inbox as a read-only commenting surface. That coupled "Claude shipped an edit" to "canonical advanced," which prevented the user from holding canonical stable across many small TODO closures. The inverted model decouples the two:

- **Edits land on the inbox first** (`apply_edit_to_inbox.py`). Canonical is untouched.
- **Comments displaced by an edit are archived** with full context (anchor text, surrounding paragraph, comment body, displacing edit, resolving log entry). Nothing is silently overwritten.
- **Canonical advances only at explicit promotion** (`promote_inbox_to_canonical.py`) — typically right before pushing to GitHub.
- **The user keeps commenting on the inbox** the entire time; comments whose anchors survive each edit are carried forward, and the inbox filename never changes.

**Inbox naming convention.** The inbox `.md` and `.docx` share the manuscript basename with `[inbox] ` prefixed — e.g., manuscript `bottom_up_wellbeing_v5_pre_phase2_FINAL.docx` gets `revisions/[inbox] bottom_up_wellbeing_v5_pre_phase2_FINAL.md` and `revisions/[inbox] bottom_up_wellbeing_v5_pre_phase2_FINAL.docx`. The prefix:
- self-documents what manuscript the inbox belongs to
- sorts together visually if there are multiple inboxes
- keeps the inbox out of the manuscript's git folder (it lives in `revisions/`, not `manuscript_repo/`)

The inbox files' names and paths **never change once created**.

### Apply — edit the inbox, archiving any displaced comments

Use when Claude is about to apply an edit (typically a TODO closure). The
edit lands on `revisions/[inbox] <manuscript>.md` only; canonical is
untouched.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/commented-edit-roundtrip/scripts/apply_edit_to_inbox.py \
    --inbox-md   "revisions/[inbox] bottom_up_wellbeing_v5_pre_phase2_FINAL.md" \
    --inbox-docx "revisions/[inbox] bottom_up_wellbeing_v5_pre_phase2_FINAL.docx" \
    --target     "old verbatim prose to replace" \
    --replacement "new prose" \
    --archive-dir "revisions/comment_archive" \
    --snapshot-dir "manuscript_comment_rounds (claude)" \
    --log-entry-id "ACTION-2026-04-30-007"
```

What it does:

1. **Lockfile guard** on the inbox `.docx` (refuses if Word has it open).
2. **Scan** the inbox `.docx` for live (un-received) comments whose anchor
   text overlaps the target (substring or significant shared substring).
3. **Archive** each overlapping comment to `<archive-dir>/<ts>_<i>_comment-<id>.md`
   with full context (author, date, body, original anchor, surrounding
   paragraph, displacing edit, resolving log entry). Append a row to
   `<archive-dir>/INDEX.md`.
4. **Edit** the inbox `.md` (verbatim find/replace; aborts if `target` is
   not unique).
5. **Snapshot** the pre-edit inbox `.docx` to the snapshot directory.
6. **Render** the new inbox `.md` to inbox `.docx` via pandoc.
7. **Carry forward** all non-archived comments by anchor matching;
   anchors that no longer match go to a `<inbox>.lost_anchors.md`
   sidecar.

**Dry run:** pass `--dry-run` to see which comments would be archived
without touching any file.

**Why a markdown source layer.** The `.md` is the editable source of
truth for inbox prose; the `.docx` is regenerated from it on each edit.
This avoids docx-XML find/replace, which silently breaks when the target
text spans multiple `<w:r>` runs.

### Promote — replace canonical with the current inbox prose

Use when the user signs off on the inbox state at a document level
("ready to push," "promote," "fold in"). Canonical advances only via
this command.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/commented-edit-roundtrip/scripts/promote_inbox_to_canonical.py \
    --inbox-md       "revisions/[inbox] bottom_up_wellbeing_v5_pre_phase2_FINAL.md" \
    --canonical-md   "<MANUSCRIPT_DIR>/<MANUSCRIPT_FILE>.md" \
    --canonical-docx "<MANUSCRIPT_DIR>/<MANUSCRIPT_FILE>.docx" \
    --snapshot-dir   "manuscript_comment_rounds (claude)/canonical_snapshots"
```

What it does:

1. **Snapshot** the pre-promotion canonical `.md` and `.docx` to the
   snapshot directory.
2. **Replace** canonical `.md` with the inbox `.md` (verbatim copy).
3. **Regenerate** canonical `.docx` from the new canonical `.md` via
   pandoc.
4. **Print a unified diff** (canonical pre vs. post) so the user can
   review what they just promoted.

The inbox files are **untouched** — the user keeps commenting on the
same inbox going forward.

### Process — extract new comments into TODOs WITHOUT renaming the inbox

Use when the user has added new comments and wants Claude to act on them. (User vocabulary: "process my comments," "drain," "pick these up," etc. — same operation.)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/commented-edit-roundtrip/scripts/process_inbox.py \
    "revisions/[inbox] bottom_up_wellbeing_v5_pre_phase2_FINAL.docx" \
    --extract-out revisions/_process_2026-04-30.json \
    --archive-dir "manuscript_comment_rounds (claude)" \
    --not-received
```

If the inbox doesn't yet exist (first-time use on a new manuscript), pass `--from-manuscript` and the script will auto-create it by copying:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/commented-edit-roundtrip/scripts/process_inbox.py \
    "revisions/[inbox] bottom_up_wellbeing_v5_pre_phase2_FINAL.docx" \
    --from-manuscript <MANUSCRIPT_DIR>/<MANUSCRIPT_FILE>.docx \
    --extract-out revisions/_process_2026-04-30.json \
    --archive-dir "manuscript_comment_rounds (claude)" \
    --not-received
```

What it does:

1. **Auto-create** the inbox if missing (only if `--from-manuscript` is given).
2. **Lockfile guard.** Refuses to write if `~$<inbox>.docx` exists (file open in Word). Tells the user to close Word first.
3. **Snapshot.** Copies the pre-process inbox to `manuscript_comment_rounds (claude)/<inbox-stem>_snapshot_<ts>.docx`.
4. **Extract.** Writes the matching comments to the JSON file at `--extract-out`. Hand this to `revision-queue` to file new TODOs.
5. **Mark in place.** Modifies `word/comments.xml` inside the inbox so each processed comment's body is prefixed with `[RECEIVED YYYY-MM-DD]` and reauthored to `Claude (received)`. The inbox keeps its name and path; the user re-opens in Word and sees which threads have been picked up.

Common flags:
- `--not-received` — skip comments already prefixed `[RECEIVED` (also recognizes the legacy `[DRAINED` prefix). Use this in normal operation.
- `--author "<USER>"` — only process comments by a specific author.
- `--since YYYY-MM-DD` — only process comments dated on/after this.
- `--mark-only` — skip extraction; only mark. Useful for migration of a pre-existing commented file whose comments are already filed elsewhere.

### Refresh — regenerate the inbox from the current manuscript

Use when Claude has changed the manuscript body enough that the user wants a fresh commenting surface. **Opt-in only** — never automatic; the regeneration loses anchor positions for any comment whose anchor text no longer exists verbatim in the new manuscript.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/commented-edit-roundtrip/scripts/refresh_inbox.py \
    --inbox "revisions/[inbox] bottom_up_wellbeing_v5_pre_phase2_FINAL.docx" \
    --new-manuscript <MANUSCRIPT_DIR>/<MANUSCRIPT_FILE>.docx \
    --archive-dir "manuscript_comment_rounds (claude)"
```

What it does:

1. Lockfile guard on the inbox.
2. Snapshot the pre-refresh inbox to the archive folder.
3. Read all comments from the current inbox; partition into **received** (prefixed `[RECEIVED` or legacy `[DRAINED`) and **live** (un-received).
4. Replace the inbox file with a fresh copy of the manuscript (filename keeps the `[inbox] ` prefix).
5. Re-inject every live comment by anchor-matching against the new manuscript text.
6. Any live comment whose anchor doesn't match goes to a sidecar `<inbox>.lost_anchors.md` so nothing silently disappears. The user reviews these manually and re-comments where needed.

### Concurrency rule

`process_inbox.py`, `refresh_inbox.py`, and `apply_edit_to_inbox.py` all refuse to write if Word has the inbox `.docx` open (lockfile `~$<inbox>.docx` present). **Workflow:** user closes Word → Claude runs the operation → user reopens Word. Brief interruption only; no overwrite risk.

The user can keep Word open the rest of the time. Claude never writes to the inbox outside of these scripts.

### Comment archive — what gets saved when an edit displaces a comment

`apply_edit_to_inbox.py` writes one file per displaced comment under `revisions/comment_archive/<ts>_<i>_comment-<id>.md`, plus a row in `revisions/comment_archive/INDEX.md`.

Per-archive file contents:

- **Author** + **date** of the comment
- **Overlap kind**: `fully-overlapped` (anchor ⊆ target), `edit-within-anchor` (target ⊆ anchor), or `partial-overlap` (≥20-char shared substring)
- **Comment body** (verbatim)
- **Original anchor text** (verbatim, full)
- **Surrounding paragraph** at edit time (≥3 lines before/after)
- **Displacing edit** — file, before, after
- **Resolving log entry ID** — points back to `completed_actions_log.md`

Searchable: `grep -r "<comment-id>" revisions/comment_archive/`.

---

## Mode B — Round-trip rewrite (one-shot)

The original four-step procedure, used when Claude is rewriting a snapshot of the user's content and needs to produce an audit copy with margin annotations.

1. **Read** the user's existing margin comments accurately
2. **Log** every change as it's made
3. **Inject** annotations on a copy of the original so the user can review on the side
4. **Verify** that no change escaped the log

### Procedure

### Step 1 — Read the user's comments (when source is `.docx`)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/commented-edit-roundtrip/scripts/read_docx_comments.py \
    INPUT.docx --since 2026-04-26 --out user_comments.json
```

Returns one entry per comment: `{id, author, date, text, anchor}`. Always parse comments by `(author, date, anchor text)` to distinguish the user's new comments from their prior ones, and from any comments Claude itself injected on a previous round.

**Critical:** quote what the user wrote verbatim — do not paraphrase. The user comments on the side specifically to avoid confusion about what they meant.

### Step 2 — Maintain the change log as you edit

For each edit Claude makes, append one JSON line to `logs/change_log_<YYYY-MM-DD>.jsonl`:

```json
{"anchor": "the pattern flips", "before": "the pattern flips", "after": "the pattern differs from the US", "file": "manuscript.tex", "line": 598, "category": "substantive-deferred", "why": "softening — flagged for user review", "page_in_output": 15}
```

`category` ∈ {`cosmetic`, `factual`, `substantive-applied`, `substantive-deferred`}. See the user's CLAUDE.md for definitions.

Reconstructing the log from a final diff loses the `why` field — log as you go, not after.

### Step 3 — Produce the comments-on-original deliverable

**For `.docx` sources:** copy the original and inject Word margin comments at every anchor.

```bash
# Build the spec from your change log
python3 -c "
import json
log = [json.loads(l) for l in open('logs/change_log_2026-04-26.jsonl')]
spec = [{'anchor': e['anchor'], 'comment': f\"[{e['category'].upper()}] {e['why']} (output p. {e.get('page_in_output','?')})\"} for e in log]
json.dump(spec, open('comments_spec.json', 'w'), indent=2)
"

python3 ${CLAUDE_PLUGIN_ROOT}/skills/commented-edit-roundtrip/scripts/inject_comments.py \
    --in ORIGINAL.docx \
    --out commented_ORIGINAL.docx \
    --spec comments_spec.json \
    --author "Claude (edit round 2026-04-26)"
```

The injection handles cross-run text splits (a known docx footgun); if you see `skipped anchors`, run a second pass after refining the anchor strings to be unique substrings actually present in the document body.

**To map output PDF pages for the `page_in_output` field:**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/commented-edit-roundtrip/scripts/pdf_page_locator.py \
    output.pdf \
    --anchors-json comments_spec.json \
    --header-pattern "PROJECT-RUNNING-HEADER" \
    --out anchor_pages.json
```

**For markdown / code / non-docx sources:** instead of injection, write a sidecar file `<original-name>.changes.md` with one section per change:

```markdown
## Change 1 — line 192

**Anchor:** `Lastly, we explored possible mechanisms`
**Category:** substantive-deferred
**Before:** `Lastly, within each study's Results section, we explored possible mechanisms...`
**After:** `Lastly, we explored possible mechanisms...`
**Why:** Removed phrase that previewed an unauthorized restructure.
**Output location:** PDF p. 5
```

### Step 4 — Verify before declaring done

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/commented-edit-roundtrip/scripts/verify_changes.py \
    --before original_text.txt \
    --after  edited_text.txt \
    --log    logs/change_log_2026-04-26.jsonl
```

Exits 0 if every diff has a corresponding log entry; exits 1 with the list of uncommented diffs otherwise. **Treat any uncovered diff as a bug** — either the log missed an edit (fix the log) or Claude made a silent change (revert it).

For `.docx` sources, get plain text via `pandoc INPUT.docx -o INPUT.txt` for both sides of the diff.

### Step 5 — Defer substantive changes

Any edit Claude is tempted to make that falls in the "substantive" category (theoretical word swaps, structural restructuring, citation changes, restoring text the user or a reviewer deleted, sign flips on numbers, brand-new paragraphs of content) MUST go to `DEFERRED_FOR_USER.md` (or whatever the project's user-deferred file is named).

Each deferred entry includes:
- Exact `before` and `after` text
- File + line + a few words of surrounding context
- Why it was flagged
- Claude's recommended resolution (so the user has a default to accept/reject)
- Status (open / resolved / declined)

The user reviews these on the side of the docx (or in the deferred file directly) and tells Claude what to do on the next round.

---

## Output Layout

Recommended folder for each round of edits:

```
change_report_<YYYY-MM-DD>/
├── README.md                    # one-line summary + counts
├── commented_ORIGINAL.docx      # original + Claude's margin annotations
├── output.pdf                   # the produced output
├── _logs/
│   ├── change_log.jsonl         # one line per change
│   ├── user_comments.json       # parsed from input docx
│   └── verification.txt         # verifier output
└── _scripts/
    └── comments_spec.json       # generated from the change log
```

Old change reports are kept; never overwrite a prior round's `commented_ORIGINAL.docx` because it's the user's audit trail.

---

## Failure Modes (avoid these)

| Mode | What goes wrong | Fix |
|---|---|---|
| Reconstructing the log from a final diff | Lose the `why` and the category for each edit; can't distinguish a typo fix from a substantive change | Log as you go |
| Paraphrasing the user's comment text | User loses confidence that Claude understood; the round-trip stops working | Quote verbatim |
| Anchoring on text that's not unique | `inject_comments.py` skips anchors that appear 0 or 2+ times; some changes go unannotated | Use longer anchor strings; verify uniqueness with `grep -c` |
| Treating Claude's prior margin comments as if they were the user's | New-round comments get mistaken for old-round audit notes; user instructions are missed | Filter by `(author, date)` — Claude's comments use a stable author label like `Change Audit (Apr 2026)` |
| Silently restoring text the user or a reviewer deleted | Tracked-change deletions are deliberate authorial choices | Read `w:ins`/`w:del` markup; never re-insert deleted text without explicit approval |
| Producing the change report only at the end of the loop | Long loops accumulate dozens of changes; reviewer can't tell which iteration introduced what | Append to the change log per-iteration, not per-loop |

---

## Origin

Built 2026-04-26 from a real round of editing on the educ-wellbeing manuscript, where the user commented on a docx that Claude had previously injected with audit comments. The mechanics here generalize from that round — see `apa-workflow/educ-wellbeing/change_report_2026-04-26/` for the worked example.
