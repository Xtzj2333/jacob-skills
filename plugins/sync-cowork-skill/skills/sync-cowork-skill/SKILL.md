---
name: sync-cowork-skill
description: "One-way publish of a Jacob-authored skill to the public Xtzj2333/jacob-skills marketplace plugin (what Tony installs). Source can be either Cowork (~/Library/.../skills-plugin/.../skills/<name>/) or Claude Code user-level (~/.claude/skills/<name>/) — the script auto-detects whichever single source exists. CRITICAL invariant: this skill NEVER writes back to the source. Trigger on 'sync calendar-search to github', 'publish my cowork skill', 'push my <skill> to jacob-skills', 'update the marketplace copy of <skill>', or '/sync-cowork-skill <skill>'. Do NOT trigger on 'tony github push' (manuscript push), generic 'git push', or 'sync everything' (one skill at a time)."
---

# sync-cowork-skill

This skill publishes one Jacob-authored skill to the corresponding plugin folder in `~/jacob-skills/`, then commits and pushes it to GitHub so collaborators get the update.

The script accepts two source locations and auto-detects whichever single one exists:

- **Cowork** — `~/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/*/*/skills/<name>/` (historically the default; used for skills Jacob authors via Cowork's skill-creator)
- **Claude Code user-level** — `~/.claude/skills/<name>/` (used for skills authored directly via Claude Code)

If both exist, the script refuses and asks for `--source-override` to make Jacob's intent explicit.

## Invariants (the safety properties)

1. **The source is read-only here.** The script reads from the source (Cowork or user-skills), writes to `~/jacob-skills/`, and never the reverse. If anything goes wrong on the GitHub side, the source file is untouched.
2. **Two-step gate.** Always dry-run first; show the diff and the sensitive-content scan to Jacob; wait for an explicit "yes, push" before re-running with `--apply`.
3. **Third-party guard.** Refuses to sync any source folder containing `LICENSE` / `pyproject.toml` / `package.json` / `Cargo.toml` / a `.git/` pointing at a non-jacob remote. Prevents accidentally republishing someone else's work.
4. **Sensitive content blocks `--apply`** unless explicitly overridden via `SYNC_OVERRIDE_SENSITIVE=1`.
5. **The marketplace repo must be clean** (no unrelated uncommitted changes) before `--apply` proceeds.
6. **Auto-scaffold + auto-register on first publish.** If `plugin.json` or `.claude-plugin/marketplace.json` lacks an entry for the skill, `--apply` adds them automatically using the description from the source's frontmatter. The dry-run flags both proposed additions so Jacob sees them before confirming.

## How to run

### Step 1: dry-run (always do this first)

```bash
python3 ~/jacob-skills/plugins/sync-cowork-skill/skills/sync-cowork-skill/scripts/sync.py <skill-name>
```

If both source locations exist, override explicitly:

```bash
python3 ~/jacob-skills/plugins/sync-cowork-skill/skills/sync-cowork-skill/scripts/sync.py <skill-name> --source-override user-skills
# or --source-override cowork
# or --source-override /absolute/path/to/skill/folder
```

Show Jacob the full output. It includes:

- **Resolved source** (`user-skills` vs `cowork` vs `explicit:<path>`).
- **SKILL.md diff** — `-` lines are current GitHub, `+` lines are source.
- **First-publish notes** — if `plugin.json` is missing or the skill isn't registered in `marketplace.json`, the dry-run says so.
- **File-level summary** — counts of files added / deleted / unchanged.
- **Sensitive-content scan** — every regex hit across all text files in the source skill folder. Reports `<file>:Lline: 'match' [reason]` for each hit. **Even one hit means stop and review.**

The dry-run never modifies anything.

### Step 2: confirm with Jacob

Before invoking `--apply`, Jacob must explicitly approve. The script reports findings and what would change; Jacob looks and says "yes, push" / "no, abort" / "remove X first."

If sensitive findings exist:

- If they are PII or third-party data → **do not push.** Tell Jacob to prune the source file first, then re-run dry-run.
- If they are intentional and acceptable (e.g., his own first name in a personalized skill) → re-run with `SYNC_OVERRIDE_SENSITIVE=1`.

### Step 3: apply (only after explicit Jacob approval)

```bash
python3 ~/jacob-skills/plugins/sync-cowork-skill/skills/sync-cowork-skill/scripts/sync.py <skill-name> --apply
```

For a sensitive-finding override:

```bash
SYNC_OVERRIDE_SENSITIVE=1 python3 ~/jacob-skills/plugins/sync-cowork-skill/skills/sync-cowork-skill/scripts/sync.py <skill-name> --apply
```

`--apply` does, in order:

1. Recompute the dry-run report. If now sensitive (without override) or now dirty repo, abort.
2. If `plugin.json` is missing, scaffold one (frontmatter description → plugin.json description).
3. If `marketplace.json` lacks an entry, append one.
4. Mirror the source skill folder to `~/jacob-skills/plugins/<skill-name>/skills/<skill-name>/` — copies new/changed files, deletes files removed in source.
5. `git add` the synced subtree + any scaffolded/registered files (precise — not `git add -A`).
6. `git commit -m "Sync <skill-name> from <provenance>"` (adds " (first-time publish)" if anything was scaffolded).
7. `git push`.

If `git push` fails (network, auth), the local commit is preserved. The script reports the failure and tells Jacob to retry manually.

## Failure modes and exit codes

| Exit code | Meaning | What to do |
|---|---|---|
| 0  | Success, or dry-run with no changes | Nothing |
| 10 | Source skill not found (neither user-skills nor Cowork) | Check spelling. Run `ls ~/.claude/skills/` or check Cowork session glob |
| 11 | Source folder exists but no `SKILL.md` | The source skill is malformed — abort and inspect |
| 13 | Sensitive findings + no override | Either prune the findings (then re-run), or set `SYNC_OVERRIDE_SENSITIVE=1` if intentional and acceptable |
| 14 | Marketplace repo has uncommitted changes | Resolve those first (`cd ~/jacob-skills && git status` and decide) |
| 15 | Push failed after successful commit | Retry manually: `cd ~/jacob-skills && git push` |
| 16 | Source exists in BOTH locations | Pass `--source-override user-skills\|cowork` to disambiguate |
| 17 | Source has third-party markers | Don't publish someone else's work; install upstream instead |

## Anti-triggers — when NOT to run this

- **"tony github push"** — that's the manuscript push, separate skill.
- **Generic "git push" / "commit and push"** — use git directly.
- **"update the calendar skill"** — ambiguous. Could mean editing, not publishing. Confirm intent first.
- **Cowork sessions** — this skill runs from Claude Code. Cowork is one of the source sides; we do not invoke the script from there.
- **Bulk "sync everything"** — explicitly out of scope. One skill at a time, by name.

## What the script will NEVER do

- Write to Cowork or to `~/.claude/skills/`.
- Pull from GitHub to overwrite the source.
- Push to a branch other than the current branch of `~/jacob-skills/`.
- `git add -A` (only the synced subtree + auto-registered metadata).
- Publish a skill containing `LICENSE` / `pyproject.toml` / `package.json` / `Cargo.toml` or pointing `.git/` at a non-jacob remote (third-party guard).
- Bypass a sensitive-content finding without explicit `SYNC_OVERRIDE_SENSITIVE=1`.

## After a successful sync

The marketplace copy is updated and pushed. Tony's `/plugin update jacob-skills` (or session-start auto-update) will pull the new version on his next Claude Code or Cowork session.

The source file (Cowork or user-skills) is **not** updated by this skill — it was already the source.

## Recovery if a bad version was pushed

If a sync pushed something Jacob regrets (e.g., a source rewrite he didn't want), recovery is via git history on the marketplace, not via the source:

```bash
cd ~/jacob-skills
git log -- plugins/<skill-name>/skills/<skill-name>/SKILL.md     # find the prior commit
git show <prev-sha>:plugins/<skill-name>/skills/<skill-name>/SKILL.md > /tmp/old.md
# review, decide what to do; could revert the commit, or restore the old version, etc.
```

The source file is unaffected by any of this — it's been read-only the whole time.
