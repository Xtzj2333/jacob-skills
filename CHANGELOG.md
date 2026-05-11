# Changelog

## 2026-05-10 — `USER_NAME` retired, replaced by `project-filename` skill

**TL;DR:** The three skills that produced per-user files (`revision-queue`, `commented-edit-roundtrip`, `citation-deepening`) no longer use a `USER_NAME` environment variable. A new skill, `project-filename`, defines a per-*project* naming convention instead.

### What changed

- **New plugin:** `project-filename` — a tiny shared skill that resolves filenames using the pattern `<role> [<project>].<ext>`, where `<role>` is the kind of file (`todos`, `actions`, `inbox`, `completed_actions_log`) and `<project>` is a short, memorable shorthand for the current project.
- **`revision-queue` scripts (`close_todo.py`, `verify_state.py`, `execute_action.py`, `regen_docx.sh`)** now accept filenames as explicit CLI arguments instead of constructing them from `$USER_NAME`.
- **`commented-edit-roundtrip` and `citation-deepening`** docs updated to point at the new convention. (Neither skill had script-level dependencies on `USER_NAME` — the references were documentation-only.)

### Why

- **DRY:** the naming convention was duplicated in three skills' `SKILL.md` sections. It's now in one place.
- **Per-project, not per-user:** the previous convention encoded *who* the files belong to (`jacob_todos.md`, `tony_todos.md`). The new convention encodes *which project* the files belong to (`todos [boom].md`), which is what actually matters when collaborators share a project.
- **No env-var coupling:** scripts no longer read environment variables. The naming decision lives in Claude's reasoning at call time; scripts stay agnostic.

### Migration (for collaborators)

If you have existing files from before this change, rename them once:

```
jacob_todos.md      →  todos [<your-shorthand>].md
jacob_actions.md    →  actions [<your-shorthand>].md
jacob_inbox.docx    →  inbox [<your-shorthand>].docx     (only if you used this — most projects don't)
completed_actions_log.md  →  completed_actions_log [<your-shorthand>].md
```

`<your-shorthand>` is a short, memorable tag for the project — e.g., `boom` for "Bottom Up Wellbeing." Claude will help you pick one when it first invokes the `project-filename` skill in a project; it can also read an existing shorthand from any `[<shorthand>]`-tagged file already in the project root.

After the rename, no further migration is needed. The `project-filename` skill detects the existing shorthand automatically on subsequent calls (it globs `* [*].*` in the project root before generating anything new).

### CLAUDE.md cleanup

If your global `~/.claude/CLAUDE.md` had a `USER_NAME=` line (per the old setup instructions), you can remove it — the variable is no longer read by any skill. The `manuscript-push` configuration block for `tony-github-push` is unaffected.

### Backwards compatibility

None. This is a clean break — scripts no longer accept the old form. The rationale is that running these scripts independently of Claude (e.g., from a plain terminal) is rare; in practice Claude invokes them with explicit filename arguments. If you do need to run them by hand, pass the filenames directly.

See `plugins/project-filename/skills/project-filename/SKILL.md` for the full resolution algorithm and design rationale.
