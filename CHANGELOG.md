# Changelog

## 2026-05-22 — `jacob-todos` v0.2 (full system bundled, not just SKILL.md)

**TL;DR:** `jacob-todos` previously shipped trigger-only (just `SKILL.md`). v0.2 bundles the real machinery — scripts, instruction docs, sanitized JSON templates — under `skills/jacob-todos/system/`, with a first-time-setup section in `SKILL.md` that scaffolds `<workspace>/to do/` on demand. Calendar IDs are no longer hard-coded in `gcal_todo_instructions.md`; they live in `state_v3.json.calendar_config` so a new user fills them in once.

### `jacob-todos` v0.2

- **Bundled `system/` folder** beside `SKILL.md` with:
  - `state_v3.template.json`, `tasks_v3.template.json` — empty/example templates (no personal data).
  - `cowork_instructions.md`, `gcal_todo_instructions.md`, `MAP.md` — genericized; calendar-specific values moved into `state_v3.json.calendar_config`.
  - `scripts/build_check_in.js`, `build_per_task_recs.js`, `pickup_actions.js`, `parse_comments.py`, `task_verbs.js`, `package.json` — copied as-is (no hard-coded personal paths or IDs).
- **First-time setup section in `SKILL.md`.** Triggers on "set up the to-do system" / "install jacob-todos" / "scaffold the to-do system". Walks Claude through: create the workspace folder structure, copy templates into place, `npm install` inside `scripts/`, prompt the user to fill in `calendar_config`, run the first check-in.
- **Sanitization.** Live `tasks_v3.json` and `state_v3.json` are NOT shipped — replaced with 2-task and defaults-only templates respectively. Real calendar IDs, primary email, personal contact names, and project content are removed.
- **plugin.json now carries a `version` field** (was missing).

### Pickup on the collaborator side

- `/plugin marketplace update` then `/plugin install jacob-todos@jacob-skills` (or just `/plugin update jacob-todos`).
- After install: "set up the to-do system" in chat — Claude reads the new SKILL.md, scaffolds `<workspace>/to do/`, and prompts for `calendar_config` values.

---

## 2026-05-12 — `claude-env-sync` v0.4 (skill bodies + external CLIs) and manifest-version bump

**TL;DR:** `claude-env-sync` now captures (a) full SKILL.md + bundled-file content for personal skills under `~/.claude/skills/`, and (b) an external CLI inventory (`uv tool list` + `brew leaves`) so the diff flags binaries that MCP servers depend on. Also: the plugin manifest version is now bumped on every release (the v0.4 code shipped initially without a manifest bump, so `/plugin install` was a silent no-op — fixed in commit following `cf6c7bf`).

### `claude-env-sync` v0.4

- **Snapshot format 0.3 → 0.4.** Backward-compat preserved.
- **New capture: user skill bodies.** Full SKILL.md text + bundled text files for each `~/.claude/skills/<name>/`. Third-party skills (marker files like `LICENSE`, `pyproject.toml`, `package.json`) keep their SKILL.md but skip the bundle — install those upstream. Per-skill opt-out via `.envsync-skip-body`. Per-file 150 KB cap, per-bundle 500 KB cap.
- **New capture: external CLI inventory.** Best-effort `uv tool list` and `brew leaves`. Surfaces, on the import side, tools that exist on the source machine but not the receiving one, with the install command beside each.
- **New: version-skew warning.** The comparer now emits a clear warning (stderr + JSON field + HTML banner) when the snapshot was produced by a newer publisher than the local comparer. Prevents silent feature gaps.
- **Manifest version is now load-bearing.** `plugin.json` "version" is bumped on every release so `/plugin install <plugin>@jacob-skills` actually pulls fresh code. (Lesson from the v0.4 silent-no-op incident: Claude Code skips the upgrade when the manifest version is unchanged, even if the script files are newer.)

### How to upgrade on the import side

```
/plugin marketplace update jacob-skills
/plugin install claude-env-sync@jacob-skills
```

Verify with `head -3 ~/.claude/plugins/cache/jacob-skills/*/plugins/claude-env-sync/.claude-plugin/plugin.json` — should show `"version": "0.4.0"`. If still 0.3.0, the marketplace update didn't take; check that the marketplace clone is current.

---

## 2026-05-11 — `project-map` skill + `claude-env-sync` v0.3

**TL;DR:** New `project-map` skill produces and maintains `MAP.md` orientation files at folder roots (legacy `INDEX.md` name is migrated). `claude-env-sync` plugin bumped to v0.3 with stronger version-pinning of installed plugins and zero-false-positive self-compare.

### `project-map` (new plugin)

- Folder-orientation skill — creates `MAP.md` at a project root and updates it when files move/rename/add. Subfolder MAPs are optional, used only when the parent's MAP can't describe a subfolder in one paragraph.
- Migrates legacy `INDEX.md` files to `MAP.md`, including text references in nearby `CLAUDE.md` / `HANDOFF.md` / `README.md` / SKILL.md.
- Anti-triggers `ls`-style questions — only fires when a written orientation file is genuinely warranted.

### `claude-env-sync` v0.3

- **Snapshot format bumped 0.2 → 0.3.** Backward-compat preserved: v0.1 and v0.2 snapshots still load; missing fields are treated as empty.
- **New capture:** `~/.claude/plugins/installed_plugins.json`. Pins, for every installed plugin, the version + git commit SHA + install date. The diff now answers "are we on the same plugin versions?" directly — strictly more useful than per-file diffs of plugin caches.
- **Bug fix — asymmetric comparison.** The publisher applies redaction + `${HOME}` normalization before writing snapshots; the comparer previously read local files raw. Self-compare was producing false positives (MCP servers, central files showing as "different" by 10 chars — exactly one un-normalized home path). The comparer now mirrors the same transforms on local reads.
- **Bug fix — skill listing pollution.** Skill enumeration now requires `SKILL.md` at the top of each candidate directory. Drops `.git/` and bundle directories (e.g. `academic-research-skills`) that were polluting the user-skills list.
- **New capture:** central reference files under `~/Claude/` (currently `manuscript-rules.md`) — for lab-agnostic project rules `@`-imported by project-local `CLAUDE.md`.

### `SKILLS_OVERVIEW.md` updated

Reflects the new plugin count: 8 collaborator-facing skills (added `project-map`), 1 utility called by others (`project-filename`, unchanged), 2 Jacob-internal plugins (`sync-cowork-skill` + new `claude-env-sync`).

---

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
