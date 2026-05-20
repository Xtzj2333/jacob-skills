---
name: env-compare
description: Fetch a collaborator's published Claude Code environment snapshot, diff it against the user's local environment, render an HTML diff report, and walk the user item-by-item through what to import — with Claude actively judging each conflict and recommending an action. Also surfaces things the local user has that the snapshot owner doesn't, and offers to publish or suggest those back. No silent stacking, no pre-deletion required, every change confirmed and backed up. Use when the user says "compare my claude env to <person>", "/env-compare", "diff my setup against jacob", "what's different between my claude and jacob's", "import jacob's env", "sync from <person>'s snapshot".
---

# env-compare

## What this skill does

1. Fetches a published environment snapshot (HTTPS URL or local path).
2. Reads the user's local `~/.claude/` environment.
3. Computes a structured diff and renders an HTML report.
4. **For each diff item, Claude actively judges**: reads both versions, forms a reasoned opinion on which is better for this user's context, and recommends an action with a one-sentence rationale.
5. Walks the user through the diff, applying chosen items to actual config files with backup.
6. **Surfaces items the local user has that the snapshot owner doesn't** and offers to publish those back so the owner can pull them.

## Core principle: judge, don't just enumerate

The previous version of this skill listed options ("(1) take theirs (2) keep yours (3) show full diff") and made the user do the thinking. The user explicitly asked for the opposite: **Claude should read both, form an opinion on which is better, and present a recommendation with reasoning.** The user can override, but the default behavior is "I read both, here's what I'd do and why."

Bias toward **conservatism**: when Claude can't tell which is better, default to "keep yours" — never apply someone else's config silently or as the recommended path when uncertain.

## When to use

User wants to see what's in a collaborator's Claude Code setup and selectively pull pieces in. Bidirectional: also catches things the user has that the collaborator might want. NOT for blanket "install everything" — that pattern leads to silent stacking.

## Inputs the skill needs (ask if unset)

- **`<SNAPSHOT_URL>`** — URL or local path to the snapshot JSON. Common form:

  `https://raw.githubusercontent.com/<gh-owner>/<repo>/main/snapshots/<owner>.json`

  If the user just says "compare to jacob," try `https://raw.githubusercontent.com/Xtzj2333/jacob-skills/main/snapshots/jacob.json` and confirm with the user before fetching.

- **`<BACKUP_DIR>`** — where to back up the user's pre-import config. Default: `~/.claude/_pre_env_compare_backup/<timestamp>/`.

## Procedure

### Step 1 — Fetch snapshot, compute diff

```bash
TS=$(date +%Y%m%d_%H%M%S)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/compare_env.py \
    --snapshot <SNAPSHOT_URL> \
    --out /tmp/env_diff_${TS}.json \
    --html /tmp/env_diff_${TS}.html
```

If the script errors (URL 404, malformed JSON), report the error and ask the user to verify the URL.

### Step 2 — Open the HTML report and summarize

```bash
open /tmp/env_diff_${TS}.html
```

Then summarize in chat in 5–8 lines, e.g.:

> Diff vs `<owner>` (`<machine_id>`)'s snapshot (format vN, generated YYYY-MM-DD, their claude version: VV):
> - Hook events differing: N
> - MCP servers — theirs only: N · yours only: N · both, different: N
> - User-level skills (`~/.claude/skills/`): theirs only N · yours only N
> - Plugin-shipped skills: theirs only N · yours only N (note: gap usually closed by enabling the right plugin, not copying files)
> - Cowork-session skills (v0.7+): theirs only N (of which N are `cowork-only` and unreachable until the owner publishes) · yours only N
> - Commands: theirs only N · yours only N · both-but-body-diverged N
> - Agents (forward-compat): theirs only N · yours only N
> - settings.local.json: identical / differs (Bash + tool permission patterns)
> - statusline config: identical / differs
> - keybindings: identical / differs / both-empty
> - Settings keys differing: N (names: …)
> - Global CLAUDE.md: identical / differs (theirs T chars vs yours M chars)
> - Central reference files (~/Claude/): N identical · N differ · N only-one-side
> - Installed plugins: N same · N version-diff · N sha-only-diff · N theirs-only · N yours-only

### Step 3 — Walk through each diff bucket with active judgment

**This is the heart of the skill.** For each non-empty diff bucket, do NOT present a generic options menu. Instead:

1. Read both versions (theirs + yours) for the specific item.
2. Form an opinion: which is better for THIS user's context, and why? Consider:
   - **Clarity**: which version is more descriptive / less likely to confuse a future reader?
   - **Conservatism**: which is the safer default — does one stack with existing behavior in a problematic way?
   - **Cost**: does taking theirs increase token spend, runtime, or operational complexity?
   - **Security**: does either version expose a path or capability the other doesn't?
   - **User context**: what do you know about this user from their CLAUDE.md, their installed skills, their prior decisions? Match the recommendation to that context.
