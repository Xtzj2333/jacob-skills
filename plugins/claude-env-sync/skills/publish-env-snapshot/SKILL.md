---
name: publish-env-snapshot
description: Capture a redacted snapshot of the user's Claude Code environment (settings.json, mcpServers, global CLAUDE.md, installed skills + commands) and publish it to a git repo so collaborators can compare against it. Use when the user says "publish my claude env", "publish my env snapshot", "update my env snapshot", "snapshot my claude setup", "/publish-env-snapshot", or asks to refresh the snapshot a collaborator pulls from.
---

# publish-env-snapshot

## What this skill does

Captures the user's Claude Code environment as a redacted JSON snapshot, then helps the user commit + push it to a git repo on GitHub. Designed to work for ANY user — Jacob, Tony, anyone — without hardcoded paths.

## When to use

User asks to publish, refresh, or update an environment snapshot so a collaborator can diff against it.

## What the snapshot is

A single JSON file (default name: `<owner>.json`) containing the user's redacted Claude Code config: settings.json contents, mcpServers config (keys redacted), global CLAUDE.md, list of installed skills + commands. Lives at `<repo>/snapshots/<owner>.json` in a public-or-collaborator-readable git repo.

## Procedure

### Step 1 — Resolve `<OWNER>` (the snapshot identifier)

In priority order:
1. Look for `USER_NAME=...` in `~/.claude/CLAUDE.md` and lowercase it.
2. Use `$USER` from the environment.
3. Ask the user: "What identifier should I use for your snapshot? (e.g. `jacob`, `tony`, your first name)"

### Step 2 — Resolve `<TARGET_REPO>` (where the snapshot file goes)

Discover the user's snapshot-publishing repo. In priority order:

1. **If user named the repo in their request**, use that.
2. **Search for any local clone** that looks like a snapshot-publishing repo:
   ```bash
   find ~/Documents ~/Projects ~/ -maxdepth 4 -type d -name ".git" 2>/dev/null \
     | xargs -I{} dirname {} \
     | while read d; do
         if [ -f "$d/.claude-plugin/marketplace.json" ] || [ -d "$d/snapshots" ]; then
           echo "$d"
         fi
       done
   ```
3. **If exactly one match**, confirm with the user: "Found `<path>` — publish there?"
4. **If multiple matches**, list them and ask which.
5. **If zero matches**, ask the user to:
   - Create a public GitHub repo (e.g., `<owner>-claude-env`)
   - Clone it locally (e.g., `~/<owner>-claude-env/`)
   - Tell you the path

The repo doesn't need to be a full plugin marketplace — a bare repo with a `snapshots/` folder works. The marketplace structure is only needed for the snapshot OWNER if they ALSO want to publish plugins.

### Step 3 — Run the publisher

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/publish_snapshot.py \
    --owner <OWNER> \
    --out <TARGET_REPO>/snapshots/<OWNER>.json
```

The script prints a one-line redaction summary to stderr (counts of key-shape matches, key-name redactions, home-path normalizations).

### Step 4 — Show the user the snapshot for review

**Mandatory before any commit.** Read the just-written `<OWNER>.json` and present a brief summary:

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

### Step 5 — Sensitive-content scan (defense in depth)

Before committing, run an extra grep for any string that LOOKS like a key the redactor missed:

```bash
grep -E "tvly-[A-Za-z0-9]{4,}|sk-[A-Za-z0-9]{10,}|sk-ant-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{4,}|gho_[A-Za-z0-9]{4,}|AKIA[0-9A-Z]{4,}|Bearer\s+[A-Za-z0-9._-]{10,}|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+" \
  <TARGET_REPO>/snapshots/<OWNER>.json
```

If anything matches, **stop**. Show the matches to the user; do not commit. Either patch the snapshot file by hand (Edit tool) or fix the redactor in `scripts/publish_snapshot.py`.

### Step 6 — Commit + push (only after explicit OK)

```bash
cd <TARGET_REPO>

# Make sure we're not bundling unrelated work
git status -s
# If output shows other dirty files, stop and ask the user how to handle them.

git add snapshots/<OWNER>.json
git -c commit.gpgsign=false commit -m "Refresh env snapshot for <OWNER> (YYYY-MM-DD)"

# Determine push target. If on main, push to origin main. If on a different branch, push there.
current_branch=$(git branch --show-current)
git push origin "$current_branch"
```

After push, tell the user the snapshot is live at:

```
https://raw.githubusercontent.com/<gh-owner>/<repo>/<branch>/snapshots/<OWNER>.json
```

This is the URL the collaborator will plug into `env-compare`.

If the user has a collaborator already set up, suggest sending them the URL.

## What this skill does NOT do

- Does not modify `~/.claude/` — read-only against the user's environment.
- Does not commit anything other than `snapshots/<OWNER>.json` (so it's safe to run with other uncommitted work in the target repo, with the dirty-state check above).
- Does not push without explicit user OK in step 4.
- Does not create the GitHub repo for the user — that's a one-time manual step.

## Failure modes to avoid

| Mode | Avoid by |
|---|---|
| Committing a snapshot that still contains real keys | Step 5 grep — never skip |
| Pushing without showing the user the snapshot first | Step 4 — never skip |
| Refreshing a snapshot when the target repo has unrelated uncommitted work | `git status` check in Step 6 |
| Snapshot appears empty | Check that `~/.claude/settings.json` and `~/.claude.json` exist; fail loudly if either is missing |
| Hardcoding Jacob-specific paths | The procedure above is generic — Tony or any other user runs the same skill |
