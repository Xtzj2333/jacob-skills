# Setting up Jacob's skills for collaborators

**Audience.** Jacob's research collaborators (e.g., Tony) who want access to the 6 skills Jacob authors and maintains: `research-27`, `citation-deepening`, `source-quality-check`, `commented-edit-roundtrip`, `revision-queue`, `tony-github-push`.

**How to use this document.** You can read it yourself and follow the steps manually, or paste this entire document into a Claude Code session and say "Follow this end-to-end and stop only at decision points marked **YOU DECIDE**."

**Companion doc.** For a concise summary of what each skill actually *does* (what / how / when / why), see [SKILLS_OVERVIEW.md](./SKILLS_OVERVIEW.md) in this same repo. You can read it before or after this setup — they're independent.

**Outcome by the end.**

1. All 6 skills installed in your Claude Code (CLI).
2. The same 6 skills installed in Claude Cowork (Desktop GUI), so you have parity across both surfaces.
3. `/focus` mode enabled in Claude Code.
4. Your own configuration values (if you push to a manuscript repo, the `tony-github-push` values) set in your global CLAUDE.md.
5. A clear update workflow: when Jacob pushes new versions of his skills, you pull them with one command on each surface.
6. A clear source-of-truth boundary: you read Jacob's skills freely, but you never push edits to his repo.

---

## Why this setup exists (background, optional reading)

Jacob authors his skills in Claude Code (CLI). He needs the same skills accessible in Claude Cowork (Desktop GUI), because Cowork's chat surface is where he often does research conversations. Cowork has its own plugin registry, separate from `~/.claude/skills/`, so symlinks don't bridge the two surfaces.

The only reliable cross-surface sync mechanism (for personal Anthropic plans, as of 2026-05) is a **public GitHub plugin marketplace**. Jacob's marketplace lives at `Xtzj2333/jacob-skills`. Both Claude Code and Cowork can install plugins from it.

---

## Prerequisites

