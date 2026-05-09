# jacob-skills

A Claude plugin marketplace bundling Jacob's research and manuscript-revision workflow skills, designed to be installed into both Claude Code and Claude Cowork from a single source.

> **For Jacob's collaborators (Tony et al.):** Jacob put together a full setup guide just for you — see **[COLLABORATOR_SETUP.md](./COLLABORATOR_SETUP.md)**. It walks through installing these skills on both Claude Code and Cowork, configuring `USER_NAME` and the manuscript-push values for *your* repo (not Jacob's), enabling `/focus` mode, and the read-only source-of-truth boundary on Jacob's repo. Hand the file to your Claude Code session and say "follow this end-to-end." Suggestions for these skills are welcome via GitHub issues or PRs from a fork — please don't push directly to this repo.

## Skills

| Plugin | What it does |
|---|---|
| `research-27` | Citation-rich literature-review brief generator. Triggers on "research 27" / `/research-27` only — never on the bare word "research". Includes verify-and-loop verification (fetch sources, run citation-checker, source-tier audit, gap detection). |
| `citation-deepening` | For manuscript citations, pulls verbatim source quotes and surfaces metadata errors as TODOs. |
| `source-quality-check` | Rates each cited reference on venue tier, peer-review status, recency-sensitivity, and author credibility. |
| `commented-edit-roundtrip` | Round-trip editing via Word margin comments. Two modes: perpetual inbox (single .docx the user keeps commenting in forever) and one-shot rewrite (Claude returns the rewrite plus a comments-on-original audit copy). |
| `revision-queue` | Multi-round revision state machine: two coordinated files (open todos + append-only changelog). Pairs with `commented-edit-roundtrip`. |
| `tony-github-push` | Push manuscript edits to a configured remote/branch. Repo URL and branch are read from the user's CLAUDE.md or env, not hardcoded. |

## Install (Claude Code)

```
/plugin marketplace add Xtzj2333/jacob-skills
/plugin install research-27@jacob-skills
/plugin install citation-deepening@jacob-skills
/plugin install source-quality-check@jacob-skills
/plugin install commented-edit-roundtrip@jacob-skills
/plugin install revision-queue@jacob-skills
/plugin install tony-github-push@jacob-skills
```

Then in `/plugin` → Marketplaces → `jacob-skills`, enable auto-update so future commits to this repo propagate on session start.

## Install (Claude Cowork, personal user)

1. Claude Desktop → **Cowork** tab → **Customize** (left sidebar) → **Browse plugins**
2. Switch to the **Personal** tab
3. Click **+** → **Add marketplace from GitHub**
4. Enter `Xtzj2333/jacob-skills`
5. Install each plugin from the marketplace listing

Known caveat: Cowork's personal-tab plugins sometimes lose their installed state on Claude Desktop restart ([anthropics/claude-code#40600](https://github.com/anthropics/claude-code/issues/40600)). The marketplace itself stays connected; you may need a one-click reinstall after restarts until upstream fixes that.

## Update workflow

Edit a `SKILL.md` (or its bundled scripts/templates), commit, push:

```bash
git add . && git commit -m "<change>" && git push
```

Plugin manifests omit `version`, so every commit counts as a new version per [Anthropic's docs](https://code.claude.com/docs/en/plugin-marketplaces#version-resolution-and-release-channels). Claude Code auto-pulls on next session start.

## Layout

```
jacob-skills/
├── .claude-plugin/marketplace.json
├── README.md
└── plugins/
    └── <plugin-name>/
        ├── .claude-plugin/plugin.json
        └── skills/<skill-name>/
            ├── SKILL.md
            └── (optional) scripts/, templates/, ...
```

## License

MIT (or whatever you decide before pushing).
