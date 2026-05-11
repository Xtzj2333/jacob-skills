---
name: publish-env-snapshot
description: Capture a redacted snapshot of the user's Claude Code environment (settings.json, mcpServers, global CLAUDE.md, installed skills + commands) and publish it to their marketplace repo so collaborators can compare against it. Use when the user says "publish my claude env", "publish my env snapshot", "update my env snapshot", "snapshot my claude setup", "/publish-env-snapshot", or asks to refresh the snapshot a collaborator pulls from.
---

# publish-env-snapshot

## What this skill does

1. Runs `scripts/publish_snapshot.py` to capture a redacted JSON snapshot of the user's `~/.claude/` and `~/.claude.json` (mcpServers only) into a target file.
2. Shows the user the redacted snapshot for visual confirmation that no secrets leaked.
3. After explicit OK, commits + pushes the snapshot to the user's marketplace repo on GitHub.

## When to use

User asks to publish, refresh, or update an environment snapshot. They want a collaborator to be able to diff against it.

## Inputs the skill needs (ask if unset)

- **`<USER>`** — short identifier for the snapshot owner (e.g. `jacob`, `tony`). Default: lowercase first name from `USER_NAME` in CLAUDE.md or `$USER`.
- **`<MARKETPLACE_DIR>`** — path to a clean local clone of the user's marketplace repo. Default search order:
  1. `~/jacob-skills/` (or `~/<user>-skills/`)
  2. `~/Documents/Claude/jacob-skills-work/`
  3. Any directory under `~/Documents/Claude/` matching `*-skills*` with a `.claude-plugin/marketplace.json`
  
  If none found, ask: "Where's your marketplace working clone?"

## Procedure

### Step 1 — Run the publisher

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/publish_snapshot.py \
    --owner <USER> \
    --out <MARKETPLACE_DIR>/snapshots/<USER>.json
```

The script prints a one-line redaction summary to stderr (counts of key-shape matches, key-name redactions, home-path normalizations).

### Step 2 — Show the user the snapshot for review

**Mandatory before any commit.** Read the just-written `<USER>.json` and present a brief summary to the user:

- Hook events captured (names + count of entries each)
- MCP servers captured (names) — confirm `env` values show `<REDACTED:...>` placeholders, NOT actual key strings
- Settings top-level keys captured
- Skills count + 5 sample names
- Commands count + names
- CLAUDE.md captured: yes/no, char count
- Redaction stats from the script

Then say (verbatim):

> I've written the snapshot. Before I commit it, please confirm:
> (a) no real API keys / OAuth tokens visible in the snapshot
> (b) no `/Users/<your-username>` paths that should have been normalized
> (c) the CLAUDE.md content is OK to publish (it's your full global instructions)
>
> Want me to commit + push, edit something first, or stop here?

### Step 3 — Sensitive-content scan (defense in depth)

Before committing, run an extra grep over the snapshot for any string that LOOKS like a key the redactor missed:

```bash
grep -E "tvly-[A-Za-z0-9]{4,}|sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{4,}|AKIA[0-9A-Z]{4,}|Bearer\s+[A-Za-z0-9_-]{10,}" <MARKETPLACE_DIR>/snapshots/<USER>.json
```

If anything matches, **stop**. Show the matches to the user; do not commit. Either patch the snapshot file by hand (Edit tool) or fix the redactor in `scripts/publish_snapshot.py`.

### Step 4 — Commit + push (only after explicit OK)

```bash
cd <MARKETPLACE_DIR>
git add snapshots/<USER>.json
git -c commit.gpgsign=false commit -m "Refresh env snapshot for <USER> (YYYY-MM-DD)"
git push origin main
```

After push, tell the user the snapshot is live at:

```
https://raw.githubusercontent.com/<gh-owner>/<repo>/main/snapshots/<USER>.json
```

This is the URL their collaborator will plug into `env-compare`.

## What this skill does NOT do

- Does not modify `~/.claude/` — read-only against the user's environment.
- Does not commit anything other than `snapshots/<USER>.json` (so it's safe to run with other uncommitted work in the marketplace clone).
- Does not push without explicit user OK in step 2.

## Failure modes to avoid

| Mode | Avoid by |
|---|---|
| Committing a snapshot that still contains real keys | Step 3 grep — never skip |
| Pushing without showing the user the snapshot first | Step 2 — never skip |
| Refreshing a snapshot when the marketplace clone has unrelated uncommitted work | `git status` before — if dirty, ask user whether to stash / discard / continue selectively |
| Snapshot appears empty | Check that `~/.claude/settings.json` and `~/.claude.json` exist; fail loudly if either is missing |