- macOS or Linux
- [Claude Code CLI](https://claude.com/claude-code) installed and working
- Claude Desktop app installed, with Cowork access on your Anthropic plan
- A GitHub account (read-only access to public repos is enough — you'll never push to Jacob's repo)
- (Optional) `pandoc` + TinyTeX if you ever want to render docs locally

---

## Part 1 — Install jacob-skills in Claude Code

Jacob's skills are bundled as 6 plugins in a public marketplace at `Xtzj2333/jacob-skills`.

### 1.1 Add the marketplace

In a Claude Code session, run:

```
/plugin marketplace add https://github.com/Xtzj2333/jacob-skills.git
```

**Use the full HTTPS URL with the `.git` suffix.** The shorthand `Xtzj2333/jacob-skills` defaults to SSH and will fail with "Permission denied (publickey)" unless you already have GitHub SSH keys configured.

Expected output: `Successfully added marketplace: jacob-skills`.

### 1.2 Install each plugin

Run each command on its own line. Do **not** paste them as a single block — Claude Code's slash-command parser will treat the entire block as arguments to the first command.

```
/plugin install research-27@jacob-skills
/plugin install citation-deepening@jacob-skills
/plugin install source-quality-check@jacob-skills
/plugin install commented-edit-roundtrip@jacob-skills
/plugin install revision-queue@jacob-skills
/plugin install tony-github-push@jacob-skills
```

Each install opens a small interactive scope picker. **Pick "User scope"** (the default — applies across all your projects, lives in `~/.claude/plugins/`).

### 1.3 Reload

```
/reload-plugins
```

Output may say something like `7 plugins · 0 skills · ...` — the "0 skills" is a counter wording quirk, not a problem. Verify by typing `/research-27` and confirming autocomplete offers it. Skills now appear with namespaces, e.g., `research-27:research-27`.

### 1.4 Quick test

In Claude Code, type `/research-27` and press Enter (or use it in a sentence). It should fire. Or run `/plugin list` and verify all 6 jacob-skills plugins are listed.

---

## Part 2 — Install jacob-skills in Claude Cowork

Cowork's plugin registry is **separate** from Claude Code's. You install separately on each surface, even though it's the same marketplace.

### 2.1 Open the personal plugins panel

1. Open Claude Desktop.
2. Click the **Cowork** tab at the top of the window.
3. Click **Customize** in the left sidebar.
4. Hover over **Personal plugins** in the sidebar — a `+` button appears next to the heading.

### 2.2 Add the marketplace

1. Click the `+` next to **Personal plugins**.
2. A small menu appears with **Browse plugins** and **Create plugin**. Hover **Create plugin** — a submenu opens.
3. In the submenu, click **Add marketplace**.
4. Paste: `Xtzj2333/jacob-skills` (Cowork's UI accepts the `owner/repo` shorthand here, unlike Claude Code).
5. Confirm.

The marketplace will appear and you'll see all 6 plugins listed.

### 2.3 Install each plugin

For each of these, click the `+` button to install:

- research-27
- citation-deepening
- source-quality-check
- commented-edit-roundtrip
- revision-queue
- tony-github-push

You'll see each appear under **Personal plugins** in the left sidebar.

### 2.4 Verify

Open a fresh Cowork conversation and say:

> research 27 a quick test topic

It should fire research-27 and start producing the output specified by the skill (a citation-rich brief). If it doesn't, try the explicit form `/research-27`.

---

## Part 3 — Configure your manuscript-push values (optional)

> **2026-05-10 update.** The previous `USER_NAME` env-var has been retired. Three skills (`revision-queue`, `commented-edit-roundtrip`, `citation-deepening`) used to prefix working files with `${USER_NAME}_` — that's gone. Filenames are now resolved per-*project* via the new `project-filename` skill (`todos [<shorthand>].md`, etc.). Nothing for you to configure on this front — your Claude session figures out the shorthand on first use of a project and reuses it after that. See [CHANGELOG.md](./CHANGELOG.md) for the full migration note.

The `tony-github-push` skill reads three values pointing at a manuscript repo. The skill is named "tony-github-push" for historical reasons, but the values are configurable — it pushes to whatever you configure. **You only need this section if you use the `tony-github-push` skill.**

### 3.1 Open or create your global CLAUDE.md

The file is at `~/.claude/CLAUDE.md`. If it doesn't exist, create it.

### 3.2 Add the manuscript-push configuration

Append this section (adjust values to your repo):

```markdown
## Skill configuration (manuscript-push)

### Manuscript-push configuration (used by `tony-github-push`)

If you use the `tony-github-push` skill, set these to YOUR manuscript repo and branch (NOT Jacob's). The skill is named "tony-github-push" but the parameters are configurable — it pushes to whatever you set here.

- `MANUSCRIPT_DIR`: <name of your local manuscript subdirectory, e.g., `manuscript/`>
- `MANUSCRIPT_REMOTE`: <your manuscript repo URL, e.g., `https://github.com/your-name/your-manuscript`>
- `MANUSCRIPT_BRANCH`: <your branch, e.g., `main`>

Trigger phrase: "tony github push" / `/tony-github-push`. Skill scope: stage + commit + push exactly the configured directory's working tree, force-push on conflict.
```

### 3.3 Save

The skill picks up these values on next invocation.

### 3.4 Migrating an older project

If you have a project with files from the pre-2026-05-10 convention (`tony_todos.md`, `tony_actions.md`, etc.), rename them once: e.g., `tony_todos.md` → `todos [<your-project-shorthand>].md`. Pick any short, memorable tag for `<your-project-shorthand>` (Claude can help). After the rename, no further configuration is needed — `project-filename` detects the shorthand from the filenames themselves.

---

## Part 4 — Enable `/focus` mode in Claude Code

Focus mode hides intermediate output (tool calls and inter-tool text). You see only the final response Claude produces in each turn. Jacob uses it to keep the terminal tidy on multi-step work.

In a Claude Code session, run:

```
/focus
```

Toggle off with the same command.

If your version of Claude Code doesn't recognize `/focus`, run `/help` and search for "focus" in the listed commands. As a fallback, the setting may live in `~/.claude/settings.json` under a key like `focusMode`.

---

## Part 5 — Pulling Jacob's updates when he pushes new versions

Jacob iterates on his skills. When he pushes a new version, you have to pull on each surface (they don't auto-sync).

### Claude Code

```
/plugin update jacob-skills
```

This re-pulls the marketplace metadata and refreshes any installed plugins.

### Claude Cowork

1. Customize → Personal plugins → click on the marketplace name (`jacob-skills`) or any plugin under it.
2. Look for an **Update** or **Refresh** button on the marketplace detail page.
3. If no update button is visible: remove and re-add the marketplace (Customize → Personal plugins → click the marketplace → Remove, then re-add via the steps in Part 2.2).

Update both surfaces when Jacob pushes a substantive change.

---

## Part 6 — Source-of-truth boundary (READ-ONLY for Jacob's repo)

**This is the most important rule in this document.** Jacob's `Xtzj2333/jacob-skills` repo is HIS source of truth. You have read access only.

### What you may do

- **Read** all skill files freely. Inspect, study, copy patterns into your own work.
- **Use** the skills in your own Claude Code and Cowork sessions however you like.
- **Experiment locally.** If you want to modify a skill's behavior on your own machine, you can edit the cached files at `~/.claude/plugins/cache/jacob-skills/<plugin>/<commit-hash>/skills/<skill>/SKILL.md`. Note: these local edits will be **overwritten** the next time you run `/plugin update jacob-skills`. They are not durable.
- **Suggest changes** to Jacob via:
  - Email or message
  - A GitHub issue at `https://github.com/Xtzj2333/jacob-skills/issues`
  - A pull request from your own fork (Jacob will review and merge if appropriate)

### What you may NOT do

- **Do NOT push to `Xtzj2333/jacob-skills`.** Even if you somehow have write access, do not push. Jacob's repo is his source of truth — collaborator pushes can stomp his pending work and confuse the version history.
- **Do NOT instruct your Claude Code session to "git push"** against any clone of Jacob's repo on your filesystem. If you have a local clone for reference, treat it as read-only.
- **Do NOT modify the installed plugin cache and assume changes persist** — they don't.

### If you want a durable fork

Fork `Xtzj2333/jacob-skills` to your own GitHub account (one-click on GitHub's web UI), then:
- Treat YOUR fork as your source of truth.
- Add YOUR fork as an additional marketplace in Claude Code (`/plugin marketplace add https://github.com/<your-name>/jacob-skills.git`) and Cowork.
- Push your changes to YOUR fork only.
- Periodically rebase or merge from `Xtzj2333/jacob-skills` to pick up Jacob's updates.

### Mirror this rule into shared project CLAUDE.md files

Jacob's `~/.claude/CLAUDE.md` Section 7 says: when a rule is relevant to a collaborator, mirror it into the project's local `CLAUDE.md`. The boundary above is one of those rules. If you and Jacob share a project (e.g., the Bottom-Up Wellbeing manuscript), please add the following block to that project's local `CLAUDE.md`:

```markdown
## Source-of-truth boundary for jacob-skills

Jacob's skills are maintained at `Xtzj2333/jacob-skills` on GitHub. Collaborators have READ access. Do NOT push edits to that repo. Suggest changes via GitHub issues, PRs from a fork, or messages to Jacob — never direct push.
```

---

## Verification checklist

When you're done, all of the below should be true:

- [ ] In Claude Code, `/plugin marketplace list` shows `jacob-skills`
- [ ] In Claude Code, `/plugin list` shows 6 installed plugins from `jacob-skills`
- [ ] In Claude Code, typing `/research-27` offers autocomplete and runs the skill
- [ ] In Cowork, Customize → Personal plugins lists all 6 skills under `jacob-skills`
- [ ] In a fresh Cowork chat, "research 27 something" actually fires research-27
- [ ] `~/.claude/CLAUDE.md` has your manuscript-push values, if applicable (no `USER_NAME` needed — retired 2026-05-10)
- [ ] `/focus` mode is enabled in Claude Code
- [ ] Your shared-project `CLAUDE.md` mirrors the source-of-truth boundary
- [ ] You have NOT cloned-with-write or pushed to `Xtzj2333/jacob-skills`

---

## Troubleshooting

**"Permission denied (publickey)" when adding the marketplace.** You used the `owner/repo` shorthand, which defaults to SSH. Use the full HTTPS URL with `.git` suffix: `https://github.com/Xtzj2333/jacob-skills.git`.

**`/plugin install ...` opens an interactive scope picker.** Pick **User scope** (the default — applies across all your projects, lives in `~/.claude/plugins/`).

**`/reload-plugins` reports `0 skills`.** Counter wording quirk; the plugins are still loaded. Verify by typing `/research-27` and seeing autocomplete.

**Pasting multiple `/plugin install` lines fails.** Claude Code's parser interprets the whole multi-line block as args to the first command. Paste each command on its own line, one at a time.

**Cowork's Personal plugins panel doesn't show a `+` button.** Hover the heading — the button only appears on hover. If it still doesn't appear, your Cowork plan may not support personal marketplaces (this changes over time; check Anthropic's current Cowork docs).

**Skill doesn't fire from natural language.** Trigger explicitly with the slash command first (`/research-27`). If the explicit form works, the auto-trigger phrasing might just need to be more specific.

**Skill writes files named `<role> [<project>].<ext>` and you're not sure what `<project>` should be.** The `project-filename` skill picks the shorthand from (1) any existing `* [*].*` files in the project root, (2) `MAP.md`'s recorded `Shorthand:` line, or (3) generates one from project context. If you want a specific shorthand, name the first file with it (e.g., `todos [myshorthand].md`) and `project-filename` will reuse it after that.

**`tony-github-push` is pushing to Jacob's repo, not yours.** You skipped Part 3.2 — set `MANUSCRIPT_REMOTE` and `MANUSCRIPT_BRANCH` to YOUR repo and branch, not Jacob's.

---

## Quick reference (cheat sheet)

| Action | Command (Claude Code) | Command (Cowork) |
| --- | --- | --- |
| Add marketplace | `/plugin marketplace add https://github.com/Xtzj2333/jacob-skills.git` | Customize → Personal plugins → `+` → Create plugin → Add marketplace → `Xtzj2333/jacob-skills` |
| Install plugin | `/plugin install <name>@jacob-skills` | Customize → Personal plugins → click `+` next to plugin in marketplace |
| Update marketplace | `/plugin update jacob-skills` | Customize → marketplace → Update button (or remove + re-add) |
| List installed | `/plugin list` | Customize → Personal plugins (sidebar) |
| Reload after install | `/reload-plugins` | Restart the Cowork conversation |
| Toggle focus mode | `/focus` | (N/A — Cowork has its own UI) |

---

*Document maintained by Jacob. Suggestions welcome via GitHub issues at `https://github.com/Xtzj2333/jacob-skills/issues` or PRs from a fork. Last updated: 2026-05-09.*
