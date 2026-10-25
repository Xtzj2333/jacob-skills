# Jacob's placement-doc format

Set by Jacob's own entries in his Berkeley doc "PhD grad placements" (Drive › Berkeley › Placement) and reused for
Princeton English. Read his latest placement doc before building a new one: he edits these by hand (the Berkeley intro
now opens "终于弄好啦！"), and his edits are the current spec.

## Layout, top to bottom

1. **Table of contents** (native Docs TOC with page numbers; see gdocs-publish.md — it needs a repair step).
2. **Intro paragraph, in Chinese**, one paragraph:
   `近十年（2015–2026）<Program> 毕业了 N 个 PhDs（…）` + the attrition finding in one clause or two (Berkeley's says
   "这里几乎从不fail PhDs"; Princeton's gives 78% / ~18% / ~4% with the source's definition) + `按主导师分组` + the adviser
   rule and its source + the highlight convention + the pending section if any + `职位截至 YYYY 年 M 月：`.
3. **One Heading 2 per adviser**, most primary students first (ties: more co-advised first, then surname):
   `**Ruth Adler**（14 人，另有 1 人共同指导）` — name bold, count normal weight; `（3 人）` when no co-advised;
   `（0 人，另有 1 人共同指导）` for an adviser who is only ever secondary.
4. **Person bullet:** `Leo Brandt (PhD 2016; PI: Ruth)`, or `(PhD 2024; PIs: Ruth & Marcus)` with the primary
   first. First names only; two advisers sharing a first name become `Jeff M.` / `Jeff N.`; `J. Allen Hart` → `J. Allen`.
5. **Job bullets, nested:** `[2016-19] Postdoctoral Fellow, *UCSF*` — years in brackets, title, comma, italic employer,
   optional note in parentheses. **First and last job bold** (title and employer), middle jobs plain; a single job is
   bold. Years: `2016-19`, `2023-` (ongoing), `2026` (one year), `2015-?`, `?-2020`, `?-`, `dates n/a`, `2019-24+`.
   Notes carry what a reader needs: `(started before the PhD)`, `(promotion year not public)`, `(+ Lecturer, SDSU)`,
   `(documented 2025–26)`, `(LinkedIn headline, Oct 2026)`.
6. **Co-advised duplicates:** the full entry again under every secondary adviser, wrapped in yellow highlight
   (`#fff2cc`), with the person line tagged ` — 重复：主导师 Ruth 名下已计（reason）` — reason such as
   `dissertation co-chairs`, `co-advised (CV / homepage)`, `Marcus was committee member / mentor`.
7. **Nothing found:** one bold job line, `[2022-] No placement found publicly (checked Oct 2026)`; for a fresh graduate
   `[2026-] No position found yet (defended May 2026; checked Oct 2026)`.
8. **Pending section last:** `**主导师尚未公开**（10 人：论文尚未入库，列出答辩委员会）`, person lines
   `(PhD 2026; committee: Jeff D., Gayle, Meredith)`.

Within an adviser: primary students by PhD year, then the highlighted duplicates by PhD year.

## people.json (input to scripts/build_gdoc.py)

```json
[{"name": "Daniel Osei", "phd_year": 2019,
  "advisers": ["Helen Park", "Marcus Webb"],
  "adviser_note": "Marcus was committee member / mentor",
  "jobs": [{"years": "2019-21", "title": "Postdoctoral Research Fellow", "employer": "Northwestern University", "note": ""},
           {"years": "2026-", "title": "Associate Professor (with tenure)", "employer": "Washington University in St. Louis", "note": ""}]},
 {"name": "Ana Example", "phd_year": 2026, "advisers": [], "committee": ["Jeff Moreau", "Susan Ortiz"],
  "empty": "[2026-] No position found yet (defended May 2026; checked Oct 2026)"}]
```

`advisers` primary first (`[]` if not public); `committee` only matters when `advisers` is empty; exactly one of `jobs`
or `empty`. `tests/sample_people.json` is a complete example. Keep doc-ready lines in a curated file (Princeton:
`research_notes/scripts/curated.py`, with a `src` note on every line Claude changed versus the agent record) and
generate people.json from it, so agent evidence (`careers/*.jsonl`) and doc wording stay separate.
