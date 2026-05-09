# What each skill does

Six skills, grouped by purpose:

- **Citations** — `research-27` (produce), `citation-deepening` (verify content), `source-quality-check` (rate quality)
- **Manuscript revision loop** — `commented-edit-roundtrip` (bridges margin comments and TODOs), `revision-queue` (state machine + audit log)
- **Push utility** — `tony-github-push`

---

## At a glance

| # | Skill | Trigger | What you get | Default scope |
| --- | --- | --- | --- | --- |
| 1 | research-27 | "research 27 <topic>" / `/research-27` | Citation-rich brief in chat | (no cap) |
| 2 | citation-deepening | "deepen citations" / "fact-check citations" | `.docx` auditing claim-vs-source per ref | 8–12 cites per pass |
| 3 | source-quality-check | "rate the references" / "are these top-tier" | `.docx` rating each ref's tier / peer-review / recency / author | 8–12 cites per pass |
| 4 | commented-edit-roundtrip | "process my comments" / "drain the inbox" | Margin comments → TODOs (with audit trail) | one manuscript at a time |
| 5 | revision-queue | "create a TODO" / "process these" / "close TODO N" | `<USER>_todos.md` + `completed_actions_log.md` | per project |
| 6 | tony-github-push | "tony github push" / `/tony-github-push` | Push of configured dir to configured branch | one configured dir |

---

## A typical end-to-end flow

Not every project uses every skill. A common sequence:

1. **Draft** a manuscript section — `research-27` for the literature-review parts.
2. **Review** — leave margin comments on the manuscript `.docx`.
3. **Process** comments into TODOs — `commented-edit-roundtrip`.
4. **Track** decisions across sessions — `revision-queue`.
5. **Audit** before submission — `citation-deepening` (claim-vs-source) + `source-quality-check` (reference quality).
6. **Push** the final manuscript — `tony-github-push` (only on solo-write branches; otherwise plain `git push`).

---

## 1. research-27 — citation-rich literature-review brief

**Trigger.** Say exactly "research 27 <topic>" or run `/research-27`.

**Anti-triggers.** Bare "research", "do a literature review on X", "find papers about Y". Those are reserved for plain English usage and must NOT auto-fire this heavyweight skill. Also skip for quick factual lookups, code questions, casual conversation.

**Input.** A topic in plain English. Optionally, a scope hint ("introductory overview" vs. "current state of the art").

**Output.** A markdown brief in chat:

- Inline citations on every major claim
- Synthesis explicitly labeled where a sentence is your own inference, not directly cited
- APA reference list at the end with working URLs
- A per-loop **errata block** showing what verification caught (errors corrected, refinements added, gaps closed, citation-checker findings triaged, fabrications detected — should always be 0)

**How it works.** Two-loop minimum, never one-shot:

- **Loop 1** — orientation web pass (map who's talking about the topic) → academic search via Scholar Gateway + paper-search MCP in parallel → tier-disciplined sourcing → first-draft brief.
- **Loop 2** — verification with four sub-passes: source-text fetch-verify, citation-checker triage, source-tier audit, gap detection.
- **Loops 3+** continue if Loop 2 surfaced material errors, until **convergence** (a full pass with zero corrections) or a hard ceiling of 25 loops. Convergence usually happens by Loop 2 or 3.

**When to use.** Drafting a manuscript section. Pre-meeting briefings. Unfamiliar-topic introductions. Anywhere you need credibly-sourced research output.

**When NOT to use.** Quick factual lookups. Code questions. Casual conversation. Anything Google can answer in one query.

**Why it's useful.** Default Claude responses on research topics confidently fabricate citations or paraphrase from training data without grounding. The verify-and-loop pattern surfaces fabrications in the same session, so the brief is something you can actually cite. Quality > speed by design.

---

## 2. citation-deepening — verify what each cited paper actually says

**Trigger phrases.** "deepen the citations", "fact-check citations", "for every citation make a more detailed citation", "build the citation backup", "verify what each cited paper actually says".

**Anti-trigger.** "find papers about X" — that's forward-looking literature search, use `research-27` instead.

**Input.** A manuscript with existing citations. PDFs of cited papers if you have them; otherwise the skill auto-acquires from arXiv / JOSS / PMC where available, and honestly labels paywalled refs as ABSTRACT-ONLY.

**Output.** A Word-readable `.docx`. One section per cite, containing:

- The manuscript's verbatim claim and which line(s) it appears on
- Source confidence — `FULL-PDF` / `ABSTRACT-ONLY` / `THIRD-PARTY-METADATA` / `NONE`
- Verbatim quotes from the source (typically 2–4 per cite, with section / page #)
- Verdict — supports / partial / citation-metadata-error / contradicts
- Recommended action

**Default scope: 8–12 citations per pass.** Quality drops sharply past that. Run multiple passes for a 40+ ref bibliography.

**Built-in safety check.** A separate-context Claude validation agent runs after the draft to verify every quote attributed to a `FULL-PDF` source actually appears in that PDF. Catches hallucinated quotes the main author missed. **Non-negotiable** — never skipped.

**Surfaces problems as TODOs.** Citation-metadata errors and claim-source mismatches go into `<USER>_todos.md` (using `revision-queue` conventions). Never auto-edits the manuscript or bibliography — substantive changes need your sign-off.

**When to use.** Late-stage manuscript review. Pre-submission. Reviewer-response prep ("a reviewer is asking what cite [7] actually says"). After heavy AI-assisted drafting.

**Why it's useful.** Catches "the AI fabricated this citation" or "the cited paper says the opposite of our claim" before reviewers do. Backward-looking audit of an artifact you already have.

---

## 3. source-quality-check — rate the references already cited

**Trigger phrases.** "rate the references", "check the quality of citations", "are these papers any good", "are we citing master's theses or top journals", "is this the right kind of source for this claim".

**Anti-triggers.** "find papers" (forward-looking — use `research-27`). "Verify what this paper says" (use `citation-deepening`). Bibliography formatting (separate format pass).

**Input.** A manuscript with existing bibliography.

**Output.** A Word-readable `.docx`. For each cite, four assessment columns plus a composite signal:

- **Venue tier** — `A*` (Nature, Science, PNAS, top discipline journals, top conferences) → `A` → `B` → `C` → `Preprint` → `Tech-report` → `Software-paper` → `Book/Chapter` → `Thesis`
- **Peer-review status** — peer-reviewed / conference-reviewed / editor-screened / preprint-only / self-published
- **Recency-sensitivity** — judged against the field (AI/ML stales in 2–3 years; foundational math is timeless)
- **Author credibility** — established researcher with prior subfield productivity, or one-off / unknown
- **Composite signal** — strong / acceptable / acceptable-with-caveat / marginal / weak

**Default scope: 8–12 cites per pass.** Pairs naturally with `citation-deepening` on the same range — the two `.docx` files are designed to be read side-by-side.

**Discipline rule: no fabricated impact factors or h-indices.** If you don't know the precise number, qualitative phrasing only ("widely regarded as a top philosophy journal", not "*Noûs* IF 3.847").

**When to use.** When a reviewer flags weak citations. When you suspect over-citing of preprints / grey literature. Pre-submission spot-check.

**When NOT to use.** Verifying claim-vs-source content (use `citation-deepening`). Citation formatting. Papers you authored yourself.

**Why it's useful.** Catches "you cited a master's thesis where there are top-journal alternatives" or "this preprint is being cited as if peer-reviewed" before a reviewer does.

---

## 4. commented-edit-roundtrip — bridge between Word margin comments and structured TODOs

Two modes. Pick by your collaboration shape.

### Mode A — Perpetual inbox (recommended for ongoing collaboration)

**The setup.** A second `.docx` lives at `revisions/[inbox] <manuscript-basename>.docx`. You keep this open in Word indefinitely and add margin comments whenever you have feedback. The **canonical** manuscript stays untouched until you explicitly ask Claude to "promote" the inbox state to canonical.

**The flow.**

- You leave margin comments on the inbox `.docx`.
- Claude `process_inbox.py` extracts new comments → TODOs (filed via `revision-queue`); marks each processed comment with a `[RECEIVED yyyy-mm-dd]` prefix in place so you can see what's been picked up.
- Claude `apply_edit_to_inbox.py` applies edits to the inbox `.md` source. Comments displaced by an edit are **archived** (anchor text + surrounding paragraph + the displacing edit + log entry ID) so nothing is silently overwritten.
- When you say "promote", Claude `promote_inbox_to_canonical.py` overwrites canonical from the inbox state, with snapshots of both pre-promotion versions saved.

**Inbox file path never changes.** You stay in the same Word window forever. Concurrency rule: scripts refuse to write while you have the inbox open in Word — close briefly, run the operation, reopen.

### Mode B — Round-trip rewrite (one-shot)

**The setup.** You hand Claude a `.docx` for revision. Claude returns two files: the rewrite, plus `commented_<original>.docx` with margin annotations of every change (anchor / before / after / why / category / output page).

**The flow.** A four-step procedure: read your existing comments → maintain a JSONL change log per edit → inject margin annotations onto a copy of the original → run a verifier that checks every diff has a corresponding log entry.

### Trigger phrases (either mode)

"process my comments", "drain the inbox", "round-trip these edits", "pick these up".

### When to use

- **Mode A** — ongoing manuscript collaboration where you're commenting weekly across many sessions.
- **Mode B** — a single one-shot rewrite pass on a snapshot.

### Why it's useful

Reading a manuscript and reading a code-style diff are different cognitive modes. This skill keeps you in editor-headspace (margin comments) while structured task-tracking happens behind the scenes. Pairs naturally with `revision-queue`.

---

## 5. revision-queue — multi-round revision state machine

**Default: two coordinated files** in your project's revisions folder.

| File | Role |
| --- | --- |
| `<USER>_todos.md` | Currently-open items. One section per TODO: artifact (screenshot/quote/diff) → issue → options → Claude's recommendation. |
| `completed_actions_log.md` | Append-only chronological audit. One entry per resolved item, tagged `[TYPE: ACTION]` (code/text edit) or `[TYPE: TODO]` (resolved without edit — e.g., declined, prior-fix). |

`<USER>` is your `USER_NAME` env-var (set in your global CLAUDE.md per Part 3 of the setup doc).

**Optional 3rd file** `<USER>_actions.md` for asynchronous handoffs only — when one session approves and a *different* session executes (e.g., overnight loops). For interactive sessions where Claude approves and applies in the same flow, **skip this layer entirely**.

### Decisions come via .docx margin comments, not by editing the markdown

The user comments on the `<USER>_todos.docx` (regenerated from the `.md` by pandoc). Claude reads the comments via `commented-edit-roundtrip`'s `read_docx_comments.py`, filters by `(author, date)`, and acts. The `.md` is never the surface where the user records decisions.

### Lifecycle of a TODO

1. Claude appends a TODO to `<USER>_todos.md` and regenerates the `.docx`.
2. You open the `.docx` in Word and leave a margin comment with your decision.
3. Claude reads the comment, applies the edit (or files a `[TYPE: TODO]` resolution if no code change is needed), appends a log entry, removes the row from `<USER>_todos.md`.
4. Verifier (`verify_state.py`) confirms invariants: no duplicate TODO IDs, log in chronological order, every cross-link resolves, `.docx` mirrors are fresh.

### Useful organizational features

- **"Later" section** for deferred items — promote/demote via "punt" / "defer" / "active priority" without changing the TODO ID.
- **Sub-items** — a single TODO body can carry numbered sub-items that resolve incrementally; the parent stays open until all sub-items close.
- **Dated corrections** — when a TODO body needs updating across sessions, append `**Correction (yyyy-mm-dd):** ...` rather than silently rewriting. Preserves audit trail.

### Trigger phrases

"create a TODO for this", "open a revision queue", "process these", "fold this in", "close TODO 11", "demote 7 to Later".

### When to use

Long-running revision projects: manuscripts going through reviewer rounds, codebases under iterative refactor, anything where you'd otherwise drift into a single mixed `todo.md` across many sessions.

### Why it's useful

Keeps "open" / "approved" / "done" cleanly separated with a permanent dated audit trail. Pairs with `commented-edit-roundtrip` (which produces the TODOs from your margin comments).

---

## 6. tony-github-push — one-command push of a configured manuscript subdirectory

**The push contract — three rules, exact:**

1. **Only the configured `${MANUSCRIPT_DIR}` is pushed.** Sibling folders, top-level files (`MAP.md`, `INDEX.md`, etc.), and anything outside that directory are NOT touched. All git commands run from inside `${MANUSCRIPT_DIR}`.
2. **Push target is the configured `${MANUSCRIPT_BRANCH}` only.** Never `main`, never any other branch.
3. **On non-fast-forward conflict, force-push.** Your local working tree is treated as authoritative for `${MANUSCRIPT_BRANCH}`.

**Configuration** (in your `~/.claude/CLAUDE.md`, see Part 3 of the setup doc):

- `MANUSCRIPT_DIR` — local subdirectory to push
- `MANUSCRIPT_REMOTE` — your manuscript repo URL
- `MANUSCRIPT_BRANCH` — branch you alone push to

**Scope discipline (intentional).** Claude does **not** auto-edit, regenerate, rename, or "clean up" anything. If you only edited the `.docx`, only the `.docx` change is committed. Push exactly what you produced, nothing else.

**Standard workflow.** `cd "${MANUSCRIPT_DIR}"` → `git status` + `git diff --stat` shown to you → `git checkout "${MANUSCRIPT_BRANCH}"` (create if missing) → `git add -A` → `git commit -m "<short factual description>"` → `git push -u origin "${MANUSCRIPT_BRANCH}"` → on rejection, `git push --force origin "${MANUSCRIPT_BRANCH}"`. You see the commit message and file list one more time before push.

**Trigger phrases.** "tony github push", "push to tony", "tony and github push them", `/tony-github-push`.

**Anti-trigger.** Generic "git push", "push the manuscript", "commit and push" — those defer to normal git workflow with explicit confirmation, no force-push behavior.

### Important caveat — only safe on solo-write branches

The force-push behavior is destructive on shared branches. **Configure this skill only for a branch you alone push to.** If others push to your `MANUSCRIPT_BRANCH`, force-pushing will silently overwrite their commits. In that case either:

- Switch `MANUSCRIPT_BRANCH` to a personal branch (e.g., `tony-edits`) that only you push to, OR
- Don't use this skill — fall back to plain `git push` so non-fast-forward errors surface and you handle them manually.

### Naming note

The skill is named "tony-github-push" for historical reasons (it was originally Jacob's skill for pushing to Tony's GitHub). The destination is fully configurable — set YOUR repo and YOUR branch via Part 3 of the setup doc, and "tony github push" pushes to *your* manuscript, not Jacob's.

### Why it's useful

One command for a routine push, with the right `cd` / branch / staging done for you. The narrow scope (one configured directory only) is a safety property — the skill physically cannot push your entire workspace by accident.

---

*Maintained by Jacob. Suggestions welcome via [GitHub issues](https://github.com/Xtzj2333/jacob-skills/issues) or PRs from a fork — please don't push directly to this repo. See [COLLABORATOR_SETUP.md](./COLLABORATOR_SETUP.md) for install + configuration.*
