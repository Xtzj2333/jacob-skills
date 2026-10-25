---
name: researching-phd-placements
description: Use when Jacob asks where a PhD program's, area's, lab's or adviser's graduates ended up ("do the placements thing for X", "PhD grad placements", a pasted placement, outcomes or degrees-awarded page), whether a program fails or loses PhD students, how one adviser's students compare with others', or wants an existing placement doc or report refreshed, extended or corrected.
---

# Researching PhD placements

## Overview

A placement study is a **census, not a highlight reel**: every graduate in the window, each with an evidenced first job
and current job, grouped by primary adviser, plus how many entrants never finish. What programs publish is a curated,
overwritten summary — use it for leads, never as the answer.

Worked examples live in `~/Claude/Berkeley/PhD placements (Codex)/` (read its MAP.md): Berkeley social-personality
(Codex's research + Claude's cross-check) and `Princeton English (claude)/` (this pipeline end to end, with its report
builder `research_notes/scripts/build_report.py`).

## Defaults — state them in your first message and start; don't wait

- Window: the last ten degree years plus this year's graduates, flagged.
- Home: a new sibling subproject `<Program> (claude)/` in the placements folder (MAP.md + parent-MAP pointer;
  `reports (claude)/` via reports-catalog).
- Deliverables: a Google Doc in Jacob's format next to his other placement docs (Drive › Berkeley › Placement), and a
  companion HTML report + CSV with every source.
- Attrition is always assessed. LinkedIn: snippets only unless the reading account is verified; list what a LinkedIn
  read would settle.
- Ask first only when scope is genuinely ambiguous and changes the denominator (e.g. where a lab's area boundary lies).

## Pipeline

1. **Denominator (you, before any fan-out).** Classify every program page as roster vs outcomes (table in
   references/sources.md). Build `roster.json` from the roster or dissertation records; add people who defended after it
   was updated; for area- or lab-level scopes classify each register name I / I? / E / E? / U with evidence.
2. **Primary adviser from an official record**: repository advisor field → catalog note → dissertation/CV → lab page.
   Committee lists are often alphabetical; never infer primary from order. First-listed (or chair) = primary.
   Not deposited yet → pending section with the committee.
3. **Attrition**: the graduate school's program metrics (completed / left / continuing by entering cohort), department
   cohort sheets; quote the source's definition and denominators.
4. **First-job archaeology**: every Wayback snapshot of the outcomes page (incl. pre-redesign URLs), department
   newsletters and annual reports. Diff each against the current page.
5. **Career fan-out**: references/agent-brief.md. ~20–25 people per agent, ≤5 agents at once, explicit `model`,
   append-as-you-go JSONL, ~15 WebSearch calls each, own Chrome tab, Bing/Yahoo when Google CAPTCHAs. Before writing
   batches, match department lines by full name (`validate_people.py` flags shared surnames).
6. **Curate (you)**: read every record; write doc-ready lines in a curated file with a note on each line you changed;
   reconcile with the department sources; `?` and a note rather than a guess.
7. **Blind accuracy audit**: a fresh agent rebuilds a stratified random sample (≥10 people or 10%, plus every
   low-confidence first job) from scratch, **given only name, year, dissertation and committee — never your answers**
   (a verifier shown the claims confirms them). Compare first and current jobs; if more than ~1 in 10 disagree, fix
   the cause across all records and widen the sample. Report the agreement rate. Open each source behind an audit
   correction yourself before applying it.
8. **Build and publish the doc**: references/gdocs-publish.md — validate, build, upload, **repair heading IDs before the
   TOC, then un-bold the counts the repair re-bolded**, insert TOC, read back and run `check_readback.py`.
9. **Report + CSV**: attrition (with definitions), first/current-job tallies by era, where the department page misleads,
   every person with sources and confidence, method and soft spots by name. Charts via the dataviz skill. Catalog row,
   `chrome-tab open`.

## When the question is one adviser vs the rest

- Spread the focal adviser's students across agent batches (stratify batches by adviser and era), so a weak agent
  can't masquerade as an adviser effect; audit **all** of the focal adviser's students blind, plus the usual sample.
- Show per-person rows, counts with denominators and an era split (hiring freezes, recent graduates not yet placed);
  no rankings or p-values on groups of 5–15.
- Lab-level attrition: track who entered each lab from Wayback snapshots of the graduate-student directory, and code
  each non-finisher by evidence (transferred, master's-out, left, unknown). A name dropping off a page is not evidence.
- Placement data can't speak to mentoring style, current lab size or whether the adviser is taking students; say so.

## Quick reference

Paths are relative to this skill's folder (`~/.claude/skills/researching-phd-placements/`).

| Need | Use |
|---|---|
| Doc format, people.json schema | references/doc-format.md |
| Where each fact comes from; Cloudflare, Wayback, CAPTCHA workarounds | references/sources.md |
| Agent brief + JSONL schema + categories | references/agent-brief.md |
| Upload, heading-ID repair, TOC, replacing a doc | references/gdocs-publish.md |
| `python3 scripts/validate_people.py people.json` | schema, year format, shared first names / surnames |
| `python3 scripts/build_gdoc.py people.json --intro f --out gdoc.html` | the doc HTML (tests: `python3 tests/test_build_gdoc.py`) |
| `bash scripts/upload_gdoc.sh [--replace] gdoc.html "<remote:folder>" "<title>"` | new native Doc; `--replace` refreshes an untouched one under the same link |
| `python3 scripts/check_readback.py readback.md --people N` | TOC links, heading count, count weight, people count |
| `python3 scripts/audit_side_by_side.py people.json audit.jsonl` | step 7: doc vs blind audit per person, with a sort hint |

## Common mistakes

| Mistake | What happened | Instead |
|---|---|---|
| Outcomes page as the denominator or first job | Princeton's page skipped 16 graduates and showed later jobs (MIT, not the Harvard fellowship before it) | roster first; Wayback + newsletters for first jobs |
| Committee order as adviser | Princeton lists committees alphabetically; one entry carried another student's committee | repository advisor field; defense-page committee as a check |
| Surname matching | one Johnson's department line landed on another Johnson | full-name matching; validator warning |
| Anchored verification | a test plan handed its verifier the claimed jobs to confirm | blind sample (step 7) |
| TOC links dead | Drive-imported headings have no IDs; the TOC jumped nowhere | Normal→Heading 2 toggle per heading, then TOC |
| Whole heading bold | the import bolds a Heading 2 unless the count is explicitly normal weight, and the heading-ID repair re-bolds it | builder writes normal weight; un-bold again after the repair; `check_readback.py` fails on it |
| Parallel Google searches | every agent CAPTCHA'd in minutes | Bing/Yahoo in Chrome; never solve a CAPTCHA |
| Dating a forwarded email by guess | an agent dated a department email a year early, shifting first jobs | date it from the jobs' start years |
| Shared adviser first names | "PIs: Jeff & Jeff" | `Jeff M.` / `Jeff N.` (builder does it) |
| Trash + re-upload to refresh a doc | changes the link Jacob has, and loses anything he typed | untouched: `upload_gdoc.sh --replace`; edited: edit in place |
| "No job found" counted as attrition | conflates two questions | attrition only from completion data |