3. Present in this shape:

   > **`<item-name>`**
   > Theirs: `<one-line summary>`
   > Yours: `<one-line summary>`
   >
   > **My read:** `<2-3 sentences with the actual reasoning>`. **Recommend:** `<keep yours / take theirs / merge / show full diff>` because `<one sentence>`.
   >
   > Apply that, override, or skip?

4. If user says "apply that," do it. If "override," ask what they want instead. If "skip," move on.
5. If you genuinely can't tell which is better — say so explicitly and default-recommend "keep yours" with that reasoning.

#### What "apply" means per bucket

| Bucket | Apply = |
|---|---|
| Hook events | Edit `~/.claude/settings.json` `hooks.<event>` to the chosen value (replace, append, or no-op). |
| MCP servers (theirs-only / both-different) | Edit either `~/.claude.json` `mcpServers` OR `~/.claude/.mcp.json` `mcpServers` to add or replace the chosen entry. Tell user any `${VAR}` placeholders that need to be set in `~/.zshenv`. **Both files exist; prefer `~/.claude/.mcp.json` for new entries unless the user explicitly wants the entry in `~/.claude.json`.** |
| Settings keys | Edit `~/.claude/settings.json` to set the chosen key to the chosen value. **Special-case `enabledPlugins` and `extraKnownMarketplaces`: union-merge by default, ask if conflict on the same plugin.** |
| settings.local.json | This is per-machine local permissions. Don't mass-copy; show specific entries (e.g. `Bash(gh repo *)`) and recommend item-by-item — usually keep yours since these reflect your actual workflow. |
| statusline config | **Don't hand-edit unless the user asks.** `~/.config/ccstatusline/settings.json` is owned by `ccstatusline` itself, which ships a TUI. The canonical setup is `npx -y ccstatusline@latest` (no stdin pipe) → configure widgets → pick "Install to Claude Code settings"; the TUI writes BOTH this file AND `~/.claude/settings.json`'s `statusLine` block. Recommend that flow first. Whole-file blob copy is a fallback if the user explicitly prefers a literal copy. |
| keybindings | Whole-file blob (`~/.claude/keybindings.json`). Same approach. |
| User-level skills (theirs-only) | Check the snapshot record's `upstream` field first (v0.5+). If `install_kind: plugin-marketplace`, recommend the `/plugin marketplace add <handle>` flow. If `install_kind: git-clone`, the diff already exposes a ready `install_command` string — use it. If the skill is captured (`bundle_status: captured`), it's Jacob-authored — paste the body from `skills_user_bodies.only_theirs` into `~/.claude/skills/<name>/`, OR (better) suggest the owner promote it into the marketplace via `sync-cowork-skill` so it becomes a one-step `/plugin install` going forward. Only fall back to "ask the owner to promote" when none of these apply (v0.4 or earlier snapshot with no upstream metadata for a third-party skill). |
| User-level skills (both-different) | If both sides have `upstream.sha` and they differ, the diff sets `upstream_sha_drift: true` — recommend a `git -C ~/.claude/skills/<name> pull` on the older side. Otherwise compare the SKILL.md bodies as usual. |
| Plugin-shipped skills (theirs-only) | The `source` field tells you which plugin: e.g., `plugin:apa-format@jacob-skills`. Recommend `/plugin install <plugin>@<marketplace>`. |
| Cowork-session skills (theirs-only) | Read the `published_via` field on the entry. **`anthropic-builtin`** → no action; the collaborator will get it by installing Cowork. **`plugin:<p>@<mp>`** → recommend `/plugin install <p>@<mp>` (same path as plugin-shipped skills). **`cowork-only`** → the skill is author-local and bodies are intentionally NOT bundled. The only retrieval paths are: (a) ask the snapshot owner to publish it via `sync-cowork-skill <name>` so it becomes installable, or (b) accept that it's unreachable for now. Never recommend file-copying — Cowork session paths are UUID-based per machine and writing into someone else's Cowork session is fragile. |
| Commands (theirs-only) | Same as user-level skills — usually plugin-shipped via the same mechanism, OR can be copied as a single `.md` file into `~/.claude/commands/`. If you copy: read the snapshot's `body` field, write to `~/.claude/commands/<name>.md` with frontmatter + body. |
| Commands (body-diverged on both sides) | Show side-by-side body. If user wants theirs, overwrite `~/.claude/commands/<name>.md`. If user wants merge, show specific lines and have user direct. **Default: keep yours** — body divergence usually means intentional local edits. |
| Agents (theirs-only) | Same single-file pattern as commands. |
| CLAUDE.md | If both differ: offer to render a side-by-side diff to a temp file (Claude can produce a markdown 3-column table: section / theirs / yours), then let user pick replace / append / skip. Never silently overwrite. |

