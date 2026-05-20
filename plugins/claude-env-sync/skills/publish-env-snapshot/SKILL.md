---
name: publish-env-snapshot
description: Capture a redacted snapshot of the user's Claude Code environment (settings.json, settings.local.json, mcpServers from both ~/.claude.json and ~/.claude/.mcp.json, global CLAUDE.md, statusline config, installed user-level + plugin-shipped skills, Cowork-session skills, slash commands with bodies, agents) and publish it to a git repo so collaborators can compare against it. Use when the user says "publish my claude env", "publish my env snapshot", "update my env snapshot", "snapshot my claude setup", "/publish-env-snapshot", or asks to refresh the snapshot a collaborator pulls from.
---

# publish-env-snapshot

## What this skill does

Captures the user's Claude Code environment as a redacted JSON snapshot, then helps the user commit + push it to a git repo on GitHub. Designed to work for ANY user — Jacob, Tony, anyone — without hardcoded paths.

## When to use

User asks to publish, refresh, or update an environment snapshot so a collaborator can diff against it.

## What the snapshot is

A single JSON file (default name: `<owner>_<machine_id>.json` if a machine_id is set, else `<owner>.json`) containing the user's redacted Claude Code config: settings.json + settings.local.json, merged mcpServers from both `~/.claude.json` and `~/.claude/.mcp.json` (keys redacted), global CLAUDE.md, central reference files (e.g. `~/Claude/manuscript-rules.md`), statusline config, keybindings, agents, list of user-level + plugin-shipped skills, slash commands (including their bodies), and `installed_plugins.json` (version + git SHA pinning for every installed plugin). Lives at `<repo>/snapshots/<filename>` in a public-or-collaborator-readable git repo.

## Snapshot format version

This skill produces v0.7 snapshots (see `SNAPSHOT_FORMAT_VERSION` in `scripts/publish_snapshot.py`). The compare side handles older snapshots gracefully (treats missing fields as empty / falls back to older key names). v0.7 added `skills_cowork`: a visibility-only list of skills found in Cowork's per-session skill directory, each tagged `published_via: anthropic-builtin | plugin:<p>@<mp> | cowork-only`. Bodies are NOT captured — collaborators see what exists but personal workflow bodies never leak into the public snapshot.

## Procedure

### Step 1 — Resolve `<OWNER>` and `<MACHINE_ID>` (the snapshot identifier)

`<OWNER>` is the person ("jacob", "tony"). `<MACHINE_ID>` is the per-machine label ("main", "jz1", "work"), only needed when the user runs Claude Code on multiple machines and wants per-machine snapshots.

**Resolve `<OWNER>` in priority order:**
1. Look for `USER_NAME=...` in `~/.claude/CLAUDE.md` and lowercase it.
2. Use `$USER` from the environment.
3. Ask the user: "What identifier should I use for your snapshot? (e.g. `jacob`, `tony`, your first name)"

**Resolve `<MACHINE_ID>` in priority order:**
1. Read `~/.claude/machine_id` (one-line file). If present, use that.
2. If absent, ask the user: "Are you on multiple machines? If yes, what's this one called (e.g. `main`, `jz1`, `work`, `laptop`)? If no, hit enter to skip."
3. If the user gives a machine_id, write it to `~/.claude/machine_id` so future runs auto-resolve. If they skip, leave `<MACHINE_ID>` unset.

**Compose the snapshot filename:**
- If `<MACHINE_ID>` is set: `<OWNER>_<MACHINE_ID>.json` (e.g. `jacob_main.json`)
- Otherwise: `<OWNER>.json`

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
    --machine-id <MACHINE_ID> \
    --out <TARGET_REPO>/snapshots/<FILENAME>
```

(Omit `--machine-id` if not set; the script will read `~/.claude/machine_id` itself or leave it null.)

The script prints a one-line redaction summary to stderr (counts of key-shape matches, key-name redactions, home-path normalizations, plus the resolved `machine_id`).

### Step 4 — Show the user the snapshot for review

**Mandatory before any commit.** Read the just-written snapshot file and present a brief summary:

- Snapshot format version + machine_id + claude --version captured
- Hook events captured (names + handler counts)
- MCP servers captured (names) — confirm `env` values show `<REDACTED:...>` placeholders, NOT actual key strings. Note: now sourced from BOTH `~/.claude.json` mcpServers AND `~/.claude/.mcp.json` mcpServers (merged).
- Settings top-level keys captured
- settings.local.json keys captured (permissions, etc.)
- Statusline config captured (whole file)
- User-level skills count + 5 sample names
- Plugin-shipped skills count + 3 sample `<name>@<plugin>` pairs
- Cowork-session skills count, broken down by `published_via` (anthropic-builtin / plugin:X@mp / cowork-only). Call out any `cowork-only` entries by name — those are author-local and won't be reachable by collaborators until published via `sync-cowork-skill`. Note: only names + descriptions are captured; bodies are NEVER bundled here, so personal Cowork workflows can't leak.
- Commands count + names + that bodies are captured (and look redacted)
- Agents count (forward-compat, may be 0)
- Keybindings captured (forward-compat, may be empty)
- CLAUDE.md captured: yes/no, char count
- Redaction stats from the script

Then say (verbatim):

> I've written the snapshot. Before I commit it, please confirm:
> (a) no real API keys / OAuth tokens visible in the snapshot
> (b) no `/Users/<your-username>` paths that should have been normalized
> (c) the CLAUDE.md content is OK to publish (it's your full global instructions)
> (d) command bodies are OK to publish (they may contain prompt logic you wrote)
> (e) settings.local.json is OK to publish (it lists your local Bash/tool permissions)
> (f) statusline config is OK to publish
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

git add snapshots/<FILENAME>
git -c commit.gpgsign=false commit -m "Refresh env snapshot for <OWNER>[<MACHINE_ID>] (YYYY-MM-DD)"

# Determine push target. If on main, push to origin main. If on a different branch, push there.
current_branch=$(git branch --show-current)
git push origin "$current_branch"
```

After push, tell the user the snapshot is live at:

```
https://raw.githubusercontent.com/<gh-owner>/<repo>/<branch>/snapshots/<FILENAME>
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
