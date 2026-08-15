---
name: reports-catalog
description: Use BEFORE choosing an output path for any rendered deliverable for Jacob — HTML report or chat-substitute, docx/pdf brief, rendered slides or images. Also when Jacob says "bump the stage/version", asks where a report should go, or wants an existing folder retrofitted. Not for manuscript files (`_PROPOSED` convention), data/code outputs, or the central `~/Claude/reports/` (Claude-infrastructure reports; keeps its own date-first convention).
---

# reports-catalog

> Every rendered deliverable lands in the owning project's `reports (claude)/`, named `s{S}.v{V}_{YYYY-MM-DD}_{slug}`, and gets a CATALOG.md row in the same turn it is written. The current stage.version lives only at the top of CATALOG.md, so naming a file forces a catalog read: the index cannot silently drift from the files.

## Where reports go

- `reports (claude)/` at the nearest project root: the folder Jacob would call "the project" for this piece of work (e.g. `SPSP symposium/reports (claude)/`), not the umbrella folder above it, and never just the cwd. Sibling subprojects each get their own folder when they first need one.
- First report in a project: create the folder plus a seeded CATALOG.md (s1.v1 with a one-line era description), and add a pointer line to the project's MAP.md (create a minimal MAP.md if the project has none, per global CLAUDE.md §4).
- Central `~/Claude/reports/` is reserved for Claude-infrastructure and meta work that belongs to no research project. It keeps its own convention (topic folders, `YYYY-MM-DD_NN_slug` names); this skill does not apply there.

## Naming

`s{S}.v{V}_{YYYY-MM-DD}_{slug}.{ext}`, for example `s1.v2_2026-07-18_abstract-draft.html`.

- Index first (the folder sorts and groups by project era), date second (chronology within an era), short kebab-case slug last. No topic prefix: the folder already scopes the topic.
- The index is a shared project-state tag: every deliverable produced during the same revision round carries the same `s.v`. It is not a per-file draft counter; three files tagged `s1.v2` mean they belong to the same round.
- Multi-format deliverables (markdown source plus its docx/pdf builds from `markdown-report-builder`) share one prefix and one catalog row.
- Chat-substitutes are the one exception: they keep stable un-prefixed names (`<topic>_chat-substitute.html`, per `chat-substitute-html`) so reopening always hits the same path, and they are listed in the catalog's Conversation surfaces section instead. When one is archived (`_ARCHIVE`), move its row under the era it belonged to. Claude-infrastructure work has no owning project — its chat-substitutes go in `~/Claude/reports/<topic>/` under that folder's own convention.

## CATALOG.md, the load-bearing index

The current `s.v` exists nowhere else. Read the top of CATALOG.md before naming any file; never infer the index from memory or from adjacent filenames (that inferability is what let the old Drive version log rot). Append the new file's row in the same turn you write the file.

Format (newest era first):

```markdown
# Report catalog: <project>

**Current: s1.v2** - <one-line era description>

Every file in `reports (claude)/` has a row here. The current stage.version
lives only in the line above; read it before naming a new file.

## Conversation surfaces

| File | What it is |
|---|---|

## s1: <stage description>

### s1.v2: <round description> (started YYYY-MM-DD)

| File | What it is | Status |
|---|---|---|
```

- A row is: filename, one-line purpose, status (`live` / `superseded` / `archived`). When a new file supersedes an older one, flip the old row's status in the same turn.
- Self-healing: whenever this skill fires, reconcile. Any file in the folder missing from the catalog gets a row (under its era if inferable, else a "Pre-convention" section); rows pointing at deleted files get pruned. Do this quietly; mention it only if something looked wrong.

## When the index bumps

- **Version** (`v`): a new revision round begins. Concretely: the first report of a session that supersedes or revises deliverables from an earlier round starts `v+1`. Reports that merely extend the current round keep the current `v`.
- **Stage** (`s`): a direction pivot: new research question, new venue or target, major reframe. Propose it ("this looks like a new stage; bump to s2?") and let Jacob confirm; never bump `s` silently. A new stage starts at `v1`.
- Jacob can order a bump at any time ("bump the version"). On any bump, write the new era's heading and one-line description into CATALOG.md immediately, before the first file of the new era.

## Retrofitting an existing folder

Rename Claude-authored files into the scheme and record old names in the catalog (a retrofit note under the era). Seed the era structure with Jacob rather than guessing fine-grained history; one coarse era beats retroactive slicing. Ask before renaming anything Jacob authored, and get explicit OK before renames in git-tracked folders.

## Composition with existing conventions

- The `(claude)` folder suffix is the established AI-authorship flag (global CLAUDE.md §4); this skill reuses it, never replaces it.
- MAP.md links to CATALOG.md; catalog content never moves into MAP.md.
- `chat-substitute-html` and `decision-forms-html` govern the inside of the HTMLs; `markdown-report-builder` governs docx/pdf builds. This skill only governs where files land and how they are indexed.
