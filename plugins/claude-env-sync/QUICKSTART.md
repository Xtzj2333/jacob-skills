# Quickstart — sync Claude Code envs with a collaborator

**Audience.** You and at least one collaborator both use Claude Code, and you want to be able to see each other's setups, compare them, and pull pieces from each other — without silent overwrites or duplicated hooks.

**How to use this doc.** Read it yourself, OR paste it into a Claude Code session and say *"Follow this end-to-end and stop only at decision points marked **YOU DECIDE**."*

**What you'll have at the end.**

1. The `claude-env-sync` plugin installed on your machine.
2. A public GitHub repo holding your published environment snapshot.
3. Your snapshot URL ready to share with your collaborator.
4. The ability to run `compare my claude env to <them>` and have your Claude actively judge each conflict, recommend an action, and apply only what you OK.
5. The ability to suggest your stuff back to your collaborator either by publishing your own snapshot they can pull from, or by drafting a GitHub issue with the specific item.

---

## One-time setup

### 1. Install the plugin

In a Claude Code session:

```
/plugin marketplace add https://github.com/Xtzj2333/jacob-skills.git
/plugin install claude-env-sync@jacob-skills
/reload-plugins
```

Verify it loaded:

```
/plugin
```

You should see `claude-env-sync` in the Installed tab. The two skills (`publish-env-snapshot`, `env-compare`) auto-load.

### 2. Create your own snapshot repo on GitHub

Your snapshot needs to live at a public (or collaborator-readable) URL on GitHub. The simplest way:

1. Create a new public GitHub repo. Name it whatever you want — `<yourname>-claude-env` is conventional.
2. Initialize it with at least a README so the default branch exists.
3. Clone it locally. A common location:

   ```bash
   cd ~
   git clone https://github.com/<your-gh-username>/<your-repo>.git
   ```

   Now you have `~/<your-repo>/` as your snapshot working directory.

You don't need any plugin scaffolding inside — just a `snapshots/` folder will be auto-created on first publish.

**YOU DECIDE:** repo name + clone location. Tell your Claude when prompted.

### 3. Publish your first snapshot

In a Claude Code session, say:

> publish my env snapshot

Your Claude will:
1. Auto-detect or ask for your snapshot identifier (your name, lowercased).
2. Auto-detect or ask for your local snapshot repo (the one you cloned in step 2).
3. Run the publisher script (snapshot format v0.4). It captures: `~/.claude/settings.json` + `settings.local.json`, the merged `mcpServers` block from `~/.claude.json` + `~/.claude/.mcp.json`, your global `~/.claude/CLAUDE.md`, installed user skills with full SKILL.md + bundled-file content (`~/.claude/skills/<name>/` — third-party skills with a `LICENSE` or `pyproject.toml` keep the SKILL.md but skip the bundle, since they should be installed the upstream way), plugin-shipped skills (metadata only — the bodies travel via the marketplace), slash command bodies, agents, keybindings, statusline config, `~/.claude/plugins/installed_plugins.json` (per-plugin version + git SHA), central reference files under `~/Claude/` (e.g., `manuscript-rules.md`), and an external CLI inventory (`uv tool list` + `brew leaves`) so the diff can flag missing binaries that MCP servers depend on. Secrets get redacted.
4. **Show you the redacted snapshot.** Eyeball it for any leaked keys or paths. The publisher also runs a defense-in-depth grep before commit.
5. Ask for your OK to commit + push.

After push, your snapshot is live at:

```
https://raw.githubusercontent.com/<your-gh-username>/<your-repo>/main/snapshots/<yourname>.json
```

Send that URL to your collaborator.

---

## Day-to-day use

### Compare your env to your collaborator's

In a Claude Code session, say:

> compare my claude env to <their-name>

OR with explicit URL:

> compare my claude env to https://raw.githubusercontent.com/.../snapshots/<them>.json

Your Claude will:

