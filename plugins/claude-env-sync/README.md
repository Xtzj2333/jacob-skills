# claude-env-sync

A two-skill plugin for **publishing** your Claude Code environment as a redacted snapshot, and on the import side, **interactively diffing** a published snapshot against your own environment and picking what to take.

This replaces the older "ship a plugin that adds hooks/MCPs to everyone's machine" pattern, which causes silent stacking and forces collaborators to manually delete their own things first. The snapshot+diff pattern keeps every change explicit and confirmed.

---

## How it works

```
        Jacob's machine                                  Tony's machine
  ┌─────────────────────────┐                  ┌──────────────────────────────┐
  │ /publish-env-snapshot   │   git push       │ /env-compare                 │
  │   ↓                     │                  │   ↓                          │
  │ scripts/publish_snap... │                  │ scripts/compare_env.py       │
  │   ↓ redact secrets,     │                  │   ↓ fetch theirs, read mine, │
  │   normalize home paths  │                  │   compute diff               │
  │   ↓                     │                  │   ↓                          │
  │ snapshots/jacob.json    │ ──── GitHub ───→ │ HTML diff report opens       │
  │   ↓                     │                  │   ↓                          │
  │ git commit + push       │                  │ walk Tony item-by-item       │
  └─────────────────────────┘                  │ apply chosen items, w/ backup│
                                               └──────────────────────────────┘
```

---

## Installing

```
/plugin marketplace add https://github.com/Xtzj2333/jacob-skills.git
/plugin install claude-env-sync@jacob-skills
/reload-plugins
```

---

## Using it

### Publish your environment (snapshot owner)

In any Claude Code session, say:

> publish my env snapshot

Claude will:
1. Run the publisher against your `~/.claude/`
2. Show you what was captured + a redaction summary
3. Ask before committing
4. Push to your marketplace repo on your OK

### Import / compare against someone else's snapshot

In any Claude Code session, say:

> compare my claude env to jacob

Claude will:
1. Fetch the snapshot at the conventional URL (or ask you for the URL)
2. Diff it against your `~/.claude/`
3. Open an HTML report in your browser
4. Walk you through each diff category, applying only what you say yes to

---

## What's captured in a snapshot

| Surface | What's captured | What's redacted |
|---|---|---|
| `~/.claude/settings.json` | All top-level keys | String values whose key name contains `api_key` / `token` / `secret` / `password` / `auth` |
| `~/.claude.json` | Only `mcpServers` block | API key values; `${VAR}` placeholders preserved |
| `~/.claude/CLAUDE.md` | Full text | Common API-key shapes; home paths normalized to `${HOME}` |
| `~/.claude/skills/<name>/` | Skill name + 1-line description from frontmatter | Full skill body NOT published |
| `~/.claude/commands/<name>.md` | Command name + 1-line description | Full command body NOT published |

Conservative redaction: when in doubt, redact. The snapshot is human-readable JSON; you're expected to eyeball it before pushing.

---

## What's NOT captured

- `~/.claude.json` fields other than `mcpServers` (it's a runtime state file with OAuth tokens, session caches, etc.)
- `~/.claude/sessions/`, `~/.claude/cache/`, `~/.claude/downloads/`
- `~/.claude/plugins/` (those are auto-managed by Claude Code from your marketplace settings)
- Per-project `.claude/` directories
- Anything in `~/.config/claude-chime/` or other local user config

---

## Security notes

- **The snapshot is intended to be public.** It goes in your marketplace repo. Anyone who can read your repo can read your snapshot. That's the design.
- The redactor is conservative but not perfect. **Always read the snapshot before committing.** The publish skill enforces this — it shows you the snapshot and asks for explicit OK before pushing.
- A defense-in-depth grep runs before commit looking for any string that LOOKS like a key the redactor missed.
- The importer side never modifies your config without a backup first.

---

## Updating

When you change your Claude Code env (new MCP server, edit your CLAUDE.md, install a new skill, etc.), re-run `publish my env snapshot`. Your collaborator can re-run `compare my env to <you>` whenever — the diff reflects whatever's currently published.

If you want auto-publishing on every change, you could wire `publish_snapshot.py` into a Stop hook or a cron job, but that's not built in by design — manual review of the snapshot is the safety gate.
