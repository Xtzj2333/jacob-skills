---
name: project-filename
description: Per-project output filename convention used by Jacob's workflow skills. Pattern `<role> [<project>].<ext>`. Invoked by consumer skills (revision-queue, commented-edit-roundtrip, citation-deepening) to determine where to read/write project-scoped artifacts. Lookup-first: filenames in the project directory are themselves the source of truth, so consistency is automatic across sessions.
---

# Project-filename skill

A single, shared convention for naming per-project output files produced by Jacob's workflow skills.

Consumer skills don't hardcode names like `jacob_todos.md`. They invoke this skill with a `<role>` (the *kind* of file — `todos`, `actions`, `inbox`, etc.) and let this skill resolve the actual filename for the current project.

## The pattern

```
<role> [<project>].<ext>
```

- `<role>` — what kind of file this is. Domain of values defined by the consumer skill (e.g., `todos`, `actions`, `inbox`, `completed_actions_log`).
- `<project>` — a short, memorable shorthand for the current project (e.g., `boom`, `eduwb`).
- `<ext>` — the file extension (`md`, `docx`, etc.).

Examples:

- `todos [boom].md`
- `actions [boom].md`
- `inbox [eduwb].docx`
- `completed_actions_log [boom].md`

## The resolution algorithm (4 steps)

When a consumer skill asks for a filename, run these in order. **Stop at the first step that produces a valid answer.**

### Step 1 — Look for existing files (lookup-first)

Glob the project root for any file matching `* [*].md` or `* [*].docx` (or any extension you care about). If you find files using a `[<shorthand>]` tag, **that shorthand is canonical for this project.** Reuse it. Do not generate a new one.

```
Found: `todos [boom].md` in project root
→ canonical shorthand: `boom`
→ requested role=actions, ext=md
→ return: `actions [boom].md`
```

This step is what makes filenames self-stabilizing: once a shorthand is in use in a project, every future session finds it before generating.

### Step 2 — Check `INDEX.md` for a recorded shorthand

If no existing `[<shorthand>]` files are found, look in the project's `INDEX.md` (or `MAP.md`) for a line of the form:

```
Shorthand: <shorthand>
```

If present, use that shorthand.

### Step 3 — Generate a shorthand from project context

If neither step 1 nor step 2 produced a shorthand, generate one. Aim for:

- **Short** — 3 to 8 characters.
- **Memorable** — derived from the project's recognizable name, not a random string. E.g., "Bottom Up Wellbeing" → `boom`, "Education-Wellbeing" → `eduwb`, "Source Quality Check" → `srcqc`.
- **Lowercase** — no spaces, no special chars except hyphen if needed.
- **Distinct enough** to not collide with other shorthands Jacob is likely using.

You may also derive from the working directory name if it's already short (e.g., directory `boom/` → shorthand `boom`).

If you're genuinely unsure between two reasonable options, **ask Jacob once.** Pick fast — this is a low-stakes decision.

### Step 4 — Optionally record the shorthand in `INDEX.md`

If the project has an `INDEX.md`, add a line `Shorthand: <chosen-shorthand>` near the top so it's discoverable without grepping filenames. Skip if there's no `INDEX.md` — the filenames themselves are sufficient memory (step 1 finds them).

## When invoked

Consumer skills should call this skill at the top of their flow, *before* attempting to read or write any per-project file. The output is a filename that the consumer skill then passes to its scripts as a CLI argument.

Typical pattern in a consumer skill's `SKILL.md`:

> Before reading or writing any per-project file, invoke the `project-filename` skill with the `<role>` and `<ext>` you need. Use the resolved filename when calling `scripts/foo.py --filename "<resolved>"`.

## What this skill does NOT do

- **Doesn't enforce anything from the scripts' side.** Scripts in consumer skills are dumb — they just take a `--filename` (or similar) argument. The naming convention is Claude's responsibility, not the scripts'.
- **Doesn't manage the file contents.** That's the consumer skill's job. This skill only resolves what the file should be called.
- **Doesn't migrate old files** like `tony_todos.md` or `jacob_todos.md`. Migration is a one-time rename that Claude (or Jacob) does in the consumer-skill context. After the rename, step 1 picks up the new name and steady-state behavior takes over.

## Migrating from the old `${USER_NAME}_*` convention

If you encounter old files like `jacob_todos.md` or `tony_todos.md` in a project:

1. Determine the canonical shorthand using steps 2–3 above (or ask Jacob).
2. Rename old files: `jacob_todos.md` → `todos [<shorthand>].md`, etc.
3. Update any cross-references inside the files (e.g., `actions [<shorthand>].md` referenced from `todos [<shorthand>].md`).
4. From that point forward, step 1 finds the renamed files and everything self-stabilizes.

## Why this skill exists (Jacob's design rationale)

- **DRY.** Before this skill, the naming convention was duplicated in three consumer skills' `SKILL.md` sections. Now there's one source of truth.
- **Future-proof.** Any future skill Jacob builds that produces per-project artifacts can invoke this skill instead of re-inventing a convention.
- **Anti-over-prescription.** The naming logic lives in Claude's reasoning (this skill), not in script code. Scripts stay dumb.
- **Per-project consistency without env vars.** No `USER_NAME` env var, no config file. The filenames in the project directory *are* the configuration.

## Origin

2026-05-10. Extracted from `revision-queue`, `commented-edit-roundtrip`, and `citation-deepening` during Jacob's CLAUDE.md / skill refactor. Replaces the previous `${USER_NAME}_*` pattern.
