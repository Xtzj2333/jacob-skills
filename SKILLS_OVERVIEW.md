# What each skill does (collaborator overview)

Six skills, each with: **what it is**, **how to use it**, **when to use it**, **why it's useful**. Read top-to-bottom or jump to whichever interests you.

A useful mental map: three of these are about **producing or auditing citations** (`research-27`, `citation-deepening`, `source-quality-check`); two are about **the manuscript revision loop** (`commented-edit-roundtrip`, `revision-queue`); one is a **utility for pushing edits** (`tony-github-push`).

---

## 1. `research-27` — citation-rich literature-review brief

**What it is.** A heavyweight research-brief generator. You give it a topic; it produces a publishable-quality mini literature review with every major claim cited inline and a verifiable APA reference list at the end. Mixed-media sources are allowed (papers, news, government reports, well-credentialed blogs) when author/outlet credibility can be established.

**How to use it.** Trigger explicitly with "research 27 <your topic>" or `/research-27 <topic>`. The skill produces a first draft (Loop 1), then **automatically** runs a verification pass (Loop 2) with four sub-passes: source-text fetch-verify, citation-checker triage, source-tier audit, gap detection. It keeps looping until a full pass produces zero corrections — or hits 25 loops, whichever comes first.

**When to use it.** Before drafting a manuscript section, before committing to a framing, when you need a credibly-sourced briefing on an unfamiliar topic. **NOT** for casual factual lookups, code questions, or anything you'd just type into Google. Don't trigger it on the bare word "research" — only "research 27".

**Why it's useful.** Default Claude responses on research-y topics will confidently fabricate citations or paraphrase from training data without grounding. The verify-and-loop pattern forces real source-fetching and exposes hallucinations within the same session, so the output you get is something you can actually cite.

---

## 2. `citation-deepening` — verify what each existing citation actually says

**What it is.** A backward-looking audit of citations *already in your manuscript*. For each cited reference, the skill pulls verbatim quotes from the source text, then issues a verdict on whether the cited paper actually supports the claim being made. Citation-metadata errors (wrong year, wrong author, dead link) get surfaced as TODOs.

**How to use it.** In a session inside your manuscript directory, say something like "deepen the citations", "for every citation make a more detailed citation", "fact-check these citations", or "verify what each cited paper actually says". Output: a Word-readable `.docx` with one row per reference — claim → verbatim quote → verdict (supports / partially supports / contradicts / unverifiable).

**When to use it.** Late-stage manuscript review. Before submission. Especially after heavy AI-assisted drafting, where citation hallucinations are likely.

**Why it's useful.** Catches "the AI fabricated this" or "the cited paper says the opposite of what we claim" *before* a reviewer does. Slow and thorough by design — this is the audit before the audit.

**Don't use it for:** finding new papers ("research X") or rating source quality (use `source-quality-check`).

---

## 3. `source-quality-check` — rate the references already cited

