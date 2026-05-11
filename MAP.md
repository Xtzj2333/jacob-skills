# `jacob-skills` — orientation

A Claude Code plugin marketplace. Lives at `Xtzj2333/jacob-skills` on GitHub. Published as a public marketplace so collaborators (primarily Tony) and Jacob's own machines can install plugins from it.

## Folder structure

```
jacob-skills/
├── .claude-plugin/         ← marketplace metadata (marketplace.json)
├── plugins/                ← one subfolder per plugin (11 plugins as of 2026-05-11)
│   ├── calendar-search/
│   ├── citation-deepening/
│   ├── claude-env-sync/         ← Jacob-internal (sync between Jacob's Macs)
│   ├── commented-edit-roundtrip/
│   ├── project-filename/        ← utility, called by other skills
│   ├── project-map/             ← orientation files (this MAP.md was produced by this skill)
│   ├── research-27/
│   ├── revision-queue/
│   ├── source-quality-check/
│   ├── sync-cowork-skill/       ← Jacob-internal (publishes Cowork-side edits)
│   └── tony-github-push/
├── snapshots/              ← env-sync snapshots from Jacob's machines (jacob_main.json, jacob_jz1.json)
├── _archive/               ← retired material (handoff docs, old plans)
├── README.md               ← top-level intro
├── SKILLS_OVERVIEW.md      ← per-skill detail for collaborators
├── COLLABORATOR_SETUP.md   ← install + configuration walkthrough
├── CHANGELOG.md            ← what changed when
├── LICENSE                 ← license
├── MAP.md                  ← this file
└── (paginated PDF mirrors): SKILLS_OVERVIEW.pdf, COLLABORATOR_SETUP.pdf
```

## Per-plugin layout (inside each `plugins/<name>/`)

Standard claude-code plugin layout:

```
plugins/<name>/
├── .claude-plugin/plugin.json    ← plugin metadata (name, version, description)
├── skills/<skill-name>/SKILL.md  ← one or more skills, each with its own SKILL.md
├── scripts/                      ← (some plugins) Python/bash helpers used by skills
└── commands/                     ← (some plugins) slash commands
```

## How to read this repo

| If you're … | Read this first |
|---|---|
| A collaborator installing for the first time | [COLLABORATOR_SETUP.md](./COLLABORATOR_SETUP.md) |
| A collaborator wanting to know what each skill does | [SKILLS_OVERVIEW.md](./SKILLS_OVERVIEW.md) |
| Curious what changed recently | [CHANGELOG.md](./CHANGELOG.md) |
| Looking at a specific plugin | `plugins/<name>/.claude-plugin/plugin.json` for the description + `plugins/<name>/skills/<skill>/SKILL.md` for the body |

## Plugin status flags

- **Collaborator-facing (8):** `research-27`, `citation-deepening`, `source-quality-check`, `commented-edit-roundtrip`, `revision-queue`, `tony-github-push`, `calendar-search`, `project-map`.
- **Utility called by other skills (1):** `project-filename` (filename convention; not user-triggered).
- **Jacob-internal (2):** `sync-cowork-skill`, `claude-env-sync`. Published in the marketplace for Jacob's own machines but documented as "not useful to collaborators" in `SKILLS_OVERVIEW.md`.

## Git / share status

Public marketplace. All commits land on `main`. Collaborators install via `claude plugins install` pointing at this repo. No protected branches; Jacob is the sole pusher.

## Source / draft flags

Nothing in this repo is `(source)`-flagged. Plugin code, SKILL.md files, and docs are all Jacob-authored (with Claude assistance documented per-commit). Auto-generated artifacts:

- `SKILLS_OVERVIEW.pdf` and `COLLABORATOR_SETUP.pdf` are rendered from the matching `.md` files; the `.md` is the source of truth.

## History

- **2026-05-11** — `MAP.md` created (this file). Reflects 11 plugins, including new `project-map` and renamed `claude-env-sync` v0.3.
- See [CHANGELOG.md](./CHANGELOG.md) for prior history.
