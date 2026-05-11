---
name: env-compare
description: Fetch a collaborator's published Claude Code environment snapshot, diff it against the user's local environment, render an HTML diff report, and walk the user item-by-item through what to import. No silent stacking, no pre-deletion required — every change is shown and confirmed. Use when the user says "compare my claude env to <person>", "/env-compare", "diff my setup against jacob", "what's different between my claude and jacob's", "import jacob's env", "sync from <person>'s snapshot".
---

# env-compare

## What this skill does

1. Fetches a published environment snapshot (HTTPS URL or local path).
2. Reads the user's local `~/.claude/` environment.
3. Computes a structured diff — `theirs-only`, `yours-only`, `both-different` — for hooks, MCP servers, settings, skills, slash commands, and the global CLAUDE.md.
4. Renders an HTML diff report and opens it for the user.
5. Walks the user item-by-item asking what to import. Applies chosen items to the user's actual config files, with a backup of the prior config.

## When to use

User wants to see what's in a collaborator's Claude Code setup and selectively pull pieces in. NOT for blanket "install everything" — that pattern leads to stacked hooks and silent surprises. This skill is the considered-and-confirmed path.

## Inputs the skill needs (ask if unset)

- **`<SNAPSHOT_URL>`** — URL or local path to the snapshot JSON. Common form:
  
  `https://raw.githubusercontent.com/<gh-owner>/<repo>/main/snapshots/<owner>.json`
  
  If the user just says "compare to jacob," try the conventional URL `https://raw.githubusercontent.com/Xtzj2333/jacob-skills/main/snapshots/jacob.json` and confirm with the user.

- **`<BACKUP_DIR>`** — where to back up the user's pre-import config. Default: `~/.claude/_pre_env_compare_backup/<timestamp>/`.

## Procedure

### Step 1 — Run the diff script

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/compare_env.py \
    --snapshot <SNAPSHOT_URL> \
    --out /tmp/env_diff_<timestamp>.json \
    --html /tmp/env_diff_<timestamp>.html
