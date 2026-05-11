# jacob-skills

A Claude plugin marketplace bundling Jacob's research and manuscript-revision workflow skills, designed to be installed into both Claude Code and Claude Cowork from a single source.

> **For Jacob's collaborators (Tony et al.):** Two docs were written for you specifically:
>
> - **[COLLABORATOR_SETUP.md](./COLLABORATOR_SETUP.md)** — installation walk-through (Claude Code + Cowork), manuscript-push configuration for *your* repo, `/focus` mode setup, and the read-only source-of-truth boundary on this repo.
> - **[SKILLS_OVERVIEW.md](./SKILLS_OVERVIEW.md)** — concise per-skill summary (what / how / when / why) for all skills, plus a typical end-to-end workflow.
> - **[CHANGELOG.md](./CHANGELOG.md)** — recent breaking change (2026-05-10): `USER_NAME` env-var retired; per-project filenames now resolved via the new `project-filename` skill. Read if you upgraded from a pre-2026-05-10 version.
>
> Hand both files to your Claude Code session and say "follow these end-to-end." Suggestions are welcome via GitHub issues or PRs from a fork — please don't push directly to this repo.

## Skills

| Plugin | What it does |
|---|---|
| `research-27` | Citation-rich literature-review brief generator. Triggers on "research 27" / `/research-27` only — never on the bare word "research". Includes verify-and-loop verification (fetch sources, run citation-checker, source-tier audit, gap detection). |
| `citation-deepening` | For manuscript citations, pulls verbatim source quotes and surfaces metadata errors as TODOs. |
| `source-quality-check` | Rates each cited reference on venue tier, peer-review status, recency-sensitivity, and author credibility. |
| `commented-edit-roundtrip` | Round-trip editing via Word margin comments. Two modes: perpetual inbox (single .docx the user keeps commenting in forever) and one-shot rewrite (Claude returns the rewrite plus a comments-on-original audit copy). |
| `revision-queue` | Multi-round revision state machine: two coordinated files (open todos + append-only changelog). Pairs with `commented-edit-roundtrip`. |
| `project-filename` | Per-project output filename convention `<role> [<project>].<ext>`. Invoked by `revision-queue`, `commented-edit-roundtrip`, and `citation-deepening` to resolve filenames consistently across sessions without env-vars. |
| `tony-github-push` | Push manuscript edits to a configured remote/branch. Repo URL and branch are read from the user's CLAUDE.md or env, not hardcoded. |
| `calendar-search` | Multi-calendar Google Calendar lookup with bilingual EN/ZH keyword expansion, chunked windows for noisy calendars, and source-timezone preservation. **Cowork-only** — Jacob does not install on Claude Code (avoids "what's on my calendar" firing in coding sessions). Skill is configured for Jacob's calendar set; fork and adapt the calendar-reference table for your own. |
| `sync-cowork-skill` | Publishes a Cowork-side skill to its marketplace plugin folder with a mandatory diff + sensitive-content scan + explicit confirm gate. Cowork remains the source of truth (read-only here); GitHub is downstream. **Jacob-specific** — hardcoded to `~/jacob-skills/` as the marketplace clone path. Run from Claude Code only. |

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

**Note for `calendar-search`:** install on Cowork only (`/plugin install calendar-search@jacob-skills` from Cowork). Skip on Claude Code unless you actually want calendar lookups firing in coding sessions.

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
