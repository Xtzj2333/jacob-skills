---
name: markdown-report-builder
description: Build polished `.docx` (via pandoc reference doc) and `.pdf` (via Eisvogel LaTeX template) from a markdown source. Cross-project; one-time setup per project, then `./reports/build.sh report.md` produces a clean Word + PDF pair. Use when Jacob asks to "render this report" / "build a polished version" / "make a docx and pdf of X" — or proactively when producing a multi-page report he'll review.
---

# Markdown report builder

The mechanics for turning one markdown source into a `.docx` + `.pdf` pair. One deliberate standardization, Jacob's call: render, don't rewrite — preserve the source's prose, inline notes, and section markers. Appearance is free — style each report as fits it (Eisvogel YAML options, colors, fonts). The pipeline's defaults are Eisvogel stock for the pdf and the project's `reports/reference.docx` for the docx; that reference file is shared by every report in the project, so per-report docx styling goes through a copy passed with `--reference-doc`, never edits to the shared file.

Skip for: quick notes (chat), apa7/IEEE/ACM-class manuscripts (their own LaTeX classes), and Quarto-feature reports (cross-references, executable code).

**Outward-facing?** If the report will be sent to someone outside the project, invoke `outward-facing-content-pass` on the markdown before building.

## Setup (once per project)

```bash
~/.claude/skills/markdown-report-builder/scripts/setup_project.sh
```

Creates `reports/` with the default reference.docx and a `build.sh` wrapper.

## Build

```bash
./reports/build.sh path/to/report.md    # or the skill's scripts/build_report.sh
```

Outputs land next to the source. Per `reports-catalog`, source + outputs belong in the project's `reports (claude)/` folder, sharing one `s.v_date_slug` prefix and one CATALOG.md row; the `reports/` directory is pipeline infrastructure, not the deliverable home.

## YAML for the source

```yaml
---
title: "Report title"
subtitle: "One-line takeaway"
author: "Drafted by Claude · Reviewed by Jacob"
date: "YYYY-MM-DD"
lang: en-US
fontsize: 11pt
geometry: "margin=1in"
# long reports (~6+ pages) only — under ~5 pages drop these four keys:
titlepage: true
toc: true
toc-own-page: true
toc-depth: 2
---
```

An **outward-facing report Jacob will send** carries his name as author (e.g., `"Jacob Zhang · University of Chicago (Oishi Lab)"`) — AI authorship stays flagged by the folder and catalog, not the title page. If IBM Plex is installed, `mainfont: "IBM Plex Serif"` / `sansfont: "IBM Plex Sans"` / `monofont: "IBM Plex Mono"` may be added.

## Pitfalls

- Backticks in `title:`/`subtitle:` break LaTeX — plain prose there.
- `--listings` is deprecated (pandoc ≥ 3.5); the build script already uses `--syntax-highlighting=idiomatic`.
- Missing TinyTeX packages on a fresh machine: `scripts/install_eisvogel_deps.sh`.
- `footnotes-pretty: true` needs the `footnotebackref` package — install it or drop the key.
