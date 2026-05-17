---
name: markdown-report-builder
description: Build polished `.docx` (via pandoc reference doc) and `.pdf` (via Eisvogel LaTeX template) from a markdown source. Cross-project; one-time setup per project, then `./reports/build.sh report.md` produces a clean Word + PDF pair. Use when Jacob asks to "render this report" / "build a polished version" / "make a docx and pdf of X" — or proactively when producing a multi-page report he'll review.
---

# Markdown report builder

Build polished `.docx` and `.pdf` from a markdown source using established templates — **not** custom-rolled designs. Two outputs from one source:

- `.docx` — uses pandoc's `--reference-doc` mechanism. Styling lives in a project-local `reports/reference.docx` that Jacob customizes once in Word.
- `.pdf` — uses [Eisvogel](https://github.com/Wandmalfarbe/pandoc-latex-template), the most-recommended pandoc LaTeX template (KOMA-Script based, BSD-3 licensed, since 2018). Use Eisvogel's stock styling — do **not** invent custom colors.

## When to use this skill

- Producing any multi-page report Jacob will review (status maps, audit reports, change logs, decision documents, briefs).
- One-time per-project setup of the rendering pipeline.
- Any request like "render this", "give me a polished version", "open the docx + pdf side by side".

## When NOT to use

- Single-paragraph notes or quick lists — paste them inline in chat.
- Manuscripts in apa7/IEEE/ACM/etc. format — those have their own LaTeX classes; use those directly.
- Reports needing Quarto-specific features (cross-references, executable code blocks) — switch to Quarto instead.

## Hard rules

1. **Use established defaults; do not hand-roll aesthetics.** Eisvogel's stock look (KOMA-Script `scrartcl`, Latin Modern fonts, blue rule, light gray) is the established option. Adding custom `titlepage-color`, `titlepage-rule-color`, custom hex picks is **forbidden** unless Jacob explicitly directs the change. When in doubt, fewer YAML keys = better.
2. **Do not modify Jacob's Word styling on his behalf.** The reference.docx lives at `<project>/reports/reference.docx` as the pandoc default. Jacob customizes it once in Word (open the Styles pane, modify each style without renaming). The skill's job ends at generating the default.
3. **Preserve inline notes and section markers** in the source markdown. Don't restructure the prose; just render.

## One-time per-project setup

Run from the project root. Creates `reports/` directory, default reference doc, and the build wrapper.

```bash
~/.claude/skills/markdown-report-builder/scripts/setup_project.sh
```

What this does:
- `mkdir -p reports/`
- `pandoc -o reports/reference.docx --print-default-data-file reference.docx` — generates the default Word styling reference
- Copies `build_report.sh` to `reports/build.sh` for convenient project-local invocation
- Prints next steps (customize reference.docx in Word; install IBM Plex if desired)

## Per-build invocation

```bash
~/.claude/skills/markdown-report-builder/scripts/build_report.sh path/to/report.md [more.md ...]
# OR (after setup): ./reports/build.sh path/to/report.md
```

Both produce `report.docx` and `report.pdf` next to the source.

## YAML metadata for the source markdown

Minimal stock-Eisvogel YAML (recommended — no hand-rolled colors):

```yaml
---
title: "Report title"
subtitle: "One-line takeaway"
author: "Drafted by Claude · Reviewed by Jacob"
date: "YYYY-MM-DD"
lang: en-US
fontsize: 11pt
geometry: "margin=1in"
titlepage: true
toc: true
toc-own-page: true
toc-depth: 2
---
```

That's it. **Don't add** `titlepage-color`, `titlepage-rule-color`, `header-left`, `footer-right` etc. unless Jacob asks for them — Eisvogel's stock defaults are the established aesthetic.

If Jacob has installed IBM Plex (Carbon design system standard, SIL OFL), add:
```yaml
mainfont: "IBM Plex Serif"
sansfont: "IBM Plex Sans"
monofont: "IBM Plex Mono"
```

## Common pitfalls

- **Backticks in `title:` or `subtitle:`** — these break LaTeX rendering. Strip them or use `\\texttt{...}` if you really need code style in metadata. Default: just plain prose in titles.
- **`--listings` flag** — deprecated in pandoc ≥ 3.5. Use `--syntax-highlighting=idiomatic` instead. The skill's build script already does.
- **Missing TinyTeX packages** — Eisvogel pulls many. The skill script handles this in a one-time pass: see `scripts/install_eisvogel_deps.sh` if a fresh machine.
- **`footnotes-pretty: true`** — requires the `footnotebackref` TinyTeX package. If missing, either install it (`tlmgr install footnotebackref`) or remove the YAML key.

## What this skill does NOT do

- **Style the reference.docx** — that's Jacob's hand pass in Word; the skill ships pandoc's default.
- **Install fonts** — IBM Plex etc. require Font Book / sudo; the skill points Jacob at the install step.
- **Custom branding** — corporate templates with logos / specific colors are out of scope. Use Eisvogel's `titlepage-logo` if a project genuinely needs it; otherwise leave stock.

## Origin

Built 2026-05-08 from the Education-Wellbeing project's report-aesthetics task. The scripts and conventions were initially placed at `<Educ-Wellbeing>/reports/` — that was a project/general scope error and the skill location is the correct home.