```

If the script errors (URL 404, malformed JSON), report the error and ask the user to check the URL.

### Step 2 — Open the HTML report

```bash
open /tmp/env_diff_<timestamp>.html
```

Then summarize the diff in chat in 4–5 lines:

> Diff vs `<owner>`'s snapshot (generated YYYY-MM-DD):
> - Hook events differing: N
> - MCP servers — theirs only: N · yours only: N · both, different: N
> - Skills they have you don't: N (names: …)
> - Commands they have you don't: N (names: …)
> - Settings keys differing: N (names: …)
> - Global CLAUDE.md: identical / differs (theirs T chars vs yours M chars)

### Step 3 — Walk through each diff category, asking the user

For **each non-empty diff bucket**, ask the user item-by-item what to do. Don't batch the question — give them one decision at a time so they can think.

#### 3a. Hook events differing
For each hook event (Stop, Notification, PermissionRequest, etc.) where theirs ≠ yours:

> Hook event `<event>`:
> - Theirs: `<one-line-summary-of-theirs>`
> - Yours: `<one-line-summary-of-yours>`
>
> Options: (1) replace yours with theirs · (2) merge — append theirs to yours (will fire both) · (3) keep yours · (4) show me the full JSON for both
>
> Which?

If user picks (1), edit `~/.claude/settings.json` so the `hooks.<event>` array is theirs.
If user picks (2), append theirs's hook entries to the user's existing `hooks.<event>` array.
If user picks (3), no change.
If user picks (4), show `<theirs>` and `<yours>` JSON inline; re-ask.

#### 3b. MCP servers only-in-theirs
For each:

> They have an MCP server `<name>` that you don't:
> - command: `<theirs.command>`
> - env vars expected: `<list of ${VAR} placeholders>`
>
> Install? (1) yes — add to your `~/.claude.json` mcpServers · (2) skip · (3) show me their full config

If yes: add the entry to the user's `~/.claude.json`'s `mcpServers` block. If env values are `${VAR}` placeholders, also remind the user to set those env vars in their `~/.zshenv`.

#### 3c. MCP servers only-in-yours
For each, just inform — no action:

> You have an MCP server `<name>` that they don't. No change unless you want to remove it (out of scope for this skill).

#### 3d. MCP servers both, different
For each:

> MCP server `<name>` is configured differently. Theirs: `<one-line>`. Yours: `<one-line>`.
> Options: (1) replace yours with theirs (your env-var values stay if `${VAR}`-style) · (2) keep yours · (3) show full diff

#### 3e. Settings keys differing
For each safe-to-share top-level settings key:

> Settings key `<key>` differs.
> - Theirs: `<value or summary>`
> - Yours: `<value or summary>`
>
> Options: (1) take theirs · (2) keep yours · (3) show me both in full

If take-theirs: edit `~/.claude/settings.json` to set that key to theirs's value. **Exception:** `enabledPlugins` and `extraKnownMarketplaces` should be merged (union the dicts), not replaced — confirm with the user if there's a conflict on the same plugin.

#### 3f. Skills only-in-theirs
For each skill name they have you don't:

> They have skill `<name>` (description: `<one-liner from the snapshot>`).
> Options: (1) install via plugin marketplace if you know which plugin ships it · (2) skip · (3) ask me where this skill comes from
>
> Note: skills typically ship inside plugins. Installing one usually means `/plugin install <plugin-name>@<marketplace-name>`. The snapshot doesn't always tell you which plugin ships a given skill — you may need to ask the snapshot owner.

#### 3g. Commands only-in-theirs
Same pattern as skills — slash commands also typically ship via plugins.

#### 3h. Global CLAUDE.md
If differs:

> Their global CLAUDE.md is `<theirs.length>` chars; yours is `<yours.length>` chars.
> Options:
> (1) Show me the full text side-by-side in a new file
> (2) Replace yours with theirs (I'll back up yours first to `<BACKUP_DIR>/CLAUDE.md`)
> (3) Append theirs to the bottom of yours (mark as "## Imported from <owner>'s CLAUDE.md")
> (4) Skip — I'll handle merging by hand

### Step 4 — Backup before any write

The first time you're about to modify any file in `~/.claude/`, create the backup dir and copy the current state:

```bash
mkdir -p <BACKUP_DIR>
cp ~/.claude/settings.json <BACKUP_DIR>/settings.json
cp ~/.claude.json <BACKUP_DIR>/claude.json
cp ~/.claude/CLAUDE.md <BACKUP_DIR>/CLAUDE.md  # if exists
```

Tell the user where the backup is. If anything goes wrong, restore is `cp <BACKUP_DIR>/settings.json ~/.claude/settings.json`.

### Step 5 — Summary at the end

Once the user has stepped through all diff buckets, tell them what changed:

- Files modified + line counts
- Which env-vars they need to set if they imported MCP servers
- Restart Claude Code to pick up settings/MCP changes; `/reload-plugins` for plugin-side changes

## What this skill does NOT do

- Does NOT silently apply anything. Every change has an explicit user decision.
- Does NOT remove anything from the user's env unless the user explicitly says so.
- Does NOT install plugins — only suggests which plugin install command might be needed.
- Does NOT modify `~/.claude.json`'s non-mcpServers fields (those are runtime state, not config).

## Failure modes to avoid

| Mode | Avoid by |
|---|---|
| Modifying user's config without backup | Step 4 — always create backup before first write |
| Stacking hooks (the original sin) | Always offer "replace" as an explicit option, default behavior is "show me both, then ask" |
| Importing an MCP server without warning user about required env-vars | Always extract `${VAR}` placeholders and tell user to set them |
| Pre-deleting user's config to make room | Never. Always add/replace explicitly with user's OK |
| Treating skills/commands as installable items | They're typically plugin-shipped; suggest `/plugin install ...` rather than copying files |
