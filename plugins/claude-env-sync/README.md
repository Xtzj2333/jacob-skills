# claude-env-sync

A two-skill plugin for **publishing** your Claude Code environment as a redacted snapshot, and on the import side, **interactively diffing** a published snapshot against your own environment and picking what to take — with Claude actively judging each conflict and recommending an action.

**Looking for the end-to-end how-to?** See [QUICKSTART.md](./QUICKSTART.md) — pasteable into a Claude Code session.

Designed for **bidirectional** collaboration: each user publishes their own snapshot to their own repo. Each user can compare against the other and pull what they want. No silent stacking, no fork-and-PR dance, no central server.

---

## How it works

Bidirectional flow: each user has their own snapshot repo and can compare against the other.

```
   Your machine                                     Their machine
   ───────────────                                  ───────────────
   "publish my env snapshot"                        "publish my env snapshot"
        ↓                                                ↓
   redact + write                                   redact + write
   <your-repo>/snapshots/<you>.json                 <their-repo>/snapshots/<them>.json
        ↓ git push                                       ↓ git push
   ┌──────────────────────┐                         ┌──────────────────────┐
   │   GitHub (theirs)    │ ←── you fetch ──────    │   GitHub (yours)     │
   └──────────────────────┘                         └──────────────────────┘
        ↑ they fetch                                      ↑ you fetch when running
                                                            "compare my env to <them>"

   "compare my env to <them>"
        ↓
   fetch their snapshot, diff vs your local, render HTML report
        ↓
   for each diff item:
     read both → form opinion → recommend action with rationale → user OK → apply with backup
        ↓
   for each yours-only item:
     "you have <X> they don't — publish it / draft a GitHub issue / skip"
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