**What it is.** A quality audit of your reference list. For each cited paper, the skill rates: **venue tier** (top journal vs. preprint vs. master's thesis), **peer-review status**, **recency-sensitivity** (does this topic move fast?), and **author credibility**. Output is a Word-readable doc.

**How to use it.** Trigger phrases like "check the quality of citations", "rate the references", "are these papers any good", "are we citing master's theses or top journals", "is this the right kind of source for this claim".

**When to use it.** When a reviewer flags weak citations. When you suspect you've over-cited preprints or grey literature. When the strength of your argument depends on the strength of your sources.

**Why it's useful.** Identifies citation-quality weaknesses early enough that you can swap in stronger sources before submission. E.g., flagging "you cited a master's thesis here when there are three top-journal alternatives."

**Don't use it for:** verifying claim-vs-source content match (use `citation-deepening`) or finding new papers.

---

## 4. `commented-edit-roundtrip` — Word margin comments → structured TODOs

**What it is.** A bridge between Microsoft Word margin comments and structured task machinery. You leave margin comments on a `.docx` like a normal editor; Claude reads them (anchored to specific text passages via the docx XML) and converts each comment into a TODO row. Two modes:

- **A. Perpetual Inbox.** One `.docx` you keep adding margin comments to forever. Claude processes new comments without renaming the file, so you never get locked out of your commenting surface. Think of it as an editor's queue you keep dropping notes into.
- **B. Round-Trip Rewrite.** Claude rewrites a `.docx` based on your instructions, then hands back two files: the rewrite, and a comments-on-original audit copy showing what changed and why — so you can review the diff in margin-comment form rather than reading a code-style diff.

**How to use it.** Drop a `.docx` with margin comments into your working directory. Trigger phrasing: "process my comments", "round-trip these edits", "here are my margin comments — tackle them". Claude generates one TODO per comment, and either acts on them directly or queues them via `revision-queue`.

**When to use it.** When iterating on a manuscript and you'd rather review by leaving margin comments than by reading a unified diff. When you want to stay in editor-headspace, not code-headspace.

**Why it's useful.** Reading a manuscript and reading a diff are different cognitive modes. This skill lets you stay in the natural review mode while still getting the structured-task benefits behind the scenes. Pairs with `revision-queue` to track the resulting actions to completion.

---

## 5. `revision-queue` — state machine for multi-round revisions

**What it is.** A two-file (optionally three-file) state machine for tracking revisions across many sessions:

- `<USER>_todos.md` — items currently under discussion (screenshots, options, recommendations).
- `completed_actions_log.md` — append-only chronological audit of every resolved item, with diffs and reasoning.
- `<USER>_actions.md` *(optional third file)* — items you've approved but not yet executed; a queue of pending edits.

`<USER>` is your `USER_NAME` env-var (set per the setup doc; for you it'd be `tony_todos.md`, `tony_actions.md`).

**How to use it.** Say "open a revision queue" or invoke `/revision-queue`. Items flow: TODO (under discussion) → ACTION (approved) → LOG (executed). Two Python helpers in the skill: `close_todo.py` (resolve a TODO without making code edits — e.g., "we discussed and decided no change") and `execute_action.py` (apply a pending action and append it to the log).

**When to use it.** Multi-round manuscript revisions. Refactors with dozens of small decisions. Anything where you'll lose track of "what's open / what's approved / what's done" if you don't write it down somewhere structured.

**Why it's useful.** Across sessions, you forget which decisions were made and why. The append-only log gives you a permanent, dated audit trail. The TODO list keeps "still open" cleanly separated. Pairs naturally with `commented-edit-roundtrip` (which produces the TODOs from your margin comments).

---

## 6. `tony-github-push` — one-command push of a configured manuscript subdirectory

**What it is.** A targeted git push helper. It stages, commits, and pushes a single configured subdirectory to a configured remote and branch — nothing else in the parent project gets touched. **Force-pushes on conflict**, because in Jacob's setup the local working tree is treated as authoritative for that branch.

**How to use it.** Configure once in your `~/.claude/CLAUDE.md` (Part 3 of the setup doc):
- `MANUSCRIPT_DIR`: name of the local subdirectory you want pushed
- `MANUSCRIPT_REMOTE`: full remote URL of YOUR manuscript repo
- `MANUSCRIPT_BRANCH`: the branch to push to

Then trigger with "tony github push", "push to tony", or `/tony-github-push`. The skill stages → commits → force-pushes only the configured directory.

**When to use it.** When you've made manuscript edits in a sub-tree of a larger workspace and want one-command push without typing the right `cd` and `git push` incantation every time.

**Why it's useful.** Eliminates "wait, am I in the right repo, am I on the right branch, did I stage the right files" friction for a routine push. The narrow scope (one configured subdirectory only) is a safety property — it can't accidentally push your entire workspace.

**Important caveat about force-push.** This skill **force-pushes on conflict**, which assumes your local branch is authoritative. That's safe when you're the only one writing to that branch (e.g., a personal feature branch). It's *destructive* if collaborators are also pushing to that branch — a force-push will silently overwrite their commits. **Before configuring this skill, confirm your `MANUSCRIPT_BRANCH` is one you alone push to.** If anyone else pushes there, either change the branch to a personal one, or don't use this skill — fall back to plain `git push` so conflicts surface.

**Naming note.** The skill is named "tony-github-push" for historical reasons (it was originally Jacob's push-to-Tony-Github skill). The destination is fully configurable — for you it'll push to YOUR repo and YOUR branch, not Jacob's, as long as you set the values per Part 3.

---

## Quick reference table

| Skill | Trigger phrase / command | Output | Pairs with |
| --- | --- | --- | --- |
| research-27 | "research 27 <topic>" / `/research-27` | Citation-rich brief in chat | `citation-deepening` (audit it later) |
| citation-deepening | "deepen the citations" / "fact-check citations" | `.docx` with claim → quote → verdict per ref | `source-quality-check`, `revision-queue` |
| source-quality-check | "rate the references" / "check citation quality" | `.docx` rating each ref's tier/peer-review/recency | `citation-deepening` |
| commented-edit-roundtrip | "process my comments" / "round-trip these edits" | TODOs in `<USER>_todos.md` | `revision-queue` |
| revision-queue | "open a revision queue" / `/revision-queue` | `<USER>_todos.md` + `completed_actions_log.md` | `commented-edit-roundtrip` |
| tony-github-push | "tony github push" / `/tony-github-push` | Force-push of configured dir to configured branch | (standalone) |

---

## Typical end-to-end workflow (manuscript revision)

A common sequence using these skills together:

1. **Draft the manuscript section** with `research-27` for the literature-review parts (citation-rich brief).
2. **Review** by leaving margin comments on the `.docx`.
3. **Process** the margin comments via `commented-edit-roundtrip` → TODOs land in `<USER>_todos.md`.
4. **Track** the revision rounds via `revision-queue` — discussion → approval → execution → audit log.
5. **Audit citations** before submission with `citation-deepening` (claim-vs-source) and `source-quality-check` (reference quality).
6. **Push** the final manuscript via `tony-github-push` (or plain git push if you can't be sure your branch is force-push-safe).

Not every project will use every skill. Pick the ones that fit your workflow.

---

*Maintained by Jacob. Suggestions welcome via [GitHub issues](https://github.com/Xtzj2333/jacob-skills/issues) or PRs from a fork — please don't push directly to this repo. See [COLLABORATOR_SETUP.md](./COLLABORATOR_SETUP.md) for install + configuration instructions.*
