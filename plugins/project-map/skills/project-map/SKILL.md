---
name: project-map
description: Creates and maintains MAP.md files — project-navigation files at folder roots that orient Claude (and humans) to what's where, who authored it, and what's source/draft/canonical. Trigger when the user says "set up a MAP," "create a project map," "make a MAP.md," "orient me to this folder," when starting work in a new project directory without an existing MAP.md, or when an existing MAP.md is stale (files moved, renamed, or added since last update). Anti-triggers: generic "list files" / "show the directory" / "ls" requests — those don't need a MAP. Each project has ONE root MAP.md; subfolders MAY have their own MAP.md only when complex enough to warrant separate orientation (same pattern as README.md). Filename is always `MAP.md` (no suffixes, no parentheses).
---

# project-map

Per-project orientation file at the root of each project. Same pattern as `README.md` — one at the project root, optional ones in complex subfolders, location encodes scope.

## When to invoke

- User explicitly asks: "set up a MAP," "create a project map," "make a MAP.md," "orient me to this folder."
- New project session starts and there's no `MAP.md` at the project root — create one as part of orientation.
- An existing `MAP.md` is clearly stale (files have moved/been renamed/added; the navigation no longer matches reality) — propose an update.
- A subfolder has grown complex enough that the root `MAP.md` can't carry it — propose adding a subfolder `MAP.md`.

**Anti-triggers:** generic `ls` / "show me the files" / "what's in this directory" — answer in chat, don't write a file.

## The filename

Always `MAP.md`. No suffixes (a `MAP (claude).md` name is wrong), no parentheses, no version numbers. If you find a `(claude)`-suffixed MAP file in an existing project, that's legacy — rename it to `MAP.md` and record the authorship in the MAP's Provenance section instead.

## What goes in MAP.md (minimum)

1. **One-line orientation** at the top — what is this directory, who's it for, what's the current state in one sentence.
2. **Folder structure** — a tree (often a fenced code block) of the immediate children with one-line descriptions.
3. **Source / draft flags** — which folders/files are `(source)` (read-only reference), which are `(claude)` (AI-drafted, awaiting review), which are canonical.
4. **Provenance** — short section listing authorship for non-obvious files (especially `CLAUDE.md`, `MAP.md`, `HANDOFF.md`, `README.md` — convention-mandated names where authorship isn't obvious from the filename).
5. **Git/share status** (for collaborative projects) — which folders are local-only vs. pushable to GitHub vs. shared with collaborators.

Optional sections (add when warranted, don't pad with empty ones):

- **Quick orientation for a new session** — "If you only have 5 minutes, read X, Y, Z."
- **Open questions** — decisions the user has parked.
- **Recent cleanup log** — what changed in the last reorg.
- **Papers/refs index** — for research projects with many PDF references.

## Location encodes scope

```
project_root/MAP.md           ← project-wide orientation. REQUIRED.
project_root/subfolder/MAP.md ← subfolder orientation. OPTIONAL — only when the subfolder is complex enough.
```

Don't create a `MAP.md` in every subfolder. The rule is: if the parent's MAP can describe this subfolder in one paragraph, no subfolder MAP needed. If the subfolder has its own internal structure that would bloat the parent MAP, give it its own.

## Source-flag rule (mirrors global CLAUDE.md)

When the user has marked a folder or file with `(source)` or `[source]`:

- **READ:** always allowed. Cite from it, quote it, build downstream analysis on it.
- **EDIT / MODIFY / DELETE / RENAME / EXTRACT INTO IT:** not allowed without explicit per-action permission via the magic phrase "extract here."

Record source-status in `MAP.md` as the canonical authoritative record. **Do NOT rename source-flagged files/folders** to add or remove the flag — renames change git history and break cross-references.

## `(claude)` suffix rule (mirrors global CLAUDE.md)

A `(claude)` suffix means AI-generated and awaiting human review:

- Folder of Claude deliverables: `lit_review (claude)/`. Files inside don't need their own suffix.
- Standalone Claude proposal file: `revision_plan (claude).md`.
- New manuscript versions use `_PROPOSED` instead.
- DON'T suffix items inside an active exchange channel (the channel encodes the convention).
- DON'T suffix mixed-authorship files — record authorship in MAP.md's Provenance section instead.
- DON'T suffix convention-mandated filenames (`CLAUDE.md`, `README.md`, `MAP.md`, `HANDOFF.md`).

## When updating an existing MAP

- Update when files move, get renamed, or change source-status.
- Don't rewrite the whole MAP if only one section is stale — surgical edits preserve provenance.

## Migrating from the legacy `INDEX.md` name

`INDEX.md` was the legacy name for this kind of file. Going forward, all project-navigation files use `MAP.md`. When you encounter an old `INDEX.md`:

1. Check if a `MAP.md` already exists at the same scope. If yes, merge or pick one; if not, rename `INDEX.md` to `MAP.md`.
2. Update any text references inside other files that point to the old name (CLAUDE.md, HANDOFF.md, README.md, skills' SKILL.md).
3. For git-tracked locations, commit the rename as a discrete commit so history is clean.

(Files like `SCRIPTS_INDEX.md`, `PROJECT_INDEX.md`, `DEMO_INDEX.md` are different concepts — script catalogs / project summaries — and should be left alone. Only bare `INDEX.md` is the legacy project-navigation name.)

## What this skill does NOT do

- Doesn't generate a file listing without orientation — that's `tree` / `ls`, not a MAP.
- Doesn't enforce a rigid template — the structure adapts to the project. The minimum five sections above are required; everything else is optional and additive.
- Doesn't manage source/draft/canonical labels on the filesystem — those are conventions; MAP.md just records them.

## Origin

2026-05-11. Extracted during Jacob's CLAUDE.md / skill refactor when the global rule "every project should have a project-navigation file" was promoted into a dedicated skill so the convention is reusable and discoverable. Standardizes on `MAP.md` (Jacob's preference) and retires the legacy `INDEX.md` name.
