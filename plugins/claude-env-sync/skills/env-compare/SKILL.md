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

Then summarize in chat in 4–5 lines, e.g.:

> Diff vs `<owner>`'s snapshot (generated YYYY-MM-DD):
> - Hook events differing: N
> - MCP servers — theirs only: N · yours only: N · both, different: N
> - Skills they have you don't: N (sample names: …)
> - Commands they have you don't: N (sample names: …)
> - Settings keys differing: N (names: …)
> - Global CLAUDE.md: identical / differs (theirs T chars vs yours M chars)

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
| MCP servers (theirs-only / both-different) | Edit `~/.claude.json` `mcpServers` to add or replace the chosen entry. Tell user any `${VAR}` placeholders that need to be set in `~/.zshenv`. |
| Settings keys | Edit `~/.claude/settings.json` to set the chosen key to the chosen value. **Special-case `enabledPlugins` and `extraKnownMarketplaces`: union-merge by default, ask if conflict on the same plugin.** |
| Skills (theirs-only) | Skills typically ship inside plugins. Recommend `/plugin install <plugin-name>@<marketplace-name>` rather than copying files. If you can identify which plugin in the snapshot owner's marketplace ships the skill, name it. If not, suggest the user ask the snapshot owner. |
| Commands (theirs-only) | Same pattern as skills. |
| CLAUDE.md | If both differ: offer to render a side-by-side diff to a temp file (Claude can produce a markdown 3-column table: section / theirs / yours), then let user pick replace / append / skip. Never silently overwrite. |

### Step 4 — Backup before any write

The first time you're about to modify any file in `~/.claude/`, create the backup dir and copy current state:

```bash
mkdir -p <BACKUP_DIR>
cp ~/.claude/settings.json <BACKUP_DIR>/settings.json 2>/dev/null
cp ~/.claude.json <BACKUP_DIR>/claude.json 2>/dev/null
cp ~/.claude/CLAUDE.md <BACKUP_DIR>/CLAUDE.md 2>/dev/null
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
