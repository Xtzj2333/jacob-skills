---
name: sync-cowork-skill
description: "One-way publish of a Cowork-side skill (where Jacob actively edits and improves) to the public Xtzj2333/jacob-skills marketplace plugin (what Tony installs). Run from Claude Code only. Trigger on phrases like 'sync calendar-search to github', 'publish my cowork skill', 'push my <skill> to jacob-skills', 'update the marketplace copy of <skill>', or '/sync-cowork-skill <skill>'. CRITICAL invariant: this skill NEVER writes to Cowork. The Cowork file is the source of truth; the marketplace copy is downstream. Do NOT trigger on 'tony github push' (that's the manuscript push), generic 'git push', or 'sync everything' (this skill operates on one named skill at a time)."
---

# sync-cowork-skill

This skill publishes one Cowork-side skill (the canonical, frequently-improved version Jacob edits via Cowork's `skill-creator` and direct edits) to the corresponding plugin folder in `~/jacob-skills/`, then commits and pushes it to GitHub so collaborators get the update.

## Invariants (the safety properties)

1. **Cowork is read-only here.** The script reads from Cowork, writes to `~/jacob-skills/`, and never the reverse. If anything goes wrong on the GitHub side, the Cowork file is untouched and remains authoritative.
2. **Two-step gate.** Always run dry-run first; show the diff and the sensitive-content scan to Jacob; wait for an explicit "yes, push" before re-running with `--apply`.
3. **Sensitive content blocks `--apply`** unless explicitly overridden via `SYNC_OVERRIDE_SENSITIVE=1`.
4. **The marketplace repo must be clean** (no unrelated uncommitted changes) before `--apply` proceeds — prevents tangling sync with other in-progress work.

## How to run

The script auto-discovers Cowork session UUIDs via glob, so it works regardless of Cowork reinstalls.

### Step 1: dry-run (always do this first)

```bash
python3 ~/jacob-skills/plugins/sync-cowork-skill/skills/sync-cowork-skill/scripts/sync.py <skill-name>
```

Show Jacob the full output. It includes:

- **SKILL.md diff** — `-` lines are current GitHub, `+` lines are Cowork. This is what would change.
- **File-level summary** — counts of files added / deleted / unchanged.
- **Sensitive-content scan** — every regex hit across all text files in the Cowork skill folder (not just `SKILL.md`). Reports `<file>:Lline: 'match' [reason]` for each hit. Patterns include emails, real names known from earlier session work, gmail/uchicago handles, gov-ID-shaped numbers, and a few API-key patterns. **Even one hit means stop and review.**

The dry-run never modifies anything (Cowork or GitHub).

### Step 2: confirm with Jacob

Before invoking `--apply`, Jacob must explicitly approve. The script reports findings and what would change; Jacob looks and says "yes, push" / "no, abort" / "remove X first."

If sensitive findings exist:

- If they are PII or third-party data → **do not push.** Tell Jacob to prune the Cowork file first, then re-run dry-run.
- If they are intentional and acceptable (e.g., his own first name in a personalized skill) → re-run with the override (Step 3 with `SYNC_OVERRIDE_SENSITIVE=1`).

### Step 3: apply (only after explicit Jacob approval)

```bash
python3 ~/jacob-skills/plugins/sync-cowork-skill/skills/sync-cowork-skill/scripts/sync.py <skill-name> --apply
```

If the dry-run flagged sensitive content that Jacob has reviewed and confirmed is OK:

```bash
SYNC_OVERRIDE_SENSITIVE=1 python3 ~/jacob-skills/plugins/sync-cowork-skill/skills/sync-cowork-skill/scripts/sync.py <skill-name> --apply
```

`--apply` does, in order:

1. Recompute the dry-run report. If now sensitive (without override) or now dirty repo, abort.
2. Mirror the Cowork skill folder to `~/jacob-skills/plugins/<skill-name>/skills/<skill-name>/` — copies new/changed files, deletes files removed in Cowork. The plugin's `.claude-plugin/plugin.json` (which lives ABOVE the synced folder) is untouched.
3. `git add` the synced subtree (precise — not `git add -A`).
4. `git commit -m "Sync <skill-name> from Cowork"` (or a custom message via `--commit-message`).
5. `git push`.

If `git push` fails (network, auth), the local commit is preserved. The script reports the failure and tells Jacob to retry manually.

## Failure modes and what to do

| Exit code | Meaning | What to do |
|---|---|---|
| 0 | Success, or dry-run with no changes | Nothing |
| 10 | Cowork skill not found | Check skill name spelling. Run `ls ~/Library/Application\ Support/Claude/local-agent-mode-sessions/skills-plugin/*/*/skills/` |
| 11 | Cowork folder exists but no SKILL.md | The Cowork skill is malformed — abort and inspect |
| 12 | Marketplace plugin folder has no `plugin.json` | This is a NEW plugin. Set up `plugins/<name>/.claude-plugin/plugin.json` manually with a real description first; then re-run `--apply` |
| 13 | Sensitive findings + no override | Either prune the findings from the Cowork file (then re-run), or set `SYNC_OVERRIDE_SENSITIVE=1` if the findings are intentional and acceptable |
| 14 | Marketplace repo has uncommitted changes | Resolve those first (`cd ~/jacob-skills && git status` and decide) |
| 15 | Push failed after successful commit | Retry manually: `cd ~/jacob-skills && git push` |

## Anti-triggers — when NOT to run this

- **"tony github push"** — that's the manuscript push, separate skill.
- **Generic "git push" / "commit and push"** — use git directly.
- **"update the calendar skill"** — ambiguous. Could mean editing, not publishing. Confirm intent first.
- **Cowork sessions** — this skill runs from Claude Code. Cowork is the source side; we do not invoke the script from there.
- **Bulk "sync everything"** — explicitly out of scope. One skill at a time, by name. Bulk operations make accidental over-pushes too easy.

## What the script will NEVER do

- Write to Cowork.
- Pull from GitHub to overwrite Cowork.
- Push to a branch other than the current branch of `~/jacob-skills/`.
- `git add -A` (only the synced subtree).
- Auto-create a new plugin's `plugin.json` (would be a silent decision about what to publish; refused by design).
- Bypass a sensitive-content finding without explicit `SYNC_OVERRIDE_SENSITIVE=1`.

## After a successful sync

The marketplace copy is updated and pushed. Tony's `/plugin update jacob-skills` (or session-start auto-update) will pull the new version on his next Claude Code or Cowork session.

Jacob's own Cowork is **not** updated by this skill — Jacob's Cowork was already the source. The local Cowork file stays exactly as it was.

## Recovery if a bad version was pushed

If a sync pushed something Jacob regrets (e.g., a Cowork rewrite he didn't want), recovery is via git history on the marketplace, not via Cowork:

```bash
cd ~/jacob-skills
git log -- plugins/<skill-name>/skills/<skill-name>/SKILL.md     # find the prior commit
git show <prev-sha>:plugins/<skill-name>/skills/<skill-name>/SKILL.md > /tmp/old.md  # extract
# review, decide what to do; could revert the commit, or restore the old version, etc.
```

The Cowork file is unaffected by any of this — it's been read-only the whole time.