### Step 4 — Backup before any write

The first time you're about to modify any file in `~/.claude/`, create the backup dir and copy current state:

```bash
mkdir -p <BACKUP_DIR>
cp ~/.claude/settings.json       <BACKUP_DIR>/settings.json       2>/dev/null
cp ~/.claude/settings.local.json <BACKUP_DIR>/settings.local.json 2>/dev/null
cp ~/.claude.json                <BACKUP_DIR>/claude.json         2>/dev/null
cp ~/.claude/.mcp.json           <BACKUP_DIR>/mcp.json            2>/dev/null
cp ~/.claude/CLAUDE.md           <BACKUP_DIR>/CLAUDE.md           2>/dev/null
cp ~/.claude/keybindings.json    <BACKUP_DIR>/keybindings.json    2>/dev/null
cp -R ~/.claude/commands         <BACKUP_DIR>/commands            2>/dev/null
cp -R ~/.claude/agents           <BACKUP_DIR>/agents              2>/dev/null
cp ~/.config/ccstatusline/settings.json <BACKUP_DIR>/ccstatusline.json 2>/dev/null
```

Tell the user where the backup is. Include restore instructions.

### Step 5 — Surface yours-only items (the suggest-back flow)

After walking through theirs-only and both-different items, look at the diff for "yours only" items — things the user has that the snapshot owner doesn't. These are candidates to **suggest back** to the snapshot owner.

For each yours-only item that's non-trivial (a real hook, a real MCP server, a real settings key with a meaningful value), say:

> **You have something `<owner>` doesn't:** `<item-name>` (`<one-line summary>`).
>
> Want to:
> (a) **Publish your own snapshot** so `<owner>` can run `env-compare` against you and pull this — I'll invoke `publish-env-snapshot` to do it. Best if you have multiple things to share.
> (b) **Draft a GitHub issue body** I'll write a complete issue for `<owner>`'s repo (https://github.com/...) describing this one item with the exact config snippet they'd add. You then open the issue manually.
> (c) **Skip** — you don't want to suggest this back.

For (a): invoke the `publish-env-snapshot` skill if you've established the user has their own publish target. If not, walk them through the one-time setup (create their own GitHub repo, clone it, then publish).

For (b): write a markdown issue body to `/tmp/suggest_<item>_<ts>.md`, show it to the user, give them the URL to open the issue (e.g., `https://github.com/<gh-owner>/<repo>/issues/new`), and instruct them to paste the body in.

Skip yours-only items that are clearly personal (e.g., user-specific MCP server with hardcoded paths) or trivial (settings keys that match defaults).

### Step 6 — Summary at the end

Once the user has stepped through every bucket they want to act on, summarize:

- Files modified + line counts
- Backup location
- Env-vars they need to set if they imported MCP servers
- Restart Claude Code to pick up settings/MCP changes; `/reload-plugins` for plugin-side changes
- If they chose to publish their own snapshot, the URL where it now lives
- Any pending suggest-back GitHub issues they're about to open

## What this skill does NOT do

- Does NOT silently apply anything. Every change has Claude's reasoning + user's explicit OK.
- Does NOT remove anything from the user's env unless the user explicitly says so.
- Does NOT install plugins automatically — only suggests which plugin install command to run.
- Does NOT modify `~/.claude.json`'s non-mcpServers fields (those are runtime state).
- Does NOT push anything to GitHub unless invoked through `publish-env-snapshot` (which has its own confirm gates).

## Failure modes to avoid

| Mode | Avoid by |
|---|---|
| Recommending take-theirs by default when unsure | Always default-recommend "keep yours" when Claude can't tell which is better |
| Generic options-list output instead of judgment | Step 3 — every diff item gets Claude's read + recommendation, not a menu |
| Modifying user's config without backup | Step 4 — always before first write |
| Stacking hooks (the original sin) | Always read both, recommend explicit replace OR explicit no-op; never silently merge |
| Importing an MCP without warning about env-vars | Always extract `${VAR}` placeholders, list them in the apply step |
| Treating skills/commands as installable items by file copy | They're plugin-shipped; recommend `/plugin install`, not file ops |
| Suggesting back trivially-different items | Filter yours-only by whether the difference is meaningful, not just present |
| Hand-editing a tool-owned config when the tool has its own setup CLI | Before recommending JSON/YAML edits, ask: does the divergent file belong to a tool that ships its own configurator (TUI, `<tool> setup`, `<tool> init`)? If yes, the canonical fix on the receiving machine is to run that tool — it usually writes multiple config files in one flow and stays in sync with the tool's schema. Examples: `ccstatusline` (TUI), `gh auth login`, `brew bundle`, `uv tool install`. Hand-edits are a fallback for diagnosis, not the first recommendation. |