1. Fetch their snapshot.
2. Read your local environment.
3. Compute the diff (theirs-only / yours-only / both-different across hooks, MCP servers, settings, settings.local, statusline, keybindings, user skills *with body-level diffs* including bundled scripts/templates, plugin-shipped skills, command bodies, agents, CLAUDE.md, installed plugins with version pinning, central reference files, and external CLI inventory — flagging tools their machine has via `uv` or `brew` that yours doesn't).
4. Open an HTML diff report in your browser.
5. **Walk you through each diff item — with active judgment.** For every conflict, your Claude reads both versions, forms a reasoned opinion (which is more rigorous? more conservative? better-engineered for your context?) and recommends an action with a one-sentence rationale.
6. Apply only items you confirm. Backs up your prior config before any write.

Default behavior on uncertainty: **keep yours**. Claude won't recommend changing your config unless it has a concrete reason to think the other version is better for you.

### Suggest your stuff back to them

The same `env-compare` run also surfaces things YOU have that THEY don't. For each, your Claude offers:

- **(a) Publish your own snapshot** so they can run `env-compare` against you and pull what they want.
- **(b) Draft a GitHub issue body** for their repo describing the specific item, with the exact config snippet they'd add. You then paste it into a new issue at their repo.
- **(c) Skip.**

The first time you go this route, option (a) is usually best — it sets up the bidirectional pattern. After that, option (b) is good for one-off "hey try this specific thing" suggestions.

### Refresh your snapshot when your env changes

Whenever you've changed your Claude Code config (added an MCP server, edited your CLAUDE.md, installed a new plugin), re-run:

> publish my env snapshot

Same flow: capture, review, push. Your collaborator's `compare my env to <you>` will reflect whatever's live at the time they run it.

---

## Common questions

**Q: Do I need to fork my collaborator's repo?**
No. You publish to your own repo. They publish to theirs. You compare against each other's URLs. Everyone owns their own publish surface.

**Q: What if I install something they have, and later we both change it differently?**
Re-run `compare my env to <them>` — the diff reflects current state on both sides. Nothing is sticky.

**Q: What about API keys?**
Your snapshot has all keys redacted (Tavily, OpenAI, GitHub PATs, Anthropic, Bearer tokens, JWTs, etc.) plus a defense-in-depth grep before push. Each user provides their own keys via env-vars in their `~/.zshenv` (or equivalent). The plugin never asks for or transports actual key values.

**Q: What can't be synced this way?**
- Per-project `.claude/` directories (those are project-scoped).
- `~/.claude.json` runtime state (sessions, OAuth tokens, internal counters).
- Secrets — by design.
- Plugin SOURCE CODE — but if your collaborator publishes a plugin you want, you install via `/plugin install <plugin>@<their-marketplace>`. That's separate from env-sync.
- **External CLI binaries themselves.** The snapshot tells you *which* tools the other machine has (via `uv tool list` / `brew leaves`), and the diff shows the install commands — but you still run `uv tool install <name>` or `brew install <name>` on your machine to actually acquire them.
- **Third-party skill internals.** Skills whose folder contains `LICENSE` / `pyproject.toml` / `package.json` etc. are flagged as third-party — only their `SKILL.md` is captured, not the implementation files. Install third-party skills the upstream way (git clone, npm install, etc.).

**Q: Can I undo an import?**
Every import creates a backup at `~/.claude/_pre_env_compare_backup/<timestamp>/`. Restore with `cp <BACKUP_DIR>/settings.json ~/.claude/settings.json`.

**Q: Can my collaborator push to MY repo?**
No, unless you give them write access. The intended pattern is each person owns their own snapshot repo. For one-off suggestions, they open a GitHub issue against your repo (which only requires read access).

---

## What to send your collaborator

After step 3 above, you'll have your snapshot URL. Send them this single message:

> Hey, I've published my Claude Code env at:
> `https://raw.githubusercontent.com/<your-gh>/<your-repo>/main/snapshots/<yourname>.json`
>
> To set up your side:
> 1. In Claude Code: `/plugin marketplace add https://github.com/Xtzj2333/jacob-skills.git`
> 2. `/plugin install claude-env-sync@jacob-skills`
> 3. `/reload-plugins`
> 4. Then read https://github.com/Xtzj2333/jacob-skills/blob/main/plugins/claude-env-sync/QUICKSTART.md or paste it into a Claude Code session and say "follow this."
>
> When you've published your own snapshot, send me the URL and I'll add `compare my env to <yourname>` to my workflow.
